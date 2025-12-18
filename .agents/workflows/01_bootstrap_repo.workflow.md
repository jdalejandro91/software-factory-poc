# 01_bootstrap_repo.workflow.md — Bootstrap del repo (estructura + hello API)

## Objetivo
Dejar el repo ejecutable localmente: FastAPI arriba, healthcheck, configuración base, sin integrar Jira/GitLab todavía.

## Entradas
- Ninguna (solo repo vacío/estructura base)

## Archivos a crear/modificar
- src/software_factory_poc/main.py
- src/software_factory_poc/api/app_factory.py
- src/software_factory_poc/api/health_router.py
- src/software_factory_poc/config/settings_pydantic.py
- tests/test_health.py (opcional)

## Pasos
1) Implementar Settings mínimos (host/port/log_level).
2) Implementar create_app() y montar router health.
3) Implementar GET /health -> {"status":"ok"}.
4) Agregar scripts (sf-poc-run/sf-poc-dev) y probar.

## Criterios de aceptación
- `uv run sf-poc-dev` levanta servidor
- GET /health responde 200 y body esperado
- `uv run sf-poc-test` pasa

## Comandos de validación
- uv run sf-poc-dev
- curl http://localhost:8000/health
- uv run sf-poc-test
