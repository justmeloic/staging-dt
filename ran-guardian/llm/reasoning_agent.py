import json
import logging
import os
from datetime import datetime
from time import sleep
from typing import Literal, Optional

import vertexai
from app.models import AgentHistory, Issue, Task, TaskStatus
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_google_vertexai import ChatVertexAI, HarmBlockThreshold, HarmCategory
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessageGraph
from langgraph.prebuilt import ToolNode
from langgraph.store.memory import InMemoryStore
from langgraph.types import StateSnapshot
from llm.logger import AgentWorkflowLogger
from llm.prompt_manager import PromptManager
from llm.task_agent import (
    activate_mlb,
    change_dss,
    deactivate_ca,
    deactivate_pdcch_power_boost,
    decrease_power,
    enhance_dsplit_threshold,
    enhance_resource_allocation,
    increase_tilt_value,
)
from llm.tools import (
    finish_and_escalate,
    finish_and_resolve_issue,
    monitor_node_metrics,
)
from llm.utils import (
    check_issue_status,
    format_message,
    strip_markdown,
    update_issue_status,
)

log_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

AUTOMATIC_TOOLS = [
    "monitor_node_metrics",
    "activate_mlb",
    "deactivate_mlb",
    "activate_ca",
    "deactivate_ca",
    "change_dss",
    "deactivate_pdcch_power_boost",
    "enhance_dsplit_threshold",
    "enhance_resource_allocation",
    "finish_and_resolve_issue",
    "finish_and_escalate",
]

UTILITY_TOOLS = [
    "monitor_node_metrics",
    "finish_and_resolve_issue",
    "finish_and_escalate",
]

MANUAL_TOOLS = ["increase_tilt_value", "decrease_power"]

TASK_TOOLS = (set(AUTOMATIC_TOOLS) | set(MANUAL_TOOLS)) - set(UTILITY_TOOLS)

pm = PromptManager()


