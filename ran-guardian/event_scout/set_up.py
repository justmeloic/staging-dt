## Use the following import for local "database"
import data_manager_flat as data_manager

## Use the following for firestore datastore as database
# import data_manager_datastore as data_manager

# --- Locations ---
# Create some sample locations
locations = [
    {"location": "Frankfurt", "comment": "City"},
    {"location": "Mainz, Germany", "comment": "City"},
    {"location": "Munich", "comment": "City"}
]
for location in locations:
    data_manager.create("locations", location)

# --- Event Types ---
# Create some sample event types
event_types = [
    {"type": "Concert", "description": "music concert in a stadium"},
    {"type": "Sports Event", "description": "Sports event in a stadium including football, basketball etc."},
    {"type": "Flea market", "description": "Pop-up flea market"}
]
for event_type in event_types:
    data_manager.create("event_types", event_type)

# --- Events of Interest ---
# Create sample event of interest
event_of_interest = [
    {"name": None, "location":None, "date":None, "time":None, "size":None}
]
for event in event_of_interest:
    data_manager.create("events_of_interest", event)