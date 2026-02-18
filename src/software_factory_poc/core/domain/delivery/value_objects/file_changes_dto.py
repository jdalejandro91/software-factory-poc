"""Structured representation of a single file's changes within a Merge Request diff."""

from dataclasses import dataclass, field


@dataclass(frozen=True, kw_only=True)
class FileChangesDTO:
    """Rich diff metadata for a single changed file.

    Provides the LLM with precise hunk boundaries and line numbers
    so it can review code changes with surgical accuracy.
    """

    old_path: str | None
    new_path: str
    hunks: list[str] = field(default_factory=list)
    added_lines: list[int] = field(default_factory=list)
    removed_lines: list[int] = field(default_factory=list)
