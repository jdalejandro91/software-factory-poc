from software_factory_poc.application.core.agents.code_reviewer.code_reviewer_agent import (
    CodeReviewerAgent,
)
from software_factory_poc.application.core.agents.code_reviewer.value_objects.code_review_order import (
    CodeReviewOrder,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)


class PerformCodeReviewUseCase:
    """
    Use Case for performing a code review.
    Acts as an intermediary to the CodeReviewerAgent.
    """

    def __init__(self, agent: CodeReviewerAgent):
        self.agent = agent
        self.logger = LoggerFactoryService.build_logger(__name__)

    def execute(self, order: CodeReviewOrder) -> None:
        """
        Executes the code review process for the given order.
        """
        self.logger.info(f"Executing Code Review Use Case for {order.issue_key}")
        self.agent.execute_flow(order)
