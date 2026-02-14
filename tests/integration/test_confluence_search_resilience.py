import unittest
import os
import logging
import sys

# Ensure src is in path
sys.path.append(os.path.join(os.getcwd(), "src"))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings
from software_factory_poc.infrastructure.adapters.drivers.research.confluence_provider_impl import ConfluenceProviderImpl

# Parse logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ConfluenceResilienceTest")

class TestConfluenceSearchResilience(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # 1. Load Settings
        try:
            cls.settings = ConfluenceSettings()
            logger.info(f"✅ Loaded Settings for User: {cls.settings.user_email}")
        except Exception as e:
            logger.warning(f"Skipping tests: Failed to load ConfluenceSettings ({e})")
            raise unittest.SkipTest("Confluence credentials not available")

        # 2. Instantiate Provider using Real Implementation
        cls.provider = ConfluenceProviderImpl(cls.settings)

    def test_search_variations(self):
        """
        Verify that the provider can find the 'shopping-cart' project 
        regardless of input casing or separators.
        """
        variations = [
            "shopping-cart",   # Exact kebab-case
            "Shopping Cart",   # Natural Language
            "shopping_cart",   # Snake case
            "SHOPPING-CART",   # Uppercase
        ]
        
        failures = []
        
        for variant in variations:
            with self.subTest(variant=variant):
                logger.info(f"\n🧪 Testing variant: '{variant}'")
                try:
                    context = self.provider.get_project_context(variant)
                    
                    # Assertions
                    self.assertIsNotNone(context, f"Context should not be None for '{variant}'")
                    self.assertTrue(len(context.documents) > 0, f"Should retrieve documents for '{variant}'")
                    
                    # Log Success
                    logger.info(f"   ✅ PASS: Found project '{context.project_name}' (Root ID: {context.root_page_id}) with {len(context.documents)} docs.")
                    
                except Exception as e:
                    logger.error(f"   ❌ FAIL: Variant '{variant}' raised exception: {e}")
                    failures.append(variant)
                    # We continue to test other variants even if one fails
        
        if failures:
            self.fail(f"The following search variants failed: {failures}")

    def test_hierarchical_path_resolution(self):
        """
        Determine the correct hierarchical path by resolving nodes step-by-step.
        Tests:
        1. projects/shopping-cart
        2. Desarrollo de software/projects/shopping-cart
        """
        paths_to_test = [
            "projects/shopping-cart",
            "Desarrollo de software/projects/shopping-cart"
        ]
        
        space_key = self.settings.space_key if hasattr(self.settings, 'space_key') else "DDS"
        logger.info(f"\n🔍 Testing Hierarchical Paths in Space '{space_key}'...")
        
        results = {}

        for path in paths_to_test:
            logger.info(f"\n   🛣️  Testing Path: '{path}'")
            segments = path.split("/")
            
            current_parent_id = None
            path_failed = False
            
            for i, segment in enumerate(segments):
                # Step 1: Root Search or Child Search
                if i == 0:
                    cql = f'space = "{space_key}" AND title = "{segment}"'
                    logger.info(f"      [Root] Searching: {cql}")
                else:
                    cql = f'parent = {current_parent_id} AND title = "{segment}"'
                    logger.info(f"      [Child] Searching: {cql}")
                
                # Execute Search
                # We use the provider's valid http_client interaction
                try:
                    res = self.provider.http_client.search(cql)
                except Exception as e:
                    logger.error(f"      ❌ Exception during search: {e}")
                    path_failed = True
                    break
                
                if res and len(res) > 0:
                    # Found
                    found_node = res[0]
                    current_parent_id = found_node['id']
                    logger.info(f"      ✅ Found Node '{segment}' (ID: {current_parent_id}, Type: {found_node.get('type')})")
                else:
                    # Not Found
                    logger.warning(f"      ❌ Node '{segment}' NOT FOUND.")
                    path_failed = True
                    # If root failed, we can't continue
                    break
            
            if path_failed:
                results[path] = "FAIL"
                logger.error(f"   ❌ Path '{path}' FAILED.")
            else:
                results[path] = f"SUCCESS (Target ID: {current_parent_id})"
                logger.info(f"   ✅ Path '{path}' SUCCEEDED.")
                
        # Print Summary
        logger.info("\n📊 Path Resolution Summary:")
        for p, r in results.items():
            logger.info(f"   - {p}: {r}")
            
        # Optional: Fail if NONE succeed, but this is an exploratory test.
        # We assume at least one must work if we want to confirm the theory.
        success_count = sum(1 for r in results.values() if "SUCCESS" in r)
        if success_count == 0:
            self.fail("No valid hierarchical path found.")

if __name__ == "__main__":
    unittest.main()
