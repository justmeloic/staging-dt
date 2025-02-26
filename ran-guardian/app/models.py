import json
import logging
import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, NamedTuple, Optional

from langchain_core.messages import BaseMessage
from langgraph.types import StateSnapshot
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class IssueStatus(str, Enum):
    NEW = "new"
    ANALYZING = "analyzing"
    PENDING_APPROVAL = "pending_approval"
    RESOLVED = "resolved"
    ESCALATE = "escalate"
    APPROVED = "approved"
    REJECTED = "rejected"
    MONITORING = "monitoring"


class Location(BaseModel):
    latitude: float
    longitude: float
    address: Optional[str] = None


class Event(BaseModel):
    event_id: str
    location: Location  # {latitude: float, longitude: float}
    city: str
    start_date: datetime
    end_date: datetime
    name: str
    url: Optional[str]
    event_type: str
    size: str
    issue_id: Optional[str] = None
    processed_at: Optional[datetime] = None

    @classmethod
    def from_firestore_doc(cls, doc_id: str, doc_data: dict) -> Optional["Event"]:
        """
        Creates an Event object from a Firestore document. This is a class method (factory method).

        Args:
            doc_id: The ID of the Firestore document.
            doc_data: The data of the Firestore document.

        Returns:
            An Event object if the conversion is successful, None otherwise.
        """
        try:
            # Parse date strings into datetime objects
            start_date = datetime.strptime(doc_data.get("start_date"), "%Y-%m-%d")
            end_date = datetime.strptime(doc_data.get("end_date"), "%Y-%m-%d")

            # Construct the location dictionary
            location = Location(
                address=doc_data.get("address", None),
                latitude=doc_data.get("lat", None),
                longitude=doc_data.get("lng", None),
            )

            # Create the Event object using the class method
            return cls(
                event_id=doc_id,
                location=location,
                city=doc_data.get("location"),
                start_date=start_date,
                end_date=end_date,
                name=doc_data.get("name"),
                url=doc_data.get("url"),
                event_type=doc_data.get("event_type"),
                size=doc_data.get("size"),
                issue_id=doc_data.get("issue_id"),
                processed_at=doc_data.get("processed_at"),
            )

        except (ValueError, TypeError, KeyError) as e:
            logger.error(
                f"[Event.from_firestore_doc] Skipp event {doc_id} due to error :{e}"
            )
            raise e


class NodeData(BaseModel):
    node_id: str
    site_id: str
    capacity: int


class Site(BaseModel):
    site_id: str
    name: str
    location: Location
    nodes: List[NodeData]


class PerformanceData(BaseModel):
    node_id: str
    timestamp: datetime
    rrc_max_users: int
    rrc_setup_sr_pct: float
    erab_ssr_volte_pct: Optional[float] = None
    erab_ssr_data_pct: Optional[float] = None
    download_throughput: Optional[float] = None
    # Various performance metrics


# TODO: need to modify to better fit alarm data
class Alarm(BaseModel):
    alarm_id: str
    node_id: str
    event_id: Optional[str]
    created_at: datetime
    cleared_at: Optional[datetime] = None
    alarm_type: str
    description: str


class NodeSummary(BaseModel):
    node_id: str
    site_id: str
    capacity: int
    timestamp: datetime
    performances: List[PerformanceData]
    alarms: List[Alarm]
    is_problematic: bool = False
    summary: str = ""


class TaskStatus(str, Enum):
    DONE = "done"
    FAILED = "failed"
    EXECUTING = "executing"
    SCHEDULED = "scheduled"


class Task(BaseModel):
    name: str
    status: TaskStatus
    node_id: str
    executed_at: Optional[datetime] = None
    commands: Optional[list[str]] = None


class IssueSnapshot(BaseModel):
    snapshot_id: str
    node_id: str
    event_id: str
    updated_at: datetime
    status: IssueStatus
    summary: str
    performance_data: PerformanceData


class IssueUpdate(BaseModel):
    timestamp: datetime
    status: IssueStatus
    summary: Optional[str] = None  # Optional summary for the update


class Issue(BaseModel):
    issue_id: str = Field(
        default_factory=lambda: str(uuid.uuid4())
    )  # maybe we can just use the same id?
    event_id: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    event_size: Optional[int]
    event_risk: Optional["EventRisk"] = None
    node_ids: list[str]
    status: IssueStatus = IssueStatus.NEW
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    updates: List[IssueUpdate] = Field(default_factory=list)  # Simplified history
    recommendation: Optional[str] = None
    summary: Optional[str] = None
    tasks: Optional[list[Task]] = None

    @classmethod
    def from_firestore_doc(cls, doc):
        doc_dict = doc.to_dict()
        try:
            if "tasks" in doc_dict and doc_dict["tasks"]:
                if isinstance(doc_dict["tasks"], list):
                    doc_dict["tasks"] = [
                        Task.model_validate(t if isinstance(t, dict) else json.loads(t))
                        for t in doc_dict["tasks"]
                    ]
                else:
                    doc_dict["tasks"] = [
                        Task.model_validate(t if isinstance(t, dict) else json.loads(t))
                        for t in json.loads(doc_dict["tasks"])
                    ]

            if "event_risk" in doc_dict and doc_dict["event_risk"]:
                node_sum = doc_dict["event_risk"]["node_summaries"]
                node_sum = [NodeSummary.model_validate(n) for n in node_sum]
                doc_dict["event_risk"]["node_summaries"] = node_sum
                doc_dict["event_risk"] = EventRisk.model_validate(
                    doc_dict["event_risk"]
                )
            issue = cls(**doc_dict)
            return issue

        except Exception as e:
            logger.error(f"parsing issue got error {e}")
            return None


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ESCALATE = "escalate"


class RiskEvalResult(BaseModel):
    risk_level: RiskLevel
    reasoning: str


# output of evaluate event risk
class EventRisk(BaseModel):
    event_id: str
    node_summaries: List[NodeSummary]
    risk_level: RiskLevel
    description: str


class ConfigSuggestion(BaseModel):
    config_changes: Dict[str, str]


class ResolutionResult(BaseModel):
    is_resolved: bool
    confidence: float


class AgentHistory(BaseModel):
    chat_history: Optional[list[BaseMessage]] = list()
    task_history: Optional[list[Task]] = list()
