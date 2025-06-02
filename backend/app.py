import json
import os
import traceback
from flask import Flask, request, jsonify, send_from_directory, render_template
from werkzeug.utils import secure_filename
from flask_cors import CORS

from converter.parser import MakeComParser
from converter.mapper import MakeComToN8nMapper
from converter.generator import N8nWorkflowGenerator

app = Flask(__name__,
            static_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend'),
            template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), '../frontend'))

# Enable CORS for development
CORS(app)

# Set UPLOAD_FOLDER relative to the current script's directory
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16 MB limit

# Ensure upload folder exists
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# Load module mappings
try:
    # Path to mappings file relative to the current script
    mappings_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'mappings', 'generic_module_mappings.json')
    with open(mappings_path, 'r') as f:
        MODULE_MAPPINGS = json.load(f)
except FileNotFoundError:
    MODULE_MAPPINGS = {}
    print(f"Warning: {mappings_path} not found. Using empty mappings.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/convert', methods=['POST'])
def convert_workflow():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and file.filename.endswith('.json'):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            with open(filepath, 'r') as f:
                make_json = json.load(f)
            
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

            # Clean up uploaded file
            os.remove(filepath)

            return jsonify({
                "success": True,
                "n8n_workflow": n8n_workflow,
                "warnings": mapped_data["warnings"]
            })

        except json.JSONDecodeError:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                "success": False,
                "error": "Invalid JSON file. The uploaded file is not a valid JSON document.",
                "stack": traceback.format_exc()
            }), 400
        except KeyError as e:
            if os.path.exists(filepath):
                os.remove(filepath)
            return jsonify({
                "success": False,
                "error": f"Invalid Make.com workflow structure. Missing key: {str(e)}",
                "stack": traceback.format_exc()
            }), 400
        except Exception as e:
            if os.path.exists(filepath):
                os.remove(filepath)
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

# Route to serve static files from the frontend directory
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# API endpoint to check server status
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "mappings_count": len(MODULE_MAPPINGS)
    })

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)