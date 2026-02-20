"""Pure functions for building and updating Jira issue descriptions (ADF-safe)."""

import copy
from typing import Any


def build_updated_description(
    current: str | dict[str, Any] | None, appended_text: str
) -> str | dict[str, Any]:
    """Build updated description handling both ADF (dict) and plain-text formats."""
    if isinstance(current, dict):
        return _append_to_adf(current, appended_text)
    return f"{current or ''}\n\n```yaml\n{appended_text}\n```"


def _append_to_adf(adf_doc: dict[str, Any], text: str) -> dict[str, Any]:
    """Deep-copy an ADF document and append a YAML codeBlock node."""
    doc = copy.deepcopy(adf_doc)
    code_block: dict[str, Any] = {
        "type": "codeBlock",
        "attrs": {"language": "yaml"},
        "content": [{"type": "text", "text": text}],
    }
    doc.setdefault("content", []).append(code_block)
    return doc
