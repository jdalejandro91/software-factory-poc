from enum import StrEnum
from typing import Optional

from pydantic import BaseModel


class ArtifactRunStatusEnum(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class ArtifactResultModel(BaseModel):
    run_id: str
    status: ArtifactRunStatusEnum
    issue_key: str
    
    mr_url: Optional[str] = None
    branch_name: Optional[str] = None
    jira_comment_id: Optional[str] = None
    
    error_summary: Optional[str] = None  # Safe summary for public consumption
