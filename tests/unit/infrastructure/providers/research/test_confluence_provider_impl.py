from unittest.mock import MagicMock

from software_factory_poc.infrastructure.providers.research.confluence_provider_impl import ConfluenceProviderImpl


def test_confluence_html_cleaning():
    settings = MagicMock()
    settings.base_url = "http://confluence.com"
    settings.user_email = "test@example.com"
    settings.api_token.get_secret_value.return_value = "token"
    provider = ConfluenceProviderImpl(settings)
    
    dirty_html = "<p>Clean <b>Text</b> &amp; More</p>"
    clean = provider._sanitize_content(dirty_html)
    
    assert "Clean Text & More" in clean
    assert "<p>" not in clean
    assert "&amp;" not in clean
