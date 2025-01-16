from fastapi import APIRouter, HTTPException
from datetime import datetime
from typing import Dict

from app.models import IssueStatus, Issue
from app.services import (
    MockEventAgent,
    MockBigQuery,
    MockNetworkConfig,
    MockNotificationService
)

router = APIRouter()

# Initialize services
event_agent = MockEventAgent()
bigquery_client = MockBigQuery()
network_config = MockNetworkConfig()
notification_service = MockNotificationService()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.post("/issues/analyze")
async def analyze_potential_issue(node_id: str, timestamp: datetime):
    """Analyze if an issue should be created based on events and performance"""
    performance_data = bigquery_client.get_performance_data(node_id)

    location = {"latitude": 0, "longitude": 0}  # Would be derived from node_id
    events = await event_agent.get_events(location, timestamp)

    should_create_issue = len(events) > 0  # Simplified logic

    if should_create_issue:
        issue = Issue(
            issue_id="mock_id",
            node_id=node_id,
            status=IssueStatus.NEW,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            events=events,
            performance_data=performance_data,
            summary="Performance degradation detected"
        )
        bigquery_client.log_issue(issue)

        await notification_service.notify_users(
            f"New issue detected for node {node_id}"
        )

        return {"issue_created": True, "issue": issue}

    return {"issue_created": False}

@router.put("/issues/{issue_id}/status")
async def update_issue_status(
    issue_id: str,
    new_status: IssueStatus
):
    """Update the status of an issue"""
    return {"message": f"Status updated to {new_status}"}

@router.post("/network/configure/{node_id}")
async def configure_network(node_id: str, config: dict):
    """Trigger network configuration changes"""
    await network_config.trigger_config_change(node_id, config)
    return {"message": "Configuration change triggered"}

@router.get("/issues/stats")
async def get_issue_stats():
    """Get summary statistics of issues"""
    return {
        "total_issues": 100,
        "status_breakdown": {
            "new": 10,
            "in_preparation": 20,
            "validated": 30,
            "reconfig": 15,
            "resolved": 20,
            "failed": 5
        }
    }

@router.get("/issues/{issue_id}")
async def get_issue(issue_id: str):
    """Get details of a specific issue"""
    return {
        "issue_id": issue_id,
        "status": IssueStatus.NEW,
        "summary": "Mock issue details"
    }
