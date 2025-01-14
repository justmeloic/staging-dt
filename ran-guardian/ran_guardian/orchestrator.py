from data_manager import DataManager
from model_utils import generate, retry
import typing_extensions as typing
from google.genai import types
from prompts import AGGREGATE_EVENTS, DISCOVER_EVENT, DEDUPLICATE_EVENTS
import itertools
import json 
import concurrent.futures

data_manager = DataManager()

@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def discover_single_event(event_type, event_location):
    """Generates event details for a single combination of event type and location."""
    prompt = DISCOVER_EVENT.format(event_type=event_type["type"],
                                   location=event_location["location"],
                                   time="next weekend")
    event = generate(prompt, include_search=True)  # Use retry wrapper
    return event

def discover_events_multithreaded():
    """Discovers events using multithreading and retry logic."""

    event_types = data_manager.read_all("event_types")
    event_locations = data_manager.read_all("locations")

    events = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(discover_single_event, event_type, event_location)
                   for event_type, event_location in itertools.product(event_types, event_locations)]

        for future in concurrent.futures.as_completed(futures):
            try:
                event = future.result()
                events.append(event)
            except Exception as e:
                print(f"An error occurred during event discovery: {e}")

    return events

# def discover_events()-> list[str]:
#     event_types = data_manager.read_all("event_types")
#     event_locations = data_manager.read_all("locations")
#     events = []
#     for event_type, event_locations in list(itertools.product(event_types, event_locations)):
#         prompt = DISCOVER_EVENT.format(event_type=event_type["type"], 
#                                        location=event_locations["location"],
#                                        time="next weekend")
#         event = generate(prompt, include_search=True)
#         events.append(event)

#     return events

@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def aggregate_events(individual_events:list[dict])->list[dict]:
    event_of_interest_response_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "location": {"type": "string"},
            "date": {"type": "string"},
            "time": {"type": "string"},
            "size": {"type": "string"},
            "event_type": {"type": "string"},
            },
            "required": ["name", "location", "date", "time", "size", "event_type"],
        },
    }
    prompt = AGGREGATE_EVENTS.format(raw_events="\n\n".join(individual_events))
    response = generate(prompt, response_schema=event_of_interest_response_schema)
    return response

def update_events(events):
    try:
        events = json.loads(events)
    except Exception as e:
        print(f"Could not parse the events: {e}")
        print(f"Events: {events}")
        raise e
    for event in events:
        data_manager.create("events_of_interest", event)


@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def dedup_events():
    import data_manager_flat
    functions = [
        data_manager_flat.read_all, 
        data_manager_flat.create, 
        data_manager_flat.update, 
        data_manager_flat.delete
        ]
    prompt = DEDUPLICATE_EVENTS.format(table_name="events_of_interest")
    result = generate(prompt, custom_tools=functions, max_remote_calls=2)
    # result = generate(prompt,model="gemini-2.0-flash-thinking-exp-1219", custom_tools=functions)
    print(result)

def main():
    events = discover_events_multithreaded()
    aggregated_events = aggregate_events(events)
    update_events(aggregated_events)

if __name__ == "__main__":
    main()
    # dedup_events()
