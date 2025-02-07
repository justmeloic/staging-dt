import asyncio
import logging
import os
from typing import List, Dict, Optional, Set
from datetime import datetime, timedelta
from dataclasses import dataclass
from app.models import IssueStatus, Event, PerformanceData, Issue, ValidationResult
from app.llm_helper import LLMHelper, Risk
from app.data_manager import DataManager
from app.network_manager import NetworkConfigManager
from llm.reasoning_agent import ReasoningAgent
from collections import deque


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    run_interval: int = 0.1  # minutes
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
        llm_helper: Optional[LLMHelper] = None,
        config: Optional[AgentConfig] = None,
    ):
        self.data_manager = data_manager
        self.network_manager = network_manager
        self.llm_helper = llm_helper or LLMHelper()
        self.config = config or AgentConfig()
        self.last_run = datetime.now()
        self._task: Optional[asyncio.Task] = None
        self.logger = AgentLogger()

    async def _run(self):
        """Internal method to run periodic tasks"""
        logger.info("Running agent...")
        logger.info("Running agent...")
        while True:
            try:
                await self._process_cycle()
            except Exception as e:
                self.logger.error(f"Error in agent loop: {e}", exc_info=True)
            await asyncio.sleep(self.config.run_interval * 60)

    async def _process_cycle(self):
        """Run a single processing cycle"""
        self.last_run = datetime.now()
        logger.info("Starting agent processing cycle")
        await self.logger.log("info", "Starting agent processing cycle")

        events = await self._get_events()
        logger.info(f"Found {len(events)} events to process")
        await self.logger.log("info", f"Found {len(events)} events to process")

        await asyncio.gather(*[self._process_event(event) for event in events])

        logger.info("Finished agent processing cycle")
        await self.logger.log("info", "Finished agent processing cycle")

    async def _get_events(self) -> List[Event]:
        """Retrieves upcoming events within the lookforward period.

        Returns:
            A list of Event objects representing upcoming events.
        """
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=self.config.lookforward_period)
        return await self.data_manager.get_events(start_time, end_time)

    async def _process_event(self, event: Event):
        """Processes a single event and creates an issue if necessary.

        This method orchestrates the processing of an event, including:
        1. Identifying nearby nodes to the event.
        2. Retrieving performance and alarm data for each node.
        3. Assessing the risk posed by the event to each node using the LLMHelper.
        4. Creating an issue if any node is deemed at risk.
        5. Handling the created issue (automatic resolution or escalation).

        Args:
            event: The Event object to process.

        Returns:
            False. This function's return value is not used.
        """
        # event driven flow
        logger.info(f"Finding nearby nodes for event {event.event_id}")
        nodes = await self.data_manager.get_nearby_nodes(event.location)

        logger.info(f"Found {len(nodes)} nearby nodes")

        ls_validation_summary = []

        # [vdantas] potentially data could be fetched from each node in parallel to speed up the process
        # ... currently execution is mostly sequential.
        for node in nodes:
            logger.info(f"Processing node {node.node_id}")
            await self.logger.log(
                "info", f"Processing event {event.event_id} for node {node.node_id}"
            )

            performance_data = await self.data_manager.get_performance_data(
                node.node_id
            )
            await self.logger.log(
                "debug",
                f"The performance data for node {node.node_id} is {performance_data}",
            )

            alarm_data = await self.data_manager.get_alarms(node.node_id)
            await self.logger.log(
                "debug",
                f"The performance data for node {node.node_id} is {performance_data}",
            )

            summary = await self.llm_helper.assess_node_event_risk(
                event, performance_data, alarm_data, node
            )
            await self.logger.log(
                "info",
                f"Here is a summary of the data collected for node {node.node_id}: {summary}",
            )

            logger.info(f"Summary of data collected: {summary}")

            ls_validation_summary.append(summary)

        if any(summary.is_valid for summary in ls_validation_summary):
            logger.info("Creating an issue...")
            issue_id = await self._create_issue(event, ls_validation_summary)

            logger.info(f"Issue ID {issue_id}")
            await self.logger.log(
                "info", f"Created issue {issue_id} for event {event.event_id}"
            )

            if not issue_id:
                logger.error(
                    "Something went wrong while creating an issue document in Firestore"
                )
                logger.error(
                    "Something went wrong while creating an issue document in Firestore"
                )
                return

            await self._handle_issue(issue_id)

        return False

    async def _create_issue(
        self, event: Event, validation_summaries: List[ValidationResult] = []
    ) -> str | None:
        """Creates an issue based on valid validation summaries.

        This method creates a new issue if any of the provided validation summaries
        are marked as valid (is_valid=True).  It extracts relevant information
        from the event and the valid summaries to populate the issue details.

        Args:
            event: The event that triggered the validation and potential issue creation.
            validation_summaries: A list of ValidationResult objects, each representing
                the outcome of validation for a specific node.

        Returns:
            The Firestore document ID of the created issue if at least one validation summary is valid.
            Returns None if no valid summaries are provided, meaning no issue was created.
        """
        valid_summaries = [s for s in validation_summaries if s.is_valid]
        if not valid_summaries:
            logger.info("No valid summaries")
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
        """Handles the resolution workflow for a given issue.

        This method determines whether an issue requires human intervention or can be
        automatically resolved.  It orchestrates the following steps:

        1. Retrieves the issue details from the data manager.
        2. Evaluates the severity of the issue using the LLM helper.
        3. Requests a network configuration proposal from the network manager.
        4. If a configuration proposal is generated:
            a. If human intervention is required, it updates the issue status to pending approval.
            b. If automatic resolution is possible, it attempts to apply the configuration and updates the issue status accordingly.
        5. If no configuration proposal is generated, it escalates the issue.

        Args:
            issue_id: The ID of the issue to handle.
        """
        """Handle issue resolution flow"""
        logger.info(f"Handling issue {issue_id}")
        await self.logger.log("info", f"Handling issue {issue_id}", issue_id=issue_id)

        issue = await self.data_manager.get_issue(issue_id)
        needs_human = await self.llm_helper.evaluate_severity(
            issue.model_dump()  # Convert pydantic model to dict
        )
        if needs_human:
            logger.info(f"Issue {issue_id} needs human intervention")
        else:
            logger.info(f"Issue {issue_id} can be automatically resolved")

        await self.logger.log(
            "info",
            f"Issue {issue_id} needs human intervention: {needs_human}",
            issue_id=issue_id,
            needs_human=needs_human,
        )

        # config = await self.network_manager.get_network_config_proposal(issue_id)
        # if not config:
        #     await self._update_status(
        #         issue_id,
        #         IssueStatus.ESCALATE,
        #         "Failed to generate network configuration",
        #     )
        #     return

        if needs_human:
            await self._handle_human_intervention(issue_id)
        else:
            await self._handle_automatic_resolution(issue_id)

    async def _handle_human_intervention(self, issue_id: str):
        """Handle issues requiring human intervention"""

        await self._update_status(
            issue_id,
            IssueStatus.PENDING_APPROVAL,
            "Awaiting human approval before any action is taken",
        )

    async def _handle_automatic_resolution(self, issue_id: str):
        """Handle issues that can be automatically resolved"""
        logger.info("Fetching issue data...")
        issue = await self.data_manager.get_issue(issue_id)
        logger.info(f"Dispatching issue {issue_id} to AI agent.")
        await self.logger.log(
            "info",
            f"Dispatching issue {issue_id} to AI agent",
            issue_id=issue_id,
        )
        ai_agent = ReasoningAgent(
            project=os.environ.get("PROJECT_ID"),
            location=os.environ.get("VERTEXAI_LOCATION"),
            issue=issue,
        )

        logger.info("Checking for existing checkpoints...")
        checkpoint = await self.data_manager.load_checkpoint(issue_id)
        if checkpoint:
            logger.info(
                f"Checkpoint found for issue {issue_id}. Agent will resume work..."
            )
            ai_agent.load_checkpoint(checkpoint[0])
            ai_agent.load_chat_history(checkpoint[1])

        ai_agent.set_up()

        await ai_agent.run_workflow()

        checkpoint = await ai_agent.get_checkpoint()
        chat_history = ai_agent.get_chat_history()

        logger.info("Saving checkpoint to Firestore...")
        await self.data_manager.save_checkpoint(issue_id, checkpoint, chat_history)

    async def _handle_approved_issue_resolution(self, issue_id: str):
        # TODO:
        # Step 1. Retrieve network config action
        pass

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
