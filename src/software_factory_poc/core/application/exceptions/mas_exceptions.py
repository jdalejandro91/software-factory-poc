"""MAS (Multi-Agent System) exception hierarchy.

Provides a typed, structured exception tree for the application layer.
Every agent, workflow, and skill raises from this hierarchy,
enabling fine-grained error handling without string-matching.
"""

from typing import Any


class ApplicationError(Exception):
    """Base exception for all application-layer errors in BrahMAS."""

    def __init__(self, message: str = "", *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.context: dict[str, Any] = context or {}


class WorkflowExecutionError(ApplicationError):
    """Raised when a deterministic workflow pipeline fails at any step."""


class WorkflowHaltedException(ApplicationError):
    """Benign early-exit — the workflow stopped intentionally.

    Example: the branch already exists, so the scaffolder aborts
    without creating a duplicate.  This is NOT an error but a
    controlled halt that callers may catch and log.
    """


class SkillExecutionError(ApplicationError):
    """Raised when a Skill.execute() call fails (LLM timeout, bad schema, etc.)."""