class ReasoningAgent:
    """
    A reasoning agent for managing and resolving network issues.

    This agent uses a LangGraph workflow to determine and execute remediation actions
    for a given network issue. It interacts with other, task-specific LLM Agents, that run
    actions against a RAN node. The Reasoning Agent oversees the entire remediation workflow.
    """

    def __init__(
        self,
        project: str,
        location: str,
        issue: Issue,
        node_id: str,
        staging_bucket: Optional[str] = None,
    ) -> None:
        """
        Initializes the ReasoningAgent.

        Args:
            project: The Google Cloud project ID.
            location: The location of the Vertex AI resources.
            issue: The network issue to be addressed.
            node_id: The ID of the affected node.
            staging_bucket: Optional staging bucket for Vertex AI.
        """
        self.project_id = project
        self.location = location
        self.issue = issue
        self.chat_history = [
            SystemMessage(content=pm.get_prompt("main_agent")),
            HumanMessage(
                content=f"Proceed with remediation for issue ID {issue.issue_id} affecting node ID {node_id}"
            ),
        ]
        self.tasks = []
        self.runnable = None
        self.config = {"configurable": {"thread_id": self.issue.issue_id}}
        self.gcs_logger = AgentWorkflowLogger(
            bucket_name=os.environ.get("BUCKET_NAME", "ran-guardian-data"),
            logs_location=os.environ.get("AGENT_LOGS_LOCATION", "agent-logs"),
            issue_id=issue.issue_id,
            node_id=node_id,
            agent_name="SUPERVISOR AGENT",
        )

        if staging_bucket and not staging_bucket.startswith("gs://"):
            staging_bucket = f"gs://{staging_bucket}"

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

        if os.environ.get("DEBUG_REASONING_AGENT", "false") == "true":
            self.handler = logging.FileHandler(
                f"agent_{issue.issue_id}_{node_id}.log", mode="a"
            )
            self.handler.setFormatter(log_formatter)
            self.logger.addHandler(self.handler)

        # Initialize Vertex AI client library
        self.logger.debug("Initializing Vertex AI client library...")
        vertexai.init(project=project, location=location, staging_bucket=staging_bucket)

    def set_up(self) -> None:
        """Sets up the LangGraph workflow and the LLM model."""
        self.logger.debug("Setting up workflow graph...")
        model = ChatVertexAI(
            model=os.environ.get("GEMINI_MODEL_NAME", "gemini-2.0-flash"),
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
                deactivate_pdcch_power_boost,
                enhance_dsplit_threshold,
                enhance_resource_allocation,
                increase_tilt_value,
                decrease_power,
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
                deactivate_pdcch_power_boost,
                enhance_dsplit_threshold,
                enhance_resource_allocation,
                increase_tilt_value,
                decrease_power,
            ]
        )
        builder.add_node("tools", tool_node)
        builder.add_conditional_edges("main_agent", self._router)
        builder.add_edge("tools", "main_agent")
        builder.add_edge("tools", END)

        builder.set_entry_point("main_agent")

        self.logger.debug("Compiling graph...")
        self.runnable = builder.compile(
            checkpointer=MemorySaver(), store=InMemoryStore()
        )

    async def get_snapshot(self) -> StateSnapshot:
        """
        Retrieves the current state of the agent's workflow.

        Returns:
            A StateSnapshot object representing the current state.
        """
        return await self.runnable.aget_state(self.config)
        # return self.runnable.get_state(self.config)

    def get_history(self) -> AgentHistory:
        """
        Retrieves the chat and task history of the agent.

        Returns:
            An AgentHistory object containing the chat and task history.
        """
        return AgentHistory(
            chat_history=self._get_chat_history(),
            task_history=self.tasks,
        )

    def load_state(
        self, snapshot: StateSnapshot, history: Optional[AgentHistory] = None
    ):
        """
        Loads a previously saved state into the agent.

        Args:
            snapshot: The StateSnapshot object to load.
            history (Optional): The AgentHistory object to load.
        """
        self._load_snapshot(snapshot)
        if history:
            self._load_chat_history(history.chat_history)
            self._load_task_history(history.task_history)

    def _load_snapshot(self, snapshost: StateSnapshot):
        """Loads the given checkpoint into the agent's config."""

        self.config = snapshost.config
        self.logger.info(f"Loaded config {self.config}")

    def _get_chat_history(self) -> list[BaseMessage]:
        """Returns a copy of the chat history excluding the last message."""
        history = self.chat_history.copy()
        history.pop()
        return history

    def _load_chat_history(self, chat_history: list[BaseMessage]):
        """Loads the given chat history into the agent."""
        self.chat_history = chat_history

    def get_task_history(self) -> list[Task]:
        """Returns the task history of the agent."""
        return self.tasks

    def _load_task_history(self, tasks: list[Task]):
        """Loads the given task history into the agent."""
        self.tasks = tasks.copy() if tasks else []

    def update_task(self, task: Task) -> None:
        """Updates or adds a task to the task history."""
        for i, tsk in enumerate(self.tasks):
            if tsk.name == task.name:  # task already in the list, just update values
                self.tasks[i] = task
                return
        self.tasks.append(task)

    async def run_workflow(self) -> list[BaseMessage]:
        """
        Runs the agent's LangGraph workflow.

        Returns:
            A list of new messages generated during the workflow execution.
        """
        if not self.runnable:
            raise RuntimeError("Agent not set up. Call set_up() first.")

        new_messages = []
        try:
            async for output_dict in self.runnable.astream(
                self.chat_history, config=self.config
            ):
                for _, output in output_dict.items():
                    self.logger.info(format_message(output))
                    self.gcs_logger.log(format_message(output))
                    if isinstance(
                        output, (SystemMessage, HumanMessage, AIMessage, ToolMessage)
                    ):
                        if any([output.content, output.tool_calls]):
                            new_messages.append(output)
                        else:
                            self.logger.warning("Got an empty message")

                        if isinstance(output, ToolMessage):
                            self._process_task_tool_response(output[0])

                    elif (
                        isinstance(output, list)
                        and len(output)
                        and isinstance(output[0], ToolMessage)
                    ):

                        new_messages.append(output[0])

                        self._process_task_tool_response(output[0])

                    elif isinstance(output, list) and not len(output):
                        self.logger.warning("Got an empty list as response")

                    else:
                        self.logger.warning(
                            f"Got an unexpected message of type {type(output)}\n. Message: {output}\n\n"
                        )

            if self.chat_history:
                self.chat_history.extend(new_messages)
            else:
                self.chat_history = new_messages

            self.gcs_logger.save_to_gcs()

            return new_messages
        except Exception:
            logger.error(f"Error during query execution", exc_info=True)
            raise

        finally:
            # Write buffered logs to GCS
            self.gcs_logger.save_to_gcs()

    def _process_task_tool_response(self, response: ToolMessage) -> Task:
        """Inspect the tool response and update task history accordingly"""
        tool_name = response.name

        if tool_name not in TASK_TOOLS:
            return None  # not a Task tool

        task_status = TaskStatus.DONE
        try:
            response_dict = json.loads(strip_markdown(response.content))

            success = response_dict["success"]
            if not success:
                task_status = TaskStatus.FAILED
        except Exception as e:  # tool response did not include a success field
            self.logger.warning(
                f"Couldn't parse tool output to check if it was successful"
            )
            success = (
                response.status == "success"
            )  # will be the case if the tool invocation itself succeeded
            if success:
                # Tool Invocation succeeded but we can't be sure that the execution was successful
                self.logger.warning(
                    f"It's possible that task {response.name} did not succeed"
                )
                task_status = TaskStatus.DONE
            else:
                # Here we know for sure it failed
                task_status = TaskStatus.FAILED

        try:
            commands = json.loads(response.content)["commands"]
        except:
            commands = None

        task = Task(
            name=response.name,
            status=task_status,
            node_id=self.issue.node_ids[0],
            executed_at=datetime.now(),
            commands=commands,
        )

        self.update_task(task)

        return task

    async def _router(
        self,
        state: list[BaseMessage],
    ) -> Literal["tools", "__end__",]:
        """
        Defines the routing logic for the LangGraph workflow.

        Args:
            state: The current state of the conversation.

        Returns:
            The next node in the workflow to execute.
        """
        # Get the tool_calls from the last message in the conversation history.
        tool_calls = state[-1].tool_calls
        issue_id = self.issue.issue_id

        if not tool_calls and len(state) > 1:
            try:
                tool_calls = state[-2].tool_calls
                self.logger.warning(
                    "No tool calls but the message before was a tool call"
                )
                state.pop()  # remove from state
                self.chat_history.pop()  # remove from history
            except:
                pass

        issue_status = await check_issue_status(issue_id)

        if issue_status == "resolved":
            self.logger.info(
                "[Issue: {issue_id} | Main agent | Router] Issue already resolved."
            )
            return END

        # If there are any tool_calls
        if len(tool_calls):
            tool_name = tool_calls[0]["name"]

            if tool_name in TASK_TOOLS and issue_status not in [
                "pending_approval",
                "rejected",
                "resolved",
                "escalate",
            ]:
                self.update_task(
                    Task(
                        name=tool_name,
                        node_id=self.issue.node_ids[0],
                        status=TaskStatus.EXECUTING,
                    )
                )

            # Check if we're about to enter monitoring phase
            if tool_name == "monitor_node_metrics" and issue_status != "monitoring":
                await update_issue_status(issue_id, "monitoring")
                self.logger.info(
                    "[Issue: {issue_id} | Main agent | Router] Updating issue status to monitoring. End of workflow"
                )
                self.gcs_logger.log("[Router] Updating issue status to monitoring")
                return END

            if tool_name in AUTOMATIC_TOOLS:
                if (
                    issue_status == "pending_approval"
                ):  # Whole workflow was pending approval to start. This scenario shouldn't happen, but handle it anyway
                    self.gcs_logger.log("[Router] Approval is pending. End of workflow")
                    return END

                if issue_status == "monitoring":
                    self.logger.info(
                        "[Issue: {issue_id} | Main agent | Router] Resuming workflow for node after monitoring"
                    )
                    self.gcs_logger.log("[Router] Updating issue status to analyzing")
                    await update_issue_status(issue_id, "analyzing")

                self.logger.info(
                    f"[Issue: {issue_id} | Main agent | Router] Routing to tool ({tool_name})"
                )
                return "tools"
            else:  # TOOLS THAT REQUIRE APPROVAL
                if issue_status == "approved":
                    self.logger.info(
                        f"[Issue: {issue_id} | Main agent | Router] Routing to tool ({tool_name})"
                    )

                    return "tools"
                elif issue_status == "analyzing":
                    self.logger.info(
                        f"[Issue: {issue_id} | Main agent | Router] Tool is not approved for execution. Updating Issue status to pending approval..."
                    )

                    self.gcs_logger.log(
                        "[Router] Tool is not approved for execution. Updating Issue status to pending approval..."
                    )
                    await update_issue_status(issue_id, "pending_approval")
                    self.logger.info(
                        f"[Issue: {issue_id} | Main agent | Router] End of workflow"
                    )

                    self.gcs_logger.log(
                        "[Router] Tool is not approved for execution. End of workflow"
                    )
                    return END

                elif issue_status in ["rejected", "pending_approval", "escalate"]:
                    print(
                        f"[Issue: {issue_id} | Main agent | Router] Issue status is {issue_status}. Will not execute tool."
                    )
                    self.logger.info("[Router] End of workflow")
                    self.gcs_logger.log(
                        f"[Router] Issue status is {issue_status}. Will not execute tool."
                    )
                    return END

        else:
            # End the conversation flow.
            self.logger.info(
                f"\n\n[Issue: {issue_id} | Main agent | Router] No tool call found. Last Message: {state[-1]}"
            )
            self.gcs_logger.log(f"[Router] No tool call found. Ending workflow")
            return END
