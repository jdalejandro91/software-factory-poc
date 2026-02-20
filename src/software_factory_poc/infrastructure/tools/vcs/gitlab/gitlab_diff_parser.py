"""Pure functions for parsing GitLab merge-request diffs into domain DTOs."""

import json
import re
from typing import Any

import structlog

from software_factory_poc.core.domain.delivery import FileChangesDTO

logger = structlog.get_logger()

_HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@", re.MULTILINE)


def parse_changes_from_diff(raw: str) -> list[FileChangesDTO]:
    """Parse the MCP response from gitlab_get_merge_request_changes."""
    changes = _extract_changes_list(raw)
    results: list[FileChangesDTO] = []
    for change in changes:
        if not isinstance(change, dict):
            continue
        try:
            results.append(_parse_single_change(change))
        except Exception:
            path = change.get("new_path", change.get("old_path", "<unknown>"))
            logger.warning("Skipping unparseable diff", file_path=path, source_system="GitLabMCP")
    return results


def _extract_changes_list(raw: str) -> list[Any]:
    """Extract the changes list from raw JSON, returning empty list on failure."""
    try:
        parsed_response = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    changes = (
        parsed_response.get("changes", parsed_response)
        if isinstance(parsed_response, dict)
        else parsed_response
    )
    return changes if isinstance(changes, list) else []


def _parse_single_change(change: dict[str, str]) -> FileChangesDTO:
    """Parse a single file change entry into a FileChangesDTO."""
    diff_text = change.get("diff", "")
    hunks, added, removed = _parse_diff_hunks(diff_text)
    return FileChangesDTO(
        old_path=change.get("old_path"),
        new_path=change.get("new_path", ""),
        hunks=hunks,
        added_lines=added,
        removed_lines=removed,
    )


def _parse_diff_hunks(diff_text: str) -> tuple[list[str], list[int], list[int]]:
    """Extract hunks, added line numbers, and removed line numbers from unified diff."""
    if not diff_text:
        return [], [], []
    hunks: list[str] = []
    added_lines: list[int] = []
    removed_lines: list[int] = []
    parts = _HUNK_HEADER_RE.split(diff_text)
    for i in range(1, len(parts), 3):
        _accumulate_hunk(parts, i, hunks, added_lines, removed_lines)
    return hunks, added_lines, removed_lines


def _accumulate_hunk(
    parts: list[str],
    index: int,
    hunks: list[str],
    added_lines: list[int],
    removed_lines: list[int],
) -> None:
    """Parse a single hunk triplet and append to the accumulator lists."""
    old_start = int(parts[index])
    new_start = int(parts[index + 1])
    body = parts[index + 2] if index + 2 < len(parts) else ""
    hunks.append(f"@@ -{old_start} +{new_start} @@{body}")
    _collect_line_numbers(body, old_start, new_start, added_lines, removed_lines)


def _collect_line_numbers(
    body: str,
    old_start: int,
    new_start: int,
    added_lines: list[int],
    removed_lines: list[int],
) -> None:
    """Walk diff body lines and record added/removed line numbers."""
    old_line, new_line = old_start, new_start
    for line in body.split("\n"):
        if line.startswith("+"):
            added_lines.append(new_line)
            new_line += 1
        elif line.startswith("-"):
            removed_lines.append(old_line)
            old_line += 1
        elif line.startswith(" ") or line == "":
            old_line += 1
            new_line += 1
