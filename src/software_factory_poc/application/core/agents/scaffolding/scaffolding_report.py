from typing import Optional
try:
    from enum import StrEnum
except ImportError:
    from enum import Enum
    class StrEnum(str, Enum):
        pass

from pydantic import BaseModel


class ArtifactRunStatusEnum(StrEnum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    DUPLICATE = "DUPLICATE"


class ScaffoldingReport(BaseModel):
    run_id: str
    status: ArtifactRunStatusEnum
    issue_key: str
    
    mr_url:Optional[ str] = None
    branch_name:Optional[ str] = None
    jira_comment_id:Optional[ str] = None
    
    error_summary:Optional[ str] = None  # Safe summary for public consumption
