from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from software_factory_poc.infrastructure.configuration.main_settings import Settings

api_key_header = APIKeyHeader(name="X-API-KEY", auto_error=False)

async def validate_api_key(api_key_header: str = Security(api_key_header)):
    settings = Settings()
    if not api_key_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    if api_key_header != settings.jira_webhook_secret.get_secret_value():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Could not validate credentials"
        )
    return api_key_header
