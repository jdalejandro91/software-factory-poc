import uvicorn

from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.entrypoints.api.app_factory import create_app


def dev():
    """Run the development server."""
    # We will let uvicorn handle the reloading if run via CLI, 
    # but here is a programmatic entry point
    settings = Settings()
    uvicorn.run(
        "software_factory_poc.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )

# Instantiate global app for ASGI
settings = Settings()
app = create_app(settings)
