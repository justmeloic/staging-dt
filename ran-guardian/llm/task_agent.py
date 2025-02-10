import logging
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
from langchain_core.tools import tool

from langgraph.graph import END, MessageGraph
from langgraph.prebuilt import ToolNode

from llm.tools import run_node_command
from llm.utils import strip_markdown
from llm.prompt_manager import PromptManager


prompt_manager = PromptManager()

logger = logging.getLogger(__name__)


class TaskAgent:
    """Class for a task-specific AI agent with access to a remote node command execution tool."""

    def __init__(
        self,
        system_instructions: str,
        node_id: str,
        model_name: Optional[str] = "gemini-1.5-flash",
    ) -> None:
        self.model_name = model_name
        self.chat_history = [
            SystemMessage(content=system_instructions),
            HumanMessage(content=f"Proceed with remediation for node ID {node_id}"),
        ]
        self.runnable = None
        self.config = {"configurable": {"thread_id": 1}}

    def set_up(self) -> None:
        model = ChatVertexAI(
            model=self.model_name,
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
                run_node_command,
            ]
        )
        builder.add_node("agent", model_with_tools)

        tool_node = ToolNode(
            [
                run_node_command,
            ]
        )
        builder.add_node("tools", tool_node)
        builder.add_conditional_edges("agent", self._router)
        builder.add_edge("tools", "agent")
        builder.add_edge("tools", END)

        builder.set_entry_point("agent")

        self.runnable = builder.compile(
            checkpointer=MemorySaver(), store=InMemoryStore()
        )

    def run_workflow(self):
        """Run the agent workflow"""
        if not self.runnable:
            raise RuntimeError("Agent not set up. Call set_up() first.")

        new_messages = []
        try:
            for output_dict in self.runnable.stream(
                self.chat_history, config=self.config
            ):
                for key, output in output_dict.items():
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
        except Exception as e:
            logger.error(f"Error during query execution", exc_info=True)
            raise

    def _router(
        self,
        state: list[BaseMessage],
    ) -> Literal[
        "tools",
        "__end__",
    ]:
        # Get the tool_calls from the last message in the conversation history.
        tool_calls = state[-1].tool_calls

        # If there are any tool_calls
        if len(tool_calls):
            tool_name = tool_calls[0]["name"]
            logger.info(f"[MLB Agent:Router] Routing to tool ({tool_name})")
            return "tools"

        else:
            # End the conversation flow.
            logger.info("[MLB Agent:Router]  Ending workflow")
            return END


@tool
def activate_mlb(node_id: str) -> str:
    """Activate MLB of a node"""
    activate_mlb_prompt = prompt_manager.get_prompt("activate_mlb", node_id=node_id)
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def deactivate_ca(node_id: str) -> str:
    """Deactivate CA for a node"""
    activate_mlb_prompt = prompt_manager.get_prompt("deactivate_ca", node_id=node_id)
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def change_dss(node_id: str) -> str:
    """Change DSS for a node"""
    activate_mlb_prompt = prompt_manager.get_prompt("change_dss", node_id=node_id)
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def deactivate_pdcch_power_boost(node_id: str) -> str:
    """Deactivate PDCCH Power Boost for node"""
    activate_mlb_prompt = prompt_manager.get_prompt(
        "deactivate_pdcch_power_boost", node_id=node_id
    )
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def enhance_dsplit_threshold(node_id: str) -> str:
    """Enhance dsplitThreshold for node"""
    activate_mlb_prompt = prompt_manager.get_prompt(
        "enhance_dsplit_threshold", node_id=node_id
    )
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def enhance_resource_allocation(node_id: str) -> str:
    """Enhance resource allocation for node"""
    activate_mlb_prompt = prompt_manager.get_prompt(
        "enhance_resource_allocation", node_id=node_id
    )
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def increase_tilt_value(node_id: str) -> str:
    """Increase cell tilt value"""
    activate_mlb_prompt = prompt_manager.get_prompt(
        "increase_tilt_value", node_id=node_id
    )
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


@tool
def decrease_power(node_id: str) -> str:
    """Decrease cell power"""
    activate_mlb_prompt = prompt_manager.get_prompt("decrease_power", node_id=node_id)
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id=node_id)
    try:
        agent.set_up()
        messages = agent.run_workflow()
        response = strip_markdown(messages[-1].content)
        return response
    except:
        logger.error("Failed to execute task", exc_info=True)
        raise


if __name__ == "__main__":
    activate_mlb_prompt = prompt_manager.get_prompt("activate_mlb")
    agent = TaskAgent(system_instructions=activate_mlb_prompt, node_id="n-123")
    agent.set_up()
    messages = agent.run_workflow()
    print(messages[-1].content)
