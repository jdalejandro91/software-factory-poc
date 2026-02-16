"""Functional DI container — builds fully-wired Use Cases using MCP adapters.

This module mirrors the ProviderResolver class but uses free functions,
making it convenient for FastAPI dependency injection.
"""

import os
import logging

from software_factory_poc.infrastructure.configuration.app_config import AppConfig

from software_factory_poc.infrastructure.observability.redaction_service import RedactionService
from software_factory_poc.infrastructure.drivers.vcs.gitlab_mcp_adapter import GitlabMcpAdapter
from software_factory_poc.infrastructure.drivers.tracker.jira_mcp_adapter import JiraMcpAdapter
from software_factory_poc.infrastructure.drivers.research.confluence_mcp_adapter import ConfluenceMcpAdapter
from software_factory_poc.infrastructure.drivers.llms.llm_gateway_adapter import LlmGatewayAdapter

from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.drivers.llms.gateway.composite_gateway import CompositeLlmGateway

from software_factory_poc.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.application.agents import CodeReviewerAgent
from software_factory_poc.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import ScaffoldingPromptBuilder
from software_factory_poc.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import CodeReviewPromptBuilder
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.usecases.code_review.perform_code_review_usecase import PerformCodeReviewUseCase

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
    vcs_driver = GitlabMcpAdapter(session_vcs, project_id, redactor)

    # 2. Tracker Driver (MCP Jira)
    session_jira = await mcp_manager.get_session("mcp_server_jira")
    tracker_driver = JiraMcpAdapter(
        mcp_session=session_jira,
        desc_mapper=JiraDescriptionMapper(),
        transition_in_review=config.jira.transition_in_review,
        redactor=redactor,
    )

    # 3. Research Driver (MCP Confluence)
    session_confluence = await mcp_manager.get_session("mcp_server_confluence")
    research_driver = ConfluenceMcpAdapter(
        mcp_session=session_confluence,
        redactor=redactor,
    )

    # 4. LLM Gateway (Composite — sin MCP, usa gateway propio)
    composite_gateway = CompositeLlmGateway(
        allowed_models=config.llm.allowed_models,
        openai_key=config.llm.openai_api_key.get_secret_value() if config.llm.openai_api_key else None,
        gemini_key=config.llm.gemini_api_key.get_secret_value() if config.llm.gemini_api_key else None,
        deepseek_key=config.llm.deepseek_api_key.get_secret_value() if config.llm.deepseek_api_key else None,
        anthropic_key=config.llm.anthropic_api_key.get_secret_value() if config.llm.anthropic_api_key else None,
    )
    llm_driver = LlmGatewayAdapter(gateway=composite_gateway)

    return vcs_driver, tracker_driver, research_driver, llm_driver


# === PUBLIC BUILDERS ===

async def build_scaffolding_agent(mcp_manager: McpConnectionManager) -> CreateScaffoldingUseCase:
    """Ensambla el caso de ubuild_code_review_usecaseso de Scaffolding con drivers 100% MCP."""
    config = AppConfig()
    vcs, tracker, research, llm = await _build_drivers(mcp_manager, config)

    return ScaffolderAgent(
        vcs=vcs,
        tracker=tracker,
        research=research,
        brain=llm,
        prompt_builder=ScaffoldingPromptBuilder(),
    )


async def build_code_review_agent(mcp_manager: McpConnectionManager) -> PerformCodeReviewUseCase:
    """Ensambla el caso de uso de Code Review con drivers 100% MCP."""
    config = AppConfig()
    vcs, tracker, research, llm = await _build_drivers(mcp_manager, config)

    return CodeReviewerAgent(
        vcs=vcs,
        tracker=tracker,
        research=research,
        brain=llm,
        prompt_builder=CodeReviewPromptBuilder(),
    )
