import asyncio
import os
from datetime import datetime
from typing import Optional

from app.data_manager import check_date
from dotenv import load_dotenv
from event_scout.firestore_helper import db as origin_db
from google.cloud import firestore

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
NEW_DB_NAME = "ran-guardian-data-manager"

new_db = firestore.Client(project=PROJECT_ID, database=NEW_DB_NAME)

import logging

logging.basicConfig(level=logging.CRITICAL)


def get_all_locations():
    docs = origin_db.collection("locations").stream()
    locations = [doc.id for doc in docs if doc.id != "0_stats"]
    return sorted(locations)


def check_event(
    event_data: dict,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    res = True
    res = res & check_date(
        event_data.get("start_date"), start_date=start_date, end_date=end_date
    )
    res = res & check_date(
        event_data.get("end_date"), start_date=start_date, end_date=end_date
    )
    # todo: add a check to verify if the url exists
    return res


def delete_all_events_from_new_db(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
):
    collection_ref = new_db.collection("events")
    if start_date:
        collection_ref = collection_ref.where("start_date", ">=", start_date)
    if end_date:
        collection_ref = collection_ref.where("end_date", "<=", end_date)

    n_docs = 0
    for doc in collection_ref.stream():
        doc.reference.delete()
        n_docs += 1
    print(f"deleted {n_docs} events from new events db")


def save_event_to_new_db(event_data: dict, event_id: str):
    event_ref = new_db.collection("events").document(event_id).get()
    if event_ref.exists:
        event_ref.update(event_data)
    else:
        _, doc_ref = new_db.collection("events").add(
            document_data=event_data, document_id=event_id
        )


async def restructure_event_per_location(location, start_date, end_date):
    n_doc = 0
    events = origin_db.collection(location).stream()
    for event_doc in events:
        event_data = event_doc.to_dict()
        if check_event(event_doc, start_date, end_date):
            event_data["location"] = location
            save_event_to_new_db(event_data, event_doc.id)
            n_doc += 1
    print(f"finish for location {location}")
    return n_doc


async def main(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    clean_up: bool = False,
):
    # clean up the new db
    if clean_up:
        delete_all_events_from_new_db(start_date, end_date)

    locations = get_all_locations()
    print("start restructure locations...")
    tasks = [
        restructure_event_per_location(location, start_date, end_date)
        for location in locations
    ]
    results = await asyncio.gather(*tasks)
    n_doc = sum(results)
    print(f"saved {n_doc} well formatted events to new db!")


if __name__ == "__main__":
    asyncio.run(main())
