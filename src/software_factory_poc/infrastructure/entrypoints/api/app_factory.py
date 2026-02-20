import os

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from software_factory_poc.infrastructure.config.main_settings import Settings
from software_factory_poc.infrastructure.entrypoints.api.code_review_router import (
    router as code_review_router,
)
from software_factory_poc.infrastructure.entrypoints.api.health_router import (
    router as health_router,
)
from software_factory_poc.infrastructure.entrypoints.api.scaffolding_router import (
    router as scaffolding_router,
)
from software_factory_poc.infrastructure.observability import (
    configure_logging,
    get_logger,
)
from software_factory_poc.infrastructure.observability.logging import (
    CorrelationMiddleware,
)
from software_factory_poc.infrastructure.observability.tracing_setup import configure_tracing

configure_logging()
configure_tracing()

logger = get_logger(__name__)


def boot_diagnostics() -> None:
    try:
        _log_env_diagnostics()
    except Exception as exc:
        logger.error(
            "Error during boot diagnostics", error_type=type(exc).__name__, error_details=str(exc)
        )


def _log_env_diagnostics() -> None:
    """Check and log the presence of critical environment variables."""
    logger.info(">>> BOOT DIAGNOSTICS START <<<")
    critical_vars = [
        "OPENAI_API_KEY",
        "DEEPSEEK_API_KEY",
        "GEMINI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ARCHITECTURE_DOC_PAGE_ID",
        "CONFLUENCE_BASE_URL",
    ]
    for var_name in critical_vars:
        env_status = "PRESENT" if os.getenv(var_name) else "MISSING"
        logger.info("ENV check", env_var=var_name, env_status=env_status)
    logger.info(">>> BOOT DIAGNOSTICS END <<<")


def create_app(settings: Settings) -> FastAPI:
    configure_logging()
    configure_tracing()
    boot_diagnostics()
    logger.info("APP INITIALIZATION", app_name=settings.app_name)
    app = FastAPI(title=settings.app_name)
    app.add_middleware(CorrelationMiddleware)
    _register_exception_handlers(app)
    FastAPIInstrumentor.instrument_app(app)
    _register_routers(app)
    return app


def _register_exception_handlers(app: FastAPI) -> None:
    """Wire up custom exception handlers for the FastAPI application."""

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        error_details = exc.errors()
        logger.error(
            "Validation error",
            error_type="RequestValidationError",
            error_details=str(error_details),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": error_details, "body": str(exc.body)},
        )


def _register_routers(app: FastAPI) -> None:
    """Register all API routers with their prefixes."""
    app.include_router(health_router)
    app.include_router(scaffolding_router, prefix="/api/v1")
    app.include_router(code_review_router, prefix="/api/v1")
