from pydantic import BaseModel, Field


class FileSchemaDTO(BaseModel):
    path: str = Field(description="Ruta relativa del archivo (ej. src/main.py)")
    content: str = Field(description="Código completo generado")
    is_new: bool = Field(default=True)


class ScaffoldingResponseSchema(BaseModel):
    """LLM CONTRACT: We force the model to return this structured JSON."""

    branch_name: str = Field(description="Debe empezar por feature/ seguido del ticket")
    commit_message: str = Field(description="Mensaje del commit (Conventional Commits)")
    files: list[FileSchemaDTO]
