import json
import os
import sys
import traceback
from flask import Flask, request, jsonify, make_response
from flask_cors import CORS
import uuid
import datetime
import re
import logging

# --- Basic Setup ---
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app)

# --- Self-Contained Converter Logic ---

class NodeUtils:
    @staticmethod
    def calculate_n8n_position(make_position: dict):
        x = make_position.get("x", 0)
        y = make_position.get("y", 0)
        return [x, y]

    @staticmethod
    def generate_node_id(node_name: str):
        slug = re.sub(r'\W+', '-', node_name).lower()
        return f"{slug}"

class MakeComParser:
    def __init__(self, make_json: dict):
        self.make_json = make_json

    def parse(self):
        modules = []
        if "flow" in self.make_json and isinstance(self.make_json["flow"], list):
            for module_data in self.make_json["flow"]:
                modules.append(module_data)
                if "routes" in module_data and isinstance(module_data["routes"], list):
                    for route in module_data["routes"]:
                        if "flow" in route and isinstance(route["flow"], list):
                            for nested_module_data in route["flow"]:
                                modules.append(nested_module_data)
        return {"modules": modules, "connections": []}

class ParameterTransformer:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.unconvertible_expressions = []
        self.function_mappings = {
            "parseDate": "new Date", "formatDate": "$items[0].json.date ? $items[0].json.date.toISOString() : ''",
            "toString": "String", "toNumber": "Number", "sum": "reduce((a, c) => a + c, 0)",
            "substring": "substring", "replace": "replace", "length": "length",
            "lower": "toLowerCase", "upper": "toUpperCase", "trim": "trim",
            "split": "split", "join": "join"
        }

    def transform_parameters(self, make_module: dict, n8n_node_type: str):
        n8n_parameters = {}
        module_type = make_module.get("module")
        module_mapping = self.mappings.get(module_type, {})
        parameter_map = module_mapping.get("parameters", {})
        all_make_params = {**make_module.get("parameters", {}), **make_module.get("mapper", {})}

        for make_param_key, n8n_param_path in parameter_map.items():
            if make_param_key in all_make_params:
                make_value = all_make_params[make_param_key]
                converted_value = self._convert_expression(make_value)
                self._set_nested_value(n8n_parameters, n8n_param_path, converted_value)
        if "operation" in module_mapping:
            n8n_parameters["operation"] = module_mapping["operation"]
        return n8n_parameters

    def _convert_expression(self, value):
        if not isinstance(value, str): return value
        full_match = re.match(r"^\{\{(.*)\}\}$", value)
        if full_match:
            return self._transform_make_expression(full_match.group(1).strip(), is_full_value=True)
        return re.sub(r"\{\{(.*?)\}\}", lambda m: self._transform_make_expression(m.group(1).strip()), value)

    def _transform_make_expression(self, content, is_full_value=False):
        # This is a simplified version for brevity
        return f"={{ {content} }}" if is_full_value else f"{{ {content} }}"

    def _set_nested_value(self, obj, path, value):
        keys = path.split('.')
        for key in keys[:-1]:
            obj = obj.setdefault(key, {})
        obj[keys[-1]] = value

class MakeComToN8nMapper:
    def __init__(self, mappings: dict):
        self.mappings = mappings
        self.parameter_transformer = ParameterTransformer(mappings)
        self.warnings = []

    def map_workflow(self, make_modules: list):
        n8n_nodes, connections, id_map = [], {}, {}
        for module in make_modules:
            make_id = module.get("id")
            n8n_id = NodeUtils.generate_node_id(module.get("metadata", {}).get("designer", {}).get("name", f"Module {make_id}"))
            id_map[make_id] = n8n_id
            node = self._create_n8n_node(module, n8n_id)
            if node: n8n_nodes.append(node)
            else: self.warnings.append(f"Unmapped module: {module.get('module')}")
        
        # Simplified connection logic
        for i, module in enumerate(make_modules[:-1]):
            from_id = id_map.get(module.get("id"))
            to_id = id_map.get(make_modules[i+1].get("id"))
            if from_id and to_id:
                connections.setdefault(from_id, {}).setdefault("main", []).append([{"node": to_id, "type": "main", "index": 0}])

        return {"nodes": n8n_nodes, "connections": connections, "warnings": self.warnings}

    def _create_n8n_node(self, module, n8n_id):
        mapping = self.mappings.get(module.get("module"))
        if not mapping: return None
        return {
            "id": n8n_id, "name": module.get("metadata", {}).get("designer", {}).get("name"),
            "type": mapping["n8n_type"], "typeVersion": 1,
            "position": NodeUtils.calculate_n8n_position(module.get("metadata", {}).get("designer", {})),
            "parameters": self.parameter_transformer.transform_parameters(module, mapping["n8n_type"])
        }

class N8nWorkflowGenerator:
    def __init__(self, nodes, connections, name):
        self.nodes, self.connections, self.name = nodes, connections, name

    def generate_workflow(self):
        now = datetime.datetime.utcnow().isoformat()
        return {
            "id": str(uuid.uuid4()), "name": self.name, "nodes": self.nodes,
            "connections": self.connections, "active": False, "versionId": str(uuid.uuid4()),
            "createdAt": now, "updatedAt": now, "tags": ["converted"],
            "settings": {"executionOrder": "v1"}, "meta": {"convertedFromMakeCom": True}
        }

# --- Mappings ---
MODULE_MAPPINGS = {
  "telegram:SendReplyMessage": {"n8n_type": "n8n-nodes-base.telegram", "parameters": {"text": "text", "chatId": "chatId"}},
  "google-calendar:ActionGetEvents": {"n8n_type": "n8n-nodes-base.googleCalendar", "operation": "event:getAll", "parameters": {"calendarId": "calendar"}},
  "util:ComposeTransformer": {"n8n_type": "n8n-nodes-base.set", "parameters": {"value": "values.string[0].value"}},
  "builtin:BasicRouter": {"n8n_type": "n8n-nodes-base.switch", "parameters": {"routes": "rules.values"}},
  "http:ActionSendData": {"n8n_type": "n8n-nodes-base.httpRequest", "parameters": {"url": "url", "method": "method", "body": "body"}},
  "webhook:CustomWebhook": {"n8n_type": "n8n-nodes-base.webhook", "parameters": {"path": "path", "httpMethod": "method"}}
}

# --- Flask App & Handler ---

@app.route('/api', methods=['POST', 'OPTIONS'])
def handler():
    if request.method == 'OPTIONS':
        headers = {'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Methods': 'POST', 'Access-Control-Allow-Headers': 'Content-Type'}
        return ('', 204, headers)

    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "No file part"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"success": False, "error": "No selected file"}), 400

        make_json = json.load(file)
        
        parser = MakeComParser(make_json)
        parsed_data = parser.parse()
        
        mapper = MakeComToN8nMapper(MODULE_MAPPINGS)
        mapped_data = mapper.map_workflow(parsed_data["modules"])

        generator = N8nWorkflowGenerator(mapped_data["nodes"], mapped_data["connections"], make_json.get("name", "Converted Workflow"))
        n8n_workflow = generator.generate_workflow()

        response_data = {"success": True, "n8n_workflow": n8n_workflow, "warnings": mapped_data["warnings"]}
        
        response = make_response(jsonify(response_data))
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

    except Exception as e:
        logger.error(f"Error during conversion: {e}\n{traceback.format_exc()}")
        response = make_response(jsonify({"success": False, "error": "Internal Server Error", "details": str(e)}), 500)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response

# This is for local development, not used by Netlify
if __name__ == "__main__":
    app.run(debug=True)