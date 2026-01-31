from dataclasses import dataclass
from typing import Optional

@dataclass
class CodeReviewOrder:
    project_id: int
    mr_id: str
    requesting_user: Optional[str] = None
