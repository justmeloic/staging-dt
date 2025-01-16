import asyncio
import aiohttp
from datetime import datetime
import json
import pytest
from app.models import IssueStatus

class RANServiceClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url

    async def test_all(self):
        async with aiohttp.ClientSession() as session:
            await self.test_health(session)
            await self.test_analyze_issue(session)
            await self.test_update_status(session)
            await self.test_configure_network(session)
            await self.test_get_stats(session)
            await self.test_get_issue(session)

    async def test_health(self, session: aiohttp.ClientSession):
        print("\n1. Testing health check endpoint...")
        async with session.get(f"{self.base_url}/health") as response:
            print(f"Status: {response.status}")
            print("Response:", await response.json())
            assert response.status == 200

    async def test_analyze_issue(self, session: aiohttp.ClientSession):
        print("\n2. Testing issue analysis...")
        params = {
            "node_id": "node_123",
            "timestamp": datetime.now().isoformat()
        }
        async with session.post(f"{self.base_url}/issues/analyze", params=params) as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print("Response:", data)
            assert response.status == 200
            assert "issue_created" in data

    async def test_update_status(self, session: aiohttp.ClientSession):
        print("\n3. Testing issue status update...")
        issue_id = "mock_id"
        params = {"new_status": IssueStatus.VALIDATED.value}
        async with session.put(f"{self.base_url}/issues/{issue_id}/status", params=params) as response:
            print(f"Status: {response.status}")
            print("Response:", await response.json())
            assert response.status == 200

    async def test_configure_network(self, session: aiohttp.ClientSession):
        print("\n4. Testing network configuration...")
        node_id = "node_123"
        config = {
            "power_level": 50,
            "frequency_band": "3.5GHz",
            "bandwidth": "100MHz"
        }
        async with session.post(
            f"{self.base_url}/network/configure/{node_id}",
            json=config
        ) as response:
            print(f"Status: {response.status}")
            print("Response:", await response.json())
            assert response.status == 200

    async def test_get_stats(self, session: aiohttp.ClientSession):
        print("\n5. Testing issue statistics...")
        async with session.get(f"{self.base_url}/issues/stats") as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print("Response:", data)
            assert response.status == 200
            assert "total_issues" in data
            assert "status_breakdown" in data

    async def test_get_issue(self, session: aiohttp.ClientSession):
        print("\n6. Testing get specific issue...")
        issue_id = "mock_id"
        async with session.get(f"{self.base_url}/issues/{issue_id}") as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print("Response:", data)
            assert response.status == 200
            assert "issue_id" in data

@pytest.mark.asyncio
async def test_ran_service():
    client = RANServiceClient()
    await client.test_all()

if __name__ == "__main__":
    print("Starting RAN Service Tests...")
    asyncio.run(test_ran_service())
