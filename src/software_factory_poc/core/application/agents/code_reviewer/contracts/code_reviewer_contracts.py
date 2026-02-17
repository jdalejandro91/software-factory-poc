from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field


@dataclass
class CodeReviewOrder:
    """Incoming request from the entrypoint mapper to trigger a code review."""

    issue_key: str
    project_id: int
    mr_id: str
    source_branch: str
    vcs_provider: str
    summary: str
    description: str
    mr_url: str
    requesting_user: str | None = None


class CodeIssueSchema(BaseModel):
    file_path: str = Field(description="Ruta del archivo analizado")
    line_number: int | None = Field(None, description="Línea donde ocurre el problema (null si es general)")
    severity: Literal["CRITICAL", "WARNING", "SUGGESTION"] = Field(description="Severidad del hallazgo")
    description: str = Field(description="Explicación técnica del problema")
    suggestion: str = Field(description="Código sugerido o acción para solucionarlo")

class CodeReviewResponseSchema(BaseModel):
    is_approved: bool = Field(description="True si el código es publicable, False si requiere cambios")
    summary: str = Field(description="Resumen ejecutivo del análisis")
    issues: list[CodeIssueSchema] = Field(default_factory=list)