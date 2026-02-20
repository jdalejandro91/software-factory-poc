"""Pure functions for parsing and validating LLM responses from litellm."""

import json
from typing import Any

from pydantic import ValidationError

from software_factory_poc.core.application.ports import T
from software_factory_poc.core.application.tools.common.exceptions import ProviderError


def parse_structured_response(
    raw_content: str | None,
    schema: type[T],
    model_id: str,
) -> T:
    """Deserialize JSON content and validate it against the Pydantic *schema*."""
    if not raw_content:
        raise ProviderError(
            provider=model_id,
            message="LLM returned empty content for structured request",
        )
    clean = strip_markdown_fences(raw_content)
    data = _safe_parse_json(clean, model_id)
    return _validate_schema(data, schema, model_id)


def extract_tool_response(response: Any) -> dict[str, Any]:
    """Normalize litellm's response into the dict shape expected by the Application layer."""
    message = response.choices[0].message
    result: dict[str, Any] = {"content": message.content or ""}
    if message.tool_calls:
        result["tool_calls"] = [_serialize_tool_call(tc) for tc in message.tool_calls]
    return result


def strip_markdown_fences(text: str) -> str:
    """Remove Markdown code fences that LLMs sometimes wrap around JSON."""
    stripped = text.strip()
    stripped = _remove_opening_fence(stripped)
    if stripped.endswith("```"):
        stripped = stripped[:-3]
    return stripped.strip()


def _remove_opening_fence(text: str) -> str:
    """Strip the opening ``` fence line from text if present."""
    if not text.startswith("```"):
        return text
    first_newline = text.find("\n")
    return text[first_newline + 1 :] if first_newline != -1 else text[3:]


def _safe_parse_json(text: str, model_id: str) -> Any:
    """Parse JSON text, raising ProviderError on decode failure."""
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(
            provider=model_id,
            message=f"LLM returned invalid JSON: {exc}",
        ) from exc


def _validate_schema(data: Any, schema: type[T], model_id: str) -> T:
    """Validate parsed data against a Pydantic schema, raising ProviderError on failure."""
    try:
        return schema.model_validate(data)
    except ValidationError as exc:
        raise ProviderError(
            provider=model_id,
            message=f"Structured response failed schema validation: {exc}",
        ) from exc


def _serialize_tool_call(tc: Any) -> dict[str, Any]:
    """Convert a single litellm tool call into the Application-layer dict format."""
    arguments = tc.function.arguments
    parsed_args = json.loads(arguments) if isinstance(arguments, str) else arguments
    return {
        "id": tc.id,
        "type": tc.type,
        "function": {"name": tc.function.name, "arguments": parsed_args},
    }
