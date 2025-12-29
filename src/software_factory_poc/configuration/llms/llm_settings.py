from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseSettings):
    # LLM Config
    openai_api_key: SecretStr | None = None
    llm_allowed_models: list[str] = Field(
        default=[
            "openai:gpt-4-turbo",
            "openai:gpt-4o",
            "deepseek:deepseek-coder",
            "anthropic:claude-3-5-sonnet-20240620",
        ]
    )

    def validate_openai_credentials(self) -> None:
        if not self.openai_api_key:
            raise ValueError("OpenAI API Key is required for AI generation features.")

    model_config = SettingsConfigDict(env_file=None, extra="ignore")
