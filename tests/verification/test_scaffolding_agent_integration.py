from unittest.mock import MagicMock

from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import \
    ScaffoldingAgentConfig
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.domain.entities.task import Task, TaskDescription, TaskUser


class TestScaffoldingAgentIntegration:

    def test_execute_flow_with_task(self):
        # 1. Setup Mock Dependencies
        mock_config = MagicMock(spec=ScaffoldingAgentConfig)
        mock_config.project_allowlist = ["allowed-group"]
        mock_config.architecture_page_id = "12345"
        mock_config.default_target_branch = "develop"
        mock_config.llm_model_priority = None
        mock_config.model_name = "gpt-4"
        
        mock_reporter = MagicMock()
        mock_vcs = MagicMock()
        mock_researcher = MagicMock()
        mock_reasoner = MagicMock()
        
        # Setup VCS to return a valid project ID and no existing branch
        mock_vcs.resolve_project_id.return_value = 123
        mock_vcs.validate_branch.return_value = None
        mock_vcs.create_merge_request.return_value = MagicMock(web_url="http://gitlab.com/mr/1")

        # Setup LLM response
        mock_reasoner.reason.return_value = '```json\n[{"path": "README.md", "content": "test"}]\n```'
        
        agent = ScaffoldingAgent(
            config=mock_config,
            reporter=mock_reporter,
            vcs=mock_vcs,
            researcher=mock_researcher,
            reasoner=mock_reasoner
        )

        # 2. Create Task Entity
        task = Task(
            id="101",
            key="KAN-5",
            event_type="create",
            status="To Do",
            summary="New Service",
            project_key="KAN",
            issue_type="Task",
            created_at=12345,
            reporter=TaskUser(name="juan", display_name="Juan"),
            description=TaskDescription(
                raw_content="...",
                config={
                    "technology_stack": "python",
                    "parameters": {"service_name": "test-service"},
                    "target": {"gitlab_project_path": "allowed-group/project"}
                }
            )
        )

        # 3. Execute
        agent.execute_flow(task)

        # 4. Verifications
        # Verify research was called with service name
        mock_researcher.research_project_technical_context.assert_called_with("test-service")
        
        # Verify VCS commit called
        mock_vcs.commit_files.assert_called()
        
        # Verify Success Report
        mock_reporter.report_success.assert_called()
        
        print("\n✅ ScaffoldingAgent successfully processed Task entity!")

if __name__ == "__main__":
    t = TestScaffoldingAgentIntegration()
    t.test_execute_flow_with_task()
