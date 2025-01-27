import asyncio
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Depends, Request
import os
from typing import Dict, Optional, List
import json
from sse_starlette.sse import EventSourceResponse

from app.models import IssueStatus, Issue
from app.agent import Agent
from app.data_manager import DataManager
from app.network_manager import NetworkConfigManager
from app.notification_manager import NotificationManager

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")


router = APIRouter()


# Dependency Injection - create instances of managers and inject them
async def get_data_manager():
    return DataManager(project_id=PROJECT_ID)  # Or however you initialize it


async def get_network_config_manager():
    return NetworkConfigManager()  # Or use dependency injection


async def get_notification_manager():
    return NotificationManager()  # Or use dependency injection


@router.get("/")
async def hello_agent():
    return "Welcome to RAN Guardian Agent!"


# ---
# Health check
# ---


@router.get("/health")
async def health_check():
    return {"status": "OK"}


# ---
# Issue management
# ---
# --- Issue management ---
@router.get("/issues", response_model=List[Issue])  # Type hint
async def get_issues(data_manager: DataManager = Depends(get_data_manager)):
    return await data_manager.get_issues()


@router.get("/issues/{issue_id}")
async def get_issue(
    issue_id: str, data_manager: DataManager = Depends(get_data_manager)
):
    """Get details of a specific issue"""
    return await data_manager.get_issue(issue_id)


@router.put("/issues/{issue_id}")
async def update_issue(
    issue_id: str, updates: Dict, data_manager: DataManager = Depends(get_data_manager)
):
    """Update the status of an issue"""
    return await data_manager.update_issue(issue_id, updates)


@router.get("/issues/stats")
async def get_issue_stats(data_manager: DataManager = Depends(get_data_manager)):
    """Get summary statistics of issues"""
    return await data_manager.get_issue_stats()


# ---
# Network config
# ---
@router.get("/network-config/propose/{issue_id}")
async def get_network_config_proposal(
    issue_id: str,
    network_manager: NetworkConfigManager = Depends(get_network_config_manager),
):
    """Get a network configuration proposal for a specific issue"""
    return await network_manager.get_network_config_proposal(issue_id)


@router.post("/network-config/run/{proposal_id}")
async def run_network_config_proposal(
    proposal_id: str,
    config: Optional[dict] = None,
    network_manager: NetworkConfigManager = Depends(get_network_config_manager),
):
    """Trigger network configuration changes based on the proposed config"""
    return await network_manager.run_network_config_proposal(proposal_id, config)


@router.get("/logs/stream")
async def stream_logs(request: Request):
    """Stream real-time logs from the agent using Server-Sent Events (SSE)"""
    if not hasattr(request.app.state, "agent"):
        raise HTTPException(status_code=503, detail="Agent not initialized")

    async def event_generator():
        queue = request.app.state.agent.logger.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break

                log_entry = None
                try:
                    log_entry = await asyncio.wait_for(
                        queue.get(), timeout=5
                    )  # Wait for up to 5 seconds
                except asyncio.TimeoutError:
                    # Send a ping message if timeout
                    yield {"event": "ping", "data": str(datetime.now())}
                    continue  # Skip to the next iteration of the loop.

                if log_entry:
                    yield {"event": "log", "data": json.dumps(log_entry)}
        finally:
            request.app.state.agent.logger.unsubscribe(queue)

    return EventSourceResponse(
        event_generator(),
    )


@router.get("/logs/recent")
async def get_recent_logs(request: Request, limit: int = 100):
    return request.app.state.agent.logger.get_recent_logs(limit)
