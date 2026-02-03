from typing import Optional

from pydantic import BaseModel, ConfigDict


class CodeReviewOrder(BaseModel):
    model_config = ConfigDict(frozen=True)

    issue_key: str
    project_id: int          # Obligatorio. Viene del YAML.
    mr_id: str               # Obligatorio. Se extrae de la URL del MR.
    source_branch: str       # Obligatorio. Viene del YAML (source_branch_name).
    vcs_provider: str = "GITLAB"
    summary: str             # Contexto de Jira
    description: str         # Contexto de Jira
    mr_url: str              # Obligatorio. Viene del YAML.
    technical_doc_id: Optional[str] = None
