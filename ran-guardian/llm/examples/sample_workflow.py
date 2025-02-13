import os
import logging
import asyncio
from time import sleep
from app.models import IssueStatus
from llm.utils import check_issue_status, get_issue, get_sample_issue
from dotenv import load_dotenv
from llm.reasoning_agent import ReasoningAgent

load_dotenv()

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("VERTEXAI_LOCATION")

logger = logging.getLogger("llm.reasoning_agent")
logger.setLevel(logging.INFO)
handler = logging.FileHandler("agent.log", mode="a")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

if __name__ == "__main__":

    loop = asyncio.get_event_loop()

    async def run_test():
        sample_issue = await get_sample_issue()
        snapshot, history = None, None

        while await check_issue_status(sample_issue.issue_id) not in (
            IssueStatus.RESOLVED,
            IssueStatus.ESCALATE,
            IssueStatus.PENDING_APPROVAL,
        ):
            sample_issue = await get_issue(sample_issue.issue_id)
            a = ReasoningAgent(
                project=PROJECT_ID,
                location=LOCATION,
                issue=sample_issue,
                node_id="node-1",
            )
            a.set_up()

            if snapshot and history:
                a.load_state(snapshot, history)

            print(f">> Issue state:\n {sample_issue}\n")
            await a.run_workflow()

            # Save state
            snapshot = await a.get_snapshot()
            history = a.get_history()

            if (
                await check_issue_status(sample_issue.issue_id)
                == IssueStatus.MONITORING.value
            ):

                logger.info("Monitoring...")
                sleep(5)
                logger.info("Continuing...")

        final_status = await check_issue_status(sample_issue.issue_id)
        logger.info(f">> Final Issue state:\n {final_status}\n")

    loop.run_until_complete(run_test())
