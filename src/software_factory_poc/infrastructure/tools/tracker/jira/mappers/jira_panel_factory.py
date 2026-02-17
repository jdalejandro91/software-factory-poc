from typing import Any

class JiraPanelFactory:
    """
    Factory to create Jira Atlassian Document Format (ADF) Panels.
    Re-implemented to support rich UI feedback in Jira comments.
    """

    @staticmethod
    def create_payload(data: dict[str, Any]) -> dict[str, Any]:
        """
        Creates a valid ADF Panel based on the input dictionary.
        Supports:
        - scaffolding_exists: Warning panel (yellow)
        - code_review_success: Success panel (green)
        - generic: Info panel (blue)
        """
        panel_type = data.get("type", "generic")
        title = data.get("title", "Update")
        summary = data.get("summary", "")
        links = data.get("links", {})

        color_map = {
            "scaffolding_exists": "#FFAB00",  # Yellow/Orange
            "code_review_success": "#36B37E",  # Green
            "generic": "#0052CC"  # Blue
        }
        
        panel_color = color_map.get(panel_type, "#0052CC")
        
        # Build the content blocks
        content_blocks = []
        
        # 1. Summary Paragraph
        if summary:
            content_blocks.append({
                "type": "paragraph",
                "content": [{"type": "text", "text": summary}]
            })
            
        # 2. Links List
        if links:
            list_items = []
            for link_text, link_url in links.items():
                list_items.append({
                    "type": "listItem",
                    "content": [{
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": link_text, "marks": [{"type": "link", "attrs": {"href": link_url}}]}
                        ]
                    }]
                })
            
            content_blocks.append({
                "type": "bulletList",
                "content": list_items
            })

        # ADF Payload Structure
        return {
            "version": 1,
            "type": "doc",
            "content": [
                {
                    "type": "heading",
                    "attrs": {"level": 3},
                    "content": [{"type": "text", "text": title}]
                },
                {
                    "type": "panel",
                    "attrs": {"panelType": "info", "panelColor": panel_color},
                    "content": content_blocks
                }
            ]
        }
