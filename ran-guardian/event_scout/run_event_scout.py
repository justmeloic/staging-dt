from model_utils import generate, retry
import typing_extensions as typing
from google.genai import types
from prompts import AGGREGATE_EVENTS, DISCOVER_EVENT, DEDUPLICATE_EVENTS
import json 
import concurrent.futures
from gmap_utils import geocode_location
import firestore_helper

@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def discover_single_event(event_type, event_location):
    """Generates event details for a single combination of event type and location."""
    prompt = DISCOVER_EVENT.format(event_type=event_type["type"],
                                   event_description=event_type["description"],
                                   location=event_location,
                                   time="this year 2025")
    event_table = generate(prompt, include_search=True)  # Use retry wrapper
    # print(event_table)
    events_formatted = format_events(event_type, event_location, event_table)
    # print("Returning ", len(events_formatted), " events")
    return events_formatted


def discover_events_multithreaded(event_location, event_types):
    """Discovers events using multithreading and retry logic."""

    location_events = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(discover_single_event, event_type, event_location)
                   for event_type in event_types]

        for future in concurrent.futures.as_completed(futures):
            try:
                events = future.result()
                location_events.extend(events)
                # print("Accumulated ", len(location_events))
            except Exception as e:
                print(f"An error occurred during event discovery: {e}")

    return location_events

# @retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def format_events(event_type, event_location, event_table)->list[dict]:
    event_of_interest_response_schema = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "address": {"type": "string"},
            "start_date": {"type": "string"},
            "end_date": {"type": "string"},
            "start_time": {"type": "string"},
            "end_time": {"type": "string"},
            "size": {"type": "string"},
            "event_type": {"type": "string"},
            "url": {"type": "string"},
            },
            "required": ["name", "address", "start_date", "end_date", "start_time", "end_time", "size", "event_type", "url"],
        },
    }
    prompt = AGGREGATE_EVENTS.format(raw_events=event_table)
    response = generate(prompt, response_schema=event_of_interest_response_schema)
    # print(response)

    try:
        events_formatted = json.loads(response)
        print(f"Retrieved {len(events_formatted)} events for {event_type} in {event_location}")
    except Exception as e:
        print(f"Could not parse the events: {e}")
        print(f"Events: {response}")
        raise e
    
    return events_formatted

def write_events_to_db(location, events):
    print(f"Writing {len(events)} events for {location} to DB")
    for event in events:
        try:    
            geo_coordinates = geocode_location(event["address"])
            event["lat"] = geo_coordinates["lat"]
            event["lng"] = geo_coordinates["lng"]
        except Exception as e:
            print(f"Could not geocode location {event['location']}: {e}")
        firestore_helper.save_event(location, event)

    # Update last_scanned field of the given location
    firestore_helper.update_last_scanned(location)
    print(f"Successfully scouted location {location}")


@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def dedup_events():
    
    functions = [
        data_manager.read_all, 
        data_manager.create, 
        data_manager.update, 
        data_manager.delete
        ]
    prompt = DEDUPLICATE_EVENTS.format(table_name="events_of_interest")
    result = generate(prompt, custom_tools=functions, max_remote_calls=20)
    # result = generate(prompt,model="gemini-2.0-flash-thinking-exp-1219", custom_tools=functions)
    print(result)

def main():
    event_types = firestore_helper.get_all_event_types()
    print(f"Total Event types: {len(event_types)}")
    event_locations = firestore_helper.get_locations()
    print(f"Total Locations: {len(event_locations)}")

    for event_location in event_locations:
        print(f"Scouting for events in: {event_location}")
        events = discover_events_multithreaded(event_location, event_types)
        write_events_to_db(event_location, events)
        # break

if __name__ == "__main__":
    print("### Looking for events and adding to database ###")
    main()
    print("### Event Scout Completed ###")
