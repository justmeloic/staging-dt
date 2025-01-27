from datetime import datetime
from typing import List, Dict, Optional
import numpy as np

from google.cloud import bigquery
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from pydantic import BaseModel, Field
from app.models import (
    Alarm,
    Location,
    IssueStatus,
    Issue,
    IssueUpdate,
    NodeData,
    PerformanceData,
    Event,
)
import app.mock_data as mock_data
from event_scout.firestore_helper import (
    get_locations,
    db as EVENT_DB,
)
import json


class DataManager:
    def __init__(self, project_id: str, manager_db: str = "ran-guardian-data-manager"):
        self.manager_db = firestore.Client(project=project_id, database=manager_db)
        self.bq_client = bigquery.Client(project=project_id, location="europe-west3")
        self.event_db = EVENT_DB

        self.perf_db = f"{project_id}.netinsights_mvp.performance"
        self.alarm_db = f"{project_id}.netinsights_mvp.alarms"
        self.infra_db = f"{project_id}.netinsights_mvp.infrastructure"

    # -------------------
    # Issue management
    # -------------------

    async def get_issues(self) -> List[Issue]:
        issues_ref = self.manager_db.collection("issues")
        docs = issues_ref.stream()
        return [Issue(**doc.to_dict()) for doc in docs]

    async def get_issue(self, issue_id: str) -> Optional[Issue]:
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()
        if doc.exists:
            return Issue(**doc.to_dict())
        return None

    async def create_issue(self, issue: Dict) -> str:
        issue_ref = self.manager_db.collection("issues").document()
        issue["issue_id"] = issue_ref.id
        issue_ref.set(issue)
        return issue_ref.id

    async def update_issue(self, issue_id: str, updates: Dict) -> bool:
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        issue_ref.update(updates)
        return True

    async def get_issue_stats(self) -> Dict:
        stats = {}
        issues_ref = self.manager_db.collection("issues")
        for status in IssueStatus:
            stats[status.value] = (
                issues_ref.where(filter=FieldFilter("status", "==", status.value))
                .count()
                .get("count")
            )
        return stats

    # -------------------
    # Event management
    # -------------------

    async def get_events_by_location(
        self,
        location: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_num_event: Optional[int] = 10,
    ):
        events_ref = self.event_db.collection(location)
        query = events_ref
        # TODO: rewrite logic
        # should enable query by time range

        if start_time:
            ...  # query = query.where(filter=FieldFilter("start_date", ">=", start_time))
        if end_time:
            ...  # query = query.where(filter=FieldFilter("end_date", "<=", end_time))
        all_events = []
        for doc in query.stream():
            event = Event.from_firestore_doc(doc.id, doc.to_dict())
            if event:
                all_events.append(event)
            if len(all_events) >= max_num_event:
                break

        return all_events

    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        node_id: Optional[str] = None,
        max_num_event: Optional[int] = 3,
    ) -> List[Event]:

        if location:
            return self.get_events_by_location(location, start_time, end_time)

        else:
            locations = get_locations()
            events = []
            for location in locations:
                # TODO: controls how many events we should get
                if len(events) > max_num_event:
                    break
                events.extend(
                    await self.get_events_by_location(
                        location, start_time, end_time, max_num_event
                    )
                )
            return events

    async def get_event(self, event_id: str) -> Optional[Event]:
        event_ref = self.event_db.collection("events").document(event_id)
        doc = event_ref.get()
        if doc.exists:
            return Event(**doc.to_dict())
        return None

    async def update_event(self, event_id: str, updates: Dict) -> bool:
        event_ref = self.manager_db.collection("events").document(event_id)
        event_ref.update(updates)
        return True

    async def get_events_stats(self) -> Dict:
        # TODO: rewrite logic
        stats = {}
        events_ref = self.manager_db.collection("events")
        for doc in events_ref.stream():  # Stream for potentially large datasets
            event_type = doc.to_dict().get("event_type")
            stats[event_type] = stats.get(event_type, 0) + 1
        return stats

    # -------------------
    # Perf data
    # -------------------

    async def get_performance_data(
        self, node_id: str, n_record: int = 4
    ) -> Optional[PerformanceData]:

        # should use data in bigquery prepared by netinsight team, but for now we use mock data
        QUERY = f"""
        SELECT OSS_NodeID_Generic, DATE_KEY_30, 4G_ERI_Max_RRC_Conn_User, 4G_ERI_RRC_Estab_SR_percent 
        FROM `{self.perf_db}`
        WHERE OSS_NodeID_Generic = '{node_id}'
        ORDER BY DATE_KEY_30 DESC
        LIMIT {4}
        """
        # query_job = self.bq_client.query(QUERY)  # API request
        # df = query_job.to_dataframe()

        # TODO: rewrite MOCK
        perf = mock_data.generate_performance_data([node_id])[0]
        return perf

    # -------------------
    # Alarm data
    # -------------------

    async def get_alarms(self, node_id: str) -> List[Alarm]:
        QUERY = """
        """
        # TODO: rewrite MOCK
        alarms = mock_data.generate_alarms([node_id], [], num_alarms=5)
        return alarms

    # -------------------
    # Node data
    # -------------------

    async def get_node_data(self, node_id: str) -> Optional[NodeData]:
        # TODO: rewrite logic
        node_ref = self.manager_db.collection("nodes").document(node_id)
        doc = node_ref.get()
        if doc.exists:
            return NodeData(**doc.to_dict())
        return None

    async def get_nearby_nodes(
        self, location: Location, radius: int = 300
    ) -> List[NodeData]:
        """Get node IDs near a specific location"""

        QUERY = """
        SELECT
        MS_MSRBS_STO_KNG AS site_id,
        CELLS_4G,
        ST_X(GEO_COORDINATES) AS longitude,
        ST_Y(GEO_COORDINATES) AS latitude,
        MS_MSRBS_HERSTELLER
        FROM
        `de1000-dev-mwc-ran-agent.ran_guardian.inventory`
        WHERE
        ST_DISTANCE(
            GEO_COORDINATES, -- Replace longitude and latitude with your table's column names
            ST_GEOGPOINT({lng}, {lat}) -- Replace with your target longitude and latitude (e.g., Chicago)
        ) <= {radius} -- 5000 meters = 5 kilometers
        AND CELLS_4G IS NOT NULL ; 
        """
        query_job = self.bq_client.query(
            QUERY.format(lng=location.longitude, lat=location.latitude, radius=radius)
        )  # API request
        df = query_job.to_dataframe()
        node_ids_list = df["CELLS_4G"].apply(
            lambda x: x.replace("[", "").replace("]", "").replace("'", "").split(", ")
        )
        nodes = []
        site_ids = df["site_id"].to_list()
        for node_ids, site_id in zip(node_ids_list, site_ids):
            for node_id in node_ids:
                nodes.append(
                    NodeData(
                        node_id=node_id,
                        site_id=site_id,
                        capacity=np.random.randint(100, 500),
                    )  # mock the capacity for now
                )
        return nodes
