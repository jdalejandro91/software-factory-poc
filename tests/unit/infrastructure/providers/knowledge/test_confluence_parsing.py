
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.knowledge.confluence_knowledge_adapter import ConfluenceKnowledgeAdapter

class TestConfluenceParsing:
    def test_extracts_nested_storage_value(self):
        adapter = ConfluenceKnowledgeAdapter(MagicMock())
        
        page_obj = {
            "id": "123",
            "title": "Page",
            "body": {
                "storage": {
                    "value": "<p>Content</p>",
                    "representation": "storage"
                }
            }
        }
        
        result = adapter._extract_text(page_obj)
        assert result == "<p>Content</p>"

    def test_extracts_first_from_list(self):
        adapter = ConfluenceKnowledgeAdapter(MagicMock())
        
        page_list = [
            {
                "body": {
                    "storage": {
                        "value": "First Item"
                    }
                }
            },
            {
                 "body": {"storage": {"value": "Second"}}
            }
        ]
        
        result = adapter._extract_text(page_list)
        assert result == "First Item"

    def test_handles_missing_body_gracefully(self):
        adapter = ConfluenceKnowledgeAdapter(MagicMock())
        
        # Summary object often used in search results
        page_obj = {"id": "999", "title": "No Body"}
        
        # Should fallback to string representation or empty, but based on code fallback is str(obj)
        result = adapter._extract_text(page_obj)
        assert "No Body" in result
        assert "999" in result

    def test_handles_empty_list(self):
         adapter = ConfluenceKnowledgeAdapter(MagicMock())
         result = adapter._extract_text([])
         assert result == "No content in list."
