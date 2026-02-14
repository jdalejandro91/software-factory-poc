from unittest.mock import MagicMock

from software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent import CodeReviewerAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import \
    CodeReviewerAgentConfig
from software_factory_poc.domain.entities.task import Task, TaskDescription, TaskUser


class TestCodeReviewerAgentIntegration:

    def test_execute_flow_with_task(self):
        # 1. Setup Mock Dependencies
        mock_config = MagicMock(spec=CodeReviewerAgentConfig)
        mock_config.llm_model_priority = None
        
        mock_reporter = MagicMock()
        mock_vcs = MagicMock()
        mock_researcher = MagicMock()
        mock_reasoner = MagicMock()
        
        mock_change = MagicMock()
        mock_change.file_path = "file1.py"
        mock_change.diff_content = "import os"
        
        # VCS Mocks
        mock_vcs.validate_mr.return_value = True
        mock_vcs.get_mr_changes.return_value = [mock_change] # Simulate changes objects
        mock_vcs.get_code_context.return_value = []
        
        # Reasoner Mock
        mock_json_response = '''```json
        {
            "summary": "Looks good",
            "verdict": "APPROVE", 
            "comments": [
                {
                    "file_path": "test.py", 
                    "line_number": 1, 
                    "severity": "INFO",
                    "comment_body": "LGTM",
                    "suggestion": null
                }
            ]
        }
        ```'''
        mock_reasoner.reason.return_value = mock_json_response

        agent = CodeReviewerAgent(
            config=mock_config,
            reporter=mock_reporter,
            vcs=mock_vcs,
            researcher=mock_researcher,
            reasoner=mock_reasoner
        )

        # 2. Create Task Entity
        task = Task(
            id="202",
            key="CR-50",
            event_type="update",
            status="In Review",
            summary="Review Auth Logic",
            project_key="CR",
            issue_type="Task",
            created_at=12345,
            reporter=TaskUser(name="dev", display_name="Developer"),
            description=TaskDescription(
                raw_content="Please review",
                config={
                    "code_review_params": {
                        "gitlab_project_id": "111",
                        "mr_id": "5"
                    },
                    "technology_stack": "python"
                }
            )
        )

        # 3. Execute
        agent.execute_flow(task)

        # 4. Verifications
        # Verify MR validation called with correct IDs
        mock_vcs.validate_mr.assert_called_with(111, 5)
        
        # Verify changes fetched
        mock_vcs.get_mr_changes.assert_called_with(111, 5)
        
        # Verify Review SUbmission
        mock_vcs.submit_review.assert_called()
        
        # Verify Success Report
        mock_reporter.report_success.assert_called()
        
        print("\n✅ CodeReviewerAgent successfully processed Task entity!")

if __name__ == "__main__":
    t = TestCodeReviewerAgentIntegration()
    t.test_execute_flow_with_task()
