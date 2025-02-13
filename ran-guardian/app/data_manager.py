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
    EventRisk,
    Issue,
    IssueStatus,
    IssueUpdate,
    Location,
    NodeData,
    NodeSummary,
    PerformanceData,
    Site,
    StateSnapshot,
    Task,
)
from event_scout.firestore_helper import db as EVENT_DB
from event_scout.firestore_helper import get_locations
from google.cloud import bigquery, firestore, storage
from google.cloud.firestore_v1.base_query import FieldFilter

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
        logger.warning(f"Could not parse date string: {date_str}")
        return False

    res = True
    if start_date:
        res = res & (date_object >= start_date)
    if end_date:
        res = res & (date_object <= end_date)
    return res


class DataManager:
    def __init__(self, project_id: str, manager_db: str = "ran-guardian-data-manager"):
        logger.info("[DataManager.__init__]: start ...")
        self.manager_db = firestore.Client(project=project_id, database=manager_db)
        self.bq_client = bigquery.Client(project=project_id, location="europe-west3")
        self.bq_event_db_name = f"{project_id}.events_db_de.people_events"
        self.event_db = EVENT_DB
        logger.info("[DataManager.__init__]: finished with data manager initialized")

    # -------------------
    # Issue management
    # -------------------

    async def get_issues(self) -> List[Issue]:
        """Retrieves all issue data from Firestore and returns a list of Issues."""
        logger.info("[get_issues]: start ...")
        issues_ref = self.manager_db.collection("issues")
        docs = issues_ref.stream()

        issues = []
        for doc in docs:
            issue = Issue.from_firestore_doc(doc)
            if issue:
                issues.append(issue)
        logger.info(f"[get_issues]: finished with {len(issues)} issues retrieved")
        return issues

    async def sort_issues(self):
        """
        sort the issues based on their start and end date,
        """
        logger.info("[sort_issues]: start ...")
        # sorting logic to be implemented
        logger.info("[sort_issues]: finished with issues sorting logic not implemented")
        pass

    async def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieves issue data from Firestore"""
        logger.info(f"[get_issue]: start ...")
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()
        if not doc or not doc.exists:
            logger.info(f"[get_issue]: finished with issue {issue_id} not found")
            return None
        issue = Issue.from_firestore_doc(doc)
        if issue:
            logger.info(f"[get_issue]: finished with issue {issue_id} retrieved")
            return issue
        else:
            logger.warning(
                f"[get_issue]: issue {issue_id} hasn't been correctly parsed!"
            )
            return None

    async def create_issue(
        self, event: Event, event_risk: EventRisk, summary: str
    ) -> str:
        # this function is probably not working well
        """Creates a new issue in Firestore with data provided in the dictionary. Returns issue_id."""
        logger.info(f"[create_issue]: start ...")
        issue_id = event.event_id  # using the same id as even
        event.issue_id = issue_id

        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()

        if doc.exists:
            issue_dict = doc.to_dict()
            current_status = issue_dict["status"]
            if current_status == IssueStatus.RESOLVED.value:
                # Reopen
                updates = {
                    "status": IssueStatus.ANALYZING,
                    "updated_at": datetime.now(),
                    "event_risk": event_risk.model_dump(),
                    "summary": summary,
                }
                issue_ref.update(updates)
                logger.info(f"[create_issue]: finished with issue {issue_id} reopened")
            else:
                logger.info(
                    f"[create_issue]: finished with issue {issue_id} already exists, no action taken"
                )
        else:
            issue = Issue(
                issue_id=issue_id,
                event_id=event.event_id,
                node_ids=[
                    s.node_id for s in event_risk.node_summaries if s.is_problematic
                ],
                event_risk=event_risk,
                summary=summary,
                status=IssueStatus.NEW,
                created_at=datetime.now(),
            )
            issue_ref.set(issue.model_dump())
            logger.info(f"[create_issue]: finished with issue {issue_id} created")

        return issue_ref.id

    async def create_issue_from_model(self, issue: Issue) -> str:
        """Creates an issue in Firestore from an instance of the Issue model"""
        logger.info("[create_issue_from_model]: start ...")
        issue_ref = self.manager_db.collection("issues").document(issue.issue_id)
        issue_ref.set(issue.model_dump())
        logger.info(
            f"[create_issue_from_model]: finished with issue {issue.issue_id} created from model"
        )
        return issue_ref.id

    async def delete_issue(self, issue_id: str):
        logger.info(f"[delete_issue]: start ...")
        await self.manager_db.collection("issues").document(
            issue_id
        ).delete()  # added await
        logger.info(f"[delete_issue]: finished with issue {issue_id} deleted")

    async def update_issue(self, issue: str | Issue, updates: Dict) -> bool:
        """Updates issue document with `issue_id` in Firestore with the new data"""
        if isinstance(issue, Issue):
            issue_id = issue.issue_id
        else:
            issue_id = issue

        logger.info(f"[update_issue]: start ...")
        updates["updated_at"] = datetime.now()
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        issue_ref.update(updates)
        logger.info(f"[update_issue]: finished with issue {issue_id} updated")
        return True

    async def get_issue_stats(self) -> Dict:
        """Retrieves statistics on the number of issues for each status."""
        logger.info("[get_issue_stats]: start ...")
        stats = {}
        issues_ref = self.manager_db.collection("issues")
        for status in IssueStatus:
            count = (
                issues_ref.where(filter=FieldFilter("status", "==", status.value))
                .count()
                .get("count")
            )
            stats[status.value] = count
        logger.info(
            f"[get_issue_stats]: finished with stats for {len(IssueStatus)} issue statuses retrieved"
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
        logger.info(f"[get_events_by_location]: start ...")
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
        logger.info(
            f"[get_events_by_location]: finished with {len(all_events)} events retrieved for location {location}"
        )
        return all_events

    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        max_num_event: Optional[int] = MAX_NUM_EVENTS,
    ):
        logger.info("[get_events]: start ...")
        event_collection = self.manager_db.collection("events")
        if start_time:
            start_time_str = start_time.strftime("%Y-%m-%d")
            event_collection = event_collection.where(
                filter=FieldFilter("start_date", ">=", start_time_str)
            )
        if end_time:
            end_time_str = end_time.strftime("%Y-%m-%d")
            event_collection = event_collection.where(
                filter=FieldFilter("start_date", "<=", end_time_str)
            )  # we can only filter on the same field , i.e. start date due to firestore query limits
        event_collection = event_collection.order_by("start_date").order_by("end_date")

        events = []
        for doc in event_collection.stream():
            try:
                event = Event.from_firestore_doc(doc.id, doc.to_dict())
                events.append(event)
                if max_num_event and (len(events) >= max_num_event):
                    break
            except Exception as e:
                logger.error(f"parsing event got error {e}")
        logger.info(f"[get_events]: finished with {len(events)} events retrieved")
        return events

    async def get_event(self, event_id: str) -> Optional[Event]:
        logger.info(f"[get_event]: start ...")
        event_ref = self.manager_db.collection("events").document(event_id)
        doc = event_ref.get()
        if doc.exists:
            event = Event.from_firestore_doc(doc.id, doc.to_dict())
            logger.info(f"[get_event]: finished with event {event_id} retrieved")
            return event
        logger.info(f"[get_event]: finished with event {event_id} not found")
        return None

    async def update_event(self, event_id: str, updates: Dict) -> bool:
        logger.info(f"[update_event]: start ...")
        event_ref = self.manager_db.collection("events").document(event_id)
        event_ref.update(updates)
        logger.info(f"[update_event]: finished with event {event_id} updated")
        return True

    async def get_events_stats(self) -> Dict:
        # TODO: rewrite logic to fully match the life-cycle of events and issues
        logger.info("[get_events_stats]: start ...")
        stats = {}
        events_ref = self.manager_db.collection("events")
        event_count = 0
        for doc in events_ref.stream():  # Stream for potentially large datasets
            event_type = doc.to_dict().get("status", "new")
            stats[event_type] = stats.get(event_type, 0) + 1
            event_count += 1
        logger.info(
            f"[get_events_stats]: finished with stats for {event_count} events retrieved"
        )
        return stats

    # -------------------
    # Perf data
    # -------------------

    async def get_performance_data(
        self, node_id: str, n_record: int = 4
    ) -> List[PerformanceData]:
        # TODO: need to be able to retrieve data for a list of node
        logger.debug(f"[get_performance_data]: start ...")

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
        perf = []
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=30
            )
            if response.status_code == 200:
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
            else:
                pass  # handled in the finally block
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching performance data from {url}")
        finally:
            logger.debug(
                f"[get_performance_data]: finished with {len(perf)} performance data records retrieved for node {node_id}"
            )
            return perf

    # -------------------
    # Alarm data
    # -------------------

    async def get_alarms(self, node_id: str) -> List[Alarm]:
        logger.debug(f"[get_alarms]: start ...")
        payload = {
            "node_id": node_id,
        }

        url = MOCK_DATA_SERVER_URL + "/alarms"
        headers = {"Content-Type": "application/json"}
        alarms = []
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=30
            )
            if response.status_code == 200:
                data = json.loads(response.content)
                for d in data:
                    alarms.append(Alarm(**d))
            else:
                pass  # handled in finally block
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching alarm data from {url}")
        finally:
            logger.debug(
                f"[get_alarms]: finished with {len(alarms)} alarms retrieved for node {node_id}"
            )
            return alarms

        ...
        # time range is now to the next

    # -------------------
    # Node data
    # -------------------

    async def get_nearby_site(
        self, location: Location, radius: int = 300
    ) -> list[Site]:
        """Get node IDs near a specific location"""

        logger.info("[get_nearby_site]: start ...")
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
        formatted_query = QUERY.format(
            lng=location.longitude, lat=location.latitude, radius=radius
        )
        query_job = self.bq_client.query(formatted_query)  # API request
        df = query_job.to_dataframe()
        node_ids_list = df["CELLS_4G"].apply(
            lambda x: x.replace("[", "").replace("]", "").replace("'", "").split(", ")
        )
        sites = []
        site_ids = df["site_id"].to_list()
        for node_ids, site_id in zip(node_ids_list, site_ids):
            sites.append(
                Site(
                    site_id=site_id,
                    nodes=[
                        NodeData(
                            node_id=node_id,
                            site_id=site_id,
                            capacity=np.random.randint(100, 500),
                        )
                        for node_id in node_ids
                    ],
                )
            )
        logger.info(f"[get_nearby_site]: finished with {len(sites)} sites retrieved")
        return sites

    async def get_nearby_nodes(
        self, location: Location, radius: int = 300
    ) -> List[NodeData]:
        """Get node IDs near a specific location"""

        logger.info("[get_nearby_nodes]: start ...")
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
        AND CELLS_4G IS NOT NULL
        LIMIT 5;
        """
        formatted_query = QUERY.format(
            lng=location.longitude, lat=location.latitude, radius=radius
        )
        query_job = self.bq_client.query(formatted_query)  # API request
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
        logger.info(f"[get_nearby_nodes]: finished with {len(nodes)} nodes retrieved")
        return nodes

    # -------------------
    # Agent state management
    # -------------------
    async def save_agent_checkpoint(
        self,
        issue_id: str,
        node_id: str,
        snapshot: StateSnapshot,
        history: Optional[AgentHistory] = None,
    ) -> None:
        """Save agent workflow state and history (chat, tasks)"""
        logger.info(
            f"[save_agent_checkpoint]: start for issue_id: {issue_id}, node_id: {node_id}..."
        )

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_{node_id}_snapshot.pkl"
        )
        history_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_{node_id}_history.pkl"
        )
        logger.debug(
            f"Snapshot blob path: {snapshot_blob.path}, history blob path: {history_blob.path}"
        )

        chat_history = history.chat_history
        task_history = history.task_history

        snapshot_blob.upload_from_string(pickle.dumps(snapshot))
        history_blob.upload_from_string(pickle.dumps(chat_history))

        await self.update_issue(
            issue_id, {"tasks": [t.model_dump_json() for t in task_history]}
        )
        logger.info(
            f"[save_agent_checkpoint]: finished with agent checkpoint saved for issue {issue_id} and node {node_id}"
        )

    async def load_agent_snapshot(self, issue_id: str, node_id: str) -> StateSnapshot:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        logger.info(f"[load_agent_snapshot]: start ...")
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_{node_id}_snapshot.pkl"
        )
        logger.debug(f"Snapshot blob path: {snapshot_blob.path}")

        if not snapshot_blob.exists():
            logger.info(
                f"[load_agent_snapshot]: finished with snapshot not found for issue {issue_id}"
            )
            return None

        snapshot_data = pickle.loads(snapshot_blob.download_as_bytes())
        logger.info(
            f"[load_agent_snapshot]: finished with snapshot loaded for issue {issue_id}"
        )
        return snapshot_data

    async def load_agent_history(
        self, issue_id: str, node_id: str
    ) -> Optional[AgentHistory]:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        logger.info(f"[load_agent_history]: start ...")
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")

        bucket = client.bucket(bucket_name)
        chat_history_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_{node_id}_history.pkl"
        )

        if not chat_history_blob.exists():
            logger.info(
                f"[load_agent_history]: finished with history not found for issue {issue_id}"
            )
            return None

        chat_history_data = pickle.loads(chat_history_blob.download_as_bytes())

        issue = await self.get_issue(issue_id)
        if not issue:
            task_history_data = []
        else:
            task_history_data = issue.tasks

        agent_history = AgentHistory(
            chat_history=chat_history_data,
            task_history=task_history_data,
        )
        logger.info(
            f"[load_agent_history]: finished with history loaded for issue {issue_id}"
        )
        return agent_history

    # -------------------
    # API utils
    # -------------------

    async def build_get_issue_response_payload(
        self, issue_or_event_id: str
    ) -> Dict | None:
        """Build the response payload for the GET issue request by combining event and issue data"""
        logger.info("[build_get_issue_response_payload]: start ...")
        event = await self.get_event(issue_or_event_id)
        issue = None  # Initialize issue to None in case only event is found at first

        if not event:
            issue = await self.get_issue(issue_or_event_id)
            if not issue:
                logger.info(
                    f"[build_get_issue_response_payload]: finished with neither issue nor event found for id {issue_or_event_id}"
                )
                return None  # Return None as requested when neither issue nor event is found
            event_id = issue.event_id
            event = await self.get_event(event_id)
        else:
            issue_id = event.issue_id
            if issue_id:  # Only fetch issue if issue_id exists
                issue = await self.get_issue(issue_id)

        payload = {
            "event": event.model_dump() if event else {},
            "issue": (
                issue.model_dump() if issue else {}
            ),  # Only include issue if it's not None
        }
        logger.info("[build_get_issue_response_payload]: finished with payload created")
        return payload
