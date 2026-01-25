import pytest
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory
from software_factory_poc.application.core.agents.reporter.config.reporter_constants import ReporterMessages

def test_panel_factory_success_payload():
    text = f"✅ Éxito: Todo bien. MR: http://gitlab/mr/1"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["type"] == "doc"
    # Basic structural check for panel
    assert body["content"][0]["type"] == "panel"
    assert body["content"][0]["attrs"]["panelType"] == "success"

def test_panel_factory_error_payload():
    text = f"❌ Fallo: Algo salió mal: Detalle técnico"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["content"][0]["attrs"]["panelType"] == "error"

def test_panel_factory_branch_exists_payload():
    text = f"{ReporterMessages.BRANCH_EXISTS_PREFIX}feature/abc|http://link"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    assert body["content"][0]["attrs"]["panelType"] == "info"

def test_panel_factory_plain_text():
    text = "Just a normal comment"
    payload = JiraPanelFactory.create_payload(text)
    
    body = payload["body"]
    # Should be paragraph, not panel
    assert body["content"][0]["type"] == "paragraph"
