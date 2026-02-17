from dataclasses import dataclass

from software_factory_poc.core.domain.delivery.value_objects.branch_name import BranchName
from software_factory_poc.core.domain.delivery.value_objects.file_content import FileContent


@dataclass
class CommitIntent:
    """Consistency Root for code operations. Ensures a valid commit."""

    branch: BranchName
    message: str
    files: list[FileContent]

    def is_empty(self) -> bool:
        return len(self.files) == 0
