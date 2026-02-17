import logging

import uvicorn

from software_factory_poc.infrastructure.configuration import Settings
from software_factory_poc.infrastructure.entrypoints.api.app_factory import create_app

logger = logging.getLogger(__name__)


def dev():
    """Entry point for development execution."""
    settings = Settings()
    
    # Use config from env or defaults
    port = 8000
    log_level = settings.log_level.lower() if hasattr(settings, "log_level") else "info"
    
    uvicorn.run(
        "software_factory_poc.main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=log_level
    )

# Instantiate global app for ASGI
settings = Settings()
app = create_app(settings)
