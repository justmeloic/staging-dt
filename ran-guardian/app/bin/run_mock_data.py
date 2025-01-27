import os
import pandas as pd
import json
from datetime import datetime
from app.models import IssueStatus
from app.mock_data import generate_mock_data


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, IssueStatus):
            return obj.value
        return super().default(obj)


def save_mock_data_to_csv(mock_data, output_dir="mock_data"):
    """Save mock data to CSV files"""
    os.makedirs(output_dir, exist_ok=True)

    # Convert Events to DataFrame and save
    events_df = pd.DataFrame(
        [
            {
                **event.model_dump(),
                "location_latitude": event.location.latitude,
                "location_longitude": event.location.longitude,
                "location_address": event.location.address,
            }
            for event in mock_data["events"]
        ]
    )
    events_df.to_csv(f"{output_dir}/events.csv", index=False)

    # Convert Nodes to DataFrame and save
    nodes_df = pd.DataFrame([node.model_dump() for node in mock_data["nodes"]])
    nodes_df.to_csv(f"{output_dir}/nodes.csv", index=False)

    # Convert Performance Data to DataFrame and save
    perf_df = pd.DataFrame(
        [perf.model_dump() for perf in mock_data["performance_data"]]
    )
    perf_df.to_csv(f"{output_dir}/performance_data.csv", index=False)

    # Convert Alarms to DataFrame and save
    alarms_df = pd.DataFrame([alarm.model_dump() for alarm in mock_data["alarms"]])
    alarms_df.to_csv(f"{output_dir}/alarms.csv", index=False)


if __name__ == "__main__":
    mock_data = generate_mock_data()
    save_mock_data_to_csv(mock_data)
    # Print sample data
    print(f"Generated {len(mock_data['events'])} events")
    print(f"Generated {len(mock_data['nodes'])} nodes")
    print(f"Generated {len(mock_data['performance_data'])} performance records")
    print(f"Generated {len(mock_data['alarms'])} alarms")
