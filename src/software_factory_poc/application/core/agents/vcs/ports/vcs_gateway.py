from abc import ABC, abstractmethod
from typing import Any, Optional
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
