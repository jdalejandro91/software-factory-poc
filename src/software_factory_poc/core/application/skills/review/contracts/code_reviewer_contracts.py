from typing import Literal

from pydantic import BaseModel, Field


class CodeIssueSchema(BaseModel):
    file_path: str = Field(description="Ruta del archivo analizado")
    line_number: int | None = Field(
        None, description="Línea donde ocurre el problema (null si es general)"
    )
    severity: Literal["CRITICAL", "WARNING", "SUGGESTION"] = Field(
        description="Severidad del hallazgo"
    )
    description: str = Field(description="Explicación técnica del problema")
    suggestion: str = Field(description="Código sugerido o acción para solucionarlo")


class CodeReviewResponseSchema(BaseModel):
    is_approved: bool = Field(
        description="True si el código es publicable, False si requiere cambios"
    )
    summary: str = Field(description="Resumen ejecutivo del análisis")
    issues: list[CodeIssueSchema] = Field(default_factory=list)
