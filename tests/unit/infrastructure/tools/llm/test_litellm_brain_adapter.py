"""Unit tests for LiteLlmBrainAdapter — zero I/O, fully mocked."""

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import BaseModel, SecretStr

from software_factory_poc.core.application.ports import BrainPort
from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.infrastructure.adapters.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter import (
    LiteLlmBrainAdapter,
    _normalize_model_id,
)

# ── Dummy schema for structured output tests ─────────────────


class DummySchema(BaseModel):
    title: str
    score: int


# ── Helpers to build fake litellm responses ───────────────────


def _fake_completion_response(content: str, tool_calls: list | None = None) -> SimpleNamespace:
    """Build a minimal object that mimics ``litellm.ModelResponse``."""
    message = SimpleNamespace(content=content, tool_calls=tool_calls)
    choice = SimpleNamespace(message=message)
    return SimpleNamespace(choices=[choice])


def _fake_tool_call(call_id: str, name: str, arguments: dict) -> SimpleNamespace:
    """Build a minimal object that mimics a tool call entry."""
    function = SimpleNamespace(name=name, arguments=json.dumps(arguments))
    return SimpleNamespace(id=call_id, type="function", function=function)


# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture()
def settings() -> LlmSettings:
    """Create LlmSettings without reading .env, using direct kwargs."""
    return LlmSettings(
        OPENAI_API_KEY=SecretStr("sk-test-key"),
        GEMINI_API_KEY=None,
        DEEPSEEK_API_KEY=None,
        ANTHROPIC_API_KEY=None,
        LLM_ALLOWED_MODELS=["openai:gpt-4o"],
        SCAFFOLDING_LLM_MODEL_PRIORITY=["openai:gpt-4o"],
        CODE_REVIEW_LLM_MODEL_PRIORITY=["openai:gpt-4o"],
    )


@pytest.fixture()
def adapter(settings: LlmSettings) -> LiteLlmBrainAdapter:
    return LiteLlmBrainAdapter(settings)


PRIORITY_MODELS = ["openai:gpt-4o", "deepseek:deepseek-coder"]


# ══════════════════════════════════════════════════════════════
#  generate_structured
# ══════════════════════════════════════════════════════════════


