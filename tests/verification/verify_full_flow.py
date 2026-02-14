import sys
import os
import unittest
from unittest.mock import MagicMock

# Ensure strict path for imports
sys.path.append(os.path.join(os.getcwd(), "src"))

from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import JiraWebhookDTO
from software_factory_poc.domain.entities.task import TaskDescription
from software_factory_poc.infrastructure.adapters.drivers.research.confluence_provider_impl import ConfluenceProviderImpl
from software_factory_poc.infrastructure.configuration.confluence_settings import ConfluenceSettings

class TestFullFlowVerification(unittest.TestCase):

    def test_1_mapper_contract_fix(self):
        print("\n--- TEST 1: Mapper Contract Verification ---")
        # 1. Setup Data (Real Payload from logs)
        payload = {
          "webhookEvent": "jira:issue_created",
          "user": {
            "name": "juanc",
            "displayName": "Juan Cadena",
            "active": True
          },
          "issue": {
            "key": "KAN-7",
            "fields": {
              "summary": "Scaffolding Request",
              "description": "Req.\n{code:yaml}version: '1.0'\ntechnology_stack: TypeScript con NestJS\nparameters:\n service_name: shopping-cart\n{code}",
              "project": {"key": "POC", "id": "100"},
              "issuetype": {"name": "Task"},
              "status": {"name": "To Do"},
              "reporter": {"name": "user", "displayName": "User", "active": True}
            }
          }
        }

        # 2. Execution
        try:
            # We explicitly allow the mapper to handle the dict via DTO conversion internally 
            # or we convert it first. The mapper supports DTO input.
            dto = JiraWebhookDTO(**payload) 
            task = JiraPayloadMapper.to_domain(dto)

            # 3. Asserts
            self.assertIsInstance(task.description, TaskDescription)
            
            # Check Config Extraction
            params = task.description.config.get("parameters", {})
            self.assertEqual(params.get("service_name"), "shopping-cart")
            
            # Check Attributes (Regression Test for TypeError)
            self.assertTrue(hasattr(task.description, "raw_content"))
            self.assertTrue(hasattr(task.description, "config"))
            
            # Ensure "human_text" is NOT what we rely on anymore if it was removed/renamed, 
            # essentially proving we are using the new contract.
            
            print("✅ MAPPER CHECK PASS: Entity created successfully.")

        except TypeError as e:
            self.fail(f"❌ TypeError detected! Contract mismatch likely persists: {e}")
        except Exception as e:
            self.fail(f"❌ Unexpected error in Mapper: {e}")

    def test_2_confluence_hierarchy_logic(self):
        print("\n--- TEST 2: Confluence Hierarchy Verification ---")
        
        # 1. Mock Setup
        mock_settings = MagicMock(spec=ConfluenceSettings)
        # Needs to satisfy validations
        mock_settings.base_url = "https://dummy.atlassian.net"
        mock_secret = MagicMock()
        mock_secret.get_secret_value.return_value = "secret"
        mock_settings.api_token = mock_secret
        mock_settings.user_email = "bot@example.com"
        
        provider = ConfluenceProviderImpl(mock_settings)
        provider.http_client = MagicMock()
        
        # Override space key to ensure consistent test
        provider.space_key = "DDS"

        # 2. Simulate Hierarchy via side_effect
        # Call 1: SEARCH 'projects' -> Returns [ROOT_100]
        # Call 2: SEARCH 'shopping-cart' (child of ROOT) -> Returns [FOLDER_200]
        def search_side_effect(cql):
            if 'title in ("projects"' in cql:
                return [{"id": "ROOT_100", "title": "projects"}]
            if 'parent = ROOT_100' and 'title = "shopping-cart"' in cql:
                return [{"id": "FOLDER_200", "title": "shopping-cart"}]
            return []
        
        provider.http_client.search.side_effect = search_side_effect

        # Call 3: GET CHILDREN of FOLDER_200
        provider.http_client.get_child_pages.return_value = [
            {
                "id": "1001", 
                "title": "Requisitos Funcionales", 
                "body": {"storage": {"value": "<p>Content A is long enough to pass validation thresholds set.</p>"}}, 
                "_links": {"webui": "/wiki/reqs"},
                "space": {"key": "DDS"}
            },
            {
                "id": "1002", 
                "title": "Arquitectura", 
                "body": {"storage": {"value": "<p>Content B is also long enough to pass validation thresholds set.</p>"}}, 
                "_links": {"webui": "/wiki/arch"},
                "space": {"key": "DDS"}
            }
        ]

        # 3. Execution
        context = provider.get_project_context("shopping-cart")

        # 4. Asserts
        self.assertEqual(len(context.documents), 2)
        titles = [doc.title for doc in context.documents]
        self.assertIn("Requisitos Funcionales", titles)
        self.assertIn("Arquitectura", titles)
        
        # Verify FOLDER_200 is treated as root for this context, not a document itself
        self.assertEqual(context.root_page_id, "FOLDER_200")
        
        print("✅ CONFLUENCE HIERARCHY PASS: Navigation logic verified.")

if __name__ == "__main__":
    unittest.main()
