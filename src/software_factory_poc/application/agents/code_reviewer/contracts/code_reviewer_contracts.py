from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class CodeIssueSchema(BaseModel):
    file_path: str = Field(description="Ruta del archivo analizado")
    line_number: Optional[int] = Field(None, description="Línea donde ocurre el problema (null si es general)")
    severity: Literal["CRITICAL", "WARNING", "SUGGESTION"] = Field(description="Severidad del hallazgo")
    description: str = Field(description="Explicación técnica del problema")
    suggestion: str = Field(description="Código sugerido o acción para solucionarlo")

class CodeReviewResponseSchema(BaseModel):
    is_approved: bool = Field(description="True si el código es publicable, False si requiere cambios")
    summary: str = Field(description="Resumen ejecutivo del análisis")
    issues: List[CodeIssueSchema] = Field(default_factory=list)