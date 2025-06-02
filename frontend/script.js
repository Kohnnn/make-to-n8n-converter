document.addEventListener('DOMContentLoaded', () => {
    const dropArea = document.getElementById('drop-area');
    const fileInput = document.getElementById('fileInput');
    const uploadButton = document.getElementById('uploadButton');
    const statusMessage = document.getElementById('status-message');
    const warningsContainer = document.getElementById('warnings-container');
    const downloadSection = document.getElementById('download-section');
    const downloadButton = document.getElementById('downloadButton');
    const copyButton = document.getElementById('copyButton');
    const viewJsonButton = document.getElementById('viewJsonButton');
    const sampleWorkflowButton = document.getElementById('sampleWorkflowButton');
    const jsonPreview = document.getElementById('json-preview');
    const jsonContent = document.getElementById('json-content');
    const importInstructions = document.getElementById('import-instructions');
    const errorDetails = document.getElementById('error-details');
    const errorMessage = document.getElementById('error-message');
    const errorStack = document.getElementById('error-stack');

    let uploadedFile = null;
    let convertedWorkflow = null;

    // Sample workflow for the "Try Sample" button
    const sampleWorkflow = {
        "name": "Sample Make.com Workflow",
        "flow": [
            {
                "id": "1",
                "module": "webhook:CustomWebhook",
                "metadata": {
                    "designer": {
                        "x": 100,
                        "y": 100,
                        "name": "Receive Webhook"
                    }
                },
                "parameters": {
                    "path": "sample-webhook",
                    "method": "POST"
                }
            },
            {
                "id": "2",
                "module": "util:Switcher",
                "metadata": {
                    "designer": {
                        "x": 300,
                        "y": 100,
                        "name": "Route Based on Request"
                    }
                },
                "parameters": {
                    "input": "{{1.data.action}}",
                    "casesTable": [
                        {
                            "value": "create",
                            "output": "create"
                        },
                        {
                            "value": "update",
                            "output": "update"
                        }
                    ]
                },
                "routes": [
                    {
                        "condition": {
                            "operand1": "{{1.data.action}}",
                            "operator": "equal",
                            "operand2": "create"
                        },
                        "flow": [
                            {
                                "id": "3",
                                "module": "http:ActionSendData",
                                "metadata": {
                                    "designer": {
                                        "x": 500,
                                        "y": 0,
                                        "name": "Create API Call"
                                    }
                                },
                                "parameters": {
                                    "url": "https://api.example.com/create",
                                    "method": "POST",
                                    "body": "{{1.data}}"
                                }
                            }
                        ]
                    },
                    {
                        "condition": {
                            "operand1": "{{1.data.action}}",
                            "operator": "equal",
                            "operand2": "update"
                        },
                        "flow": [
                            {
                                "id": "4",
                                "module": "http:ActionSendData",
                                "metadata": {
                                    "designer": {
                                        "x": 500,
                                        "y": 200,
                                        "name": "Update API Call"
                                    }
                                },
                                "parameters": {
                                    "url": "https://api.example.com/update",
                                    "method": "PUT",
                                    "body": "{{1.data}}"
                                }
                            }
                        ]
                    }
                ]
            }
        ]
    };

    // Handle drag and drop events
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropArea.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropArea.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropArea.classList.add('highlight');
    }

    function unhighlight() {
        dropArea.classList.remove('highlight');
    }

    dropArea.addEventListener('drop', handleDrop, false);

    function handleDrop(e) {
        const dt = e.dataTransfer;
        const files = dt.files;
        handleFiles(files);
    }

    // Handle file input click
    dropArea.addEventListener('click', () => {
        fileInput.click();
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length === 0) {
            return;
        }

        const file = files[0];
        if (file.type !== 'application/json') {
            displayStatus('error', 'Invalid file type. Please upload a JSON file.');
            uploadedFile = null;
            uploadButton.disabled = true;
            return;
        }

        uploadedFile = file;
        displayStatus('success', `File selected: ${file.name}`);
        uploadButton.disabled = false;
        resetUI();
    }

    // Sample workflow button
    sampleWorkflowButton.addEventListener('click', () => {
        // Create a blob from the sample workflow
        const blob = new Blob([JSON.stringify(sampleWorkflow, null, 2)], { type: 'application/json' });
        
        // Create a file from the blob
        const file = new File([blob], 'sample-make-workflow.json', { type: 'application/json' });
        
        // Set as the uploaded file
        uploadedFile = file;
        displayStatus('success', 'Sample workflow loaded. Click "Upload & Convert" to process it.');
        uploadButton.disabled = false;
        resetUI();
    });

    uploadButton.addEventListener('click', async () => {
        if (!uploadedFile) {
            displayStatus('error', 'No file selected for upload.');
            return;
        }

        displayStatus('info', 'Converting workflow...');
        uploadButton.disabled = true;
        downloadSection.classList.add('hidden');
        warningsContainer.innerHTML = '';
        errorDetails.classList.add('hidden');

        const formData = new FormData();
        formData.append('file', uploadedFile);

        try {
            const response = await fetch('/convert', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok && result.success) {
                displayStatus('success', 'Conversion successful!');
                convertedWorkflow = result.n8n_workflow;
                downloadSection.classList.remove('hidden');
                importInstructions.classList.remove('hidden');
                
                // Display warnings if any
                if (result.warnings && result.warnings.length > 0) {
                    warningsContainer.innerHTML = '<h3>Warnings:</h3>';
                    result.warnings.forEach(warning => {
                        const p = document.createElement('p');
                        p.textContent = `- ${warning}`;
                        warningsContainer.appendChild(p);
                    });
                }
            } else {
                displayStatus('error', `Conversion failed: ${result.error || 'Unknown error'}`);
                if (result.error) {
                    showErrorDetails(result.error, result.stack || '');
                }
            }
        } catch (error) {
            displayStatus('error', `An error occurred: ${error.message}`);
            showErrorDetails(error.message, error.stack || '');
        } finally {
            uploadButton.disabled = false;
        }
    });

    downloadButton.addEventListener('click', () => {
        if (convertedWorkflow) {
            downloadWorkflow();
        }
    });

    copyButton.addEventListener('click', () => {
        if (convertedWorkflow) {
            copyToClipboard(JSON.stringify(convertedWorkflow, null, 2));
            displayTemporaryMessage(copyButton, 'Copied!');
        }
    });

    viewJsonButton.addEventListener('click', () => {
        if (convertedWorkflow) {
            if (jsonPreview.classList.contains('hidden')) {
                // Show JSON preview
                jsonContent.textContent = JSON.stringify(convertedWorkflow, null, 2);
                jsonPreview.classList.remove('hidden');
                viewJsonButton.innerHTML = '<i class="fas fa-eye-slash"></i> Hide JSON';
            } else {
                // Hide JSON preview
                jsonPreview.classList.add('hidden');
                viewJsonButton.innerHTML = '<i class="fas fa-eye"></i> View JSON';
            }
        }
    });

    function downloadWorkflow() {
        const filename = `${convertedWorkflow.name.replace(/\s/g, '_') || 'converted_workflow'}.json`;
        const blob = new Blob([JSON.stringify(convertedWorkflow, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    function copyToClipboard(text) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
    }

    function displayTemporaryMessage(button, message) {
        const originalContent = button.innerHTML;
        button.textContent = message;
        setTimeout(() => {
            button.innerHTML = originalContent;
        }, 2000);
    }

    function showErrorDetails(message, stack) {
        errorMessage.textContent = message;
        errorStack.textContent = stack;
        errorDetails.classList.remove('hidden');
    }

    function displayStatus(type, message) {
        statusMessage.className = `status-message ${type}`;
        statusMessage.textContent = message;
    }

    function resetUI() {
        warningsContainer.innerHTML = '';
        downloadSection.classList.add('hidden');
        jsonPreview.classList.add('hidden');
        importInstructions.classList.add('hidden');
        errorDetails.classList.add('hidden');
        viewJsonButton.innerHTML = '<i class="fas fa-eye"></i> View JSON';
        convertedWorkflow = null;
    }
});