class TestGenerateStructuredSuccess:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_returns_validated_pydantic_instance(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange
        payload = {"title": "Test Plan", "score": 95}
        mock_acompletion.return_value = _fake_completion_response(json.dumps(payload))

        # Act
        result = await adapter.generate_structured(
            prompt="Generate a plan",
            schema=DummySchema,
            priority_models=["openai:gpt-4o"],
        )

        # Assert
        assert isinstance(result, DummySchema)
        assert result.title == "Test Plan"
        assert result.score == 95
        mock_acompletion.assert_awaited_once()

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_model_id_normalized_to_slash(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange
        payload = {"title": "X", "score": 1}
        mock_acompletion.return_value = _fake_completion_response(json.dumps(payload))

        # Act
        await adapter.generate_structured(
            prompt="p", schema=DummySchema, priority_models=["deepseek:deepseek-coder"]
        )

        # Assert — litellm received the slash-based model id
        call_kwargs = mock_acompletion.call_args.kwargs
        assert call_kwargs["model"] == "deepseek/deepseek-coder"


class TestFallbackRoutingLogic:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_falls_back_to_second_model_on_first_failure(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange — first call raises, second succeeds
        payload = {"title": "Fallback OK", "score": 42}
        mock_acompletion.side_effect = [
            RuntimeError("Rate limit hit"),
            _fake_completion_response(json.dumps(payload)),
        ]

        # Act
        result = await adapter.generate_structured(
            prompt="Generate", schema=DummySchema, priority_models=PRIORITY_MODELS
        )

        # Assert
        assert isinstance(result, DummySchema)
        assert result.title == "Fallback OK"
        assert mock_acompletion.await_count == 2

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_fallback_uses_correct_model_ids(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange
        payload = {"title": "OK", "score": 1}
        mock_acompletion.side_effect = [
            RuntimeError("fail"),
            _fake_completion_response(json.dumps(payload)),
        ]

        # Act
        await adapter.generate_structured(
            prompt="p", schema=DummySchema, priority_models=PRIORITY_MODELS
        )

        # Assert — first call used first model, second call used second model
        calls = mock_acompletion.call_args_list
        assert calls[0].kwargs["model"] == "openai/gpt-4o"
        assert calls[1].kwargs["model"] == "deepseek/deepseek-coder"


class TestAllModelsExhausted:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_raises_provider_error_when_all_fail(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange — every model explodes
        mock_acompletion.side_effect = RuntimeError("Persistent failure")

        # Act & Assert
        with pytest.raises(ProviderError) as exc_info:
            await adapter.generate_structured(
                prompt="Generate", schema=DummySchema, priority_models=PRIORITY_MODELS
            )

        assert "All 2 model(s) failed" in str(exc_info.value)
        assert exc_info.value.__cause__ is not None
        assert mock_acompletion.await_count == 2

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_raises_provider_error_on_empty_model_list(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Act & Assert — zero models should also raise
        with pytest.raises(ProviderError) as exc_info:
            await adapter.generate_structured(
                prompt="Generate", schema=DummySchema, priority_models=[]
            )

        assert "All 0 model(s) failed" in str(exc_info.value)
        mock_acompletion.assert_not_awaited()


class TestStructuredResponseParsing:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_empty_content_raises_provider_error(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange — LLM returns empty string
        mock_acompletion.return_value = _fake_completion_response("")

        with pytest.raises(ProviderError, match="empty content"):
            await adapter.generate_structured(
                prompt="p", schema=DummySchema, priority_models=["openai:gpt-4o"]
            )

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_invalid_json_raises_provider_error(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        mock_acompletion.return_value = _fake_completion_response("not-json{{{")

        with pytest.raises(ProviderError, match="invalid JSON"):
            await adapter.generate_structured(
                prompt="p", schema=DummySchema, priority_models=["openai:gpt-4o"]
            )

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_schema_validation_failure_raises_provider_error(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange — valid JSON but wrong shape for DummySchema
        mock_acompletion.return_value = _fake_completion_response(json.dumps({"bad": "data"}))

        with pytest.raises(ProviderError, match="schema validation"):
            await adapter.generate_structured(
                prompt="p", schema=DummySchema, priority_models=["openai:gpt-4o"]
            )


# ══════════════════════════════════════════════════════════════
#  generate_with_tools
# ══════════════════════════════════════════════════════════════


class TestGenerateWithToolsSuccess:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_returns_content_when_no_tool_calls(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange
        mock_acompletion.return_value = _fake_completion_response("Done.", tool_calls=None)
        messages = [{"role": "user", "content": "Hello"}]

        # Act
        result = await adapter.generate_with_tools(
            messages=messages, tools=[], priority_models=["openai:gpt-4o"]
        )

        # Assert
        assert result["content"] == "Done."
        assert "tool_calls" not in result

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_returns_tool_calls_with_parsed_arguments(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        # Arrange
        tc = _fake_tool_call("call-1", "create_file", {"path": "/src/main.py", "content": "pass"})
        mock_acompletion.return_value = _fake_completion_response("Using tool", tool_calls=[tc])
        messages = [{"role": "user", "content": "Create a file"}]
        tools = [{"type": "function", "function": {"name": "create_file"}}]

        # Act
        result = await adapter.generate_with_tools(
            messages=messages, tools=tools, priority_models=["openai:gpt-4o"]
        )

        # Assert
        assert result["content"] == "Using tool"
        assert len(result["tool_calls"]) == 1
        tc_out = result["tool_calls"][0]
        assert tc_out["id"] == "call-1"
        assert tc_out["function"]["name"] == "create_file"
        assert tc_out["function"]["arguments"] == {"path": "/src/main.py", "content": "pass"}


class TestGenerateWithToolsFallback:
    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_all_models_fail_raises_provider_error(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        mock_acompletion.side_effect = RuntimeError("Timeout")

        with pytest.raises(ProviderError) as exc_info:
            await adapter.generate_with_tools(
                messages=[{"role": "user", "content": "x"}],
                tools=[],
                priority_models=PRIORITY_MODELS,
            )

        assert "All 2 model(s) failed" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch(
        "software_factory_poc.infrastructure.adapters.llm.litellm_brain_adapter.litellm.acompletion"
    )
    async def test_fallback_succeeds_on_second_model(
        self, mock_acompletion: AsyncMock, adapter: LiteLlmBrainAdapter
    ) -> None:
        mock_acompletion.side_effect = [
            RuntimeError("Rate limit"),
            _fake_completion_response("OK", tool_calls=None),
        ]

        result = await adapter.generate_with_tools(
            messages=[{"role": "user", "content": "x"}],
            tools=[],
            priority_models=PRIORITY_MODELS,
        )

        assert result["content"] == "OK"
        assert mock_acompletion.await_count == 2


# ══════════════════════════════════════════════════════════════
#  _normalize_model_id
# ══════════════════════════════════════════════════════════════


class TestNormalizeModelId:
    def test_replaces_colon_with_slash(self) -> None:
        assert _normalize_model_id("openai:gpt-4o") == "openai/gpt-4o"

    def test_only_first_colon_replaced(self) -> None:
        assert _normalize_model_id("a:b:c") == "a/b:c"

    def test_no_colon_unchanged(self) -> None:
        assert _normalize_model_id("gpt-4o") == "gpt-4o"


# ══════════════════════════════════════════════════════════════
#  Constructor / API key injection
# ══════════════════════════════════════════════════════════════


class TestApiKeyInjection:
    def test_injects_non_null_keys_into_environ(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — clean slate
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        settings = LlmSettings(
            OPENAI_API_KEY=SecretStr("sk-injected"),
            GEMINI_API_KEY=None,
            DEEPSEEK_API_KEY=None,
            ANTHROPIC_API_KEY=None,
        )

        # Act
        import os

        LiteLlmBrainAdapter(settings)

        # Assert
        assert os.environ["OPENAI_API_KEY"] == "sk-injected"
        assert "GEMINI_API_KEY" not in os.environ

    def test_adapter_is_brain_port(self, settings: LlmSettings) -> None:
        adapter = LiteLlmBrainAdapter(settings)
        assert isinstance(adapter, BrainPort)
