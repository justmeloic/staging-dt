import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
import pytest
from app.models import IssueStatus, Issue, Event  # Import necessary models


class RANServiceClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def test_all(self):
        async with aiohttp.ClientSession() as session:
            await self.test_health(session)
            await self.test_get_issues(session)
            await self.test_get_issue(session)
            await self.test_update_issue(session)
            await self.test_get_issue_stats(session)
            await self.test_get_network_config_proposal(session)
            await self.test_run_network_config_proposal(session)
            await self.test_get_events(session)
            await self.test_get_event(session)
            await self.test_update_event(session)  # Added
            await self.test_get_event_stats(session)  # Added

    async def test_health(self, session: aiohttp.ClientSession):
        print("\n1. Testing health check endpoint...")
        async with session.get(f"{self.base_url}/health") as response:
            assert response.status == 200
            assert await response.json() == {"status": "OK"}

    async def test_get_issues(self, session):
        print("\n2. Testing get all issues...")
        async with session.get(f"{self.base_url}/issues") as response:
            assert response.status == 200
            issues = await response.json()
            assert isinstance(issues, list)  # Expect a list of issues

    async def test_get_issue(self, session):
        print("\n3. Testing get specific issue...")
        issue_id = "1"  # Replace with a valid issue ID from your mock data
        async with session.get(f"{self.base_url}/issues/{issue_id}") as response:
            if response.status == 200:  # Check if the issue exists
                issue = await response.json()
                assert isinstance(issue, dict)
                assert issue.get("issue_id") == issue_id
            elif response.status == 404:
                print(
                    "Issue not found (404), which might be expected depending on your mock data."
                )
            else:
                assert (
                    False
                ), f"Unexpected status code: {response.status}"  # Fail if it's not 200 or 404

    async def test_update_issue(self, session):
        print("\n4. Testing issue update...")
        issue_id = "1"  # Replace with a valid issue ID
        updates = {"status": IssueStatus.RESOLVED.value}
        async with session.put(
            f"{self.base_url}/issues/{issue_id}", json=updates
        ) as response:
            assert 200 <= response.status < 300  # Allow 2xx codes (success)

    async def test_get_issue_stats(self, session):
        print("\n5. Testing issue statistics...")
        async with session.get(f"{self.base_url}/issues/stats") as response:
            assert response.status == 200
            stats = await response.json()
            assert isinstance(stats, dict)

    async def test_get_network_config_proposal(self, session):
        print("\n6. Testing network config proposal...")
        issue_id = "1"  # Or a known issue ID from your mock data
        async with session.get(
            f"{self.base_url}/network-config/propose/{issue_id}"
        ) as response:
            assert response.status == 200
            proposal = await response.json()
            assert isinstance(proposal, dict)

    async def test_run_network_config_proposal(self, session):
        print("\n7. Testing run network config proposal...")
        proposal_id = "proposal_123"  # Replace with a valid proposal ID
        config = {"parameter": "value"}  # Provide config if needed

        async with session.post(
            f"{self.base_url}/network-config/run/{proposal_id}", json=config
        ) as response:
            assert 200 <= response.status < 300
            result = await response.json()
            assert isinstance(result, dict)

    async def test_get_events(self, session):
        print("\n8. Testing get events...")
        start = datetime.now() - timedelta(days=1)
        end = datetime.now() + timedelta(days=1)
        params = {
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
        }  # Example time range

        async with session.get(f"{self.base_url}/events", params=params) as response:
            assert response.status == 200
            events = await response.json()
            assert isinstance(events, list)

    async def test_get_event(self, session):
        print("\n9. Testing get specific event...")
        event_id = "event1"  # Replace with valid event ID
        async with session.get(f"{self.base_url}/events/{event_id}") as response:
            if response.status == 200:  # Check if the event exists
                event = await response.json()
                assert isinstance(event, dict)
                assert event.get("event_id") == event_id
            elif (
                response.status == 404
            ):  # Handle the case where the event doesn't exist.
                print(
                    "Event not found (404) - this may be expected based on your test data."
                )
            else:
                assert False, f"Unexpected status code: {response.status}"

    async def test_update_event(self, session):
        print("\n10. Testing update event...")
        event_id = "event1"  # Replace with a valid event ID
        updates = {"size": 300}  # Example update
        async with session.put(
            f"{self.base_url}/events/{event_id}", json=updates
        ) as response:
            assert 200 <= response.status < 300  # Check for success (2xx status codes)

    async def test_get_event_stats(self, session):
        print("\n11. Testing event statistics...")
        async with session.get(f"{self.base_url}/events/stats") as response:
            assert response.status == 200
            stats = await response.json()
            assert isinstance(stats, dict)


@pytest.mark.asyncio
async def test_ran_service():
    client = RANServiceClient()
    await client.test_all()


if __name__ == "__main__":
    print("Starting RAN Service Tests...")
    asyncio.run(test_ran_service())
