import json

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseSettings):
    """Settings for LLM Providers and model priority configuration."""

    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: SecretStr | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")

    allowed_models: list[str] = Field(default_factory=list, alias="LLM_ALLOWED_MODELS")
    scaffolding_llm_model_priority: list[str] = Field(
        default_factory=list, alias="SCAFFOLDING_LLM_MODEL_PRIORITY"
    )
    code_review_llm_model_priority: list[str] = Field(
        default_factory=list, alias="CODE_REVIEW_LLM_MODEL_PRIORITY"
    )

    @field_validator(
        "allowed_models",
        "scaffolding_llm_model_priority",
        "code_review_llm_model_priority",
        mode="before",
    )
    @classmethod
    def parse_json_list(cls, value: object) -> list[str]:
        """Accept both raw JSON strings and native lists from .env or direct injection."""
        if isinstance(value, str):
            parsed = json.loads(value)
            if not isinstance(parsed, list):
                raise ValueError(f"Expected a JSON list, got {type(parsed).__name__}")
            return parsed
        if isinstance(value, list):
            return value
        raise ValueError(f"Expected str or list, got {type(value).__name__}")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )
