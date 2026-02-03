
import unittest
from software_factory_poc.infrastructure.providers.tracker.mappers.jira_panel_factory import JiraPanelFactory

class TestJiraPanelFactory(unittest.TestCase):

    def test_create_payload_renders_links_correctly(self):
        """
        Verifies that JiraPanelFactory correctly transforms a dictionary with links 
        into an ADF structure with clickable link marks.
        """
        # 1. Setup
        # Note: Using raw URL as the factory expects clean URLs.
        input_data = {
            "type": "scaffolding_exists",
            "title": "Branch Exists",
            "summary": "No changes.",
            "links": {"View MR": "https://gitlab.com/mr/1"}
        }

        # 2. Action
        result = JiraPanelFactory.create_payload(input_data)

        # 3. Assertions
        body_content = result["body"]["content"]
        
        # Verify valid ADF doc structure
        self.assertEqual(result["body"]["type"], "doc")
        self.assertEqual(result["body"]["version"], 1)
        
        # Checking content structure: [Heading, Panel]
        # Index 0 is Heading, Index 1 is Panel.
        heading_node = body_content[0]
        self.assertEqual(heading_node["type"], "heading")
        self.assertIn("Branch Exists", heading_node["content"][0]["text"])

        panel_node = body_content[1]
        self.assertEqual(panel_node["type"], "panel")

        
        # Verify Panel Attributes (scaffolding_exists -> warning)
        self.assertEqual(panel_node["attrs"]["panelType"], "warning")
        
        # Verify Links in Panel Content
        # Structure: Panel -> bulletList -> listItem -> paragraph -> text (with marks)
        panel_content = panel_node["content"]
        bullet_list = next((node for node in panel_content if node["type"] == "bulletList"), None)
        self.assertIsNotNone(bullet_list, "BulletList for links not found in Panel")
        
        list_item = bullet_list["content"][0]
        paragraph = list_item["content"][0]
        text_node = paragraph["content"][0]
        
        # Assert Text Label
        self.assertIn("View MR", text_node["text"])
        
        # Assert Link Mark
        self.assertTrue("marks" in text_node)
        link_mark = next((mark for mark in text_node["marks"] if mark["type"] == "link"), None)
        self.assertIsNotNone(link_mark, "Link mark not found in text node")
        self.assertEqual(link_mark["attrs"]["href"], "https://gitlab.com/mr/1")

if __name__ == "__main__":
    unittest.main()
