import os
import random
import asyncio
from google.cloud import firestore
from app.models import Issue, IssueStatus
from app.data_manager import DataManager
from langchain_core.messages import (
    BaseMessage,
    AIMessage,
    ToolMessage,
)


# DUMMY_ISSUE = {"status": "ANALYZING", "node_ids": ["n-123"], "summary": ""}

dm = DataManager(project_id=os.environ.get("PROJECT_ID"))


def format_message(message: BaseMessage | list[BaseMessage]) -> str:
    """Helper function to format BaseMessage objects for better display"""
    print(message)

    if isinstance(message, list):
        message = message[0]

    if isinstance(message, AIMessage):
        return f"[Agent]: {message.content} (Tool call: {message.tool_calls})"
    elif isinstance(message, ToolMessage):
        return f"[Tool:{message.name}]: {message.content}"
    else:
        try:
            return f"[{message.__class__.__name__}]: {message.content}"
        except:
            return str(message)


async def get_sample_issue() -> Issue:
    issues = await dm.get_issues()
    issue = random.choice(issues)
    issue.status = IssueStatus.ANALYZING
    return issue


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
            "updated_at": firestore.SERVER_TIMESTAMP,
        },
    )


async def update_issue_status(issue_id: str, status: IssueStatus) -> bool:
    return await dm.update_issue(
        issue_id,
        {"status": status, "updated_at": firestore.SERVER_TIMESTAMP},
    )


def strip_markdown(text: str) -> str:
    return text.replace("```json", "```").replace("```python", "```").replace("```", "")
