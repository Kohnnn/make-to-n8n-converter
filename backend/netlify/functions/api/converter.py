"""
Simplified converter module that combines parser, mapper, transformer, and generator
into a single file to make the serverless function more self-contained.
"""
import json
import uuid
import datetime
import re
import logging

logger = logging.getLogger(__name__)

class NodeUtils:
    @staticmethod
    def calculate_n8n_position(make_position: dict):
        """
        Calculates n8n node position from Make.com module position.
        """
        x = make_position.get("x", 0)
        y = make_position.get("y", 0)
        return [x, y]

    @staticmethod
    def generate_node_id(node_name: str):
        """
        Generates a simple n8n-like ID for a node based on its name.
        """
        # Simple slugification for ID
        import re
        slug = re.sub(r'\W+', '-', node_name).lower()
        return f"{slug}"

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
        
        return {
            "modules": modules,
            "connections": connections # Placeholder, actual connection logic in mapper
        }

class ParameterTransformer:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.unconvertible_expressions = []
        # Dictionary of common Make.com functions and their n8n equivalents
        self.function_mappings = {
            "parseDate": "new Date",
            "formatDate": "$items[0].json.date ? $items[0].json.date.toISOString() : ''",
            "toString": "String",
            "toNumber": "Number",
            "sum": "reduce((accumulator, currentValue) => accumulator + currentValue, 0)",
            "substring": "substring",
            "replace": "replace",
            "length": "length",
            "lower": "toLowerCase",
            "upper": "toUpperCase",
            "trim": "trim",
            "split": "split",
            "join": "join"
        }

    def transform_parameters(self, make_module: dict, n8n_node_type: str):
        """
        Transforms Make.com module parameters into n8n node parameters based on mappings.
        """
        n8n_parameters = {}
        module_type = make_module.get("module")
        module_mapping = self.mappings.get(module_type, {})
        parameter_map = module_mapping.get("parameters", {})

        make_parameters = make_module.get("parameters", {})
        make_mapper = make_module.get("mapper", {})

        # Combine parameters from 'parameters' and 'mapper' fields in Make.com
        all_make_params = {**make_parameters, **make_mapper}

        for make_param_key, n8n_param_path in parameter_map.items():
            if make_param_key in all_make_params:
                make_value = all_make_params[make_param_key]
                converted_value = self._convert_expression(make_value)
                self._set_nested_value(n8n_parameters, n8n_param_path, converted_value)
            elif make_param_key == "routes" and "routes" in make_module: # Special handling for BasicRouter routes
                n8n_parameters["rules"] = {"values": []}
                for route in make_module["routes"]:
                    rule = {
                        "outputKey": f"output_{len(n8n_parameters['rules']['values'])}",
                        "conditions": {
                            "conditions": []
                        }
                    }
                    
                    # Try to extract conditions from route if available
                    if "condition" in route:
                        condition = route["condition"]
                        if isinstance(condition, dict) and "operand1" in condition and "operand2" in condition and "operator" in condition:
                            op1 = self._convert_expression(condition["operand1"])
                            op2 = self._convert_expression(condition["operand2"])
                            operator = self._map_operator(condition["operator"])
                            
                            rule["conditions"]["conditions"].append({
                                "id": f"condition_{len(rule['conditions']['conditions'])}",
                                "value1": op1,
                                "operation": operator,
                                "value2": op2
                            })
                    
                    n8n_parameters["rules"]["values"].append(rule)
        
        # Add operation if specified in mapping
        if "operation" in module_mapping:
            n8n_parameters["operation"] = module_mapping["operation"]

        return n8n_parameters

    def _convert_expression(self, value):
        """
        Converts Make.com expressions (e.g., {{...}}) to n8n expressions (e.g., ={{...}}).
        """
        if not isinstance(value, str):
            return value

        # Regex to find Make.com expressions: {{...}}
        make_expression_pattern = r"\{\{(.*?)\}\}"
        
        # Check if the entire value is an expression
        full_match = re.match(r"^\{\{(.*)\}\}$", value)
        if full_match:
            expression_content = full_match.group(1).strip()
            return self._transform_make_expression(expression_content, is_full_value=True)
            
        # Find all expressions
        matches = re.findall(make_expression_pattern, value)

        if not matches:
            return value # No expression found, return as is

        converted_parts = []
        last_idx = 0
        for match in re.finditer(make_expression_pattern, value):
            start, end = match.span()
            expression_content = match.group(1).strip()

            # Add the text before the current expression
            converted_parts.append(value[last_idx:start])

            # Convert the expression
            converted_expression = self._transform_make_expression(expression_content, is_full_value=False)
            converted_parts.append(converted_expression)
            
            last_idx = end
        
        # Add any remaining text after the last expression
        converted_parts.append(value[last_idx:])

        return "".join(converted_parts)

    def _transform_make_expression(self, expression_content, is_full_value=False):
        """
        Transforms a Make.com expression into an n8n expression.
        """
        # Direct item access (e.g., 1.data or $json.data)
        if re.match(r'\d+\..*', expression_content) or re.match(r'\$\w+\..*', expression_content):
            # For full value expressions, wrap in =
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
        
        # Handle Make.com functions
        for make_func, n8n_func in self.function_mappings.items():
            # Pattern to match function calls: functionName(arguments)
            pattern = rf'{make_func}\((.*?)\)'
            if re.search(pattern, expression_content):
                try:
                    # Replace the function name and keep arguments
                    expression_content = re.sub(pattern, f'{n8n_func}(\\1)', expression_content)
                except Exception as e:
                    self.unconvertible_expressions.append(f"Error converting function {make_func}: {str(e)}")
        
        # Handle array references like myArray[0]
        if re.search(r'\[\d+\]', expression_content):
            # Already compatible with n8n
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
        
        # Handle simple variable references (e.g., $data)
        if expression_content.startswith("$"):
            if is_full_value:
                return f"={{ {expression_content} }}"
            return f"{{ {expression_content} }}"
            
        # For other cases, mark as potentially unconvertible
        self.unconvertible_expressions.append(f"Potentially unconvertible expression: {{{{{expression_content}}}}}")
        return f"/* REVIEW_EXPRESSION: {{{{{expression_content}}}}} */"

    def _map_operator(self, make_operator):
        """
        Maps Make.com operators to n8n operators.
        """
        operator_map = {
            "equal": "equal",
            "notEqual": "notEqual",
            "greaterThan": "larger",
            "greaterThanOrEqual": "largerEqual",
            "lessThan": "smaller",
            "lessThanOrEqual": "smallerEqual",
            "contains": "contains",
            "notContains": "notContains",
            "startsWith": "startsWith",
            "notStartsWith": "notStartsWith",
            "endsWith": "endsWith",
            "notEndsWith": "notEndsWith",
            "isEmpty": "empty",
            "notEmpty": "notEmpty",
            "in": "in",
            "notIn": "notIn",
            "regex": "regex"
        }
        
        return operator_map.get(make_operator, "unknown")

    def _set_nested_value(self, obj, path, value):
        """
        Sets a value in a nested dictionary/list structure given a dot-separated path.
        """
        parts = path.split('.')
        current = obj
        for i, part in enumerate(parts):
            # Check if we're dealing with array notation like 'values.string[0].name'
            if '[' in part and ']' in part:
                # Handle list index
                base_key, index_part = part.split('[', 1)
                index = int(index_part.split(']')[0])
                
                # Create the key if it doesn't exist
                if base_key not in current:
                    current[base_key] = {}
                
                # If the next path component is after ], we're accessing a property of the array element
                if '].' in part:
                    # Extract the property name after ]
                    prop = part.split('].')[1]
                    
                    # Make sure we have an array
                    if not isinstance(current[base_key], list):
                        current[base_key] = []
                    
                    # Ensure the array is long enough
                    while len(current[base_key]) <= index:
                        current[base_key].append({})
                    
                    if i == len(parts) - 1:
                        # If it's the last part, set the value
                        current[base_key][index][prop] = value
                    else:
                        # Otherwise continue traversing
                        current = current[base_key][index][prop]
                else:
                    # We're setting a direct array index
                    if not isinstance(current[base_key], list):
                        current[base_key] = []
                    
                    # Ensure the array is long enough
                    while len(current[base_key]) <= index:
                        current[base_key].append({})
                    
                    if i == len(parts) - 1:
                        current[base_key][index] = value
                    else:
                        current = current[base_key][index]
            else:
                # Handle dictionary key
                if i == len(parts) - 1:
                    current[part] = value
                else:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

