from typing import List
from datetime import datetime
from app.models import Event, NetworkPerformance, Issue

class MockEventAgent:
    async def get_events(self, location: dict, timestamp: datetime) -> List[Event]:
        return []  # Mock implementation

class MockBigQuery:
    def get_performance_data(self, node_id: str) -> List[NetworkPerformance]:
        return []  # Mock implementation

    def log_issue(self, issue: Issue):
        pass  # Mock implementation

class MockNetworkConfig:
    async def trigger_config_change(self, node_id: str, config: dict):
        pass  # Mock implementation

class MockNotificationService:
    async def notify_users(self, message: str):
        pass  # Mock implementation
