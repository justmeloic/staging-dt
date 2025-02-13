curl -X 'POST' \
     -H 'accept: application/json'  \
     -H "Content-Type: application/json" \
     -d '{"node_id": "64506186.0", "start_time": "2025-03-01T10:00:00+00:00", "end_time": "2025-03-01T11:00:00+00:00"}' \
     "http://127.0.0.1:8001/alarms"


curl -X 'POST' \
     -H 'accept: application/json'  \
     -H "Content-Type: application/json" \
     -d '{"node_id": "64506186.0", "start_time": "2025-03-01T10:00:00+00:00", "end_time": "2025-03-01T11:00:00+00:00"}' \
     "http://127.0.0.1:8001/performances"


curl -X 'POST'\
     -H 'accept: application/json'  \
     -H "Content-Type: application/json" \
     -d '{"node_id": "123.0", "start_time": "2025-03-01T10:00:00+00:00", "end_time": "2025-03-01T11:00:00+00:00"}' \
     "http://127.0.0.1:8001/performances"
