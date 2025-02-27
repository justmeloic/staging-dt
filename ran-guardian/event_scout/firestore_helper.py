"""Helper functions to interfact with Firestore database."""

import os
from datetime import datetime, timezone, timedelta
from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import bigquery
import pandas
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
FIREBASE_DB_NAME = os.getenv("FIREBASE_DB_NAME")

db = firestore.Client(project=PROJECT_ID, database=FIREBASE_DB_NAME)

def get_all_event_types() -> list[dict]:
    """Returns a list of all event types."""

    docs = db.collection('event_types').stream()
    event_types = [doc.to_dict() for doc in docs]

    return event_types

def get_locations(priority: str, days_since_last_scan: int) -> list[str]:
    """Returns all locations with the specified priority and last scan date."""

    num_days_ago = datetime.now(timezone.utc) - timedelta(days=days_since_last_scan)

    if priority != "all":
        docs = db.collection('locations').where(
            filter=FieldFilter("priority", "==", priority)
            ).where(
                filter=FieldFilter("last_scanned", "<", num_days_ago)
            ).stream()
    else:
        docs = db.collection('locations').where(
            filter=FieldFilter("last_scanned", "<", num_days_ago)
            ).stream()

    locations = [doc.id for doc in docs if doc.id != "0_stats"]
    return sorted(locations)

def update_last_scanned(location: str) -> None:
    """Updates the last_scanned field of the given location."""

    doc_ref = db.collection("locations").document(location)
    doc_ref.set({"last_scanned": datetime.now(tz=timezone.utc)}, merge=True)

def get_global_stats() -> dict:
    """Returns the global scanning stats."""

    return db.collection("locations").document("0_stats").get().to_dict()

def get_num_scanned_locations(num_days: int = 90) -> int:
    """Returns the number of locations scanned in the last num_days days."""

    num_days_ago = datetime.now(timezone.utc) - timedelta(days=num_days)
    docs = db.collection("locations").where(
        filter=FieldFilter("last_scanned", ">=", num_days_ago)
        ).stream()
    locations = [doc.id for doc in docs]

    return len(locations)

def get_unscanned_locations(num_days: int = 360) -> list[str]:
    """Returns the list of locations that have not been scanned in the last num_days days."""

    num_days_ago = datetime.now(timezone.utc) - timedelta(days=num_days)
    docs = db.collection("locations").where(
        filter=FieldFilter("last_scanned", "<", num_days_ago)
        ).stream()
    locations = [doc.id for doc in docs]

    return sorted(locations)

def save_events(location: str, events: list[dict]) -> None:
    """Writes events to Firestore and BigQuery."""

    for event in events:
        # Write event to the location collection
        _, doc_ref = db.collection(location).add(event)

        event["event_id"] = doc_ref.id

        # Increment total events stat
        total_ref_stats = db.collection("locations").document("0_stats")
        total_ref_stats.update({
            "num_events": firestore.Increment(1)
        })

        # Increment location events stat
        loc_ref_stats = db.collection("locations").document(location)
        loc_ref_stats.update({
            "num_events": firestore.Increment(1)
        })

    # Write event to BQ
    df = pandas.DataFrame(events)
    pandas_gbq.to_gbq(df, "events_db_de.people_events", 
                      project_id=PROJECT_ID, if_exists='append', 
                      location='europe-west3')

    update_last_scanned(location)

def get_events_by_location(location: str) -> list[dict]:
    """""Returns all events for the specified location."""

    events = db.collection(location).stream()
    events_list = [{**event.to_dict(), 'id': event.id} for event in events]
    return events_list

def delete_event_by_id(event_location: str, event_id: str) -> None:
    """
    Delete an event with the specified event_id for the specified event_location.
    """
    db.collection(event_location).document(event_id).delete()

    # Decrement location events stat
    loc_ref_stats = db.collection("locations").document(event_location)
    loc_ref_stats.update({
        "num_events": firestore.Increment(-1)
    })

    # Decrement total events stat
    total_ref_stats = db.collection("locations").document("0_stats")
    total_ref_stats.update({
        "num_events": firestore.Increment(-1)
    })

QUERY = """
    SELECT
    ST_X(GEO_COORDINATES) AS longitude,
    ST_Y(GEO_COORDINATES) AS latitude,
    MS_MSRBS_HERSTELLER
    FROM
    `de1000-dev-mwc-ran-agent.ran_guardian.inventory`
    WHERE
    ST_DISTANCE(
        GEO_COORDINATES, -- Replace longitude and latitude with your table's column names
        ST_GEOGPOINT({lng}, {lat}) -- Replace with your target longitude and latitude (e.g., Chicago)
    ) <= {radius}; -- 5000 meters = 5 kilometers
    """

def get_nodes_within_radius(lng: float, lat: float, radius: int = 4000) -> pandas.DataFrame:
    """Get nodes within the specidied radius of the given coordinates."""

    client = bigquery.Client(project=PROJECT_ID, location='europe-west3')
    query_job = client.query(QUERY.format(lng=lng, lat=lat, radius=radius))  # API request
    df = query_job.to_dataframe()
    return df

def get_event_by_location_and_id(location: str, event_id: str) -> dict:
    """Returns a single event for the specified location and event ID."""
    doc_ref = db.collection(location).document(event_id)
    return doc_ref.get().to_dict()

def delete_events_by_location(location: str) -> int:
    """Deletes all events for the specified location."""
    docs = db.collection(location).stream()
    num_deleted = 0
    for doc in docs:
        doc.reference.delete()
        num_deleted += 1

    # Reset location events stat counter
    loc_ref_stats = db.collection("locations").document(location)
    loc_ref_stats.update({
        "num_events": 0
    })

    # Decrement total events stat
    total_ref_stats = db.collection("locations").document("0_stats")
    total_ref_stats.update({
        "num_events": firestore.Increment(-1*num_deleted)
    })

    return num_deleted

# print(get_nodes_within_radius(13.4049, 52.5200, 4000))
# print(get_event_by_location_and_id("Aach Baden-Württemberg", "0fdGDkY2A34O1PzFJwF2"))