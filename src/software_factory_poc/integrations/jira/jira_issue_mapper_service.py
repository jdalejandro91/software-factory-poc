from typing import Any, Dict, Optional
from pydantic import BaseModel

class JiraIssueDataModel(BaseModel):
    issue_key: str
    summary: str
    description: str


class JiraIssueMapperService:
    def map_issue(self, raw_data: Dict[str, Any]) -> JiraIssueDataModel:
        """
        Maps raw Jira JSON response to internal data model.
        Handles ADF description best-effort extraction.
        """
        fields = raw_data.get("fields", {})
        key = raw_data.get("key", "")
        summary = fields.get("summary", "")
        
        description_raw = fields.get("description")
        description_text = self._extract_text(description_raw)
        
        return JiraIssueDataModel(
            issue_key=key,
            summary=summary,
            description=description_text
        )

    def _extract_text(self, description_raw: Any) -> str:
        if description_raw is None:
            return ""
        
        if isinstance(description_raw, str):
            return description_raw
        
        if isinstance(description_raw, dict):
            # Attempt to parse ADF
            # content -> list of nodes -> content -> list of text nodes
            # Very naive flat extraction
            return self._extract_adf_text(description_raw)
            
        return str(description_raw)

    def _extract_adf_text(self, node: Dict[str, Any]) -> str:
        text_parts = []
        node_type = node.get("type", "")
        
        if node_type == "text":
            return node.get("text", "")
        
        content = node.get("content", [])
        if isinstance(content, list):
            for child in content:
                if isinstance(child, dict):
                    text_parts.append(self._extract_adf_text(child))
                
        # Add newlines for paragraphs/code blocks implicitly by join?
        # Let's just join with space or newline depending on block type?
        # Naive approach: join with newline if it's a block type, else join.
        # This is PoC best-effort.
        
        result = "".join(text_parts)
        if node_type in ["paragraph", "codeBlock", "heading"]:
            result += "\n"
            
        return result
