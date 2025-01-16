from pydantic import BaseModel
from typing import List
from datetime import datetime
from enum import Enum

class IssueStatus(str, Enum):
    NEW = "new"
    IN_PREPARATION = "in_preparation"
    VALIDATED = "validated"
    RECONFIG = "reconfig"
    RESOLVED = "resolved"
    FAILED = "failed"

class Event(BaseModel):
    event_id: str
    location: dict  # {latitude: float, longitude: float}
    timestamp: datetime
    event_type: str
    expected_crowd_size: int

class NetworkPerformance(BaseModel):
    node_id: str
    timestamp: datetime
    metrics: dict  # Various performance metrics

class Issue(BaseModel):
    issue_id: str
    node_id: str
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
    events: List[Event]
    performance_data: List[NetworkPerformance]
    summary: str
