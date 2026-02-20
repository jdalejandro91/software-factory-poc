"""Unit tests — LiteLlmBrainAdapter (zero I/O, fully mocked litellm)."""

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel

from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter import (
    LiteLlmBrainAdapter,
)
from software_factory_poc.infrastructure.adapters.llm.llm_response_parser import (
    parse_structured_response,
    strip_markdown_fences,
)

MODULE = "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter"


# ── Test schema ──


class DummySchema(BaseModel):
    name: str
    value: int


# ── Helpers ──


class FakeUsage:
    prompt_tokens: int = 10
    completion_tokens: int = 20


class FakeMessage:
    def __init__(self, content: str | None = None, tool_calls: Any = None) -> None:
        self.content = content
        self.tool_calls = tool_calls


class FakeChoice:
    def __init__(self, message: FakeMessage) -> None:
        self.message = message


class FakeResponse:
    def __init__(self, content: str | None = None, tool_calls: Any = None) -> None:
        self.choices = [FakeChoice(FakeMessage(content, tool_calls))]
        self.usage = FakeUsage()


# ══════════════════════════════════════════════════════════════════════
# _strip_markdown_fences
# ══════════════════════════════════════════════════════════════════════


class TestStripMarkdownFences:
    def test_strips_json_fences(self) -> None:
        text = '```json\n{"name": "a", "value": 1}\n```'
        result = strip_markdown_fences(text)
        assert result == '{"name": "a", "value": 1}'

    def test_strips_plain_fences(self) -> None:
        text = '```\n{"key": "val"}\n```'
        result = strip_markdown_fences(text)
        assert result == '{"key": "val"}'

    def test_leaves_clean_json_untouched(self) -> None:
        text = '{"name": "b", "value": 2}'
        result = strip_markdown_fences(text)
        assert result == text

    def test_handles_extra_whitespace(self) -> None:
        text = '  \n```json\n{"x": 1}\n```  \n'
        result = strip_markdown_fences(text)
        assert result == '{"x": 1}'

    def test_handles_empty_string(self) -> None:
        assert strip_markdown_fences("") == ""

    def test_handles_fences_without_newline(self) -> None:
        text = "```json```"
        result = strip_markdown_fences(text)
        assert "```" not in result


# ══════════════════════════════════════════════════════════════════════
# _parse_structured_response
# ══════════════════════════════════════════════════════════════════════


class TestParseStructuredResponse:
    def test_parses_clean_json(self) -> None:
        raw = '{"name": "test", "value": 42}'
        result = parse_structured_response(raw, DummySchema, "model-x")
        assert result.name == "test"
        assert result.value == 42

    def test_parses_json_wrapped_in_markdown_fences(self) -> None:
        raw = '```json\n{"name": "fenced", "value": 7}\n```'
        result = parse_structured_response(raw, DummySchema, "model-x")
        assert result.name == "fenced"
        assert result.value == 7

    def test_raises_on_empty_content(self) -> None:
        with pytest.raises(ProviderError, match="empty content"):
            parse_structured_response(None, DummySchema, "model-x")

    def test_raises_on_invalid_json(self) -> None:
        with pytest.raises(ProviderError, match="invalid JSON"):
            parse_structured_response("not json", DummySchema, "model-x")

    def test_raises_on_schema_validation_failure(self) -> None:
        raw = '{"name": "test", "value": "not_int"}'
        with pytest.raises(ProviderError, match="schema validation"):
            parse_structured_response(raw, DummySchema, "model-x")


# ══════════════════════════════════════════════════════════════════════
# generate_structured (integration with mocked litellm)
# ══════════════════════════════════════════════════════════════════════


class TestGenerateStructured:
    @pytest.fixture(autouse=True)
    def _mock_litellm(self) -> None:
        self.mock_acompletion = AsyncMock()
        patcher = patch(f"{MODULE}.litellm.acompletion", self.mock_acompletion)
        patcher.start()
        yield
        patcher.stop()

    def _build_adapter(self) -> LiteLlmBrainAdapter:
        with patch(f"{MODULE}._inject_api_keys"):
            from software_factory_poc.infrastructure.adapters.llm.config.llm_settings import (
                LlmSettings,
            )

            settings = LlmSettings(_env_file=None)  # type: ignore[call-arg]
            return LiteLlmBrainAdapter(settings)

    async def test_returns_validated_schema(self) -> None:
        self.mock_acompletion.return_value = FakeResponse('{"name": "ok", "value": 1}')
        adapter = self._build_adapter()

        result = await adapter.generate_structured("prompt", DummySchema, ["openai:gpt-4o"])

        assert isinstance(result, DummySchema)
        assert result.name == "ok"

    async def test_strips_fences_before_parsing(self) -> None:
        self.mock_acompletion.return_value = FakeResponse(
            '```json\n{"name": "fenced", "value": 2}\n```'
        )
        adapter = self._build_adapter()

        result = await adapter.generate_structured("prompt", DummySchema, ["openai:gpt-4o"])

        assert result.name == "fenced"
        assert result.value == 2

    async def test_invalid_json_raises_provider_error(self) -> None:
        self.mock_acompletion.return_value = FakeResponse("not json at all")
        adapter = self._build_adapter()

        with pytest.raises(ProviderError, match="invalid JSON"):
            await adapter.generate_structured("prompt", DummySchema, ["openai:gpt-4o"])
