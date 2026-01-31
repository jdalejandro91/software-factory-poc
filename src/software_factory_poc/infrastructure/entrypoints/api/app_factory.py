import os

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


def boot_diagnostics():
    try:
        logger.info(">>> BOOT DIAGNOSTICS START <<<")
        critical_vars = [
            "OPENAI_API_KEY", "DEEPSEEK_API_KEY",
            "GEMINI_API_KEY", "ANTHROPIC_API_KEY",
            "ARCHITECTURE_DOC_PAGE_ID", "CONFLUENCE_BASE_URL"
        ]
        for k in critical_vars:
            val = os.getenv(k)
            status = "PRESENT" if val else "MISSING"
            logger.info(f"ENV: {k:<30} = {status}")
        logger.info(">>> BOOT DIAGNOSTICS END <<<")
    except Exception as e:
        logger.error(f"Error during boot diagnostics: {e}")


def create_app(settings: Settings) -> FastAPI:
    # 1. CRITICAL: Configure Root Logger so INFO logs appear in Docker console
    LoggerFactoryService.configure_root_logger()

    boot_diagnostics()

    logger.info(f"--- APP INITIALIZATION: {settings.app_name} ---")

    app = FastAPI(title=settings.app_name)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_details = exc.errors()
        logger.error(f"Validation error: {error_details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": error_details, "body": str(exc.body)},
        )

    app.include_router(health_router)
    app.include_router(jira_router, prefix="/api/v1")

    return app