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

    @staticmethod
    def _create_code_block(text: str, language: str = "text") -> Dict[str, Any]:
        return {
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": text}]
        }

    @classmethod
    def build_info_panel(cls, title: str, details: str) -> Dict[str, Any]:
        panel_content = []
        
        # 1. Heading
        panel_content.append(cls._create_heading(3, title))
        
        # 2. Details
        panel_content.append(cls._create_paragraph([
            cls._create_text(details)
        ]))

        root_content = [
            cls._create_panel("info", panel_content)
        ]
        return cls._create_doc(root_content)

    @classmethod
    def build_error_panel(cls, error_summary: str, technical_detail: str) -> Dict[str, Any]:
        panel_content = []
        
        # 1. Heading
        panel_content.append(cls._create_heading(3, "❌ No se pudo completar la Tarea"))
        
        # 2. Summary
        panel_content.append(cls._create_paragraph([
            cls._create_text(error_summary)
        ]))

        # 3. Technical Detail Label
        panel_content.append(cls._create_paragraph([
            cls._create_text("Detalle del Error:", marks=[{"type": "strong"}])
        ]))

        # 4. Technical Detail Code Block
        panel_content.append(cls._create_code_block(str(technical_detail)))

        root_content = [
            cls._create_panel("error", panel_content)
        ]
        return cls._create_doc(root_content)

    @classmethod
    def build_success_panel(cls, title: str, summary: str, links: Dict[str, str]) -> Dict[str, Any]:
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