class MakeComToN8nMapper:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.parameter_transformer = ParameterTransformer(mappings)
        self.n8n_nodes = []
        self.n8n_connections = {}
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
                    "color": 6, # Red color for warning
                    "width": 400,
                    "height": 200,
                    "content": sticky_note_content
                },
                "typeVersion": 1
            })
            self.warnings.append("Some Make.com expressions could not be converted. Please check the 'Unconvertible Expressions' sticky note in the generated n8n workflow for details.")


        return {
            "nodes": self.n8n_nodes,
            "connections": self.n8n_connections,
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
            "typeVersion": 1 # Default typeVersion, might need to be dynamic
        }
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

class N8nWorkflowGenerator:
    def __init__(self, nodes: list, connections: dict, workflow_name: str = "Converted Workflow"):
        self.nodes = nodes
        self.connections = connections
        self.workflow_name = workflow_name

    def generate_workflow(self):
        """
        Generates the final n8n workflow JSON structure.
        """
        # Generate unique identifiers
        workflow_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        instance_id = str(uuid.uuid4())
        
        # Current timestamp for metadata
        current_time = datetime.datetime.utcnow().isoformat()

        n8n_workflow = {
            "id": workflow_id,
            "name": self.workflow_name,
            "nodes": self.nodes,
            "connections": self._format_connections(),
            "active": False, # Default to inactive
            "settings": {
                "executionOrder": "v1", # Default execution order
                "saveManualExecutions": True,
                "callerPolicy": "any",
                "saveDataErrorExecution": "all"
            },
            "versionId": version_id,
            "meta": {
                "instanceId": instance_id,
                "templateCredsSetupCompleted": True,
                "convertedFromMakeCom": True,
                "conversionDate": current_time
            },
            "tags": ["converted", "make.com"],
            "pinData": {},
            "staticData": None,
            "triggerCount": 0,
            "updatedAt": current_time,
            "createdAt": current_time,
            "description": "This workflow was automatically converted from a Make.com workflow. Some manual adjustments may be required."
        }
        
        return n8n_workflow
    
    def _format_connections(self):
        """
        Format connections into valid n8n format.
        """
        formatted_connections = {}
        
        # First check if connections is already in the right format
        if self.connections and all(isinstance(v, dict) for v in self.connections.values()):
            return self.connections
        
        # Otherwise, format it correctly
        for source_node_id, targets in self.connections.items():
            formatted_connections[source_node_id] = {
                "main": []
            }
            
            # n8n expects an array of arrays for outputs
            main_outputs = []
            
            # If we have a list of targets, they go in the first output index
            if isinstance(targets, list):
                output_targets = []
                for target in targets:
                    output_targets.append({
                        "node": target["node"],
                        "type": "main",
                        "index": target.get("index", 0)
                    })
                main_outputs.append(output_targets)
            
            formatted_connections[source_node_id]["main"] = main_outputs
            
        return formatted_connections

