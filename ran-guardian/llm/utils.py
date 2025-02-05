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


def get_sample_issue() -> Issue:
    issues = asyncio.run(dm.get_issues())
    issue = random.choice(issues)
    issue.status = IssueStatus.ANALYZING
    return issue


def get_issue(issue_id: str) -> Issue:
    return asyncio.run(dm.get_issue(issue_id))


def check_issue_status(issue_id: str) -> str:
    issue = asyncio.run(dm.get_issue(issue_id))
    if issue:
        return issue.status
    else:
        raise ValueError("Issue does not exist")


def update_issue_status_and_summary(
    issue_id: str, status: IssueStatus, summary: str
) -> bool:
    return asyncio.run(
        dm.update_issue(
            issue_id,
            {
                "status": status,
                "summary": summary,
                "updated_at": firestore.SERVER_TIMESTAMP,
            },
        )
    )


def update_issue_status(issue_id: str, status: IssueStatus) -> bool:
    return asyncio.run(
        dm.update_issue(
            issue_id,
            {"status": status, "updated_at": firestore.SERVER_TIMESTAMP},
        )
    )


def strip_markdown(text: str) -> str:
    return text.replace("```json", "```").replace("```python", "```").replace("```", "")


sample_issue = get_sample_issue()
