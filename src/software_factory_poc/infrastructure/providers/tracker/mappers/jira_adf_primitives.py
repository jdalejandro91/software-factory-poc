from typing import Any


class JiraAdfPrimitives:
    """
    Primitive builders for Atlassian Document Format (ADF) nodes.
    Extracted from JiraAdfBuilder to enforce single responsibility and reduce class size.
    """

    @staticmethod
    def create_doc(content: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "version": 1,
            "type": "doc",
            "content": content
        }

    @staticmethod
    def create_panel(panel_type: str, content: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "panel",
            "attrs": {
                "panelType": panel_type
            },
            "content": content
        }

    @staticmethod
    def create_heading(level: int, text: str) -> dict[str, Any]:
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
    def create_paragraph(content: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "type": "paragraph",
            "content": content
        }

    @staticmethod
    def create_text(text: str, marks: list[dict[str, Any]] = None) -> dict[str, Any]:
        node = {
            "type": "text",
            "text": text
        }
        if marks:
            node["marks"] = marks
        return node

    @staticmethod
    def create_bullet_list(items: list[str]) -> dict[str, Any]:
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
    def create_link_list(links: dict[str, str]) -> dict[str, Any]:
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
    def create_code_block(text: str, language: str = "text") -> dict[str, Any]:
        return {
            "type": "codeBlock",
            "attrs": {"language": language},
            "content": [{"type": "text", "text": text}]
        }
