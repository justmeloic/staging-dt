import asyncio
import os
from datetime import datetime
from typing import Optional

from app.data_manager import EVENTS_COLLECTION, ISSUES_COLLECTION, check_date
from dotenv import load_dotenv
from event_scout.firestore_helper import db as origin_db
from google.cloud import firestore

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
DB_NAME = "ran-guardian-data-manager"

db = firestore.Client(project=PROJECT_ID, database=DB_NAME)


def delete_all_issues_from_db(
    start_date: Optional[datetime] = None, end_date: Optional[datetime] = None
):
    collection_ref = db.collection(ISSUES_COLLECTION)
    if start_date:
        start_date_str = start_date.strftime("%Y-%m-%d")
        collection_ref = collection_ref.where("start_date", ">=", start_date_str)
    if end_date:
        end_date_str = end_date.strftime("%Y-%m-%d")
        collection_ref = collection_ref.where("start_date", "<=", end_date_str)

    n_docs = 0
    for doc in collection_ref.stream():
        print(doc.id)
        event_id = doc.to_dict().get("event_id", None)
        if event_id:
            event = db.collection(EVENTS_COLLECTION).document(event_id)
            if event.get().exists:
                event.update({"issue_id": firestore.DELETE_FIELD})
        doc.reference.delete()
        n_docs += 1
    print(f"deleted {n_docs} events from new events db")


if __name__ == "__main__":
    delete_all_issues_from_db()
