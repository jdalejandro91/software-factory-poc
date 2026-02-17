
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class LlmSettings(BaseSettings):
    """
    Settings for LLM Providers.
    """
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    deepseek_api_key: SecretStr | None = Field(default=None, alias="DEEPSEEK_API_KEY")
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    
    # Unified field: Upper uses allowed_models, Lower uses llm_allowed_models.
    # We prefer allowed_models but map both for safety or pick one.
    # ScaffoldingConfigLoader doesn't access this directly. AppConfig does.
    # Let's stick to the Upper naming (allowed_models) as it is cleaner, and fix usage in main_settings.py.
    allowed_models: list[str] = Field(default_factory=list, alias="LLM_ALLOWED_MODELS")

    model_config = SettingsConfigDict(
        env_file=".env", 
        extra="ignore"
    )

