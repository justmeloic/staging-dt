from datetime import datetime, timedelta, timezone
import random
import uuid
from app.models import Event, PerformanceData, NodeData, Alarm, Location


def generate_random_location():
    """Generate random coordinates within a specified range"""
    return Location(
        address=f"Mock Address",
        latitude=round(random.uniform(35.0, 45.0), 6),
        longitude=round(random.uniform(-120.0, -110.0), 6),
    )


def generate_random_timestamp(max_days_ago=7):
    """Generate random timestamp within specified days ago"""
    days_ago = random.uniform(0, max_days_ago)
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def generate_nodes(num_nodes=5):
    """Generate mock node data"""
    nodes = []
    node_ids = [f"node_{i}" for i in range(1, num_nodes + 1)]

    for node_id in node_ids:
        node = NodeData(
            site_id="site_0",  # suppose that it's all from the same site
            node_id=node_id,
            capacity=random.randint(100, 500),
        )
        nodes.append(node)
    return nodes, node_ids


def generate_events(num_events=10):
    """Generate mock event data"""
    events = []
    event_types = ["concert", "sports", "festival", "emergency"]
    event_sizes = ["small", "medium", "large", "extra_large"]

    for _ in range(num_events):
        start_date = generate_random_timestamp()
        event = Event(
            event_id=str(uuid.uuid4()),
            location=generate_random_location(),
            start_date=start_date,
            end_date=start_date + timedelta(days=random.randint(1, 3)),
            name=f"Mock Event {random.randint(1, 1000)}",
            url=f"https://example.com/event/{random.randint(1000, 9999)}",
            event_type=random.choice(event_types),
            size=random.choice(event_sizes),
        )
        events.append(event)
    return events


def generate_performance_data(node_ids):
    """Generate mock performance data for given node IDs"""
    performance_data = []
    for node_id in node_ids:
        data = PerformanceData(
            node_id=node_id,
            timestamp=datetime.now(timezone.utc),
            rrc_max_users=random.randint(0, 200),
            rrc_setup_sr_pct=random.uniform(0.3, 0.99),
        )
        performance_data.append(data)
    return performance_data


def generate_alarms(node_ids, events=None, num_alarms=None):
    """Generate mock alarms for given node IDs and events"""
    if num_alarms is None:
        num_alarms = random.randint(3, 8)

    alarm_types = ["OVERLOAD", "CONNECTION_FAILURE", "CAPACITY_WARNING"]
    alarms = []

    for _ in range(num_alarms):
        created_at = generate_random_timestamp()
        if not events:
            event_id = None
        else:
            event_id = random.choice(events).event_id
        alarm = Alarm(
            alarm_id=str(uuid.uuid4()),
            node_id=random.choice(node_ids),
            event_id=event_id,
            created_at=created_at,
            cleared_at=(
                created_at + timedelta(hours=random.randint(1, 24))
                if random.random() > 0.5
                else None
            ),
            alarm_type=random.choice(alarm_types),
            description=f"Mock alarm description {random.randint(1, 100)}",
        )
        alarms.append(alarm)
    return alarms


def generate_mock_data(num_events=10):
    """Generate a set of mock data for testing"""
    nodes, node_ids = generate_nodes()
    events = generate_events(num_events)
    performance_data = generate_performance_data(node_ids)
    alarms = generate_alarms(node_ids, events)

    return {
        "events": events,
        "nodes": nodes,
        "performance_data": performance_data,
        "alarms": alarms,
    }
