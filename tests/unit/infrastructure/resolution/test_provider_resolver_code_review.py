
import unittest
from unittest.mock import MagicMock
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver
from software_factory_poc.application.core.agents.scaffolding.config.scaffolding_agent_config import ScaffoldingAgentConfig
from software_factory_poc.infrastructure.configuration.app_config import AppConfig

class TestProviderResolverCodeReview(unittest.TestCase):
    def test_create_code_reviewer_agent_initializes_correctly(self):
        # Setup mocks
        mock_config = MagicMock(spec=ScaffoldingAgentConfig)
        
        # Mock app_config structure
        # We don't use spec=AppConfig here to avoid strict attribute checking on the mock itself 
        # for nested attributes during this simple test setup
        mock_app_config = MagicMock()
        mock_app_config.tools.code_review_llm_model_priority = '["openai:gpt-4-turbo"]'
        mock_app_config.tools.code_review_model = "gpt-4-turbo" # Legacy support

        resolver = ProviderResolver(mock_config, mock_app_config)
        
        # Mock the dependent create_ methods so we don't need deep dependency trees
        resolver.create_reporter_agent = MagicMock()
        resolver.create_vcs_agent = MagicMock()
        resolver.create_research_agent = MagicMock()
        resolver.create_reasoner_agent = MagicMock()

        # Execute
        agent = resolver.create_code_reviewer_agent()
        
        # Verify
        self.assertIsNotNone(agent)
        self.assertEqual(agent.name, "CodeReviewerAgent")  # Name is hardcoded in agent.__init__
        print("Successfully created CodeReviewerAgent")

if __name__ == "__main__":
    unittest.main()
