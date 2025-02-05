import vertexai
import logging
import os

from time import sleep
from typing import Literal, Optional
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    SystemMessage,
    AIMessage,
    ToolMessage,
)
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from langgraph.checkpoint.memory import MemorySaver
from langgraph.store.memory import InMemoryStore
from langgraph.types import StateSnapshot

from langgraph.graph import END, MessageGraph
from langgraph.prebuilt import ToolNode

from app.models import Issue
from llm.utils import (
    check_issue_status,
    get_issue,
    update_issue_status_and_summary,
    update_issue_status,
    format_message,
    sample_issue,
)
from llm.tools import (
    monitor_node_metrics,
    finish_and_resolve_issue,
    finish_and_escalate,
    deactivate_ca,
    change_dss,
)
from llm.task_agent import activate_mlb

logger = logging.getLogger(__name__)

SYSTEM_INSTRUCTION_DUMMY = """
You are a RAN operator assistant who helps fix network capacity and performance issues by reconfiguring RAN nodes. 

You always use the following remediation plan:

# Remediation plan
1. Activate MLB of a node
2. Deactivate CA of a node
3. Monitor RRC_success_rate metric for the next 15 minutes. If it's above or equal 80%, finish and consider the issue resolved. If it's below 80%, proceed to step 4.
4. Change DSS
5. Monitor RRC_success_rate metric for the next 15 minutes. If it's above or equal 80%, finish and consider the issue resolved. If it's below 80%, escalate.


You have the following tools at your disposal: 

## Utility tools
1. monitor_node_metrics(node_id): monitor node performance metrics for the next 15 minutes and get results.
2. finish_and_resolve_issue(issue_id, summary): finish and mark the issue as resolved
3. finish_and_escalate(issue_id, summary): finish due to any error with the tools or because performance metrics were not satisfactory after all steps.
## Node action tools
4. activate_mlb(node_id)
5. deactivate_ca(node_id)
6. change_dss(node_id)

Guidelines:
- Do not execute tools in parallel. You can only run one tool at a time always.
- You do not need to monitor RRC_success_rate after activating MLB of a node.
- Always follow the remediation plan. You are not to deviate from this sequence of steps at any time. If a tool fails at any point, simply end and escalate the issue by using the tool finish_and_escalate as your final action.

"""

AUTOMATIC_TOOLS = [
    "monitor_node_metrics",
    "activate_mlb",
    "deactivate_mlb",
    "activate_ca",
    "deactivate_ca",
    "change_dss",
    "finish_and_resolve_issue",
    "finish_and_escalate",
]

MANUAL_TOOLS = ["change_tilt", "decrease_power"]


