from dataclasses import dataclass
from typing import Any

from software_factory_poc.application.core.agents.base_agent import BaseAgent
from software_factory_poc.application.core.agents.code_reviewer.config.code_reviewer_agent_config import (
    CodeReviewerAgentConfig,
)
from software_factory_poc.application.core.agents.code_reviewer.tools.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.application.core.agents.code_reviewer.tools.review_result_parser import ReviewResultParser
from software_factory_poc.application.core.agents.reasoner.reasoner_agent import ReasonerAgent
from software_factory_poc.application.core.agents.reporter.reporter_agent import ReporterAgent
from software_factory_poc.application.core.agents.research.research_agent import ResearchAgent
from software_factory_poc.application.core.agents.vcs.vcs_agent import VcsAgent
from software_factory_poc.application.usecases.dtos.code_review_order import CodeReviewOrder
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService


@dataclass
class CodeReviewerAgent(BaseAgent):
    """
    Orchestrator Agent for Code Review Tasks.
    """

    config: CodeReviewerAgentConfig
    reporter: ReporterAgent
    vcs: VcsAgent
    researcher: ResearchAgent
    reasoner: ReasonerAgent

    def __post_init__(self):
        self.logger = LoggerFactoryService.build_logger(__name__)
        self.prompt_builder = CodeReviewPromptBuilder()
        self.parser = ReviewResultParser()
        self.logger.info("CodeReviewerAgent initialized")

    def execute_flow(self, order: CodeReviewOrder) -> None:
        self.logger.info(f"Starting code review for {order}")
