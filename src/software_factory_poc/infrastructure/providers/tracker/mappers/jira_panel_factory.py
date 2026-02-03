from typing import Any, Dict, List

class JiraPanelFactory:
    """
    Factory to convert domain message payloads into Jira ADF (Atlassian Document Format).
    """

    @staticmethod
    def create_payload(data: Any) -> Dict[str, Any]:
        # 1. Detection Logic: If it looks like a message dict, treat it as one.
        if isinstance(data, dict) and ("title" in data or "summary" in data):
            return JiraPanelFactory._build_rich_doc(data)
        
        # 2. Fallback: Wrap simple strings/objects in a paragraph
        return {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [{
                    "type": "paragraph", 
                    "content": [{"type": "text", "text": str(data)}]
                }]
            }
        }

    @staticmethod
    def _build_rich_doc(data: Dict[str, Any]) -> Dict[str, Any]:
        msg_type = data.get("type", "info")
        # Logic to map type -> panel color (info, success, warning, error)
        panel_type = "info"
        if "success" in msg_type: panel_type = "success"
        elif "warning" in msg_type or "exists" in msg_type: panel_type = "warning"
        elif "error" in msg_type or "fail" in msg_type: panel_type = "error"

        content_nodes = []
        
        # Summary Paragraph
        if data.get("summary"):
            content_nodes.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": data["summary"]}]
            })

        # Links List (The fix for clickable links)
        links = data.get("links", {})
        if links:
            ul_items = []
            for label, url in links.items():
                if not url: continue # Skip if URL is None/Empty
                
                # Ensure label has emoji if not present
                final_label = f"🔗 {label}" if "🔗" not in label else label
                
                ul_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [{
                            "type": "text",
                            "text": final_label,
                            "marks": [
                                {
                                    "type": "link", 
                                    "attrs": {"href": str(url).strip()} # Force string and strip whitespace
                                }
                            ]
                        }]
                    }]
                })
            
            if ul_items:
                content_nodes.append({
                    "type": "bulletList",
                    "content": ul_items
                })

        return {
            "body": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "heading", 
                        "attrs": {"level": 3}, 
                        "content": [{"type": "text", "text": data.get("title", "Notificación")}]
                    },
                    {
                        "type": "panel",
                        "attrs": {"panelType": panel_type},
                        "content": content_nodes
                    }
                ]
            }
        }