class ReasoningAgent:
    def __init__(
        self,
        project: str,
        location: str,
        issue: Issue,
        staging_bucket: Optional[str] = None,
    ) -> None:
        self.project_id = project
        self.location = location
        self.issue = issue
        self.chat_history = [
            SystemMessage(content=SYSTEM_INSTRUCTION_DUMMY),
            HumanMessage(
                content=f"Proceed with remediation for issue ID {issue.issue_id} affecting node ID {issue.node_ids[0]}"
            ),
        ]
        self.runnable = None
        self.config = {"configurable": {"thread_id": 1}}

        if staging_bucket and not staging_bucket.startswith("gs://"):
            staging_bucket = f"gs://{staging_bucket}"

        # Initialize Vertex AI client library
        logger.debug("Initializing Vertex AI client library...")
        vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    def set_up(self) -> None:
        logger.debug("Setting up workflow graph...")
        model = ChatVertexAI(
            model="gemini-1.5-pro",
            safety_settings={
                HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            },
        )

        builder = MessageGraph()

        model_with_tools = model.bind_tools(
            [
                monitor_node_metrics,
                finish_and_resolve_issue,
                finish_and_escalate,
                activate_mlb,
                deactivate_ca,
                change_dss,
            ]
        )
        builder.add_node("main_agent", model_with_tools)

        tool_node = ToolNode(
            [
                monitor_node_metrics,
                finish_and_resolve_issue,
                finish_and_escalate,
                activate_mlb,
                deactivate_ca,
                change_dss,
            ]
        )
        builder.add_node("tools", tool_node)
        builder.add_conditional_edges("main_agent", self._router)
        builder.add_edge("tools", "main_agent")
        builder.add_edge("tools", END)

        builder.set_entry_point("main_agent")

        logger.debug("Compiling graph...")
        self.runnable = builder.compile(
            checkpointer=MemorySaver(), store=InMemoryStore()
        )

    def get_checkpoint(self) -> StateSnapshot:
        """Get the current state of the agent."""

        return self.runnable.get_state(self.config)

    def load_checkpoint(self, checkpoint: StateSnapshot):
        """Load the given checkpoint into the agent's config."""
        self.config = checkpoint.config

    def get_chat_history(self) -> list[BaseMessage]:
        """Get the current chat history excluding the latest message entry"""
        history = self.chat_history.copy()
        history.pop()
        return history

    def load_chat_history(self, chat_history: list[BaseMessage]):
        """Load the given chat history into the agent."""
        self.chat_history = chat_history

    def run_workflow(self) -> list[BaseMessage]:
        """Run the agent's LangGraph workflow and returns new messages since starting history"""
        if not self.runnable:
            raise RuntimeError("Agent not set up. Call set_up() first.")

        new_messages = []
        try:
            for output_dict in self.runnable.stream(
                self.chat_history, config=self.config
            ):
                for _, output in output_dict.items():
                    logger.info(format_message(output))
                    if isinstance(
                        output, (SystemMessage, HumanMessage, AIMessage, ToolMessage)
                    ):
                        if any([output.content, output.tool_calls]):
                            new_messages.append(output)
                        else:
                            logger.warning("Got an empty message")
                    elif (
                        isinstance(output, list)
                        and len(output)
                        and isinstance(output[0], ToolMessage)
                    ):
                        new_messages.append(output[0])

                    else:
                        logger.warning(
                            f"Got an unexpected message of type {type(output)}\n. Message: {output}\n\n"
                        )

            if self.chat_history:
                self.chat_history.extend(new_messages)
            else:
                self.chat_history = new_messages

            return new_messages
        except Exception:
            logger.error(f"Error during query execution", exc_info=True)
            raise

    def _router(
        self,
        state: list[BaseMessage],
    ) -> Literal[
        "tools",
        "__end__",
    ]:
        """Defines the conditional routing logic for the agent."""
        # Get the tool_calls from the last message in the conversation history.
        tool_calls = state[-1].tool_calls
        issue_id = self.issue.issue_id

        # If there are any tool_calls
        if len(tool_calls):
            tool_name = tool_calls[0]["name"]
            if (
                tool_name == "monitor_node_metrics"
                and check_issue_status(issue_id) != "monitoring"
            ):
                update_issue_status(issue_id, "monitoring")
                logger.info("[Router] End of workflow")
                return END

            if tool_name in AUTOMATIC_TOOLS:
                if check_issue_status(issue_id) == "monitoring":
                    update_issue_status(issue_id, "analyzing")

                logger.info(f"[Router] Routing to tool ({tool_name})")
                return "tools"
            else:
                if check_issue_status(issue_id) == "approved":
                    logger.info(f"[Router] Routing to tool ({tool_name})")
                    return "tools"
                elif check_issue_status(issue_id) == "analyzing":
                    print(
                        f"[Router] Tool is not approved for execution. Updating Issue status to pending approval..."
                    )
                    update_issue_status(issue_id, "pending_approval")
                    logger.info("[Router] End of workflow")
                    return END

                elif check_issue_status(issue_id) in ["rejected", "pending_approval"]:
                    print(
                        f"[Router] Issue was rejected or is still pending approval. Will not execute tool."
                    )
                    logger.info("[Router] End of workflow")
                    return END

        else:
            # End the conversation flow.
            logger.info("[Router] No tool call found. Ending workflow.")
            return END


if __name__ == "__main__":

    logging.basicConfig(
        filename="agent.log",
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    a = ReasoningAgent(
        project="de1000-dev-mwc-ran-agent", location="us-central1", issue=sample_issue
    )
    a.set_up()
    print(f">> Issue state:\n {sample_issue}\n")
    a.run_workflow()
    # Save state before interruption
    checkpoint = a.get_checkpoint()
    history = a.get_chat_history()

    logger.info("Monitoring...")
    sleep(5)
    logger.info("Continuing...")
    issue = get_issue(sample_issue.issue_id)
    logger.info(f">> Issue state:\n {issue}\n")

    new_agent = ReasoningAgent(
        project="de1000-dev-mwc-ran-agent",
        location="us-central1",
        issue=get_issue(sample_issue.issue_id),
    )
    new_agent.set_up()
    new_agent.load_checkpoint(checkpoint)
    new_agent.load_chat_history(history)

    # Continue the workflow
    new_agent.run_workflow()

    issue = get_issue(sample_issue.issue_id)
    logger.info(f">> Issue state:\n {issue}\n")

    checkpoint = new_agent.get_checkpoint()
    history = new_agent.get_chat_history()

    ## Final stage

    logger.info("Monitoring...")
    sleep(5)
    logger.info("Continuing...")
    new_agent = ReasoningAgent(
        project="de1000-dev-mwc-ran-agent",
        location="us-central1",
        issue=get_issue(sample_issue.issue_id),
    )
    new_agent.set_up()
    new_agent.load_checkpoint(checkpoint)
    new_agent.load_chat_history(history)

    # Continue the workflow
    new_agent.run_workflow()

    issue = get_issue(sample_issue.issue_id)
    logger.info(f">> Final Issue state:\n {issue}\n")
