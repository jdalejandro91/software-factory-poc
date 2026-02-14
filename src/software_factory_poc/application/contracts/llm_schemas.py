from pydantic import BaseModel, Field
from typing import List, Literal, Optional

class FileSchemaDTO(BaseModel):
    path: str = Field(description="Ruta relativa del archivo (ej. src/main.py)")
    content: str = Field(description="Código completo generado")
    is_new: bool = Field(default=True)

class ScaffoldingResponseSchema(BaseModel):
    """LLM CONTRACT: We force the model to return this structured JSON."""
    branch_name: str = Field(description="Debe empezar por feature/ seguido del ticket")
    commit_message: str = Field(description="Mensaje del commit (Conventional Commits)")
    files: List[FileSchemaDTO]

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