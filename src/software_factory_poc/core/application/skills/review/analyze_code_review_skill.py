import logging
from dataclasses import dataclass, field

from software_factory_poc.core.application.exceptions import SkillExecutionError
from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.application.skills.review.contracts.code_reviewer_contracts import (
    CodeReviewResponseSchema,
)
from software_factory_poc.core.application.skills.review.prompt_templates.code_review_prompt_builder import (
    CodeReviewPromptBuilder,
)
from software_factory_poc.core.application.skills.skill import BaseSkill
from software_factory_poc.core.domain.mission import Mission
from software_factory_poc.core.domain.quality import CodeReviewReport, ReviewComment, ReviewSeverity
from software_factory_poc.core.domain.shared.skill_type import SkillType

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AnalyzeCodeReviewInput:
    """Input contract for the LLM code analysis step."""

    mission: Mission
    mr_diff: str
    conventions: str
    priority_models: list[str]
    code_review_params: dict[str, str] = field(default_factory=dict)


class AnalyzeCodeReviewSkill(BaseSkill[AnalyzeCodeReviewInput, CodeReviewReport]):
    """Builds the review prompt, calls the LLM, and converts the response to a domain report.

    The ``CodeReviewReport`` domain aggregate enforces the invariant that
    critical issues force rejection regardless of the LLM's approval flag.
    """

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ANALYZE_CODE_REVIEW

    def __init__(self, brain: BrainPort, prompt_builder: CodeReviewPromptBuilder) -> None:
        self._brain = brain
        self._prompt_builder = prompt_builder

    async def execute(self, input_data: AnalyzeCodeReviewInput) -> CodeReviewReport:
        logger.info("[AnalyzeCodeReview] Building prompt and calling LLM")
        ctx = {"skill": "analyze_code_review"}
        try:
            sys_prompt = self._prompt_builder.build_system_prompt()
            user_prompt = self._prompt_builder.build_analysis_prompt(
                mission=input_data.mission,
                mr_diff=input_data.mr_diff,
                conventions=input_data.conventions,
                code_review_params=input_data.code_review_params or None,
            )

            full_prompt = f"{sys_prompt}\n\n{user_prompt}"

            review_schema: CodeReviewResponseSchema = await self._brain.generate_structured(
                prompt=full_prompt,
                schema=CodeReviewResponseSchema,
                priority_models=input_data.priority_models,
            )

            report = self._to_domain_report(review_schema)

            verdict = "APPROVED" if report.is_approved else "REJECTED"
            logger.info(
                "[AnalyzeCodeReview] Verdict: %s — %d issues found",
                verdict,
                len(report.comments),
            )
            return report
        except SkillExecutionError:
            raise
        except Exception as exc:
            raise SkillExecutionError(f"Code review analysis failed: {exc}", context=ctx) from exc

    @staticmethod
    def _to_domain_report(schema: CodeReviewResponseSchema) -> CodeReviewReport:
        """Convert the LLM Pydantic response to the CodeReviewReport domain aggregate."""
        domain_comments = [
            ReviewComment(
                file_path=issue.file_path,
                description=issue.description,
                suggestion=issue.suggestion,
                severity=ReviewSeverity(issue.severity),
                line_number=issue.line_number,
            )
            for issue in schema.issues
        ]

        has_critical = any(c.severity == ReviewSeverity.CRITICAL for c in domain_comments)
        is_approved = schema.is_approved and not has_critical

        return CodeReviewReport(
            is_approved=is_approved,
            summary=schema.summary,
            comments=domain_comments,
        )
