from abc import ABC, abstractmethod
from typing import Any


class GitLabProvider(ABC):
    """Abstract base class for GitLab operations."""

    @abstractmethod
    def resolve_project_id(self, project_path: str) -> int:
        """Resolves a project path to an ID."""
        pass

    @abstractmethod
    def create_branch(self, project_id: int, branch_name: str, ref: str = "main") -> dict[str, Any]:
        """Creates a new branch in the specified project."""
        pass

    @abstractmethod
    def branch_exists(self, project_id: int, branch_name: str) -> bool:
        """Checks if a branch exists in the project."""
        pass

    @abstractmethod
    def commit_files(self, project_id: int, branch_name: str, files_map: dict[str, str], commit_message: str) -> dict[str, Any]:
        """Commits files to a branch. Performs smart upsert."""
        pass

    @abstractmethod
    def create_merge_request(
        self, 
        project_id: int, 
        source_branch: str, 
        target_branch: str, 
        title: str, 
        description: str | None = None
    ) -> dict[str, Any]:
        """Creates a merge request."""
        pass
