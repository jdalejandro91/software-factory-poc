from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper


class TestJiraPayloadMapperStrict:

    def test_scaffolding_mapping(self):
        """
        Test Case 1: Scaffolding with {code:yaml}
        """
        payload_dict = {
            "webhookEvent": "jira:issue_created",
            "timestamp": 123456789,
            "user": {
                "name": "juanc",
                "displayName": "Juan Cadena",
                "active": True
            },
            "issue": {
                "key": "KAN-3",
                "id": "10003",
                "fields": {
                    "summary": "Create Shopping Cart Service",
                    "description": "Here is the config:\n\n{code:yaml}\nversion: '1.0'\ntechnology_stack: 'TypeScript con NestJS'\nparameters:\n  service_name: shopping-cart\n{code}\n\nThanks.",
                    "project": {
                        "key": "KAN",
                        "name": "Kanban Project"
                    },
                    "status": {"name": "To Do"},
                    "issuetype": {"name": "Task"}
                }
            }
        }

        # Convert to DTO to simulate real API entry
        dto = JiraWebhookDTO(**payload_dict)
        
        # Execute
        task = JiraPayloadMapper.to_domain(dto)

        # Assertions
        assert task.key == "KAN-3"
        assert task.description.config.get("version") == "1.0"
        assert task.description.config.get("technology_stack") == "TypeScript con NestJS"
        
        # Nested Access Critical Check
        params = task.description.config.get("parameters", {})
        assert params.get("service_name") == "shopping-cart"

        print("\n✅ Test Case 1 (Scaffolding) Passed!")

    def test_code_review_mapping(self):
        """
        Test Case 2: Code Review with Markdown ```yaml
        """
        payload_dict = {
            "webhookEvent": "jira:issue_updated",
            "issue": {
                "key": "CR-99",
                "fields": {
                    "summary": "Review Code for Auth",
                    "description": "Please review.\n\n```yaml\ncode_review_params:\n  gitlab_project_id: '77189062'\n```",
                    "project": {"key": "CR"}
                }
            }
        }
        
        # Execute from Dict directly (supported by mapper)
        task = JiraPayloadMapper.to_domain(payload_dict)

        # Assertions
        assert task.key == "CR-99"
        
        # Deep Check
        cr_params = task.description.config.get("code_review_params", {})
        assert cr_params.get("gitlab_project_id") == "77189062"

        print("\n✅ Test Case 2 (Code Review) Passed!")

if __name__ == "__main__":
    t = TestJiraPayloadMapperStrict()
    t.test_scaffolding_mapping()
    t.test_code_review_mapping()
