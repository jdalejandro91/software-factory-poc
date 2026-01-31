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
    """
    Imprime un diagnóstico directo de las variables de entorno a stderr.
    Esto es crucial para verificar la inyección de secretos en Docker/EC2
    sin depender de que Pydantic esté configurado correctamente.
    """
    try:

        logger.info(">>> BOOT DIAGNOSTICS START (Direct Env Check) <<<")
        
        # Lista de variables críticas a verificar
        critical_vars = [
            "OPENAI_API_KEY", 
            "DEEPSEEK_API_KEY", 
            "GEMINI_API_KEY",
            "ANTHROPIC_API_KEY",
            "SCAFFOLDING_LLM_MODEL_PRIORITY",
            "VCS_PROVIDER",
            "TRACKER_PROVIDER"
        ]
        
        for k in critical_vars:
            val = os.getenv(k)
            if val:
                # Sanitización segura: solo mostrar existencia o longitud
                logger.info(f"ENV: {k:<30} = PRESENT (Len={len(val)})")
            else:
                logger.warning(f"ENV: {k:<30} = MISSING")
                
        logger.info(">>> BOOT DIAGNOSTICS END <<<")
    except Exception as e:
        logger.error(f"Error during boot diagnostics: {e}")

def create_app(settings: Settings) -> FastAPI:
    # 1. Ejecutar diagnósticos de bajo nivel primero
    boot_diagnostics()

    logger.info("--- APP INITIALIZATION ---")
    logger.info(f"App Name: {settings.app_name}")
    # CORRECCIÓN: 'env' no existe en Settings, usamos os.getenv o default
    env_name = os.getenv("ENV", "production") 
    logger.info(f"Environment: {env_name}")
    
    # CORRECCIÓN: Settings hereda de LlmSettings, acceso directo a los atributos
    has_openai = bool(settings.openai_api_key)
    has_deepseek = bool(settings.deepseek_api_key)
    logger.info(f"Pydantic Settings Loaded: OpenAI={has_openai}, DeepSeek={has_deepseek}")
    logger.info("------------------------")

    app = FastAPI(title=settings.app_name)
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        error_details = exc.errors()
        logger.error(f"Validation error for request {request.url}: {error_details}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": error_details, "body": str(exc.body)},
        )
    
    app.include_router(health_router)
    app.include_router(jira_router, prefix="/api/v1")
    
    return app
