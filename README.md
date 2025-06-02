# Make.com to n8n Workflow Converter

This application provides a tool to convert Make.com workflow JSON files into n8n workflow JSON format. It features a simple web interface for uploading Make.com workflows and downloading the converted n8n workflows.

## Features

- Upload Make.com workflow JSON files.
- Convert Make.com modules, connections, and configurations to n8n format.
- Handle common parameter mappings and expression transformations.
- Provide a downloadable n8n workflow JSON.
- Notify users about unconvertible expressions or unmapped modules.

## Project Structure

```
make-to-n8n-converter/
├── backend/
│   ├── app.py                 # Flask/FastAPI application
│   ├── converter/
│   │   ├── __init__.py
│   │   ├── parser.py          # Make.com JSON parser
│   │   ├── mapper.py          # Generic module mapping logic
│   │   ├── transformer.py     # Parameter and expression transformation
│   │   ├── generator.py       # n8n JSON generator
│   │   └── utils.py           # Helper functions (e.g., position calculation)
│   ├── mappings/
│   │   └── generic_module_mappings.json  # Generic Make.com to n8n module mappings
│   └── requirements.txt
├── frontend/
│   ├── index.html             # Main HTML file for the SPA
│   ├── style.css              # Styling for the UI
│   └── script.js              # Frontend logic (upload, download, UI updates)
├── netlify/
│   └── functions/
│       └── api/               # Netlify function files
│           ├── api.py         # Handler for the API function
│           ├── flask_app.py   # Flask app for serverless
│           ├── requirements.txt # Python dependencies
│           └── runtime.txt    # Python runtime version
├── netlify.toml               # Netlify configuration
└── README.md
```

## How to Use (Local Development)

1. Navigate to the `backend` directory.
2. Install dependencies: `pip install -r requirements.txt`
3. Run the Flask application: `python app.py`
4. Open `frontend/index.html` in your web browser.
5. Upload your Make.com workflow JSON file or use the "Try Sample Workflow" button.
6. Process the file and download the converted n8n workflow JSON.

## Deployment on Netlify

### Prerequisites

- A GitHub account
- A Netlify account

### Steps to Deploy

1. **Push Your Code to GitHub**

   ```bash
   git add .
   git commit -m "Prepare for Netlify deployment"
   git push origin main
   ```

2. **Connect to Netlify**

   - Go to [Netlify](https://app.netlify.com/teams/kohnnn/projects)
   - Click "Add new site" > "Import an existing project"
   - Select GitHub as the Git provider
   - Authorize Netlify to access your GitHub repositories
   - Select the "make-to-n8n-converter" repository

3. **Configure Build Settings**

   - Build command: Leave blank (already configured in netlify.toml)
   - Publish directory: `frontend`
   - Click "Deploy site"

4. **Verify Function Deployment**

   - Once deployed, check the "Functions" tab in your Netlify dashboard
   - You should see an "api" function listed
   - Test by visiting your-site-url/.netlify/functions/api

### Local Development with Netlify CLI

1. **Install Dependencies**

   ```bash
   # Install Netlify CLI
   npm install netlify-cli -g

   # Install backend dependencies
   pip install -r backend/requirements.txt
   ```

2. **Run Locally with Netlify Dev**

   ```bash
   netlify dev
   ```

   This will start the application at http://localhost:3000

## Limitations

-   **Expression Complexity**: Some complex Make.com expressions may not have direct n8n equivalents and will be removed with a notification. Manual adjustment in n8n may be required.
-   **Module Coverage**: Initial conversion will focus on generic mappings. Specific or highly custom Make.com modules might require manual adjustments in the generated n8n workflow.
-   **Netlify Functions**: Netlify functions have a 10MB payload limit and 10-second execution timeout which may affect processing large workflows.

## Contributing

Contributions are welcome! Please help expand the module mappings or improve the conversion logic by submitting pull requests.