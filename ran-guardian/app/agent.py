from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
import asyncio
import logging
from dataclasses import dataclass
from app.models import IssueStatus, Event, PerformanceData, Issue, ValidationResult
from app.llm_helper import LLMHelper, Risk
from app.data_manager import DataManager
from app.notification_manager import NotificationManager
from app.network_manager import NetworkConfigManager
from collections import deque
import json

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    run_interval: int = 1  # minutes
    lookforward_period: int = 24  # hours


class AgentLogger:
    def __init__(self, max_logs=1000):
        self.logs = deque(maxlen=max_logs)
        self.subscribers: Set[asyncio.Queue] = set()

    async def log(self, level: str, message: str, **kwargs):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        self.logs.append(log_entry)

        # Notify all subscribers
        for queue in self.subscribers:
            await queue.put(log_entry)

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self.subscribers.discard(queue)

    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        return list(self.logs)[-limit:]


class Agent:
    def __init__(
        self,
        data_manager: DataManager,
        network_manager: NetworkConfigManager,
        notification_manager: NotificationManager,
        llm_helper: Optional[LLMHelper] = None,
        config: Optional[AgentConfig] = None,
    ):
        self.data_manager = data_manager
        self.network_manager = network_manager
        self.notification_manager = notification_manager
        self.llm_helper = llm_helper or LLMHelper()
        self.config = config or AgentConfig()
        self.last_run = datetime.now()
        self._task: Optional[asyncio.Task] = None
        self.logger = AgentLogger()

    async def _run(self):
        """Internal method to run periodic tasks"""
        while True:
            try:
                await self._process_cycle()
            except Exception as e:
                self.logger.error(f"Error in agent loop: {e}", exc_info=True)
            await asyncio.sleep(self.config.run_interval * 60)


    async def _process_cycle(self):
        """Run a single processing cycle"""
        self.last_run = datetime.now()
        await self.logger.log("info", "Starting agent processing cycle")

        events = await self._get_events()
        await self.logger.log("info", f"Found {len(events)} events to process")

        await asyncio.gather(*[self._process_event(event) for event in events])

        await self.logger.log("info", "Finished agent processing cycle")

    async def _get_events(self) -> List[Event]:
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=self.config.lookforward_period)
        return await self.data_manager.get_events(start_time, end_time)

    async def _process_event(self, event: Event):
        # event driven flow
        nodes = await self.data_manager.get_nearby_nodes(event.location)
        ls_validation_summary = []
        for node in nodes:
            await self.logger.log(
                "info", f"Processing event {event.event_id} for node {node.node_id}"
            )

            performance_data = await self.data_manager.get_performance_data(
                node.node_id
            )
            await self.logger.log("debug", f"The performance data for node {node.node_id} is {performance_data}")

            alarm_data = await self.data_manager.get_alarms(node.node_id)
            await self.logger.log("debug", f"The performance data for node {node.node_id} is {performance_data}")

            summary = await self.llm_helper.assess_node_event_risk(
                event, performance_data, alarm_data, node
            )
            await self.logger.log("info", f"Here is a summary of the data collected for node {node.node_id}: {summary}")

            ls_validation_summary.append(summary)

        if any(summary.is_valid for summary in ls_validation_summary):
            issue_id = await self._create_issue(event, ls_validation_summary)
            await self.logger.log("info", f"Created issue {issue_id} for event {event.event_id}")

            if not issue_id:
                return

            await self._handle_issue(issue_id)

        return False

    async def _create_issue(
        self, event: Event, validation_summaries: List[ValidationResult] = []
    ) -> str | None:
        """Create an issue from event and validation results"""
        valid_summaries = [s for s in validation_summaries if s.is_valid]
        if not valid_summaries:
            return None

        issue = {
            "event_id": event.event_id,
            "node_ids": [
                s.node_id for s in valid_summaries
            ],  # Assuming ValidationResult has node_id
            "status": IssueStatus.NEW,
            "summary": "; ".join(s.summary for s in valid_summaries),
        }
        return await self.data_manager.create_issue(issue)

    async def _handle_issue(self, issue_id: str):
        """Handle issue resolution flow"""
        await self.logger.log("info", f"Handling issue {issue_id}", issue_id=issue_id)

        issue = await self.data_manager.get_issue(issue_id)
        needs_human = await self.llm_helper.evaluate_severity(
            issue.model_dump()  # Convert pydantic model to dict
        )
        await self.logger.log(
            "info",
            f"Issue {issue_id} needs human intervention: {needs_human}",
            issue_id=issue_id,
            needs_human=needs_human,
        )

        config = await self.network_manager.get_network_config_proposal(issue_id)
        if not config:
            await self._update_status(
                issue_id,
                IssueStatus.ESCALATE,
                "Failed to generate network configuration",
            )
            return

        if needs_human:
            await self._handle_human_intervention(issue_id)
        else:
            await self._handle_automatic_resolution(issue_id, config)

    async def _handle_human_intervention(self, issue_id: str):
        """Handle issues requiring human intervention"""
        await self.notification_manager.send_notification(issue_id)
        await self._update_status(
            issue_id,
            IssueStatus.PENDING_APPROVAL,
            "Awaiting human approval for proposed configuration",
        )

    async def _handle_automatic_resolution(self, issue_id: str, config: Dict):
        """Handle issues that can be automatically resolved"""
        success = await self.network_manager.run_network_config_proposal(
            issue_id, config
        )
        status = IssueStatus.RESOLVED if success else IssueStatus.ESCALATE
        message = (
            f"Configuration {'applied successfully' if success else 'failed to apply'}"
        )
        await self._update_status(issue_id, status, message)

    async def _update_status(self, issue_id: str, status: IssueStatus, message: str):
        """Update issue status with message"""
        await self.data_manager.update_issue(
            issue_id, {"status": status.value, "summary": message}
        )

    async def start(self):
        """Start the periodic task runner"""
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            logger.info("Agent started")

    async def stop(self):
        """Stop the periodic task runner"""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            logger.info("Agent stopped")

    async def run_once(self):
        """Internal method to run periodic tasks"""
        await self._process_cycle()