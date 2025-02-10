from enum import Enum
import os
import random
import asyncio
from typing import Any, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.transforms import Sentinel
from app.models import Issue, IssueStatus, Task, TaskStatus
from app.data_manager import DataManager
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    ToolMessage,
)
from pydantic import BaseModel
from datetime import datetime

# DUMMY_ISSUE = {"status": "ANALYZING", "node_ids": ["n-123"], "summary": ""}

dm = DataManager(project_id=os.environ.get("PROJECT_ID"))


def format_message(message: BaseMessage | list[BaseMessage]) -> str:
    """Helper function to format BaseMessage objects for better display"""

    if isinstance(message, list) and len(message) > 0:
        langchain_message = message[0]
    else:
        langchain_message = message

    if isinstance(langchain_message, AIMessage):
        return f"[LLM]: {langchain_message.content} (Tool call: {langchain_message.tool_calls})"
    elif isinstance(langchain_message, ToolMessage):
        return f"[Tool:{langchain_message.name}]: {langchain_message.content}"
    else:
        try:
            return (
                f"[{langchain_message.__class__.__name__}]: {langchain_message.content}"
            )
        except:
            return str(langchain_message)


async def get_sample_issue() -> Issue:
    return await dm.get_issue("081168e3-6309-4b30-9526-18d66e1767b1")


async def get_issue(issue_id: str) -> Issue:
    return await dm.get_issue(issue_id)


async def check_issue_status(issue_id: str) -> str:
    issue = await dm.get_issue(issue_id)
    if issue:
        return issue.status
    else:
        raise ValueError("Issue does not exist")


async def update_issue_status_and_summary(
    issue_id: str, status: IssueStatus, summary: str
) -> bool:
    return await dm.update_issue(
        issue_id,
        {
            "status": status,
            "summary": summary,
            "updated_at": datetime.now(),
        },
    )


async def update_issue_status(issue_id: str, status: IssueStatus) -> bool:
    return await dm.update_issue(
        issue_id,
        {"status": status, "updated_at": datetime.now()},
    )


async def get_current_issue_tasks(issue_id: str) -> list[Task]:
    issue = await dm.get_issue(issue_id)
    tasks = issue.tasks if issue and issue.tasks else []
    return tasks


async def set_issue_tasks(issue_id: str, tasks: list[Task]) -> bool:
    return await dm.update_issue(issue_id, {"tasks": tasks})


def strip_markdown(text: str) -> str:
    return text.replace("```json", "```").replace("```python", "```").replace("```", "")
