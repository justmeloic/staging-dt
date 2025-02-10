import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import requests
from app.models import (
    AgentHistory,
    Alarm,
    Event,
    Issue,
    IssueStatus,
    IssueUpdate,
    Location,
    NodeData,
    PerformanceData,
    Task,
)
from event_scout.firestore_helper import db as EVENT_DB
from event_scout.firestore_helper import get_locations
from google.cloud import bigquery, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter
from langchain_core.load import dumpd, load
from langchain_core.messages import BaseMessage
from langgraph.types import StateSnapshot
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

MOCK_DATA_SERVER_URL = os.getenv("MOCK_DATA_SERVER_URL")
TIME_INTERVAL = int(os.getenv("TIME_INTERVAL"))
MAX_NUM_EVENTS = int(os.getenv("MAX_NUM_EVENTS", 10))


# utility functions.. TODO: Move to utilities
def parse_date(date_str: str):
    try:
        date_object = datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_object
    except Exception as e:
        return None


def check_date(
    date_str: str,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    # Potentially we can use Gemini to parse date and time in a more flexible way
    date_object = parse_date(date_str)

    if not date_object:
        return False

    res = True
    if start_date:
        res = res & (date_object >= start_date)
    if end_date:
        res = res & (date_object <= end_date)
    return res


class DataManager:
    def __init__(self, project_id: str, manager_db: str = "ran-guardian-data-manager"):
        self.manager_db = firestore.Client(project=project_id, database=manager_db)
        self.bq_client = bigquery.Client(project=project_id, location="europe-west3")
        self.bq_event_db_name = f"{project_id}.events_db_de.people_events"
        self.event_db = EVENT_DB

    # -------------------
    # Issue management
    # -------------------

    async def get_issues(self) -> List[Issue]:
        """Retrieves all issue data from Firestore and returns a list of Issues."""
        issues_ref = self.manager_db.collection("issues")
        docs = issues_ref.stream()

        issues = []
        for doc in docs:
            doc_dict = doc.to_dict()
            if "tasks" in doc_dict and doc_dict["tasks"]:
                doc_dict["tasks"] = [
                    Task.model_validate_json(t) for t in doc_dict["tasks"]
                ]
            issues.append(Issue(**doc_dict))

        return issues

    async def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieves issue data from Firestore"""
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()
        if not doc or not doc.exists:
            return None
        doc_dict = doc.to_dict()
        if "tasks" in doc_dict:
            doc_dict["tasks"] = [Task.model_validate_json(t) for t in doc_dict["tasks"]]

        return Issue(**doc_dict)

    async def create_issue(self, event: Dict) -> str:
        """Creates a new issue in Firestore with data provided in the dictionary. Returns issue_id."""
        logger.info("Creating issue in Firestore or checking for existing one")
        issue_id = event.get("event_id")
        event["issue_id"] = issue_id

        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()

        if doc.exists:
            logger.info("Getting existing doc...")
            issue_dict = doc.to_dict()
            current_status = issue_dict["status"]
            logger.info(f"Found existing issue with status {current_status}")
            if current_status == IssueStatus.RESOLVED.value:
                # Reopen
                updates = {
                    "status": IssueStatus.NEW,
                    "created_at": firestore.SERVER_TIMESTAMP,
                    "updated_at": firestore.SERVER_TIMESTAMP,
                }
                issue_ref.update(updates)
            else:
                logger.info(
                    f"Issue already exists for event. Current status is {current_status}"
                )
        else:
            logger.info("Creating new issue for event")
            issue_ref.set(event)

        return issue_ref.id

    async def update_issue(self, issue_id: str, updates: Dict) -> bool:
        """Updates issue document with `issue_id` in Firestore with the new data"""
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        issue_ref.update(updates)
        return True

    async def get_issue_stats(self) -> Dict:
        """Retrieves statistics on the number of issues for each status.

        This method queries the Firestore database to count the number of issues
        associated with each possible value of the `IssueStatus` enum.

        Returns:
            A dictionary where keys represent issue statuses (as strings) and values
            are the corresponding counts of issues with that status.
        """
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

    # use gemini to parse date

    async def get_events_by_location(
        self,
        location: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_num_event: Optional[int] = MAX_NUM_EVENTS,
    ):
        events_ref = self.event_db.collection(location)
        query = events_ref

        all_events = []
        for doc in query.stream():
            # We only collect events whose start and end dates are well formated
            if check_date(doc.get("start_date"), start_time, end_time) & check_date(
                doc.get("end_date"), start_time, end_time
            ):
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
        max_num_event: Optional[int] = MAX_NUM_EVENTS,
    ) -> List[Event]:

        query = f"""
        SELECT * FROM `{self.bq_event_db_name}` as e
        where SAFE_CAST(e.start_date AS DATE) IS NOT NULL
        """
        if start_time:
            start_time_str = start_time.strftime("%Y-%m-%d")
            query = (
                query
                + f""" AND SAFE_CAST(e.start_date AS DATE) >= DATE('{start_time_str}')"""
            )
        if end_time:
            end_time_str = end_time.strftime("%Y-%m-%d")
            query = (
                query
                + f""" AND SAFE_CAST(e.end_date AS DATE) <= DATE('{end_time_str}')"""
            )
        if max_num_event:
            query = query + f""" LIMIT {max_num_event}"""

        query = query + ";"

        try:
            query_job = self.bq_client.query(query)
            query_result = query_job.result()
            events = []
            for row in query_result:
                row_dict = dict(row)
                event = Event.from_firestore_doc(row_dict["event_id"], row_dict)
                events.append(event)
            return events

        except Exception as e:
            print(e)  # need better error management
            return []

    async def get_event(self, event_id: str) -> Optional[Event]:
        event_ref = self.manager_db.collection("events").document(event_id)
        doc = event_ref.get()
        if doc.exists:
            return Event.from_firestore_doc(doc.id, doc.to_dict())
        return None

    async def update_event(self, event_id: str, updates: Dict) -> bool:
        event_ref = self.manager_db.collection("events").document(event_id)
        event_ref.update(updates)
        return True

    async def get_events_stats(self) -> Dict:
        # TODO: rewrite logic to fully match the life-cycle of events and issues
        stats = {}
        events_ref = self.manager_db.collection("events")
        for doc in events_ref.stream():  # Stream for potentially large datasets
            event_type = doc.to_dict().get("status", "new")
            stats[event_type] = stats.get(event_type, 0) + 1
        return stats

    # -------------------
    # Perf data
    # -------------------

    async def get_performance_data(
        self, node_id: str, n_record: int = 4
    ) -> List[PerformanceData]:

        # Using the mock data generator
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=n_record * int(TIME_INTERVAL))
        payload = {
            "node_id": node_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }

        url = MOCK_DATA_SERVER_URL + "/performances"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url, headers=headers, data=json.dumps(payload), timeout=30
        )
        if response.status_code == 200:
            perf = []
            data = json.loads(response.content)
            for d in data:
                perf.append(
                    PerformanceData(
                        node_id=d["node_id"],
                        timestamp=d["timestamp"],
                        rrc_max_users=d["Max_RRC_Conn_User"],
                        rrc_setup_sr_pct=d["RRC_Estab_SR_pct"],
                    )
                )
            return perf
        else:
            logger.warning("Performance data not found")
            return []

    # -------------------
    # Alarm data
    # -------------------

    async def get_alarms(self, node_id: str) -> List[Alarm]:
        payload = {
            "node_id": node_id,
        }

        url = MOCK_DATA_SERVER_URL + "/alarms"
        headers = {"Content-Type": "application/json"}
        response = requests.get(
            url, headers=headers, data=json.dumps(payload), timeout=30
        )
        if response.status_code == 200:
            alarms = []
            data = json.loads(response.content)
            for d in data:
                alarms.append(Alarm(**d))
            return alarms
        else:
            logger.warning("Alarm data not found")
            return []

        ...
        # time range is now to the next

    # -------------------
    # Node data
    # -------------------

    async def get_nearby_nodes(
        self, location: Location, radius: int = 300
    ) -> List[NodeData]:
        """Get node IDs near a specific location"""

        logger.info("Fetching nearby nodes...")
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

    # -------------------
    # Agent state management
    # -------------------
    async def save_agent_checkpoint(
        self,
        issue_id: str,
        snapshot: StateSnapshot,
        history: Optional[AgentHistory] = None,
    ) -> None:
        """Save agent workflow state and history (chat, tasks)"""

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_snapshot.pkl")
        history_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_history.pkl")

        chat_history = history.chat_history
        task_history = history.task_history

        snapshot_blob.upload_from_string(pickle.dumps(snapshot))
        history_blob.upload_from_string(pickle.dumps(chat_history))

        await self.update_issue(
            issue_id, {"tasks": [t.model_dump_json() for t in task_history]}
        )

    async def load_agent_snapshot(self, issue_id: str) -> StateSnapshot:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_snapshot.pkl")

        if not snapshot_blob.exists():
            return None

        snapshot_data = pickle.loads(snapshot_blob.download_as_bytes())

        return snapshot_data

    async def load_agent_history(self, issue_id: str) -> Optional[AgentHistory]:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        bucket = client.bucket(bucket_name)
        chat_history_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_history.pkl"
        )

        if not chat_history_blob.exists():
            return None

        chat_history_data = pickle.loads(chat_history_blob.download_as_bytes())

        issue = await self.get_issue(issue_id)
        if not issue:
            logger.warning(
                f"Issue was {issue_id} not found, could not retrieve task list"
            )
            task_history_data = []
        else:
            task_history_data = issue.tasks

        return AgentHistory(
            chat_history=chat_history_data,
            task_history=task_history_data,
        )
