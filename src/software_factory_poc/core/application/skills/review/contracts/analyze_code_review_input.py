"""Input contract for the LLM code analysis step."""

from dataclasses import dataclass, field

from software_factory_poc.core.domain.delivery import FileContent
from software_factory_poc.core.domain.mission import Mission


@dataclass(frozen=True)
class AnalyzeCodeReviewInput:
    """Input contract for the LLM code analysis step."""

    mission: Mission
    mr_diff: str
    conventions: str
    priority_models: list[str]
    repository_tree: str = ""
    code_review_params: dict[str, str] = field(default_factory=dict)
    original_branch_code: list[FileContent] = field(default_factory=list)
