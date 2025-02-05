from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
import uuid


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
    start_date: datetime
    end_date: datetime
    name: str
    url: Optional[str]
    event_type: str
    size: str

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
                start_date=start_date,
                end_date=end_date,
                name=doc_data.get("name"),
                url=doc_data.get("url"),
                event_type=doc_data.get("event_type"),
                size=doc_data.get("size"),
            )

        except (ValueError, TypeError, KeyError) as e:
            # print(f"Error converting document {doc_id}: {e}")
            # print(f"Problematic data: {doc_data}")
            return None


class NodeData(BaseModel):
    node_id: str
    site_id: str
    capacity: int


class PerformanceData(BaseModel):
    node_id: str
    timestamp: datetime
    rrc_max_users: int
    rrc_setup_sr_pct: float
    # Various performance metrics


class Alarm(BaseModel):
    alarm_id: str
    node_id: str
    event_id: Optional[str]
    created_at: datetime
    cleared_at: Optional[datetime] = None
    alarm_type: str
    description: str


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
    issue_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_id: str
    node_ids: list[str]
    status: IssueStatus = IssueStatus.NEW
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    updates: List[IssueUpdate] = Field(default_factory=list)  # Simplified history
    summary: Optional[str] = None


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Risk(BaseModel):
    event_id: str
    node_id: str
    risk_level: RiskLevel
    description: str


class RiskAnalysis(BaseModel):
    identified_risks: List[Risk]


class ValidationResult(BaseModel):
    node_id: str
    event_id: str
    is_valid: bool
    summary: str


class ConfigSuggestion(BaseModel):
    config_changes: Dict[str, str]


class ResolutionResult(BaseModel):
    is_resolved: bool
    confidence: float
