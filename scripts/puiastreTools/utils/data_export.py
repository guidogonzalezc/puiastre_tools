import json
import os

class DataExport:
    def __init__(self): 
        complete_path = os.path.realpath(__file__)
        self.relative_path = complete_path.split("\\scripts")[0]
        self.build_path = os.path.join(self.relative_path, "build", "build_cache.cache")

    def new_build(self):
        with open(self.build_path, "w") as f:
            json.dump({}, f, indent=4)

    def append_data(self, module_name, data_dict):
        if os.path.exists(self.build_path):
            with open(self.build_path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    current_data = {}
        else:
            current_data = {}

        if module_name not in current_data:
            current_data[module_name] = {}

        current_data[module_name].update(data_dict)

        with open(self.build_path, "w") as f:
            json.dump(current_data, f, indent=4)

    def get_data(self, module_name, attribute_name):
        if os.path.exists(self.build_path):
            with open(self.build_path, "r") as f:
                try:
                    current_data = json.load(f)
                except json.JSONDecodeError:
                    current_data = {}
        else:
            current_data = {}

        for module, data in current_data.items():
            if module == module_name:
                for attr, value in data.items():
                    if attr == attribute_name:
                        return value



        return None

