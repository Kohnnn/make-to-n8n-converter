import json

class MakeComParser:
    def __init__(self, make_json: dict):
        self.make_json = make_json

    def parse(self):
        """
        Parses the Make.com workflow JSON and extracts modules and connections.
        """
        modules = []
        connections = []

        # Extract modules
        if "flow" in self.make_json and isinstance(self.make_json["flow"], list):
            for module_data in self.make_json["flow"]:
                modules.append(module_data)
                # Handle nested routes for routers (e.g., BasicRouter)
                if "routes" in module_data and isinstance(module_data["routes"], list):
                    for route in module_data["routes"]:
                        if "flow" in route and isinstance(route["flow"], list):
                            for nested_module_data in route["flow"]:
                                modules.append(nested_module_data)

        # Extract connections (Make.com connections are implicit in flow order and routes)
        # This will be handled more explicitly in the mapper/generator
        
        return {
            "modules": modules,
            "connections": connections # Placeholder, actual connection logic in mapper
        }