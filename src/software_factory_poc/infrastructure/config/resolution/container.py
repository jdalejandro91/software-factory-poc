"""Functional DI container — builds fully-wired Use Cases using MCP adapters.

This module mirrors the ProviderResolver class but uses free functions,
making it convenient for FastAPI dependency injection.
"""

import logging
import os

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.infrastructure.config.app_config import AppConfig
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)
from software_factory_poc.infrastructure.tools.llm.litellm_brain_adapter import LiteLlmBrainAdapter
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import JiraMcpClient
from software_factory_poc.infrastructure.tools.tracker.jira.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client import GitlabMcpClient

logger = logging.getLogger(__name__)


class McpConnectionManager:
    """Gestiona conexiones stdio a los servidores MCP."""

    async def get_session(self, server_name: str):
        pass


async def _build_drivers(mcp_manager: McpConnectionManager, config: AppConfig):
    """Factory interno que ensambla los 4 drivers MCP del Tooling Plane."""
    redactor = RedactionService()

    # 1. VCS Driver (MCP GitLab)
    session_vcs = await mcp_manager.get_session("mcp_server_gitlab")
    project_id = os.getenv("GITLAB_PROJECT_ID", "default_project")
    vcs = GitlabMcpClient(session_vcs, project_id, redactor)

    # 2. Tracker Driver (MCP Jira)
    session_jira = await mcp_manager.get_session("mcp_server_jira")
    tracker = JiraMcpClient(
        mcp_session=session_jira,
        desc_mapper=JiraDescriptionMapper(),
        transition_in_review=config.jira.transition_in_review,
        redactor=redactor,
    )

    # 3. Research Driver (MCP Confluence)
    session_confluence = await mcp_manager.get_session("mcp_server_confluence")
    docs = ConfluenceMcpClient(
        mcp_session=session_confluence,
        redactor=redactor,
    )

    # 4. Brain (LiteLLM)
    brain = LiteLlmBrainAdapter(config.llm)

    return vcs, tracker, docs, brain


# === PUBLIC BUILDERS ===


async def build_scaffolding_agent(mcp_manager: McpConnectionManager) -> ScaffolderAgent:
    """Ensambla el ScaffolderAgent con drivers 100% MCP + LiteLLM."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)

    return ScaffolderAgent(
        vcs=vcs,
        tracker=tracker,
        research=docs,
        brain=brain,
        prompt_builder=ScaffoldingPromptBuilder(),
    )


async def build_code_review_agent(mcp_manager: McpConnectionManager) -> CodeReviewerAgent:
    """Ensambla el CodeReviewerAgent con drivers 100% MCP + LiteLLM."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)

    return CodeReviewerAgent(
        vcs=vcs,
        tracker=tracker,
        research=docs,
        brain=brain,
        prompt_builder=CodeReviewPromptBuilder(),
    )
