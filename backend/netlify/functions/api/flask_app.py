import json
import os
import sys
import traceback
from flask import Flask, request, jsonify, render_template, make_response
from werkzeug.utils import secure_filename
from flask_cors import CORS

# Set up logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Print debug information
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.info(f"Current directory: {current_dir}")
logger.info(f"Files in current directory: {os.listdir(current_dir)}")

# Import the self-contained converter module
try:
    from converter import perform_conversion, FALLBACK_MODULE_MAPPINGS
    logger.info("Successfully imported self-contained converter module")
except Exception as e:
    logger.error(f"Error importing converter module: {str(e)}")
    logger.error(traceback.format_exc())

app = Flask(__name__)
CORS(app)

# Try to load module mappings, but use fallback if not available
try:
    mappings_path = os.path.join(current_dir, 'module_mappings.json')
    logger.info(f"Looking for mappings at: {mappings_path}")
    
    if os.path.exists(mappings_path):
        with open(mappings_path, 'r') as f:
            MODULE_MAPPINGS = json.load(f)
        logger.info(f"Loaded {len(MODULE_MAPPINGS)} module mappings")
    else:
        # Try the original path as fallback
        original_mappings_path = os.path.join(current_dir, '../../../../backend/mappings/generic_module_mappings.json')
        if os.path.exists(original_mappings_path):
            with open(original_mappings_path, 'r') as f:
                MODULE_MAPPINGS = json.load(f)
            logger.info(f"Loaded {len(MODULE_MAPPINGS)} module mappings from original path")
        else:
            logger.warning("Using fallback module mappings")
            MODULE_MAPPINGS = FALLBACK_MODULE_MAPPINGS
except Exception as e:
    logger.warning(f"Error loading mappings, using fallback: {str(e)}")
    MODULE_MAPPINGS = FALLBACK_MODULE_MAPPINGS

# For serverless, we'll need to handle file uploads differently
@app.route('/', methods=['POST'])
def convert_workflow():
    logger.info("Received POST request to /")
    
    try:
        # Add CORS headers to the response
        def create_cors_response(response_data, status_code=200):
            response = make_response(jsonify(response_data), status_code)
            response.headers.add('Access-Control-Allow-Origin', '*')
            response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
            response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
            return response
        
        # Handle preflight OPTIONS request
        if request.method == 'OPTIONS':
            return create_cors_response({"status": "ok"})
        
        # Check if request has files
        if 'file' not in request.files:
            logger.warning("No file part in request")
            return create_cors_response({"success": False, "error": "No file part"}, 400)
        
        file = request.files['file']
        logger.info(f"Received file: {file.filename}")
        
        if file.filename == '':
            logger.warning("Empty filename")
            return create_cors_response({"success": False, "error": "No selected file"}, 400)
        
        try:
            # Read file content as text first
            file_content = file.read().decode('utf-8', errors='replace')
            logger.info(f"File content length: {len(file_content)} characters")
            
            # Check if content starts with HTML doctype or tags
            if file_content.strip().startswith(('<!DOCTYPE', '<html')):
                logger.warning("HTML content detected in file")
                return create_cors_response({
                    "success": False,
                    "error": "Received HTML content instead of JSON. Please use the 'Export blueprint' option in Make.com.",
                    "stack": "HTML content detected in file"
                }, 400)
            
            # Attempt to parse JSON
            make_json = json.loads(file_content)
            logger.info("Successfully parsed JSON")
            
            # Check if it has the expected Make.com structure
            if "flow" not in make_json:
                logger.warning("Missing 'flow' property in JSON")
                return create_cors_response({
                    "success": False,
                    "error": "Invalid Make.com workflow format. Missing 'flow' property.",
                    "stack": "Invalid workflow structure"
                }, 400)
            
            logger.info("Starting conversion process using self-contained converter")
            
            # Use the self-contained converter function
            result = perform_conversion(make_json)
            logger.info("Conversion completed successfully")
            
            logger.info("Returning successful response")
            return create_cors_response(result)

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            return create_cors_response({
                "success": False,
                "error": f"Invalid JSON format: {str(e)}",
                "stack": f"Line {e.lineno}, column {e.colno}: {e.msg}"
            }, 400)
        except Exception as e:
            logger.error(f"Conversion error: {str(e)}")
            logger.error(traceback.format_exc())
            return create_cors_response({
                "success": False,
                "error": f"Conversion failed: {str(e)}",
                "stack": traceback.format_exc()
            }, 500)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        return create_cors_response({
            "success": False,
            "error": f"Server error: {str(e)}",
            "stack": traceback.format_exc()
        }, 500)

@app.route('/', methods=['GET'])
def index():
    logger.info("Received GET request to /")
    response = make_response(jsonify({
        "status": "API is running",
        "version": "1.0.0",
        "environment": os.environ.get('NETLIFY', 'local'),
        "python_version": sys.version,
        "mappings_count": len(MODULE_MAPPINGS)
    }))
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Add a health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    logger.info("Received health check request")
    response = make_response(jsonify({
        "status": "ok",
        "version": "1.0.0",
        "mappings_count": len(MODULE_MAPPINGS)
    }))
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response

# Add an OPTIONS route to handle preflight requests
@app.route('/', methods=['OPTIONS'])
def options():
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    return response
