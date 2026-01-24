from abc import ABC, abstractmethod
from typing import Any, List, Optional

class VcsAgent(ABC):
    """
    Capability contract for Agents responsible for Version Control interactions.
    """
    
    @abstractmethod
    def branch_exists(self, repo_url: str, branch_name: str) -> Optional[str]:
        """
        Checks if a branch exists in the repository.
        Returns the URL of the branch if it exists, None otherwise.
        """
        pass
    
    @abstractmethod
    def prepare_workspace(self, repo_url: str, branch_name: str) -> None:
        """
        Prepares the workspace (clone/checkout) for the given repo and branch.
        """
        pass

    @abstractmethod
    def publish_changes(self, files: List[Any], message: str) -> str:
        """
        Publishes the given files to the VCS (Commit -> Push -> Merge Request).
        Returns the URL of the created Merge Request.
        """
        pass
