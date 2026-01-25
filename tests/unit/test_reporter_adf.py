
import pytest
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory

def test_jira_factory_structured_success_payload():
    input_payload = {
        "type": "scaffolding_success",
        "title": "Done",
        "summary": "Everything is fine",
        "links": {"MR": "http://mr"}
    }
    
    result = JiraPanelFactory.create_payload(input_payload)
    body = result["body"]
    
    # Check ADF Structure
    assert body["version"] == 1
    assert body["content"][0]["type"] == "panel"
    assert body["content"][0]["attrs"]["panelType"] == "success"
    
    # Check Content
    panel_content = body["content"][0]["content"]
    # 0: Heading, 1: Paragraph (Summary), 2: Link List
    assert panel_content[0]["content"][0]["text"] == "Done"
    assert panel_content[1]["content"][0]["text"] == "Everything is fine"
    
    # Check Link
    # list -> listItem -> paragraph -> text
    # panel_content[2] is bulletList
    # ["content"][0] is listItem
    # ["content"][0] is paragraph
    # ["content"][0] is text node
    link_item = panel_content[2]["content"][0]["content"][0]["content"][0] 
    assert link_item["text"] == "MR"
    assert link_item["marks"][0]["attrs"]["href"] == "http://mr"

def test_jira_factory_legacy_string_fallback():
    result = JiraPanelFactory.create_payload("✅ Success detected MR: http://legacy")
    body = result["body"]
    assert body["content"][0]["attrs"]["panelType"] == "success"
