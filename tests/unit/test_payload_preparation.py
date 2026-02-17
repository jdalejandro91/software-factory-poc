import pytest
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_payload_mapper import JiraPayloadMapper
from software_factory_poc.core.domain.mission.entities.mission import Mission

class TestJiraPayloadMapper:
    
    def test_map_webhook_to_mission(self):
        """Test basic mapping from Jira Webhook JSON to Domain Mission."""
        payload = {
            "issue": {
                "key": "POC-42",
                "fields": {
                    "summary": "Create User Microservice",
                    "description": "Please create this.\n\n```yaml\ntechnology_stack: Python/FastAPI\nreporter_email: dev@example.com\n```",
                    "status": {"name": "To Do"},
                    "reporter": {"emailAddress": "dev@example.com"}
                }
            }
        }
        mission = JiraPayloadMapper.to_domain(payload)
        
        assert isinstance(mission, Mission)
        assert mission.key == "POC-42"
        assert mission.summary == "Create User Microservice"
        # Check config extraction logic (simplified)
        assert mission.description.config.get("technology_stack") == "Python/FastAPI"
        assert mission.reporter.name == "unknown" # Correctly check reporter name if mapped

    def test_map_invalid_payload(self):
        """Test behavior with missing fields."""
        payload = {"issue": {}}
        mapper = JiraPayloadMapper()
        
        mission = JiraPayloadMapper.to_domain(payload)
        assert mission.key == "UNKNOWN"
        assert mission.summary == "No Summary"
