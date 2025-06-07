// This file serves as a bridge between the Netlify Functions system (Node.js)
// and our Python handler in api.py

// Import the netlify-lambda-wsgi package
const { createHandler } = require('netlify-lambda-wsgi');

// Import path for resolving file paths
const path = require('path');
const fs = require('fs');

// Log the current directory and files for debugging
console.log('Current directory:', __dirname);
console.log('Files in directory:', fs.readdirSync(__dirname));

// Create the handler from the Flask app in flask_app.py
// We're using flask_app.py directly instead of api.py to simplify the import chain
const handler = createHandler(path.resolve(__dirname, './flask_app.py'), {
  app: 'app', // The name of the Flask app variable in flask_app.py
  debug: true // Enable debug mode for more detailed logs
});

// Export the handler for use in the parent api.js file
module.exports = { handler };