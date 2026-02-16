from typing import List
from dataclasses import dataclass
from software_factory_poc.domain.value_objects.vcs.branch_name import BranchName
from software_factory_poc.domain.value_objects.vcs.file_content import FileContent

@dataclass
class CommitIntent:
    """Consistency Root for code operations. Ensures a valid commit."""
    branch: BranchName
    message: str
    files: List[FileContent]

    def is_empty(self) -> bool:
        return len(self.files) == 0