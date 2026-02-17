"""Integration tests — verify DI wiring produces a working LiteLlmBrainAdapter."""

import pytest
from pydantic import SecretStr

from software_factory_poc.core.application.ports.brain_port import BrainPort
from software_factory_poc.infrastructure.tools.llm.config.llm_settings import LlmSettings
from software_factory_poc.infrastructure.tools.llm.litellm_brain_adapter import (
    LiteLlmBrainAdapter,
)


class TestLlmSettingsFromEnv:
    """Verify LlmSettings loads and parses JSON lists from env vars."""

    def test_parses_json_list_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — simulate .env values injected via monkeypatch
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")
        monkeypatch.setenv("GEMINI_API_KEY", "gem-test-456")
        monkeypatch.setenv("DEEPSEEK_API_KEY", "ds-test-789")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "ant-test-000")
        monkeypatch.setenv(
            "LLM_ALLOWED_MODELS",
            '["openai:gpt-4o", "deepseek:deepseek-coder"]',
        )
        monkeypatch.setenv(
            "SCAFFOLDING_LLM_MODEL_PRIORITY",
            '["gemini:gemini-1.5-pro", "openai:gpt-4o"]',
        )
        monkeypatch.setenv(
            "CODE_REVIEW_LLM_MODEL_PRIORITY",
            '["openai:gpt-4-turbo"]',
        )

        # Act — build from env (no .env file needed, monkeypatch covers it)
        settings = LlmSettings()

        # Assert — API keys are SecretStr
        assert settings.openai_api_key is not None
        assert settings.openai_api_key.get_secret_value() == "sk-test-123"

        # Assert — JSON lists parsed correctly
        assert settings.allowed_models == ["openai:gpt-4o", "deepseek:deepseek-coder"]
        assert settings.scaffolding_llm_model_priority == [
            "gemini:gemini-1.5-pro",
            "openai:gpt-4o",
        ]
        assert settings.code_review_llm_model_priority == ["openai:gpt-4-turbo"]

    def test_defaults_to_empty_lists_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange — clear all LLM env vars AND disable .env file reading
        for var in (
            "LLM_ALLOWED_MODELS",
            "SCAFFOLDING_LLM_MODEL_PRIORITY",
            "CODE_REVIEW_LLM_MODEL_PRIORITY",
            "OPENAI_API_KEY",
            "GEMINI_API_KEY",
            "DEEPSEEK_API_KEY",
            "ANTHROPIC_API_KEY",
        ):
            monkeypatch.delenv(var, raising=False)

        # Act — _env_file=None prevents reading from .env on disk
        settings = LlmSettings(_env_file=None)  # type: ignore[call-arg]

        # Assert
        assert settings.allowed_models == []
        assert settings.scaffolding_llm_model_priority == []
        assert settings.openai_api_key is None


class TestBrainPortWiring:
    """Verify that building LiteLlmBrainAdapter through LlmSettings yields a valid BrainPort."""

    def test_adapter_from_settings_is_brain_port(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Arrange
        monkeypatch.setenv("OPENAI_API_KEY", "sk-wiring-test")
        monkeypatch.setenv("LLM_ALLOWED_MODELS", '["openai:gpt-4o"]')
        monkeypatch.setenv("SCAFFOLDING_LLM_MODEL_PRIORITY", '["openai:gpt-4o"]')
        monkeypatch.setenv("CODE_REVIEW_LLM_MODEL_PRIORITY", '["openai:gpt-4o"]')

        settings = LlmSettings()

        # Act
        adapter = LiteLlmBrainAdapter(settings)

        # Assert
        assert isinstance(adapter, BrainPort)
        assert isinstance(adapter, LiteLlmBrainAdapter)

    def test_native_list_injection_without_json_string(self) -> None:
        """Verify LlmSettings accepts native Python lists (not just JSON strings)."""
        settings = LlmSettings(
            OPENAI_API_KEY=SecretStr("sk-direct"),
            LLM_ALLOWED_MODELS=["openai:gpt-4o", "deepseek:deepseek-coder"],
            SCAFFOLDING_LLM_MODEL_PRIORITY=["openai:gpt-4o"],
            CODE_REVIEW_LLM_MODEL_PRIORITY=["openai:gpt-4-turbo"],
        )

        assert settings.allowed_models == ["openai:gpt-4o", "deepseek:deepseek-coder"]

        adapter = LiteLlmBrainAdapter(settings)
        assert isinstance(adapter, BrainPort)
