import random
from langchain_core.tools import tool
from llm.utils import update_issue_status, update_issue_status_and_summary


### Tools ###


@tool
def get_node_information(node_id: str) -> dict:
    """Retrieve performance metrics and operational data for node.."""
    data = {
        "RRC_success_rate_percentage": random.random() * 100,
        "status": "RUNNING",
    }
    return data


@tool
def monitor_node_metrics(node_id: str) -> dict:
    """Mnitor node performance metrics for the next 15 minutes and get results."""
    data = {
        "RRC_success_rate_percentage": random.random() * 100,
        "status": "RUNNING",
    }
    return data


@tool
def finish_and_resolve_issue(issue_id: str, summary: str) -> str:
    """Finish and mark the issue as resolved."""
    update_issue_status_and_summary(issue_id, "resolved", summary)

    return "Issue resolved"


@tool
def finish_and_escalate(issue_id: str, summary: str) -> str:
    """Finish and mark the issue as escalated."""

    update_issue_status_and_summary(issue_id, "escalate", summary)

    return "Issue escalated"


@tool
def activate_mlb(node_id: str) -> dict:
    """Activate MLB of a node"""

    return {
        "commands": [
            "set CXC4011944 FeatureState 1",
            "set . targetloadawarelbdar true",
            "set . mediumhighloadthreshold 2000",
        ],
        "rollback_commands": [
            "set CXC4011944 FeatureState 0",
            "set . targetloadawarelbdar false",
            "set . mediumhighloadthreshold 500",
        ],
        "summary": "Successfully activated MLB",
        "success": True,
    }


@tool
def deactivate_ca(node_id: str) -> dict:
    """Deactivate CA of a node"""

    return {
        "commands": [
            "set ca false",
        ],
        "rollback_commands": ["set ca true"],
        "summary": "Successfully deactivated CA",
        "success": True,
    }


@tool
def change_dss(node_id: str) -> dict:
    """Change DSS for a node"""

    return {
        "commands": [
            "set dss 1",
        ],
        "rollback_commands": ["set dss 2"],
        "summary": "Successfully changed DSS",
        "success": True,
    }


@tool
def run_node_command(command: str, node_id: str) -> str:
    """Runs a command against a node"""
    print(f"Running command on {node_id}", command)
    return "Dummy output"
