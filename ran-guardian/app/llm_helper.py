import json
import logging
import os
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.models import (
    Alarm,
    ConfigSuggestion,
    Event,
    EventRisk,
    Issue,
    NodeData,
    NodeSummary,
    PerformanceData,
    ResolutionResult,
    RiskLevel,
)
from app.prompts import assess_event_risk, assess_node_risk, recommend_network_config
from dotenv import load_dotenv
from google import genai
from google.api_core import exceptions, retry
from google.genai import types
from pydantic import BaseModel

load_dotenv()
logger = logging.getLogger(__name__)


class EventRiskEvalResult(BaseModel):
    risk_level: str
    reasoning: str


class NodeRiskEvalResult(BaseModel):
    is_problematic: str
    summary: str


class LLMHelper:
    def __init__(
        self,
        project_id: str = os.environ.get("PROJECT_ID"),
        location: str = os.environ.get("GEMINI_MODEL_LOCATION"),
        model_id: str = os.environ.get("GEMINI_MODEL_NAME"),
    ):
        self.client = genai.Client(vertexai=True, project=project_id, location=location)
        self.model_id = model_id

    async def assess_event_risk(
        self, event: Event, node_summaries: List[NodeSummary]
    ) -> Event:
        total_capacity = sum(node.capacity for node in node_summaries)
        # todo: add retry logic
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=assess_event_risk.prompt,
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema=EventRiskEvalResult,
                ),
                contents=types.Content(
                    parts=[
                        types.Part.from_text(
                            "Event details: " + event.model_dump_json()
                        ),
                        types.Part.from_text(f"Total node capacity: {total_capacity}"),
                        types.Part.from_text(
                            "Node summaries: "
                            + ";".join([n.model_dump_json() for n in node_summaries])
                        ),
                    ],
                    role="user",
                ),
            )
            result = json.loads(response.text)
            risk_level = RiskLevel(result["risk_level"].strip().lower())
            return EventRisk(
                event_id=event.event_id,
                node_summaries=node_summaries,
                risk_level=risk_level,
                description=result["reasoning"],
            )
        except Exception as e:  # TODO, should only except after some retry...
            msg = f"Failed to evaluate risk for event {event.event_id} due to: {e}"
            logger.error(msg)
            return EventRisk(
                event_id=event.event_id,
                node_summaries=node_summaries,
                risk_level=RiskLevel.ESCALATE,
                description=msg,
            )

    @retry.Retry(
        predicate=retry.if_transient_error,
        initial=2.0,
        maximum=64.0,
        multiplier=2.0,
        timeout=600,
    )
    async def assess_node_risk(self, node_summary: NodeSummary) -> NodeSummary:
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=assess_node_risk.prompt,
                    temperature=0.3,
                    response_mime_type="application/json",
                    response_schema=NodeRiskEvalResult,
                ),
                contents=types.Content(
                    parts=[
                        types.Part.from_text(
                            "Node summary: " + node_summary.model_dump_json()
                        ),
                    ],
                    role="user",
                ),
            )
            result = json.loads(response.text)
            node_summary.is_problematic = bool(result["is_problematic"])
            node_summary.summary = result["summary"]
            return node_summary
        except Exception as e:  # TODO, should only except after some retry...
            msg = f"Failed to automatically evaluate risk for node {node_summary.node_id} due to: {e}"
            logger.error(msg)
            node_summary.is_problematic = True
            node_summary.summary = msg
            return node_summary

    @retry.Retry(
        predicate=retry.if_transient_error,
        initial=2.0,
        maximum=64.0,
        multiplier=2.0,
        timeout=600,
    )
    async def recommend_network_config(
        self, event: Event, event_risk: EventRisk
    ) -> str:
        """Suggest network configuration changes based on the issue"""
        try:
            response = self.client.models.generate_content(
                model=self.model_id,
                config=types.GenerateContentConfig(
                    system_instruction=recommend_network_config.prompt,
                    temperature=0.3,
                ),
                contents=types.Content(
                    parts=[
                        types.Part.from_text("Event: " + event.model_dump_json()),
                        types.Part.from_text(
                            "Event risk: " + event_risk.model_dump_json()
                        ),
                    ],
                    role="user",
                ),
            )
            return response.text
        except Exception as e:  # TODO, should only except after some retry...
            msg = f"Failed to automatically generate configuration recommendation due to: {e}"
            logger.error(msg)
            return msg
