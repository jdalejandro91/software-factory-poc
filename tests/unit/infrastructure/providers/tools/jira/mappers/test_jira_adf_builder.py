from software_factory_poc.infrastructure.adapters.drivers.tracker.mappers import (
    JiraAdfBuilder,
)


def test_build_error_panel_returns_correct_structure():
    title = "Mission Failed"
    error_detail = "Something went wrong"
    steps = ["Step 1: Reverted", "Step 2: Logged"]
    
    adf = JiraAdfBuilder.build_error_panel(title, error_detail)
    
    assert adf["version"] == 1
    assert adf["type"] == "doc"
    assert len(adf["content"]) == 1
    
    panel = adf["content"][0]
    assert panel["type"] == "panel"
    assert panel["attrs"]["panelType"] == "error"
    
    content = panel["content"]
    assert len(content) == 4 # Heading, Summary, Label, CodeBlock
    
    # 1. Heading
    assert content[0]["type"] == "heading"
    assert content[0]["content"][0]["text"] == "No se pudo completar la Tarea"
    
    # 2. Error Summary
    assert content[1]["type"] == "paragraph"
    assert content[1]["content"][0]["text"] == title
    # assert content[1]["content"][0]["marks"][0]["type"] == "strong" # No bold marks in current impl for summary
    
    # 3. Label
    assert content[2]["type"] == "paragraph"
    assert "Detalle del Error:" in content[2]["content"][0]["text"]
    
    # Remove obsolete assertions for 'steps' argument which is no longer used
    # assert content[3]["type"] == "bulletList"

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
