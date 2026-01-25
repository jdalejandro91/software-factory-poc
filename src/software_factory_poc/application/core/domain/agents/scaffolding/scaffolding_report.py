from enum import StrEnum

from pydantic import BaseModel


class ArtifactRunStatusEnum(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class ScaffoldingReport(BaseModel):
    run_id: str
    status: ArtifactRunStatusEnum
    issue_key: str
    
    mr_url: str | None = None
    branch_name: str | None = None
    jira_comment_id: str | None = None
    
    error_summary: str | None = None  # Safe summary for public consumption
