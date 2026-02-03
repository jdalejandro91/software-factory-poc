from abc import ABC, abstractmethod
from typing import Optional, List

from software_factory_poc.application.core.agents.code_reviewer.dtos.code_review_result_dto import ReviewCommentDTO
from software_factory_poc.application.core.agents.common.dtos.file_changes_dto import FileChangesDTO
from software_factory_poc.application.core.agents.common.dtos.file_content_dto import FileContentDTO
from software_factory_poc.application.core.agents.vcs.dtos.vcs_dtos import BranchDTO, CommitResultDTO, MergeRequestDTO


class VcsGateway(ABC):
    @abstractmethod
    def resolve_project_id(self, project_path: str) -> int:
        """Resolves a project path to an ID."""
        pass

    @abstractmethod
    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> BranchDTO:
        """Creates a new branch."""
        pass

    @abstractmethod
    def branch_exists(self, project_id: int, branch_name: str) -> bool:
        """Checks if a branch exists."""
        pass

    @abstractmethod
    def get_branch_details(self, project_id: int, branch_name: str) -> Optional[BranchDTO]:
        """Retrieves branch details including web URL."""
        pass

    @abstractmethod
    @abstractmethod
    def commit_files(self, project_id: int, branch_name: str, files_map: dict[str, str], commit_message: str, force_create: bool = False) -> CommitResultDTO:
        """Commits files to a branch."""
        pass

    @abstractmethod
    def create_merge_request(
        self, 
        project_id: int, 
        source_branch: str, 
        target_branch: str, 
        title: str, 
        description:Optional[ str] = None
    ) -> MergeRequestDTO:
        """Creates a merge request."""
        pass

    @abstractmethod
    def get_repository_files(self, project_id: int, branch_name: str, max_files: int = 50, max_file_size_kb: int = 100) -> List[FileContentDTO]:
        """Retrieves all text files from a specific branch with safety limits."""
        pass

    @abstractmethod
    def get_merge_request_diffs(self, project_id: int, mr_id: str) -> List[FileChangesDTO]:
        """Retrieves the file changes (diffs) for a specific Merge Request."""
        pass

    @abstractmethod
    def post_review_comments(self, project_id: int, mr_id: str, comments: List[ReviewCommentDTO]) -> None:
        """Posts a batch of review comments to a Merge Request."""
        pass

    @abstractmethod
    def validate_mr_exists(self, project_id: int, mr_id: str) -> bool:
        """Checks if a Merge Request exists and is accessible."""
        pass

    @abstractmethod
    def get_active_mr_url(self, project_id: int, source_branch: str) -> Optional[str]:
        """Retrieves the URL of an active MR for a specific branch."""
        pass
