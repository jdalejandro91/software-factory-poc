from typing import Any, Dict, List

class JiraPanelFactory:
    """
    Factory to convert domain message payloads into Jira ADF (Atlassian Document Format).
    """

    @staticmethod
    def create_payload(data: Any) -> Dict[str, Any]:
        """
        Main entry point. Automatically detects if input is a structured dict or plain string.
        """
        # If it's already a dictionary with title/summary, treat as Rich Panel
        if isinstance(data, dict) and ("title" in data or "summary" in data):
            return JiraPanelFactory._build_rich_doc(data)
            
        # Fallback for plain strings
        return {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [{"type": "text", "text": str(data)}]
                    }
                ]
            }
        }

    @staticmethod
    def _build_rich_doc(data: Dict[str, Any]) -> Dict[str, Any]:
        msg_type = data.get("type", "info")
        panel_color = JiraPanelFactory._map_to_panel_type(msg_type)
        
        # 1. Build Panel Content
        panel_content = []
        
        # Add Summary Text
        if data.get("summary"):
            panel_content.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": data["summary"]}]
            })
            
        # Add Links (Hyperlinks)
        links = data.get("links", {})
        if links:
            # Create a bullet list for links for better visibility
            ul_content = []
            for label, url in links.items():
                ul_content.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "type": "text",
                            "text": f"🔗 {label}" if "🔗" not in label else label,
                            "marks": [
                                {
                                    "type": "link",
                                    "attrs": {"href": url}
                                }
                            ]
                        }]
                    }]
                })
            
            if ul_content:
                panel_content.append({
                    "type": "bulletList",
                    "content": ul_content
                })

        # 2. Wrap in Panel Node
        panel_node = {
            "type": "panel",
            "attrs": {"panelType": panel_color},
            "content": panel_content
        }

        # 3. Build Root Doc with Title Heading
        root_content = []
        if data.get("title"):
            root_content.append({
                "type": "heading",
                "attrs": {"level": 3},
                "content": [{"type": "text", "text": data["title"]}]
            })
        
        root_content.append(panel_node)

        return {
            "body": {
                "version": 1,
                "type": "doc",
                "content": root_content
            }
        }

    @staticmethod
    def _map_to_panel_type(msg_type: str) -> str:
        """Maps domain message types to Jira Panel types (info, success, warning, error)."""
        msg_type = msg_type.lower()
        if "success" in msg_type:
            return "success"
        if "error" in msg_type or "fail" in msg_type:
            return "error"
        if "warning" in msg_type or "exists" in msg_type:
            return "warning"
        return "info"
