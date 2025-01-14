import json
import os
import inspect

# Define data_dir at the top level of the file
data_dir = "data"  # You can change this to your desired directory

def _ensure_data_dir():
    """Creates the data directory if it doesn't exist."""
    os.makedirs(data_dir, exist_ok=True)

def _get_file_path(data_type):
    """Gets the file path for the given data type."""
    return os.path.join(data_dir, f"{data_type}.json")

def _load_data(data_type):
    """Loads data from the JSON file for the given data type."""
    file_path = _get_file_path(data_type)
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []  # Return empty list if file not found

def _save_data(data_type, data):
    """Saves data to the JSON file for the given data type."""
    file_path = _get_file_path(data_type)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

def create(data_type:str, item:dict)->dict:
    """Adds a new item to the specified data type."""
    _ensure_data_dir()
    data = _load_data(data_type)
    
    # Find the next available ID
    next_id = max([item.get("id", 0) for item in data], default=0) + 1
    item["id"] = next_id

    data.append(item)
    _save_data(data_type, data)
    return item

def read_all(data_type:str)->list[dict]:
    """Returns all items of the specified data type."""
    _ensure_data_dir()
    print(f"Gemini just used {inspect.currentframe().f_code.co_name} function")
    return _load_data(data_type)

def read(data_type:str, id_key:str, id_value:int)->dict|None:
    """Returns an item of the specified data type by its ID."""
    _ensure_data_dir()
    data = _load_data(data_type)
    for item in data:
        if item.get(id_key) == id_value:
            return item
    return None

def update(data_type:str, id_key:str, id_value:int, updates:dict)->dict|None:
    """Updates an item of the specified data type by its ID."""
    _ensure_data_dir()
    print(f"Gemini just used {inspect.currentframe().f_code.co_name} function")
    data = _load_data(data_type)
    for i, item in enumerate(data):
        if item.get(id_key) == id_value:
            item.update(updates)
            data[i] = item
            _save_data(data_type, data)
            return item
    return None

def delete(data_type:str, id_key:str, id_value:int)->bool:
    """Deletes an item of the specified data type by its ID."""
    _ensure_data_dir()
    print(f"Gemini just used {inspect.currentframe().f_code.co_name} function")
    data = _load_data(data_type)
    initial_len = len(data)
    data = [item for item in data if item.get(id_key) != id_value]
    if len(data) < initial_len:
        _save_data(data_type, data)
        return True
    return False


# Example Usage (no need to pass data_dir anymore):

# # --- Locations ---
# # Create
# new_location = {"location": "London", "comment": "Headquarters"}
# created_location = create("locations", new_location)
# print("Created Location:", created_location)

# # Read All
# all_locations = read_all("locations")
# print("All Locations:", all_locations)

# # Read by ID
# location = read("locations", "id", 1)
# print("Location with ID 1:", location)

# # Update
# update("locations", "id", 1, {"comment": "Main Office"})
# location = read("locations", "id", 1)
# print("Location with ID 1:", location)

# # Delete
# delete("locations", "id", 1)


# # --- EventTypes ---
# # Create
# new_event_type = {"type": "Conference", "description": "Annual meeting"}
# created_event_type = create("event_types", new_event_type)
# print("Created EventType:", created_event_type)

# # Read All
# all_event_types = read_all("event_types")
# print("All EventTypes:", all_event_types)

# # Read by ID
# event_type = read("event_types", "id", 1)
# print("EventType with ID 1:", event_type)

# # Update
# update("event_types", "id", 1, {"description": "Yearly conference"})
# event_type = read("event_types", "id", 1)
# print("EventType with ID 1:", event_type)

# # Delete
# delete("event_types", "id", 1)