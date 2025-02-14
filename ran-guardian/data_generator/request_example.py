import json
from datetime import datetime, timezone

import requests

BASE_URL = "http://127.0.0.1:8001"  # Example: Local development server

# Example for /performances
node_id = "64506186.0"  # this has to be a 4G node which already exists

start_time = datetime(2025, 3, 1, 10, 0, 0, tzinfo=timezone.utc)
end_time = datetime(2025, 4, 1, 11, 0, 0, tzinfo=timezone.utc)

payload = {
    "node_id": node_id,
    "start_time": start_time.isoformat(),
    "end_time": end_time.isoformat(),
}


url = BASE_URL + "/performances"
headers = {"Content-Type": "application/json"}
response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
print(response.content)


url = BASE_URL + "/alarms"
headers = {"Content-Type": "application/json"}
response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
print(response.content)
