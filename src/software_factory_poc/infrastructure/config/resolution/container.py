"""Functional DI container — builds fully-wired Use Cases using MCP adapters.

This module mirrors the ProviderResolver class but uses free functions,
making it convenient for FastAPI dependency injection.
"""

import logging

from software_factory_poc.core.application.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.core.application.agents.code_reviewer.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.agents.loops.agentic_loop_runner import (
    AgenticLoopRunner,
)
from software_factory_poc.core.application.agents.scaffolder.prompt_templates.scaffolding_prompt_builder import (
    ScaffoldingPromptBuilder,
)
from software_factory_poc.core.application.agents.scaffolder.scaffolder_agent import ScaffolderAgent
from software_factory_poc.core.application.policies.tool_safety_policy import ToolSafetyPolicy
from software_factory_poc.core.application.skills.review.analyze_code_review_skill import (
    AnalyzeCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.fetch_review_diff_skill import (
    FetchReviewDiffSkill,
)
from software_factory_poc.core.application.skills.review.publish_code_review_skill import (
    PublishCodeReviewSkill,
)
from software_factory_poc.core.application.skills.review.validate_review_context_skill import (
    ValidateReviewContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.apply_scaffold_delivery_skill import (
    ApplyScaffoldDeliverySkill,
)
from software_factory_poc.core.application.skills.scaffold.fetch_scaffold_context_skill import (
    FetchScaffoldContextSkill,
)
from software_factory_poc.core.application.skills.scaffold.generate_scaffold_plan_skill import (
    GenerateScaffoldPlanSkill,
)
from software_factory_poc.core.application.skills.scaffold.idempotency_check_skill import (
    IdempotencyCheckSkill,
)
from software_factory_poc.core.application.skills.scaffold.report_success_skill import (
    ReportSuccessSkill,
)
from software_factory_poc.infrastructure.config.app_config import AppConfig
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_mcp_client import (
    ConfluenceMcpClient,
)
from software_factory_poc.infrastructure.tools.llm.litellm_brain_adapter import LiteLlmBrainAdapter
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


# === PUBLIC BUILDERS ===


async def build_scaffolding_agent(mcp_manager: McpConnectionManager) -> ScaffolderAgent:
    """Ensambla el ScaffolderAgent con drivers 100% MCP + LiteLLM."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)
    prompt_builder = ScaffoldingPromptBuilder()

    return ScaffolderAgent(
        vcs=vcs,
        tracker=tracker,
        research=docs,
        brain=brain,
        idempotency_check=IdempotencyCheckSkill(vcs=vcs, tracker=tracker),
        fetch_context=FetchScaffoldContextSkill(docs=docs),
        generate_plan=GenerateScaffoldPlanSkill(brain=brain, prompt_builder=prompt_builder),
        apply_delivery=ApplyScaffoldDeliverySkill(vcs=vcs),
        report_success=ReportSuccessSkill(tracker=tracker),
        loop_runner=AgenticLoopRunner(brain=brain, policy=ToolSafetyPolicy()),
        priority_models=config.llm.scaffolding_llm_model_priority,
    )


async def build_code_review_agent(mcp_manager: McpConnectionManager) -> CodeReviewerAgent:
    """Ensambla el CodeReviewerAgent con drivers 100% MCP + Skills + LoopRunner."""
    config = AppConfig()
    vcs, tracker, docs, brain = await _build_drivers(mcp_manager, config)
    prompt_builder = CodeReviewPromptBuilder()

    return CodeReviewerAgent(
        vcs=vcs,
        tracker=tracker,
        research=docs,
        brain=brain,
        validate_context=ValidateReviewContextSkill(tracker=tracker),
        fetch_diff=FetchReviewDiffSkill(vcs=vcs, docs=docs),
        analyze=AnalyzeCodeReviewSkill(brain=brain, prompt_builder=prompt_builder),
        publish=PublishCodeReviewSkill(vcs=vcs, tracker=tracker),
        loop_runner=AgenticLoopRunner(brain=brain, policy=ToolSafetyPolicy()),
        priority_models=config.llm.code_review_llm_model_priority,
    )
