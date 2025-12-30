from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseSettings):
    openai_api_key: SecretStr | None = None
    deepseek_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    anthropic_api_key: SecretStr | None = None
    llm_allowed_models: list[str] = Field(default_factory=list)

    model_config = SettingsConfigDict(env_file=None, extra="ignore")
