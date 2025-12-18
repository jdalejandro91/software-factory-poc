from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from software_factory_poc.observability.logger_factory_service import build_logger

from software_factory_poc.api.health_router import router as health_router
from software_factory_poc.api.jira_trigger_router import router as jira_router
from software_factory_poc.config.settings_pydantic import Settings

logger = build_logger(__name__)

def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(title=settings.app_name)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(f"Validation error for request {request.url}: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors(), "body": exc.body},
        )
    
    app.include_router(health_router)
    app.include_router(jira_router, prefix="/api/v1")
    
    return app
