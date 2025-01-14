from data_manager import DataManager

# Initialize DataManager (creates the data directory)
data_manager = DataManager()
# --- Locations ---
# Create some sample locations
locations = [
    {"location": "Maastricht", "comment": "City"},
    {"location": "Eindhoven", "comment": "City"},
    {"location": "Zandvoort Aan Zee", "comment": "Beach"}
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