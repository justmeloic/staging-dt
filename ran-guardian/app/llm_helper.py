import random
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from app.models import (
    Alarm,
    ConfigSuggestion,
    Event,
    NodeData,
    PerformanceData,
    ResolutionResult,
)


class LLMHelper:
    def __init__(self, model_config: Optional[Dict] = None):
        self.model_config = model_config or {}

    async def assess_node_event_risk(
        self,
        event: Event,
        performance_data: PerformanceData,
        alarm_data: Optional[list[Alarm]] = None,
        node_data: Optional[NodeData] = None,
    ):
        ...

    async def generate_config_suggestion(
        self, issue: Dict, current_config: Dict
    ) -> ConfigSuggestion:
        """Suggest network configuration changes based on the issue"""
        return ConfigSuggestion(config_changes={"param1": "value1", "param2": "value2"})

    async def evaluate_severity(self, issue: Dict) -> bool:
        """Evaluate if an issue requires human attention"""
        # return True if random.random() < 0.1 else False
        return False

    async def evaluate_resolution_success(
        self, issue: Dict, performance_data: List[Dict]
    ) -> ResolutionResult:
        """Evaluate if the applied changes have resolved the issue"""
        return ResolutionResult(is_resolved=True, confidence=0.95)
