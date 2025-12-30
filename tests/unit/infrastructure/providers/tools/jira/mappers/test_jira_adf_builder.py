import json
import pytest
from software_factory_poc.infrastructure.providers.tools.jira.mappers.jira_adf_builder import JiraAdfBuilder

def test_build_error_panel_returns_correct_structure():
    title = "Mission Failed"
    error_detail = "Something went wrong"
    steps = ["Step 1: Reverted", "Step 2: Logged"]
    
    adf = JiraAdfBuilder.build_error_panel(title, error_detail, steps)
    
    assert adf["version"] == 1
    assert adf["type"] == "doc"
    assert len(adf["content"]) == 1
    
    panel = adf["content"][0]
    assert panel["type"] == "panel"
    assert panel["attrs"]["panelType"] == "error"
    
    content = panel["content"]
    assert len(content) == 4
    
    # 1. Heading
    assert content[0]["type"] == "heading"
    assert content[0]["content"][0]["text"] == title
    
    # 2. Error Detail
    assert content[1]["type"] == "paragraph"
    assert content[1]["content"][0]["text"] == "Error: "
    assert content[1]["content"][0]["marks"][0]["type"] == "strong"
    assert content[1]["content"][1]["text"] == error_detail
    
    # 3. Label
    assert content[2]["type"] == "paragraph"
    assert "Acciones tomadas" in content[2]["content"][0]["text"]
    
    # 4. List
    assert content[3]["type"] == "bulletList"
    assert len(content[3]["content"]) == 2
    assert content[3]["content"][0]["content"][0]["content"][0]["text"] == "Step 1: Reverted"

def test_build_success_panel_returns_correct_structure():
    title = "Mission Complete"
    summary = "Generated successfully"
    links = {"Merge Request": "http://gitlab", "Docs": "http://confluence"}
    
    adf = JiraAdfBuilder.build_success_panel(title, summary, links)
    
    assert adf["type"] == "doc"
    panel = adf["content"][0]
    assert panel["attrs"]["panelType"] == "success"
    
    content = panel["content"]
    # Heading, Summary, List
    assert len(content) == 3
    
    # Links
    list_node = content[2]
    assert list_node["type"] == "bulletList"
    items = list_node["content"]
    assert len(items) == 2
    
    item1 = items[0]["content"][0]["content"][0]
    assert item1["text"] == "Merge Request"
    assert item1["marks"][0]["type"] == "link"
    assert item1["marks"][0]["attrs"]["href"] == "http://gitlab"
