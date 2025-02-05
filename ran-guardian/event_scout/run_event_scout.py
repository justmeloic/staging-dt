from model_utils import generate, retry
from prompts import AGGREGATE_EVENTS, DISCOVER_EVENT, DEDUPLICATE_EVENTS
import json 
import concurrent.futures
from gmap_utils import geocode_location
import firestore_helper
from tqdm import tqdm
import logging

logger = logging.getLogger(__name__)

duplicate_events_response_schema = {
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "duplicate_ids": {
        "type": "array",
        "items": {
          "type": "string"
        },
        "description": "Array of IDs representing duplicate events"
      },
      "name": {
        "type": "string",
        "description": "Name of the event"
      },
      "address": {
        "type": "string",
        "description": "Address of the event venue"
      },
      "start_date": {
        "type": "string",
        "format": "date",
        "description": "Start date of the event in YYYY-MM-DD format"
      },
      "end_date": {
        "type": "string",
        "format": "date",
        "description": "End date of the event in YYYY-MM-DD format"
      }
    },
    "required": [
      "duplicate_ids",
      "name",
      "address",
      "start_date",
      "end_date"
    ]
  },
  "description": "Array of duplicate event objects"
}

@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def discover_single_event(event_type, event_location):
    """Generates event details for a single combination of event type and location."""
    prompt = DISCOVER_EVENT.format(event_type=event_type["type"],
                                   event_description=event_type["description"],
                                   location=event_location,
                                   time="this year 2025")
    event_table = generate(prompt, include_search=True)
    events_formatted = format_events(event_type, event_location, event_table)
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
            except Exception as e:
                logger.warning(f"An error occurred during event discovery for location {event_location}: {e}")

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

    try:
        events_formatted = json.loads(response)
        logger.info(f"Retrieved {len(events_formatted)} events for {event_type} in {event_location}")
    except Exception as e:
        logger.warning(f"Could not parse the events: {e}")
        raise e
    
    return events_formatted

def write_events_to_db(location, events):
    logger.info(f"Writing {len(events)} events for {location} to DB")
    for event in events:
        try:    
            geo_coordinates = geocode_location(event["address"])
            event["lat"] = geo_coordinates["lat"]
            event["lng"] = geo_coordinates["lng"]
        except Exception as e:
            logger.warning(f"Could not geocode location {event['address']}: {e}")

    firestore_helper.save_events(location, events)
    
    # Update last_scanned field of the given location
    firestore_helper.update_last_scanned(location)
    logger.info(f"Successfully scouted location {location}")


@retry(exceptions=(Exception), retries=4, delay=10, backoff=2)
def dedup_events_per_location(event_location):
    events = firestore_helper.get_events_by_location(event_location)

    prompt = DEDUPLICATE_EVENTS.format(events=str(events))
    response = generate(prompt, response_schema=duplicate_events_response_schema)

    try:
        duplicate_events = json.loads(response)
        logger.info(f"Retrieved {len(duplicate_events)} duplicate events in location {event_location}")
    except Exception as e:
        logger.warning(f"Could not parse the events: {e}")
        raise e
    
    deleted_events = 0
    for event in duplicate_events:
        v(f'Deleting duplicate entries for event name {event["name"]} start date {event["start_date"]} end date {event["end_date"]} address {event["address"]}')
        
        if(len(event["duplicate_ids"]) < 2):
            logger.warning(f"Less than two duplicate_id encountered")
            continue
        
        for duplicate_id in event["duplicate_ids"][1:]:
            logger.info(f"Deleting duplicate id {duplicate_id}")
            firestore_helper.delete_event_by_id(event_location, duplicate_id)
            deleted_events = deleted_events + 1

    logger.info("Deleted events", deleted_events)

def main():
    event_types = firestore_helper.get_all_event_types()
    logger.info(f"Total Event types: {len(event_types)}")

    event_locations = firestore_helper.get_unscanned_locations()
    logger.info(f"Total Locations: {len(event_locations)}")

    with tqdm(total=len(event_locations), desc="Scouting Locations", unit="location", bar_format="{l_bar}{bar} {n_fmt}/{total_fmt} | ETA: {remaining} | Elapsed: {elapsed} | {rate_fmt}") as pbar:
        for event_location in event_locations:
            pbar.set_description(f"Scouting: {event_location}")
            events = discover_events_multithreaded(event_location, event_types)
            write_events_to_db(event_location, events)

            # Dedup events after writing to database
            dedup_events_per_location(event_location)

            pbar.update(1)  # Increment the progress bar by 1 for each location
            pbar.set_postfix({"Location": event_location})

if __name__ == "__main__":
    
    logging.basicConfig(
        filename="event_scout.log",
        filemode="w",
        format="%(asctime)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )

    logger.info("### Event Scout Started: Looking for events and adding to database ###")
    main()
    logger.info("### Event Scout Completed ###")
