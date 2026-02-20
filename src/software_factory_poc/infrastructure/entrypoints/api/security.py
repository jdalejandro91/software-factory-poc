from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from software_factory_poc.infrastructure.tools.tracker.jira.config.jira_settings import (
    JiraSettings,
)

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)


async def validate_api_key(api_key_header: str = Security(api_key_header)) -> str:
    settings = JiraSettings()
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    if not settings.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook secret not configured",
        )
    if api_key_header != settings.webhook_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    return api_key_header
