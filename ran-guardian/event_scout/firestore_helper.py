from google.cloud import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from google.cloud import bigquery
import pandas
import pandas_gbq
import datetime
import os
from dotenv import load_dotenv

load_dotenv()
PROJECT_ID = os.getenv("PROJECT_ID")
FIREBASE_DB_NAME = os.getenv("FIREBASE_DB_NAME")

db = firestore.Client(project=PROJECT_ID, database=FIREBASE_DB_NAME)

def get_all_event_types():
    docs = db.collection('event_types').stream()
    event_types = [doc.to_dict() for doc in docs]
    return event_types

def get_locations(priority = ""):
    if priority:
        docs = db.collection('locations').where(filter=FieldFilter("priority", "==", priority)).stream()
    else:
        docs = db.collection('locations').stream()
    locations = [doc.id for doc in docs if doc.id != "0_stats"]
    return locations

def update_last_scanned(location):
    doc_ref = db.collection("locations").document(location)
    doc_ref.set({u"last_scanned": datetime.datetime.now(tz=datetime.timezone.utc)}, merge=True)

def get_global_stats():
    return db.collection("locations").document("0_stats").get().to_dict()

def get_num_scanned_locations(num_days = 90):
    num_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=num_days)
    docs = db.collection("locations").where(filter=FieldFilter("last_scanned", ">=", num_days_ago)).stream()
    locations = [doc.id for doc in docs]
    return len(locations)

def get_unscanned_locations(num_days = 360):
    num_days_ago = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=num_days)
    docs = db.collection("locations").where(filter=FieldFilter("last_scanned", "<", num_days_ago)).stream()
    locations = [doc.id for doc in docs]
    return locations

def save_events(location, events):
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
    pandas_gbq.to_gbq(df, "events_db_de.people_events", project_id=PROJECT_ID, if_exists='append')

    update_last_scanned(location)

def get_events_by_location(location):
    events = db.collection(location).stream()
    events_list = [event.to_dict() for event in events]
    return events_list

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

def get_nodes_within_radius(lng, lat, radius = 4000):
    client = bigquery.Client(project=PROJECT_ID, location='europe-west3')
    query_job = client.query(QUERY.format(lng=lng, lat=lat, radius=radius))  # API request
    df = query_job.to_dataframe()
    return df

# print(get_unscanned_locations()[:10])
# print(get_num_scanned_locations())
# print(get_nodes_within_radius(13.4049, 52.5200, 4000))
# print(get_global_stats())
# get_events_by_location(location="Berlin Berlin")

# print(get_all_event_types())
# locations = get_locations(priority="medium")
# print(locations)

# event = json.loads("""{
#         "address": "Mannheim, Germany",
#         "date": "2025-06-07 to 2025-06-09",
#         "end_time": "N/A",
#         "event_type": "Art, Technology, Culture Festival",
#         "name": "APEX Mannheim",
#         "size": "L",
#         "start_time":"N/A",
#         "url": "https://vertexaisearch.cloud.google.com/grounding-api-redirect/AUBnsYtPBU-Bc7Xmbbk1-gxUDYlvH99caaXeaw-40fT1QbtIb17JYGO_7j32zsVTf9yglZl8ySAAfGkqCuWMa9R8bw_dGalv3OWtqcBnQDDh9Hcl1qExdcleBPyjtJUjJl2XvKe1AG9mBPbtE--ECGJsgZuuwwLZBHisKma376MAOJXzXRlVn8hX"
#     }""")
# save_event("Aach Baden-Württemberg", event)

# update_last_scanned("Aach Baden-Württemberg")