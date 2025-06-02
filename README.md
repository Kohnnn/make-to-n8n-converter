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
└── README.md
```

## How to Use (Planned)

1.  **Run the Backend**: Start the Python Flask/FastAPI application.
2.  **Access the Frontend**: Open `index.html` in your web browser.
3.  **Upload**: Drag and drop your Make.com workflow JSON file or use the "Browse files" button.
4.  **Convert**: The application will automatically process the file.
5.  **Download**: Once converted, a download button will appear for the n8n workflow JSON.

## Limitations

-   **Expression Complexity**: Some complex Make.com expressions may not have direct n8n equivalents and will be removed with a notification. Manual adjustment in n8n may be required.
-   **Module Coverage**: Initial conversion will focus on generic mappings. Specific or highly custom Make.com modules might require manual adjustments in the generated n8n workflow.

## Development Setup (Planned)

### Backend

1.  Navigate to the `backend` directory.
2.  Install dependencies: `pip install -r requirements.txt`
3.  Run the Flask application: `python app.py`

### Frontend

1.  Open `frontend/index.html` in your web browser.

## Contributing (Planned)

Contributions are welcome! Please refer to the detailed plan for more information on how to contribute to module mappings or conversion logic.