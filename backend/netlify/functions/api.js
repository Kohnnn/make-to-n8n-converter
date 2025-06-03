// Import the handler from the api.py file
const { handler } = require('./api/api');

// Export the handler to be used by Netlify Functions
exports.handler = handler;