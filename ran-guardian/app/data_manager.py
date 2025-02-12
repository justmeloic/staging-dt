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
MAX_NUM_EVENTS = int(os.getenv("MAX_NUM_EVENTS", 1))


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
        logger.info(
            f"Starting function: DataManager.__init__, project_id: {project_id}, manager_db: {manager_db}"
        )
        self.manager_db = firestore.Client(project=project_id, database=manager_db)
        self.bq_client = bigquery.Client(project=project_id, location="europe-west3")
        self.bq_event_db_name = f"{project_id}.events_db_de.people_events"
        self.event_db = EVENT_DB

    # -------------------
    # Issue management
    # -------------------

    async def get_issues(self) -> List[Issue]:
        """Retrieves all issue data from Firestore and returns a list of Issues."""
        logger.info(f"Starting function: DataManager.get_issues")
        issues_ref = self.manager_db.collection("issues")
        docs = issues_ref.stream()

        issues = []
        for doc in docs:
            doc_dict = doc.to_dict()

            try:
                if "tasks" in doc_dict and doc_dict["tasks"]:
                    doc_dict["tasks"] = [
                        Task.model_validate_json(t) for t in doc_dict["tasks"]
                    ]
                if "event_risk" in doc_dict and doc_dict["event_risk"]:
                    node_sum = doc_dict["event_risk"]["node_summaries"]
                    node_sum = [NodeSummary.model_validate(n) for n in node_sum]
                    doc_dict["event_risk"]["node_summaries"] = node_sum
                    doc_dict["event_risk"] = EventRisk.model_validate(
                        doc_dict["event_risk"]
                    )

                issues.append(Issue(**doc_dict))
            except Exception as e:
                logger.error(f"parsing issue got error {e}")
        logger.info(f"Retrieved {len(issues)} issues from Firestore")
        return issues

    async def sort_issues(self):
        """
        sort the issues based on their start and end date,
        """
        pass

    async def get_issue(self, issue_id: str) -> Optional[Issue]:
        """Retrieves issue data from Firestore"""
        logger.info(f"Starting function: DataManager.get_issue, issue_id: {issue_id}")
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        doc = issue_ref.get()
        if not doc or not doc.exists:
            logger.info(f"Issue with id: {issue_id} not found")
            logger.info(f"Finished function: DataManager.get_issue, issue not found")
            return None
        doc_dict = doc.to_dict()
        try:
            if "tasks" in doc_dict and doc_dict["tasks"]:
                doc_dict["tasks"] = [
                    Task.model_validate_json(t) for t in doc_dict["tasks"]
                ]
            if "event_risk" in doc_dict and doc_dict["event_risk"]:
                node_sum = doc_dict["event_risk"]["node_summaries"]
                node_sum = [NodeSummary.model_validate(n) for n in node_sum]
                doc_dict["event_risk"]["node_summaries"] = node_sum
                doc_dict["event_risk"] = EventRisk.model_validate(
                    doc_dict["event_risk"]
                )
        except Exception as e:
            logger.error(f"parsing issue got error {e}")

        issue = Issue(**doc_dict)
        logger.info(f"Retrieved issue with id: {issue_id}")
        logger.info(f"Finished function: DataManager.get_issue")
        return issue

    async def create_issue(
        self, event: Event, event_risk: EventRisk, summary: str
    ) -> str:
        # this function is probably not working well
        """Creates a new issue in Firestore with data provided in the dictionary. Returns issue_id."""
        logger.info(
            f"Starting function: DataManager.create_issue, event_id: {event.event_id}"
        )
        issue_id = event.event_id  # using the same id as even
        event.issue_id = issue_id

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
                    "status": IssueStatus.ANALYZING,
                    "updated_at": datetime.now(),
                    "event_risk": event_risk.model_dump(),
                    "summary": summary,
                }
                issue_ref.update(updates)
                logger.info(f"Reopened issue {issue_id}, setting status to ANALYZING")
            else:
                logger.info(
                    f"Issue already exists for event. Current status is {current_status}, no action taken"
                )
        else:
            logger.info("Creating new issue for event")
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
            logger.info(f"Created new issue with id: {issue_id}")

        logger.info(
            f"Finished function: DataManager.create_issue, issue_id: {issue_id}"
        )
        return issue_ref.id

    async def create_issue_from_model(self, issue: Issue) -> str:
        """Creates an issue in Firestore from an instance of the Issue model"""
        issue_ref = self.manager_db.collection("issues").document(issue.issue_id)
        issue_ref.set(issue.model_dump())
        return issue_ref.id

    async def delete_issue(self, issue_id: str):
        self.manager_db.collection("issues").document(issue_id).delete()

    async def update_issue(self, issue: str | Issue, updates: Dict) -> bool:
        """Updates issue document with `issue_id` in Firestore with the new data"""
        if isinstance(issue, Issue):
            issue_id = issue.issue_id
        else:
            issue_id = issue

        logger.info(
            f"Starting function: DataManager.update_issue, issue_id: {issue_id}, updates: {updates}"
        )
        updates["updated_at"] = datetime.now()
        issue_ref = self.manager_db.collection("issues").document(issue_id)
        issue_ref.update(updates)
        logger.info(f"Updated issue with id: {issue_id} with data: {updates}")
        return True

    async def get_issue_stats(self) -> Dict:
        """Retrieves statistics on the number of issues for each status.

        This method queries the Firestore database to count the number of issues
        associated with each possible value of the `IssueStatus` enum.

        Returns:
            A dictionary where keys represent issue statuses (as strings) and values
            are the corresponding counts of issues with that status.
        """
        logger.info(f"Starting function: DataManager.get_issue_stats")
        stats = {}
        issues_ref = self.manager_db.collection("issues")
        for status in IssueStatus:
            count = (
                issues_ref.where(filter=FieldFilter("status", "==", status.value))
                .count()
                .get("count")
            )
            stats[status.value] = count
            logger.debug(f"Issue status: {status.value}, count: {count}")
        logger.info(f"Issue statistics: {stats}")
        logger.info(f"Finished function: DataManager.get_issue_stats")
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
        logger.info(
            f"Starting function: DataManager.get_events_by_location, location: {location}, start_time: {start_time}, end_time: {end_time}, max_num_event: {max_num_event}"
        )
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
                    logger.info(f"Reached maximum number of events: {max_num_event}")
                    break
        logger.info(f"Retrieved {len(all_events)} events for location: {location}")
        logger.info(f"Finished function: DataManager.get_events_by_location")
        return all_events

    async def get_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        location: Optional[str] = None,
        max_num_event: Optional[int] = MAX_NUM_EVENTS,
    ):
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
        return events

    async def get_event(self, event_id: str) -> Optional[Event]:
        logger.info(f"Starting function: DataManager.get_event, event_id: {event_id}")
        event_ref = self.manager_db.collection("events").document(event_id)
        doc = event_ref.get()
        if doc.exists:
            event = Event.from_firestore_doc(doc.id, doc.to_dict())
            logger.info(f"Retrieved event with id: {event_id}")
            logger.info(f"Finished function: DataManager.get_event")
            return event
        logger.info(f"Event with id: {event_id} not found")
        logger.info(f"Finished function: DataManager.get_event, event not found")
        return None

    async def update_event(self, event_id: str, updates: Dict) -> bool:
        logger.info(
            f"Starting function: DataManager.update_event, event_id: {event_id}, updates: {updates}"
        )
        event_ref = self.manager_db.collection("events").document(event_id)
        event_ref.update(updates)
        logger.info(f"Updated event with id: {event_id} with data: {updates}")
        logger.info(f"Finished function: DataManager.update_event")
        return True

    async def get_events_stats(self) -> Dict:
        # TODO: rewrite logic to fully match the life-cycle of events and issues
        logger.info(f"Starting function: DataManager.get_events_stats")
        stats = {}
        events_ref = self.manager_db.collection("events")
        for doc in events_ref.stream():  # Stream for potentially large datasets
            event_type = doc.to_dict().get("status", "new")
            stats[event_type] = stats.get(event_type, 0) + 1
            logger.debug(f"Event type: {event_type}, count: {stats[event_type]}")
        logger.info(f"Event statistics: {stats}")
        logger.info(f"Finished function: DataManager.get_events_stats")
        return stats

    # -------------------
    # Perf data
    # -------------------

    async def get_performance_data(
        self, node_id: str, n_record: int = 4
    ) -> List[PerformanceData]:
        # TODO: need to be able to retrieve data for a list of node
        logger.debug(
            f"Starting function: DataManager.get_performance_data, node_id: {node_id}, n_record: {n_record}"
        )

        # Using the mock data generator
        end_time = datetime.now()
        start_time = end_time - timedelta(minutes=n_record * int(TIME_INTERVAL))
        payload = {
            "node_id": node_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
        }
        logger.debug(f"Payload for performance data request: {payload}")

        url = MOCK_DATA_SERVER_URL + "/performances"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=30
            )
            logger.debug(
                f"Performance data request status code: {response.status_code}"
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
                logger.debug(
                    f"Retrieved {len(perf)} performance data records for node: {node_id}"
                )
                logger.debug(f"Finished function: DataManager.get_performance_data")
                return perf
            else:
                logger.warning(
                    f"Performance data not found for node: {node_id}, status code: {response.status_code}"
                )
                logger.warning(
                    f"Finished function: DataManager.get_performance_data, data not found"
                )
                return []
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching performance data from {url}")
            logger.info(
                f"Finished function: DataManager.get_performance_data with error"
            )
            return []

    # -------------------
    # Alarm data
    # -------------------

    async def get_alarms(self, node_id: str) -> List[Alarm]:
        logger.debug(f"Starting function: DataManager.get_alarms, node_id: {node_id}")
        payload = {
            "node_id": node_id,
        }
        logger.debug(f"Payload for alarm data request: {payload}")

        url = MOCK_DATA_SERVER_URL + "/alarms"
        headers = {"Content-Type": "application/json"}
        try:
            response = requests.post(
                url, headers=headers, data=json.dumps(payload), timeout=30
            )
            logger.debug(f"Alarm data request status code: {response.status_code}")
            if response.status_code == 200:
                alarms = []
                data = json.loads(response.content)
                for d in data:
                    alarms.append(Alarm(**d))
                logger.debug(f"Retrieved {len(alarms)} alarms for node: {node_id}")
                logger.debug(f"Finished function: DataManager.get_alarms")
                return alarms
            else:
                logger.warning(
                    f"Alarm data not found for node: {node_id}, status code: {response.status_code}"
                )
                logger.warning(
                    f"Finished function: DataManager.get_alarms, data not found"
                )
                return []
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error fetching alarm data from {url}")
            logger.debug(f"Finished function: DataManager.get_alarms with error")
            return []

        ...
        # time range is now to the next

    # -------------------
    # Node data
    # -------------------

    async def get_nearby_site(
        self, location: Location, radius: int = 300
    ) -> list[Site]:
        """Get node IDs near a specific location"""

        logger.info(
            f"Starting function: DataManager.get_nearby_site, location: {location}, radius: {radius}"
        )
        logger.info("Fetching nearby site...")
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
        logger.debug(f"BQ Query: {formatted_query}")
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
        logger.info(f"Retrieved {len(sites)} nearby sites")
        logger.info(f"Finished function: DataManager.get_nearby_site")
        return sites

    async def get_nearby_nodes(
        self, location: Location, radius: int = 300
    ) -> List[NodeData]:
        """Get node IDs near a specific location"""

        logger.info(
            f"Starting function: DataManager.get_nearby_nodes, location: {location}, radius: {radius}"
        )
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
        AND CELLS_4G IS NOT NULL
        LIMIT 5;
        """
        formatted_query = QUERY.format(
            lng=location.longitude, lat=location.latitude, radius=radius
        )
        logger.debug(f"BQ Query: {formatted_query}")
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
        logger.info(f"Retrieved {len(nodes)} nearby nodes")
        logger.info(f"Finished function: DataManager.get_nearby_nodes")
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
        logger.info(
            f"Starting function: DataManager.save_agent_checkpoint, issue_id: {issue_id}"
        )

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")
        logger.debug(
            f"Bucket name: {bucket_name}, checkpoints location: {checkpoints_location}"
        )

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_snapshot.pkl")
        history_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_history.pkl")
        logger.debug(
            f"Snapshot blob path: {snapshot_blob.path}, history blob path: {history_blob.path}"
        )

        chat_history = history.chat_history
        task_history = history.task_history

        snapshot_blob.upload_from_string(pickle.dumps(snapshot))
        history_blob.upload_from_string(pickle.dumps(chat_history))
        logger.info(f"Saved agent snapshot and history to GCS for issue: {issue_id}")

        await self.update_issue(
            issue_id, {"tasks": [t.model_dump_json() for t in task_history]}
        )
        logger.info(f"Updated issue document with tasks history for issue: {issue_id}")
        logger.info(f"Finished function: DataManager.save_agent_checkpoint")

    async def load_agent_snapshot(self, issue_id: str) -> StateSnapshot:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        logger.info(
            f"Starting function: DataManager.load_agent_snapshot, issue_id: {issue_id}"
        )
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")
        logger.debug(
            f"Bucket name: {bucket_name}, checkpoints location: {checkpoints_location}"
        )

        bucket = client.bucket(bucket_name)
        snapshot_blob = bucket.blob(f"{checkpoints_location}/{issue_id}_snapshot.pkl")
        logger.debug(f"Snapshot blob path: {snapshot_blob.path}")

        if not snapshot_blob.exists():
            logger.info(f"No snapshot found for issue: {issue_id}")
            logger.info(
                f"Finished function: DataManager.load_agent_snapshot, snapshot not found"
            )
            return None

        snapshot_data = pickle.loads(snapshot_blob.download_as_bytes())
        logger.info(f"Loaded agent snapshot from GCS for issue: {issue_id}")
        logger.info(f"Finished function: DataManager.load_agent_snapshot")
        return snapshot_data

    async def load_agent_history(self, issue_id: str) -> Optional[AgentHistory]:
        """Retrieves a saved agent state if it exists, otherwise returns None"""
        logger.info(
            f"Starting function: DataManager.load_agent_history, issue_id: {issue_id}"
        )
        client = storage.Client()

        bucket_name = os.environ.get("BUCKET_NAME")
        checkpoints_location = os.environ.get("CHECKPOINTS_LOCATION")
        logger.debug(
            f"Bucket name: {bucket_name}, checkpoints location: {checkpoints_location}"
        )

        bucket = client.bucket(bucket_name)
        chat_history_blob = bucket.blob(
            f"{checkpoints_location}/{issue_id}_history.pkl"
        )
        logger.debug(f"Chat history blob path: {chat_history_blob.path}")

        if not chat_history_blob.exists():
            logger.info(f"No chat history found for issue: {issue_id}")
            logger.info(
                f"Finished function: DataManager.load_agent_history, history not found"
            )
            return None

        chat_history_data = pickle.loads(chat_history_blob.download_as_bytes())
        logger.info(f"Loaded chat history from GCS for issue: {issue_id}")

        issue = await self.get_issue(issue_id)
        if not issue:
            logger.warning(
                f"Issue was {issue_id} not found, could not retrieve task list"
            )
            task_history_data = []
        else:
            task_history_data = issue.tasks
            logger.debug(
                f"Loaded task history from issue document for issue: {issue_id}"
            )

        agent_history = AgentHistory(
            chat_history=chat_history_data,
            task_history=task_history_data,
        )
        logger.info(f"Finished function: DataManager.load_agent_history")
        return agent_history

    # -------------------
    # API utils
    # -------------------

    async def build_get_issue_response_payload(
        self, issue_or_event_id: str
    ) -> Dict | None:
        """Build the response payload for the GET issue request by combining event and issue data"""
        event = await self.get_event(issue_or_event_id)

        if not event:
            issue = await self.get_issue(issue_or_event_id)
            if not issue:
                raise ValueError(
                    f"Neither issue nor event were found with id {issue_or_event_id}"
                )

            logger.info(f"Found issue with id: {issue_or_event_id}")
            event_id = issue.event_id
            logger.info(f"Related event id is: {event_id}")
            event = await self.get_event(event_id)
        else:
            logger.info(f"Found event with id: {issue_or_event_id}")
            issue_id = event.issue_id
            if not issue_id:
                logger.info(f"Event has no associated issue")
                return None

            logger.info(f"Related issue id is: {issue_id}")
            issue = await self.get_issue(issue_id)

            if not issue:
                # This shouldn't happen and it's an error
                logger.error("Could not find the issue associated with the event")
                return None

        if issue and not event:
            # This shouldn't happen and it's an error
            logger.error("Could not find the event associated with the issue")

        payload = {
            "event": event.model_dump() if event else {},
            "issue": issue.model_dump(),
        }

        return payload
