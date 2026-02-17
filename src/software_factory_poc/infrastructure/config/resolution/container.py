"""Functional DI container — builds fully-wired agents using MCP adapters.

Convenient free-function API for FastAPI dependency injection.
"""

import logging
from typing import Any

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.scaffold.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.application.workflows.review.code_review_deterministic_workflow import (
    CodeReviewDeterministicWorkflow,
)
from software_factory_poc.core.application.workflows.scaffold.scaffolding_deterministic_workflow import (
    ScaffoldingDeterministicWorkflow,
)
from software_factory_poc.core.domain.agent import CodeReviewerAgentConfig, ScaffolderAgentConfig
from software_factory_poc.core.domain.shared.base_tool import BaseTool
from software_factory_poc.core.domain.shared.skill_type import SkillType
from software_factory_poc.core.domain.shared.tool_type import ToolType
from software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter import (
    LiteLlmBrainAdapter,
)
from software_factory_poc.infrastructure.config.app_config import AppConfig
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)
from software_factory_poc.infrastructure.tools.tracker.jira.jira_mcp_client import JiraMcpClient
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_mcp_client import GitlabMcpClient

logger = logging.getLogger(__name__)


class McpConnectionManager:
    """Gestiona conexiones stdio a los servidores MCP."""

    async def get_session(self, _server_name: str):
        pass


async def _build_drivers(mcp_manager: McpConnectionManager, config: AppConfig):
    """Factory interno que ensambla los 4 drivers MCP del Tooling Plane."""
    vcs = GitlabMcpClient(settings=config.gitlab)
    tracker = JiraMcpClient(settings=config.jira)
    docs = ConfluenceMcpClient(settings=config.confluence)
    brain = LiteLlmBrainAdapter(config.llm)

    return vcs, tracker, docs, brain


def _build_tools(
    vcs: GitlabMcpClient,
    tracker: JiraMcpClient,
    docs: ConfluenceMcpClient,
) -> dict[ToolType, BaseTool]:
    """Build the peripheral tools registry (Brain is NOT a tool)."""
    return {
        ToolType.VCS: vcs,
        ToolType.TRACKER: tracker,
        ToolType.DOCS: docs,
    }


# === PUBLIC BUILDERS ===


async def build_scaffolding_agent(mcp_manager: McpConnectionManager) -> ScaffolderAgent:
    """Ensambla el ScaffolderAgent con drivers 100% MCP + LiteLLM."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)
    tools = _build_tools(vcs, tracker, docs)
    priority_models = config.llm.scaffolding_llm_model_priority

    generate_plan = GenerateScaffoldPlanSkill(
        brain=brain, prompt_builder=ScaffoldingPromptBuilder()
    )
    skills: dict[SkillType, BaseSkill[Any, Any]] = {
        SkillType.GENERATE_SCAFFOLD_PLAN: generate_plan,
    }
    deterministic_workflow = ScaffoldingDeterministicWorkflow(
        vcs=vcs,
        tracker=tracker,
        docs=docs,
        generate_plan=generate_plan,
        priority_models=priority_models,
    )

    return ScaffolderAgent(
        config=ScaffolderAgentConfig(priority_models=priority_models),
        brain=brain,
        tools=tools,
        skills=skills,
        deterministic_workflow=deterministic_workflow,
    )


async def build_code_review_agent(mcp_manager: McpConnectionManager) -> CodeReviewerAgent:
    """Ensambla el CodeReviewerAgent con drivers 100% MCP + Skills."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)
    tools = _build_tools(vcs, tracker, docs)
    priority_models = config.llm.code_review_llm_model_priority

    analyze = AnalyzeCodeReviewSkill(brain=brain, prompt_builder=CodeReviewPromptBuilder())
    skills: dict[SkillType, BaseSkill[Any, Any]] = {
        SkillType.ANALYZE_CODE_REVIEW: analyze,
    }
    deterministic_workflow = CodeReviewDeterministicWorkflow(
        vcs=vcs,
        tracker=tracker,
        docs=docs,
        analyze=analyze,
        priority_models=priority_models,
    )

    return CodeReviewerAgent(
        config=CodeReviewerAgentConfig(priority_models=priority_models),
        brain=brain,
        tools=tools,
        skills=skills,
        deterministic_workflow=deterministic_workflow,
    )
