import json
import uuid
import datetime

class N8nWorkflowGenerator:
    def __init__(self, nodes: list, connections: dict, workflow_name: str = "Converted Workflow"):
        self.nodes = nodes
        self.connections = connections
        self.workflow_name = workflow_name

    def generate_workflow(self):
        """
        Generates the final n8n workflow JSON structure.
        """
        # Generate unique identifiers
        workflow_id = str(uuid.uuid4())
        version_id = str(uuid.uuid4())
        instance_id = str(uuid.uuid4())
        
        # Current timestamp for metadata
        current_time = datetime.datetime.utcnow().isoformat()

        n8n_workflow = {
            "id": workflow_id,
            "name": self.workflow_name,
            "nodes": self.nodes,
            "connections": self._format_connections(),
            "active": False, # Default to inactive
            "settings": {
                "executionOrder": "v1", # Default execution order
                "saveManualExecutions": True,
                "callerPolicy": "any",
                "saveDataErrorExecution": "all"
            },
            "versionId": version_id,
            "meta": {
                "instanceId": instance_id,
                "templateCredsSetupCompleted": True,
                "convertedFromMakeCom": True,
                "conversionDate": current_time
            },
            "tags": ["converted", "make.com"],
            "pinData": {},
            "staticData": null,
            "triggerCount": 0,
            "updatedAt": current_time,
            "createdAt": current_time,
            "description": "This workflow was automatically converted from a Make.com workflow. Some manual adjustments may be required."
        }
        
        return n8n_workflow
    
    def _format_connections(self):
        """
        Format connections into valid n8n format.
        n8n expects connections in a format like:
        {
          "Node_Name": {
            "main": [
              [
                {
                  "node": "Target_Node_Name",
                  "type": "main",
                  "index": 0
                }
              ]
            ]
          }
        }
        """
        formatted_connections = {}
        
        # First check if connections is already in the right format
        # (when MakeComToN8nMapper._format_connections was called)
        if self.connections and all(isinstance(v, dict) for v in self.connections.values()):
            return self.connections
        
        # Otherwise, format it correctly
        for source_node_id, targets in self.connections.items():
            formatted_connections[source_node_id] = {
                "main": []
            }
            
            # n8n expects an array of arrays for outputs
            main_outputs = []
            
            # If we have a list of targets, they go in the first output index
            if isinstance(targets, list):
                output_targets = []
                for target in targets:
                    output_targets.append({
                        "node": target["node"],
                        "type": "main",
                        "index": target.get("index", 0)
                    })
                main_outputs.append(output_targets)
            
            formatted_connections[source_node_id]["main"] = main_outputs
            
        return formatted_connections