from abc import ABC, abstractmethod
from typing import Any

class VcsAgent(ABC):
    """
    Domain Entity/Service responsible for Branch & Commit semantics.
    """
    
    @abstractmethod
    def prepare_repository(self, repo_url: str, branch_name: str) -> bool:
        """
        Clones/Fetch repository and checks out the specific branch.
        Returns True if branch is ready (new or switched), False if it already exists and we should skip?
        Actually, let's make it simple: Prepare the repo for work.
        """
        pass

    @abstractmethod
    def check_branch_exists(self, repo_url: str, branch_name: str) -> Any:
        """
        Checks if the branch exists. Returns details if so, None otherwise.
        """
        pass

    @abstractmethod
    def publish_changes(self, files: list[Any], message: str) -> str:
        """
        Commits and pushes changes. Returns the Change Request (MR/PR) link or Commit hash.
        """
        pass
