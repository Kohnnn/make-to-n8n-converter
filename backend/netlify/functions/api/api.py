import os
import sys
from netlify_lambda_wsgi import make_wsgi_handler

# Import the Flask app from the local flask_app.py file
# This makes the function more self-contained and reliable
from flask_app import app

# Configure app for serverless
app.debug = False

# Add some debug logging
print("Netlify function initialized")
print(f"Current directory: {os.path.dirname(os.path.abspath(__file__))}")

# Create the handler
handler = make_wsgi_handler(app)