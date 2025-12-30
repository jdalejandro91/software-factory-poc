from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.entrypoints.api.health_router import (
    router as health_router,
)
from software_factory_poc.infrastructure.entrypoints.api.jira_trigger_router import (
    router as jira_router,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)

def create_app(settings: Settings) -> FastAPI:
    logger.info("--- BOOT DIAGNOSTICS ---")
    logger.info(f"App Name: {settings.app_name}")
    logger.info(f"Env: {settings.env}")
    has_openai = bool(settings.llm_settings.openai_api_key)
    has_deepseek = bool(settings.llm_settings.deepseek_api_key)
    logger.info(f"LLM Keys Present: OpenAI={has_openai}, DeepSeek={has_deepseek}")
    logger.info("------------------------")

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
