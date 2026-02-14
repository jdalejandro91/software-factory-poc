import unittest
from unittest.mock import MagicMock
from software_factory_poc.application.core.domain.entities.task import Task, TaskDescription, TaskUser
from software_factory_poc.application.core.agents.scaffolding.scaffolding_agent import ScaffoldingAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent

class TestScaffoldingReporting(unittest.TestCase):
    def setUp(self):
        self.mock_vcs = MagicMock(spec=VcsAgent)
        # Mock nested gateway access
        self.mock_vcs.gateway = MagicMock() 
        self.mock_reporter = MagicMock(spec=ReporterAgent)
        
        # Partial mock of agent (only methods we test)
        self.agent = ScaffoldingAgent(
            config=MagicMock(),
            reporter=self.mock_reporter,
            vcs=self.mock_vcs,
            researcher=MagicMock(),
            reasoner=MagicMock()
        )

    def test_report_branch_exists_with_mr(self):
        # Setup
        task = Task(id="1", key="KAN-10", 
                   description=TaskDescription(raw_content="", config={}),
                   reporter=TaskUser(name="u", display_name="U", active=True),
                   created_at=0, status="Start", summary="Sum", project_key="PROJ", issue_type="Task", event_type="Evt")
        
        project_id = 100
        branch_name = "feature/kan-10-scaffolding"
        branch_url = "http://git/branch"
        mr_url = "http://git/mr/1"
        
        # Mock VCS Gateway response
        self.mock_vcs.gateway.get_active_mr_url.return_value = mr_url
        
        # Execute
        self.agent._report_branch_exists(task, branch_name, branch_url, project_id)
        
        # Verify
        self.mock_vcs.gateway.get_active_mr_url.assert_called_with(project_id, branch_name)
        
        # Check Reporter Call
        args = self.mock_reporter.report_success.call_args
        self.assertIsNotNone(args)
        payload = args[0][1] # Second arg is message/payload
        
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["type"], "scaffolding_exists")
        self.assertIn("links", payload)
        self.assertEqual(payload["links"]["🔗 Ver Merge Request Existing"], mr_url)

    def test_report_branch_exists_no_mr(self):
        # Setup
        task = Task(id="1", key="KAN-10", 
                   description=TaskDescription(raw_content="", config={}),
                   reporter=TaskUser(name="u", display_name="U", active=True),
                   created_at=0, status="Start", summary="Sum", project_key="PROJ", issue_type="Task", event_type="Evt")
        
        project_id = 100
        branch_name = "feature/kan-10-scaffolding"
        branch_url = "http://git/branch"
        
        # Mock VCS Gateway response (None)
        self.mock_vcs.gateway.get_active_mr_url.return_value = None
        
        # Execute
        self.agent._report_branch_exists(task, branch_name, branch_url, project_id)
        
        # Verify
        self.mock_vcs.gateway.get_active_mr_url.assert_called_with(project_id, branch_name)
        
        # Check Reporter Call
        args = self.mock_reporter.report_success.call_args
        payload = args[0][1]
        
        self.assertIsInstance(payload, dict)
        self.assertEqual(payload["links"]["🔗 Ver Rama Existente"], branch_url)

if __name__ == "__main__":
    unittest.main()
