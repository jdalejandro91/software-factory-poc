from typing import Any, Dict, List

class JiraAdfBuilder:
    """
    Builder for Atlassian Document Format (ADF) structures for Jira Cloud comments.
    """

    @staticmethod
    def _create_doc(content: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

    @staticmethod
    def _create_panel(panel_type: str, content: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": "panel",
            "attrs": {
                "panelType": panel_type
            },
            "content": content
        }

    @staticmethod
    def _create_heading(level: int, text: str) -> Dict[str, Any]:
        return {
            "type": "heading",
            "attrs": {
                "level": level
            },
            "content": [
                {
                    "type": "text",
                    "text": text
                }
            ]
        }

    @staticmethod
    def _create_paragraph(content: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "type": "paragraph",
            "content": content
        }

    @staticmethod
    def _create_text(text: str, marks: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        node = {
            "type": "text",
            "text": text
        }
        if marks:
            node["marks"] = marks
        return node

    @staticmethod
    def _create_bullet_list(items: List[str]) -> Dict[str, Any]:
        list_items = []
        for item in items:
            list_items.append({
                "type": "listItem",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": item
                            }
                        ]
                    }
                ]
            })
        
        return {
            "type": "bulletList",
            "content": list_items
        }

    @staticmethod
    def _create_link_list(links: Dict[str, str]) -> Dict[str, Any]:
        list_items = []
        for label, url in links.items():
            list_items.append({
                "type": "listItem",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": label,
                                "marks": [
                                    {
                                        "type": "link",
                                        "attrs": {
                                            "href": url
                                        }
                                    }
                                ]
                            }
                        ]
                    }
                ]
            })

        return {
            "type": "bulletList",
            "content": list_items
        }

    @classmethod
    def build_error_panel(cls, title: str, error_detail: str, steps_taken: List[str]) -> Dict[str, Any]:
        """
        Builds an error panel ADF document.
        """
        panel_content = []
        
        # 1. Heading
        panel_content.append(cls._create_heading(3, title))
        
        # 2. Error Detail
        panel_content.append(cls._create_paragraph([
            cls._create_text("Error: ", marks=[{"type": "strong"}]),
            cls._create_text(error_detail)
        ]))

        # 3. Actions Taken Label
        panel_content.append(cls._create_paragraph([
            cls._create_text("Acciones tomadas:")
        ]))

        # 4. Steps List
        panel_content.append(cls._create_bullet_list(steps_taken))

        root_content = [
            cls._create_panel("error", panel_content)
        ]
        
        return cls._create_doc(root_content)

    @classmethod
    def build_success_panel(cls, title: str, summary: str, links: Dict[str, str]) -> Dict[str, Any]:
        """
        Builds a success panel ADF document.
        """
        panel_content = []
        
        # 1. Heading
        panel_content.append(cls._create_heading(3, title))
        
        # 2. Summary
        panel_content.append(cls._create_paragraph([
            cls._create_text(summary)
        ]))

        # 3. Links List
        if links:
            panel_content.append(cls._create_link_list(links))

        root_content = [
            cls._create_panel("success", panel_content)
        ]
        
        return cls._create_doc(root_content)
