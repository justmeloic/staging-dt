import os

from app.data_manager import EVENTS_COLLECTION, convert_size_into_number
from dotenv import load_dotenv
from google.cloud import firestore
from tqdm import tqdm

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
DB_NAME = "ran-guardian-data-manager"


db = firestore.Client(project=PROJECT_ID, database=DB_NAME)

FROM_ISSUE_COLLECTION = "issues-dev"
TO_ISSUE_COLLECTION = "issues"


def main(max_num: int | None = 1):
    count = 0
    issue_stream = db.collection(FROM_ISSUE_COLLECTION).stream()
    for issue in tqdm(issue_stream):
        print(issue.id)
        issue_data = issue.to_dict()
        issue_ref = db.collection(TO_ISSUE_COLLECTION).document(issue_data["event_id"])

        if count > max_num:
            break
        count += 1

        if issue_ref.get().exists:
            print("Issue already exists")
            continue
        else:
            issue_ref.set(issue_data)
            print(f"created new issue in {TO_ISSUE_COLLECTION}")


if __name__ == "__main__":
    main(500)
