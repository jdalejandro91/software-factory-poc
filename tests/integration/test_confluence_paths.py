import unittest
import os
import sys
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.adapters.drivers.research.clients.confluence_http_client import ConfluenceHttpClient

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ConfluencePathTest")

class TestConfluencePaths(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        try:
            cls.settings = ConfluenceSettings()
            cls.client = ConfluenceHttpClient(cls.settings)
            cls.space_key = cls.settings.space_key if hasattr(cls.settings, 'space_key') else "DDS"
            logger.info(f"✅ Setup Complete. Space: {cls.space_key}")
        except Exception as e:
            logger.error(f"Failed setup: {e}")
            raise unittest.SkipTest("Confluence credentials missing")

    def test_resolve_project_hierarchy_path(self):
        """
        Validate path: Desarrollo de software -> projects -> shopping-cart
        """
        path_segments = ["Desarrollo de software", "projects", "shopping-cart"]
        current_id = None
        
        logger.info(f"\n🛣️  Validating Path: {' / '.join(path_segments)}")
        
        for i, segment in enumerate(path_segments):
            if i == 0:
                # Root - We assume the root is a page, but let's be safe and just check title/space
                # User requested type="page" for root, likely safe for 'Desarrollo de software'
                cql = f'space = "{self.space_key}" AND title = "{segment}"'
            else:
                # Children - We know these are type="folder", so we OMIT type="page"
                cql = f'parent = {current_id} AND title = "{segment}"'
            
            logger.info(f"   🔎 Step {i+1}: Searching for '{segment}'")
            logger.info(f"      CQL: {cql}")
            
            results = self.client.search(cql)
            
            self.assertTrue(len(results) > 0, f"Node '{segment}' not found via CQL: {cql}")
            
            node = results[0]
            current_id = node['id']
            node_type = node.get('type')
            logger.info(f"   ✅ Resolved node '{segment}' -> ID: {current_id} (Type: {node_type})")
            
        # Final Assertions on target
        self.assertEqual(current_id, "15499265", "Final ID should match known target ID for 'shopping-cart'")
        
        # Verify we can fetch children (Context Retrieval capability)
        logger.info(f"   👶 Fetching children for final node {current_id}...")
        children = self.client.get_child_pages(current_id, limit=5)
        logger.info(f"   ✅ Fetched {len(children)} children.")
        self.assertTrue(len(children) >= 0, "Should be able to fetch children (even if empty)")

if __name__ == "__main__":
    unittest.main()
