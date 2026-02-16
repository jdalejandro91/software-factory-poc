from dataclasses import dataclass, field
from typing import List
from software_factory_poc.domain.value_objects.vcs.review_comment import ReviewComment
from software_factory_poc.domain.value_objects.vcs.review_severity import ReviewSeverity

@dataclass
class CodeReviewReport:
    """Raíz de Consistencia. Protege al negocio de que la IA apruebe fallos críticos."""
    is_approved: bool
    summary: str
    comments: List[ReviewComment] = field(default_factory=list)

    def has_critical_issues(self) -> bool:
        return any(c.severity == ReviewSeverity.CRITICAL for c in self.comments)

    def __post_init__(self):
        # INVARIANTE: Rechazo forzoso si hay issues CRITICAL
        if self.has_critical_issues() and self.is_approved:
            raise ValueError("Inconsistencia: No se puede aprobar un MR con fallos CRITICAL.")