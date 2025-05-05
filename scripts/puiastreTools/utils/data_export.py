import json
import os

class DataExport:
    def __init__(self): 
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\\scripts")[0]  # If you're on Windows
        self.build_path = os.path.join(self.relative_path, "build", "build_cache.cache")

    def new_build(self):
        # Start with an empty dict instead of a string
        with open(self.build_path, "w") as f:
            json.dump({}, f, indent=4)

    def append_data(self, module_name, data_dict):
        # Load current data
        if os.path.exists(self.build_path):
            with open(self.build_path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    current_data = {}
        else:
            current_data = {}

        # Merge or update module data
        if module_name not in current_data:
            current_data[module_name] = {}

        current_data[module_name].update(data_dict)

        # Save back
        with open(self.build_path, "w") as f:
            json.dump(current_data, f, indent=4)
