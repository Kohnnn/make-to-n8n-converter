import os
import sys
from netlify_lambda_wsgi import make_wsgi_handler

# Add the backend directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
backend_path = os.path.join(project_root)
sys.path.insert(0, backend_path)

# Import the Flask app
from netlify.functions.api.flask_app import app

# Configure app for serverless
app.debug = False

# Create the handler
handler = make_wsgi_handler(app) 