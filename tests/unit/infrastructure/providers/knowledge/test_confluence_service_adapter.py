import time
import pytest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.providers.knowledge.confluence_service_adapter import ConfluenceServiceAdapter
from software_factory_poc.application.ports.tools.confluence_provider import ConfluenceProvider
from software_factory_poc.configuration.tools.tool_settings import ToolSettings

def test_get_knowledge_fetches_and_caches():
    # Arrange
    mock_provider = MagicMock(spec=ConfluenceProvider)
    mock_settings = MagicMock(spec=ToolSettings)
    mock_settings.architecture_doc_page_id = "12345"
    
    adapter = ConfluenceServiceAdapter(mock_provider, mock_settings)
    
    expected_content = "Real Content"
    mock_provider.get_page_content.return_value = expected_content

    # Act 1: First call (Cache Miss)
    result1 = adapter.get_knowledge("ignore")
    
    # Assert 1
    assert result1 == expected_content
    mock_provider.get_page_content.assert_called_once_with("12345")
    
    # Act 2: Second call (Cache Hit)
    result2 = adapter.get_knowledge("ignore")
    
    # Assert 2
    assert result2 == expected_content
    # Call count remains 1
    mock_provider.get_page_content.assert_called_once() 

def test_get_knowledge_refreshes_after_ttl():
    # Arrange
    mock_provider = MagicMock(spec=ConfluenceProvider)
    mock_settings = MagicMock(spec=ToolSettings)
    mock_settings.architecture_doc_page_id = "12345"
    
    adapter = ConfluenceServiceAdapter(mock_provider, mock_settings)
    
    mock_provider.get_page_content.return_value = "Content 1"
    
    # Act 1
    adapter.get_knowledge("ignore")
    mock_provider.get_page_content.assert_called_once()
    
    # Simulate TTL expiry
    adapter._cache_time = time.time() - 301 # > 5 min ago
    mock_provider.get_page_content.return_value = "Content 2"
    
    # Act 2
    result2 = adapter.get_knowledge("ignore")
    
    # Assert
    assert result2 == "Content 2"
    assert mock_provider.get_page_content.call_count == 2
