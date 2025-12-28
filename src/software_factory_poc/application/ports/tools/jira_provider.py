from abc import ABC, abstractmethod
from typing import Any


class JiraProvider(ABC):
    """Abstract base class for Jira operations."""

    @abstractmethod
    def get_issue(self, issue_key: str) -> dict[str, Any]:
        """Retrieves details of a Jira issue."""
        pass

    @abstractmethod
    def add_comment(self, issue_key: str, body: Any) -> dict[str, Any]:
        """Adds a comment to a Jira issue. Body can be ADF (dict) or text."""
        pass

    @abstractmethod
    def transition_issue(self, issue_key: str, transition_id: str) -> None:
        """Transitions a Jira issue to a new status."""
        pass
