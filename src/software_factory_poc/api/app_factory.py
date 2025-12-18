from fastapi import FastAPI

from software_factory_poc.api.health_router import router as health_router
from software_factory_poc.api.jira_trigger_router import router as jira_router
from software_factory_poc.config.settings_pydantic import Settings


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    
    app.include_router(health_router)
    app.include_router(jira_router)
    
    return app
