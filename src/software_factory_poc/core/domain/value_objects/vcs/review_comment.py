from dataclasses import dataclass

from software_factory_poc.core.domain.value_objects.vcs.review_severity import ReviewSeverity


@dataclass(frozen=True)
class ReviewComment:
    """Guardrail: Evita que el LLM devuelva archivos vacíos o líneas imposibles."""
    file_path: str
    description: str
    suggestion: str
    severity: ReviewSeverity
    line_number: int | None = None

    def __post_init__(self):
        if not self.file_path.strip(): raise ValueError("El archivo no puede estar vacío.")
        if not self.description.strip(): raise ValueError("La descripción no puede estar vacía.")
        if self.line_number is not None and self.line_number < 0: raise ValueError("Línea inválida.")