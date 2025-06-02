import json
from .utils import NodeUtils
from .transformer import ParameterTransformer

class MakeComToN8nMapper:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.parameter_transformer = ParameterTransformer(mappings)
        self.n8n_nodes = []
        self.n8n_connections = {} # This format was incorrect - needs to be transformed
        self.make_module_id_to_n8n_node_id = {}
        self.warnings = []

    def map_workflow(self, make_modules: list):
        """
        Maps Make.com modules to n8n nodes and establishes connections.
        """
        # First pass: Create n8n nodes and map IDs
        for make_module in make_modules:
            make_module_id = make_module.get("id")
            make_module_type = make_module.get("module")
            make_module_name = make_module.get("metadata", {}).get("designer", {}).get("name", f"Module {make_module_id}")

            n8n_node_id = NodeUtils.generate_node_id(make_module_name)
            self.make_module_id_to_n8n_node_id[make_module_id] = n8n_node_id

            n8n_node = self._create_n8n_node(make_module, n8n_node_id, make_module_name)
            if n8n_node:
                self.n8n_nodes.append(n8n_node)
            else:
                self.warnings.append(f"Could not map Make.com module '{make_module_type}' (ID: {make_module_id}, Name: '{make_module_name}'). A placeholder node has been created.")
                # Create a placeholder node for unmapped modules
                placeholder_node = {
                    "id": n8n_node_id,
                    "name": f"UNMAPPED: {make_module_name}",
                    "type": "n8n-nodes-base.noOp", # Using No-Op as a generic placeholder
                    "position": NodeUtils.calculate_n8n_position(make_module.get("metadata", {}).get("designer", {})),
                    "parameters": {
                        "notes": f"Original Make.com Module Type: {make_module_type}\nOriginal Make.com Module ID: {make_module_id}\nThis module could not be automatically converted. Manual adjustment is required."
                    },
                    "typeVersion": 1
                }
                self.n8n_nodes.append(placeholder_node)


        # Second pass: Establish connections
        # Make.com connections are implicit in the 'flow' array and 'routes'
        # We need to infer connections based on the sequence of modules
        for i, make_module in enumerate(make_modules):
            current_make_id = make_module.get("id")
            current_n8n_id = self.make_module_id_to_n8n_node_id.get(current_make_id)

            if not current_n8n_id:
                continue # Skip if the node itself was not mapped

            # Handle sequential connections
            if i < len(make_modules) - 1:
                next_make_module = make_modules[i+1]
                next_make_id = next_make_module.get("id")
                next_n8n_id = self.make_module_id_to_n8n_node_id.get(next_make_id)

                if next_n8n_id:
                    self._add_connection(current_n8n_id, next_n8n_id, "main", 0)

            # Handle router connections (e.g., BasicRouter)
            if make_module.get("module") == "builtin:BasicRouter" and "routes" in make_module:
                for route_index, route in enumerate(make_module["routes"]):
                    if "flow" in route and route["flow"]:
                        first_node_in_route_make_id = route["flow"][0].get("id")
                        first_node_in_route_n8n_id = self.make_module_id_to_n8n_node_id.get(first_node_in_route_make_id)
                        if first_node_in_route_n8n_id:
                            self._add_connection(current_n8n_id, first_node_in_route_n8n_id, "main", route_index)
        
        # Add unconvertible expression warnings to a sticky note if any
        if self.parameter_transformer.unconvertible_expressions:
            sticky_note_id = NodeUtils.generate_node_id("unconvertible-expressions-warning")
            sticky_note_content = "## Unconvertible Expressions Warning\n\nThe following expressions from the Make.com workflow could not be directly converted to n8n expressions and have been removed or replaced with placeholders. Manual review and adjustment are required:\n\n"
            for expr_warning in self.parameter_transformer.unconvertible_expressions:
                sticky_note_content += f"- {expr_warning}\n"
            
            # Find a suitable position for the sticky note (e.g., top-left)
            min_x = min(node["position"][0] for node in self.n8n_nodes) if self.n8n_nodes else 0
            min_y = min(node["position"][1] for node in self.n8n_nodes) if self.n8n_nodes else 0

            self.n8n_nodes.insert(0, { # Insert at the beginning for visibility
                "id": sticky_note_id,
                "name": "Unconvertible Expressions",
                "type": "n8n-nodes-base.stickyNote",
                "position": [min_x - 300, min_y - 200], # Offset from the top-leftmost node
                "parameters": {
                    "color": "6", # Red color for warning (as string to match n8n format)
                    "width": 400,
                    "height": 200,
                    "content": sticky_note_content
                },
                "typeVersion": 1
            })
            self.warnings.append("Some Make.com expressions could not be converted. Please check the 'Unconvertible Expressions' sticky note in the generated n8n workflow for details.")

        # Transform connections into n8n format
        formatted_connections = self._format_connections()

        return {
            "nodes": self.n8n_nodes,
            "connections": formatted_connections,
            "warnings": self.warnings
        }

    def _create_n8n_node(self, make_module: dict, n8n_node_id: str, make_module_name: str):
        """
        Creates an n8n node from a Make.com module.
        """
        make_module_type = make_module.get("module")
        mapping = self.mappings.get(make_module_type)

        if not mapping:
            return None # Indicate that this module could not be mapped

        n8n_node = {
            "id": n8n_node_id,
            "name": make_module_name,
            "type": mapping["n8n_type"],
            "position": NodeUtils.calculate_n8n_position(make_module.get("metadata", {}).get("designer", {})),
            "parameters": self.parameter_transformer.transform_parameters(make_module, mapping["n8n_type"]),
            "typeVersion": mapping.get("typeVersion", 1) # Use mapping typeVersion or default to 1
        }
        
        # Add credentials if specified in mapping
        if "credentials" in mapping:
            n8n_node["credentials"] = mapping["credentials"]
            
        return n8n_node

    def _add_connection(self, from_node_id: str, to_node_id: str, type: str, index: int):
        """
        Adds a connection to the n8n connections dictionary.
        """
        if from_node_id not in self.n8n_connections:
            self.n8n_connections[from_node_id] = {}
        
        if type not in self.n8n_connections[from_node_id]:
            self.n8n_connections[from_node_id][type] = []
        
        # Ensure the list is long enough for the given index
        while len(self.n8n_connections[from_node_id][type]) <= index:
            self.n8n_connections[from_node_id][type].append([])

        self.n8n_connections[from_node_id][type][index].append({
            "node": to_node_id,
            "type": "main", # Assuming 'main' connection type for now
            "index": 0 # Assuming first input for now
        })
    
    def _format_connections(self):
        """
        Formats the connections dictionary into n8n compatible structure.
        n8n connections format uses source node ID as the key and a structure of output-input mappings.
        """
        formatted_connections = {}
        
        for source_id, connection_types in self.n8n_connections.items():
            formatted_connections[source_id] = {}
            
            for conn_type, indexes in connection_types.items():
                formatted_connections[source_id][conn_type] = []
                
                for index, targets in enumerate(indexes):
                    if targets:  # Only add if there are targets at this index
                        formatted_connections[source_id][conn_type].append(targets)
        
        return formatted_connections 