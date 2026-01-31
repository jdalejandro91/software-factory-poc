from typing import Optional

from pydantic import BaseModel


class CodeReviewOrder(BaseModel):
    """Value Object representing a Code Review Order."""
    issue_key: str
    project_id: int
    mr_id: str
    source_branch: str
    vcs_provider: str
    requesting_user: Optional[str] = None
    
    class Config:
        frozen = True
