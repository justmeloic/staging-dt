import asyncio
import logging
import os
import random
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Set

import numpy as np
from app.data_manager import TIME_INTERVAL, DataManager
from app.llm_helper import LLMHelper
from app.models import (
    AgentHistory,
    Event,
    EventRisk,
    Issue,
    IssueStatus,
    NodeData,
    NodeSummary,
    PerformanceData,
    RiskLevel,
    Site,
)
from app.network_manager import NetworkConfigManager
from llm.reasoning_agent import ReasoningAgent

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    run_interval: int = 5  # minutes
    lookforward_period: int = 24  # hours
    monitoring_period: int = 15  # minutes
    concurrency_limit: int = 5  # max. num of reasoning agents to run concurrently


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
        self.agent_semaphore = asyncio.Semaphore(self.config.concurrency_limit)

    async def _run(self):
        """Internal method to run periodic tasks"""
        while True:
            try:
                await self._process_event_cycle()
                await self.data_manager.sort_issues()
                await self._process_issue_cycle()
            except Exception as e:
                logger.error(f"Something went wrong {e}")

            await asyncio.sleep(self.config.run_interval * 60)

    async def _process_event_cycle(self):
        """Run a single processing cycle"""
        self.last_run = datetime.now()
        logger.info("Starting event processing cycle")

        events = await self._get_events()
        logger.info(f"Found {len(events)} events to process")

        await asyncio.gather(*[self._process_event(event) for event in events])
        logger.info("Finished event processing cycle")

    async def _process_issue_cycle(self):
        """Run a single processing cycle"""
        issues = await self.data_manager.get_issues()
        issue_tasks = [self._process_issue(issue) for issue in issues]
        asyncio.gather(*issue_tasks)

    async def _get_events(self, location: Optional[str] = None) -> List[Event]:
        logger.info(f"Fetching events near location {location}...")
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=self.config.lookforward_period)
        events = await self.data_manager.get_events(
            start_time, end_time, location=location
        )
        logger.info(f"Found {len(events)}")
        return events

    async def _event_has_wip_issue(self, event: Event) -> bool:
        # Find issue from event
        # Check updated_at
        # If updated_at < 15 min ago, skip and process next event
        # or, if issue status is not "resolved"
        if event.issue_id is None:
            return False
        else:
            return True

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
        # the data manager get event from bigquery which is different than the event data base
        # this should be fixed!
        if not await self.data_manager.get_event(event.event_id):
            return
        else:
            logger.info(f"Processing event {event.event_id} ...")

            if await self._event_has_wip_issue(event):
                # update the issue with the latest event information
                # do not process event if it already has an issue
                return

            event_risk = await self._evaluate_event_risk(event=event)

            if event_risk.risk_level != RiskLevel.LOW:
                recommendation = await self._create_recommendation(event_risk)
                issue_id = await self._create_issue(event, event_risk, recommendation)
                await self.data_manager.update_event(
                    event.event_id, {"issue_id": issue_id}
                )
            else:
                # if event is low risk, do nothing for now
                pass

    # TODO: need to understand how capacity is distributed on each node (Node should actually be sites ... )

    async def _evaluate_event_risk(self, event: Event) -> EventRisk:
        """
        - if the combined capacity of the nodes is enough to cover even
        - if there's on-going alarm for the site
        - if the performance is degrading

        for example:
        if [x, x, y] performance is already degrading, then it is high risk
        if [y, y, n] then it is medium risk
        if [y, n, n] then it's low risk

        Then decide if the risk level is high or medium or low
        """

        # TODO: use Gemini to implement the decision process

        # gather node data
        logger.info(f"Evaluating risk for event {event.event_id}...")

        nodes = await self.data_manager.get_nearby_nodes(event.location)
        node_summary_tasks = [self._get_node_summary(node=node) for node in nodes]
        node_summaries = await asyncio.gather(*node_summary_tasks)

        # calculate if capacity is enough
        total_capacity = sum(node.capacity for node in node_summaries)
        # is_enough_capacity = total_capacity >= event.size # need to convert size into a numeric value

        # some magic happens with gemini toe determine the risk level and description
        risk_level = random.choice([RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW])

        logger.info("Finished evaluating risk for event...")

        return EventRisk(
            event_id=event.event_id,
            node_summaries=node_summaries,
            risk_level=risk_level,
            description="mock description",
        )

    async def _get_node_summary(self, node: NodeData):
        performance_data = await self.data_manager.get_performance_data(node.node_id)
        alarm_data = await self.data_manager.get_alarms(node.site_id)
        capacity = node.capacity

        return NodeSummary(
            node_id=node.node_id,
            site_id=node.site_id,
            performances=performance_data,
            alarms=alarm_data,
            capacity=capacity,
            timestamp=datetime.now(),
        )

    # TODO: make sure that nodes are processed parallelly
    # using output here https://aistudio.google.com/app/prompts/1uWEYHmB0yJQhBR0zIWd_dYXfAZ2dfwLe?resourceKey=0-2iBAs1mFr_W4UO2EfxDTcg
    # TODO: need to understand how capacity is distributed on each node (Node should actually be sites ... )

    async def _create_issue(
        self,
        event: Event,
        event_risk: EventRisk,
        recommendation: Optional[str] = None,
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
        logger.info(f"Creating issue for event {event.event_id}...")
        # sumary should be generated by gemini, taking into account the risk and node summaries
        return await self.data_manager.create_issue(
            event=event, event_risk=event_risk, summary="mock summary"
        )

    async def _process_issue(self, issue: Issue):
        logger.info(f"Processing issue {issue.issue_id}...")
        # based on the issue risk level
        # create recommendation
        # either handover to human
        # or automatic resolution
        event_updates = {}

        if issue.updated_at.tzinfo:
            time_threshold = datetime.now(timezone.utc) - timedelta(
                minutes=TIME_INTERVAL
            )
        else:
            time_threshold = datetime.now() - timedelta(minutes=TIME_INTERVAL)

        if issue.updated_at < time_threshold or (issue.event_risk is None):
            event = await self.data_manager.get_event(issue.event_id)
            if not event:
                # if not event exists anymore then delete the issue and return
                # await self.data_manager.delete_issue(issue.issue_id)
                return

            event_risk = await self._evaluate_event_risk(event=event)
        else:
            event_risk = issue.event_risk
        event_updates["event_risk"] = event_risk.model_dump()
        await self.data_manager.update_issue(issue.issue_id, updates=event_updates)

        # if issue 's data is outdated, then update the latest data (node summary, )
        if await self._evaluate_if_human_intervention(issue):
            await self._handle_human_intervention(issue.issue_id)
        else:
            await self._handle_automatic_resolution(issue.issue_id)

        logger.info(f"Finished processing issue {issue.issue_id}...")

    async def _evaluate_if_human_intervention(self, issue: Issue) -> bool:
        logger.info("Evaluating if human intervention is needed...")
        # replace with some gemini magic here
        if not (issue.node_ids):
            # if we don't find any nodes near the issue
            return True
        else:
            return True if np.random.rand() < 0.5 else False

    async def _create_recommendation(self, event_risk: EventRisk) -> str:
        logger.info(
            "Creating recommendation for network reconfiguration based on the event..."
        )
        # replace with some gemini magic here)
        return "mock recommendation"

    async def _handle_human_intervention(self, issue_id: str):
        logger.info("Handling human intervention...")
        """Handle issues requiring human intervention"""

        await self.data_manager.update_issue(
            issue_id,
            updates={
                "status": IssueStatus.PENDING_APPROVAL,
                "summary": "Awaiting human approval before any action is taken",
            },
        )

    async def _process_node_with_ai_agent(self, issue_id: str, node_id: str) -> None:
        """Process a single node with a ReasoningAgent instance.

        This helper method handles the creation and execution of a ReasoningAgent
        for a single node while respecting the concurrency limit.
        """
        async with self.agent_semaphore:  # Using semaphore to limit concurrent executions
            logger.info(f"Starting ReasoningAgent for node {node_id}")
            await self.logger.log(
                "info",
                f"Starting ReasoningAgent for node {node_id}",
                issue_id=issue_id,
                node_id=node_id,
            )

            try:
                ai_agent = ReasoningAgent(
                    project=os.environ.get("PROJECT_ID"),
                    location=os.environ.get("VERTEXAI_LOCATION"),
                    issue=await self.data_manager.get_issue(issue_id),
                    node_id=node_id,
                )

                # Check for existing checkpoints
                snapshot = await self.data_manager.load_agent_snapshot(
                    issue_id, node_id
                )
                history = await self.data_manager.load_agent_history(issue_id, node_id)

                if snapshot:
                    logger.info(
                        f"Checkpoint found for issue {issue_id}, node {node_id}. Agent will resume work..."
                    )
                    ai_agent.load_state(snapshot, history)

                ai_agent.set_up()
                await ai_agent.run_workflow()

                # Save agent state
                snapshot = await ai_agent.get_snapshot()
                history = ai_agent.get_history()
                await self.data_manager.save_agent_checkpoint(
                    issue_id=issue_id,
                    node_id=node_id,
                    snapshot=snapshot,
                    history=history,
                )

            except Exception as e:
                logger.error(f"Error processing node {node_id}", exc_info=True)
                await self.logger.log(
                    "error",
                    f"Error processing node {node_id}: {str(e)}",
                    issue_id=issue_id,
                    node_id=node_id,
                )

    async def _handle_automatic_resolution(self, issue_id: str):
        """Handle issues that can be automatically resolved"""
        logger.info(f"Handling automatic resolution for issue {issue_id}...")
        issue = await self.data_manager.get_issue(issue_id)

        if not issue.node_ids:
            logger.warning(f"No nodes found for issue {issue_id}")
            return

        logger.info(
            f"Processing {len(issue.node_ids)} nodes with concurrency limit of {self.config.concurrency_limit}"
        )
        await self.logger.log(
            "info",
            f"Starting parallel processing of {len(issue.node_ids)} nodes",
            issue_id=issue_id,
        )

        # Create tasks for all nodes with concurrency control
        tasks = [
            asyncio.create_task(self._process_node_with_ai_agent(issue_id, node_id))
            for node_id in issue.node_ids
        ]

        # Wait for all tasks to complete
        # NOTE: this could potentially take several minutes to complete
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Error during node processing: {str(e)}", exc_info=True)
            await self.logger.log(
                "error",
                f"Error during node processing: {str(e)}",
                issue_id=issue_id,
            )

        logger.info(f"Completed processing all nodes for issue {issue_id}")
        await self.logger.log(
            "info",
            "Completed processing all nodes",
            issue_id=issue_id,
        )

    async def start(self):
        """Start the periodic task runner"""
        logger.info("Starting agent...")
        if self._task is None:
            self._task = asyncio.create_task(self._run())
            logger.info("Agent started")

    async def stop(self):
        """Stop the periodic task runner"""
        logger.info("Stopping agent...")
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
        await self._process_event_cycle()
        await self._process_issue_cycle()
