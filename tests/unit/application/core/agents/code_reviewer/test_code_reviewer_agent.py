
import unittest
from unittest.mock import MagicMock

from software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent import CodeReviewerAgent
from software_factory_poc.domain.entities.task import Task, TaskDescription
from software_factory_poc.application.ports.drivers.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.ports.drivers.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.ports.drivers.research import ResearchAgent
from software_factory_poc.application.ports.drivers.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import CodeReviewerAgentConfig

class TestCodeReviewerAgent(unittest.TestCase):
    def setUp(self):
        # Mocks for dependencies
        self.mock_config = MagicMock(spec=CodeReviewerAgentConfig)
        self.mock_config.llm_model_priority = ["openai:gpt-4-turbo"]
        self.mock_reporter = MagicMock(spec=ReporterAgent)
        self.mock_vcs = MagicMock(spec=VcsAgent)
        self.mock_researcher = MagicMock(spec=ResearchAgent)
        self.mock_reasoner = MagicMock(spec=ReasonerAgent)

        # Instantiate SUT
        self.agent = CodeReviewerAgent(
            config=self.mock_config,
            reporter=self.mock_reporter,
            vcs=self.mock_vcs,
            researcher=self.mock_researcher,
            reasoner=self.mock_reasoner
        )

    def test_execute_flow_extracts_mr_id_from_url_correctly(self):
        """
        Verifies that execute_flow correctly extracts the MR IID from the 'review_request_url'
        when 'mr_id' is missing/None in the parameters.
        """
        # 1. Setup Data
        nested_params = {
            "gitlab_project_id": "123",
            "review_request_url": "https://gitlab.com/group/repo/-/merge_requests/44",
            # "mr_id" is intentionally missing
        }
        
        task_config = {
            "code_review_params": nested_params
        }

        task = Task(
            id="101", 
            key="TEST-1",
            summary="Review my code",
            status="In Progress",
            project_key="TEST",
            issue_type="Task",
            description=TaskDescription(
                raw_content="Please review this.",
                config=task_config
            )
        )

        # 2. Setup Behavior Mocks
        # validate_mr returns True so flow proceeds
        self.mock_vcs.validate_mr.return_value = True
        
        # get_mr_changes returns something so flow proceeds
        self.mock_vcs.get_mr_changes.return_value = [MagicMock()] 
        
        # get_code_context returns something
        self.mock_vcs.get_code_context.return_value = []
        
        # reasoner.reason returns a string to avoid Parser TypeError
        self.mock_reasoner.reason.return_value = "```json\n{\"verdict\": \"APPROVE\", \"summary\": \"LGTM\", \"comments\": []}\n```"

        # 3. Action
        self.agent.execute_flow(task)

        # 4. Assertions
        # Verify validate_mr was called with the extracted ID (44)
        self.mock_vcs.validate_mr.assert_called_with(123, 44)
        
        # Verify get_mr_changes was called with the extracted ID (44)
        self.mock_vcs.get_mr_changes.assert_called_with(123, 44)
        
if __name__ == "__main__":
    unittest.main()