# Fallback module mappings in case the JSON file can't be loaded
FALLBACK_MODULE_MAPPINGS = {
    "telegram:SendReplyMessage": {
        "n8n_type": "n8n-nodes-base.telegram",
        "parameters": {
            "text": "text",
            "chatId": "chatId"
        }
    },
    "webhook:CustomWebhook": {
        "n8n_type": "n8n-nodes-base.webhook",
        "parameters": {
            "path": "path",
            "httpMethod": "method"
        }
    },
    "http:ActionSendData": {
        "n8n_type": "n8n-nodes-base.httpRequest",
        "parameters": {
            "url": "url",
            "method": "method",
            "body": "body"
        }
    },
    "util:Switcher": {
        "n8n_type": "n8n-nodes-base.switch",
        "parameters": {
            "input": "value1",
            "casesTable": "rules.values"
        }
    },
    "builtin:BasicRouter": {
        "n8n_type": "n8n-nodes-base.switch",
        "parameters": {
            "routes": "rules.values"
        }
    }
}

def perform_conversion(make_json):
    """
    Main function to convert a Make.com workflow to n8n format.
    """
    logger.info("Starting conversion process")
    
    # Parse Make.com JSON
    parser = MakeComParser(make_json)
    parsed_data = parser.parse()
    logger.info(f"Parsed Make.com JSON with {len(parsed_data['modules'])} modules")
    
    # Map to n8n format
    mapper = MakeComToN8nMapper(FALLBACK_MODULE_MAPPINGS)
    mapped_data = mapper.map_workflow(parsed_data["modules"])
    logger.info(f"Mapped to n8n format with {len(mapped_data['nodes'])} nodes")

    # Generate n8n workflow
    workflow_name = make_json.get("name", "Converted Workflow")
    generator = N8nWorkflowGenerator(mapped_data["nodes"], mapped_data["connections"], workflow_name)
    n8n_workflow = generator.generate_workflow()
    logger.info("Generated n8n workflow")
    
    return {
        "success": True,
        "n8n_workflow": n8n_workflow,
        "warnings": mapped_data["warnings"]
    }