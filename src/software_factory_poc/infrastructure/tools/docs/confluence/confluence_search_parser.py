"""Pure functions for parsing Confluence CQL search responses."""

import json
from typing import Any


def extract_first_page_id(raw: str) -> str | None:
    """Extract the ID of the first result from a CQL search response."""
    try:
        search_response = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    results = (
        search_response.get("results", search_response)
        if isinstance(search_response, dict)
        else search_response
    )
    if isinstance(results, list) and results:
        return str(results[0].get("id", ""))
    return None


def extract_page_list(raw: str) -> list[dict[str, str]]:
    """Extract a list of {id, title} dicts from a CQL search response."""
    try:
        search_response = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return []
    results: Any = (
        search_response.get("results", search_response)
        if isinstance(search_response, dict)
        else search_response
    )
    if not isinstance(results, list):
        return []
    return [
        {"id": str(r.get("id", "")), "title": str(r.get("title", "Untitled"))}
        for r in results
        if isinstance(r, dict) and r.get("id")
    ]
