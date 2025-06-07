const { createHandler } = require('../netlify_lambda_wsgi.js');
const path = require('path');

exports.handler = createHandler(path.resolve(__dirname, 'flask_app.py'));