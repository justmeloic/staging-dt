import os

from app.data_manager import EVENTS_COLLECTION, convert_size_into_number
from dotenv import load_dotenv
from google.cloud import firestore
from tqdm import tqdm

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
DB_NAME = "ran-guardian-data-manager"

db = firestore.Client(project=PROJECT_ID, database=DB_NAME)


def check_issue(issue_data):
    result = True
    result = result & ("start_date" in issue_data)
    result = result & ("end_date" in issue_data)
    result = result & ("event_size" in issue_data)
    if "event_size" in issue_data:
        result = result & isinstance(issue_data["event_size"], int)
    return result


def add_dates_to_issue(issue):
    issue_data = issue.to_dict()
    if not check_issue(issue_data):
        event = db.collection(EVENTS_COLLECTION).document(issue_data["event_id"]).get()
        if event.exists:
            update_dict = {}
            event_data = event.to_dict()
            update_dict["start_date"] = event_data.get("start_date")
            update_dict["end_date"] = event_data.get("end_date")
            size_num = convert_size_into_number(event_data.get("size"))
            update_dict["event_size"] = size_num
            issue_ref = db.collection("issues").document(issue.id)
            issue_ref.update(update_dict)
            return True
    return False


def main():
    issues_stream = db.collection("issues").stream()
    total_doc_updated = {}
    for issue in tqdm(issues_stream):
        total_doc_updated[issue.id] = add_dates_to_issue(issue)
    return total_doc_updated


if __name__ == "__main__":
    total_doc_updated = main()
    n_updated = sum(total_doc_updated.values())
    n_skipped = len(total_doc_updated.values()) - n_updated
    print(f"Added event dates and sizes to total {n_updated} and skipped {n_skipped}")
