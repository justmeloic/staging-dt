import json
import os

class DataManager:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Creates the data directory if it doesn't exist."""
        os.makedirs(self.data_dir, exist_ok=True)

    def _get_file_path(self, data_type):
        """Gets the file path for the given data type."""
        return os.path.join(self.data_dir, f"{data_type}.json")

    def _load_data(self, data_type):
        """Loads data from the JSON file for the given data type."""
        file_path = self._get_file_path(data_type)
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []  # Return empty list if file not found

    def _save_data(self, data_type, data):
        """Saves data to the JSON file for the given data type."""
        file_path = self._get_file_path(data_type)
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

    def create(self, data_type, item):
        """Adds a new item to the specified data type."""
        data = self._load_data(data_type)
        
        # Find the next available ID
        next_id = max([item.get("id", 0) for item in data], default=0) + 1
        item["id"] = next_id

        data.append(item)
        self._save_data(data_type, data)
        return item

    def read_all(self, data_type:str)->list[dict]:
        """Returns all items of the specified data type.
        
        Args:
            data_type: The name of the table to use to read data from
        """
        return self._load_data(data_type)

    def read(self, data_type, id_key, id_value):
        """Returns an item of the specified data type by its ID."""
        data = self._load_data(data_type)
        for item in data:
            if item.get(id_key) == id_value:
                return item
        return None

    def update(self, data_type, id_key, id_value, updates):
        """Updates an item of the specified data type by its ID."""
        data = self._load_data(data_type)
        for i, item in enumerate(data):
            if item.get(id_key) == id_value:
                item.update(updates)
                data[i] = item
                self._save_data(data_type, data)
                return item
        return None

    def delete(self, data_type, id_key, id_value):
        """Deletes an item of the specified data type by its ID."""
        data = self._load_data(data_type)
        initial_len = len(data)
        data = [item for item in data if item.get(id_key) != id_value]
        if len(data) < initial_len:
            self._save_data(data_type, data)
            return True
        return False
    


# # Initialize DataManager (creates the data directory)
# data_manager = DataManager()

# # --- Locations ---
# # Create
# new_location = {"location": "London", "comment": "Headquarters"}
# created_location = data_manager.create("locations", new_location)
# print("Created Location:", created_location)

# # Read All
# all_locations = data_manager.read_all("locations")
# print("All Locations:", all_locations)

# # Read by ID
# location = data_manager.read("locations", "id", 1)
# print("Location with ID 1:", location)

# # Update
# data_manager.update("locations", "id", 1, {"comment": "Main Office"})
# location = data_manager.read("locations", "id", 1)
# print("Location with ID 1:", location)

# # Delete
# data_manager.delete("locations", "id", 1)


# # --- EventTypes ---
# # Create
# new_event_type = {"type": "Conference", "description": "Annual meeting"}
# created_event_type = data_manager.create("event_types", new_event_type)
# print("Created EventType:", created_event_type)

# # Read All
# all_event_types = data_manager.read_all("event_types")
# print("All EventTypes:", all_event_types)

# # Read by ID
# event_type = data_manager.read("event_types", "id", 1)
# print("EventType with ID 1:", event_type)

# # Update
# data_manager.update("event_types", "id", 1, {"description": "Yearly conference"})
# event_type = data_manager.read("event_types", "id", 1)
# print("EventType with ID 1:", event_type)
# # Delete
# data_manager.delete("event_types", "id", 1)