from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class ConfluenceSettings(BaseSettings):
    """
    Settings for Confluence integration.
    """
    user_email: str = Field(..., description="Confluence User Email")
    api_token: SecretStr = Field(..., description="Confluence API Token")
    base_url: str = Field(..., description="Confluence Base URL")
    architecture_doc_page_id: str = Field(default="3571713", description="Page ID for architecture docs", alias="ARCHITECTURE_DOC_PAGE_ID")

    model_config = SettingsConfigDict(
        env_prefix="CONFLUENCE_",
        case_sensitive=True, 
        extra="ignore"
    )
