import json
import os
import sys
import traceback
from flask import Flask, request, jsonify, render_template
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Import your converter modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../'))
from backend.converter.parser import MakeComParser
from backend.converter.mapper import MakeComToN8nMapper
from backend.converter.generator import N8nWorkflowGenerator

app = Flask(__name__)
CORS(app)

# Load module mappings - adjust path for serverless environment
try:
    mappings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../../backend/mappings/generic_module_mappings.json')
    with open(mappings_path, 'r') as f:
        MODULE_MAPPINGS = json.load(f)
except FileNotFoundError:
    MODULE_MAPPINGS = {}
    print(f"Warning: Mappings file not found. Using empty mappings.")

# For serverless, we'll need to handle file uploads differently
@app.route('/convert', methods=['POST'])
def convert_workflow():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"success": False, "error": "No selected file"}), 400
    
    if file and file.filename.endswith('.json'):
        try:
            # Read file content as text first to check for HTML
            file_content = file.read().decode('utf-8')
            
            # Check if content starts with HTML doctype or tags - likely invalid
            if file_content.strip().startswith(('<!DOCTYPE', '<html')):
                return jsonify({
                    "success": False,
                    "error": "Received HTML content instead of JSON. This can happen when downloading from Make.com via browser save. Please use the 'Export blueprint' option in Make.com.",
                    "stack": "HTML content detected in JSON file"
                }), 400
            
            # Parse the JSON content
            make_json = json.loads(file_content)
            
            # Parse Make.com JSON
            parser = MakeComParser(make_json)
            parsed_data = parser.parse()
            
            # Map to n8n format
            mapper = MakeComToN8nMapper(MODULE_MAPPINGS)
            mapped_data = mapper.map_workflow(parsed_data["modules"])

            # Generate n8n workflow
            workflow_name = make_json.get("name", "Converted Workflow")
            generator = N8nWorkflowGenerator(mapped_data["nodes"], mapped_data["connections"], workflow_name)
            n8n_workflow = generator.generate_workflow()

            return jsonify({
                "success": True,
                "n8n_workflow": n8n_workflow,
                "warnings": mapped_data["warnings"]
            })

        except json.JSONDecodeError as e:
            return jsonify({
                "success": False,
                "error": f"Invalid JSON format: {str(e)}",
                "stack": f"Line {e.lineno}, column {e.colno}: {e.msg}"
            }), 400
        except Exception as e:
            return jsonify({
                "success": False, 
                "error": f"Conversion failed: {str(e)}",
                "stack": traceback.format_exc()
            }), 500
    else:
        return jsonify({
            "success": False,
            "error": "Invalid file type. Please upload a JSON file."
        }), 400

@app.route('/', methods=['GET'])
def index():
    return jsonify({"status": "API is running"})
