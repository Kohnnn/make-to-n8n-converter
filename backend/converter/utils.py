class NodeUtils:
    @staticmethod
    def calculate_n8n_position(make_position: dict):
        """
        Calculates n8n node position from Make.com module position.
        Make.com positions are in metadata.designer.x and y.
        n8n positions are [x, y].
        """
        x = make_position.get("x", 0)
        y = make_position.get("y", 0)
        return [x, y]

    @staticmethod
    def generate_node_id(node_name: str):
        """
        Generates a simple n8n-like ID for a node based on its name.
        This is a placeholder and might need more robust UUID generation in a real app.
        """
        # Simple slugification for ID
        import re
        slug = re.sub(r'\W+', '-', node_name).lower()
        return f"{slug}"