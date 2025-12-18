# 10_style_conventions.md — Convenciones (para legibilidad + orientación rápida)

## 1) Reglas de organización
- 1 clase por archivo.
- 1 enum por archivo.
- Evitar archivos contenedores gigantes (entities.py / models.py / utils.py genérico).
- Evitar carpetas con 50 archivos sin agrupación: agrupa por intención (api, contracts, integrations, templates, etc.).

## 2) Sufijos obligatorios de archivos
- *_router.py            -> endpoints HTTP (FastAPI routers)
- *_service.py           -> lógica orquestada o utilitaria con responsabilidad clara
- *_client.py            -> cliente HTTP para herramientas externas (Jira/GitLab)
- *_adapter.py           -> adaptador de persistencia/IO (file store, etc.)
- *_model.py             -> modelos Pydantic / DTOs del contract o resultados
- *_mapper_service.py    -> mapeo de responses externas a estructuras internas
- *_builder_service.py   -> construcción de payloads (GitLab commit/MR)
- *_enum.py              -> enums explícitos
- *_vo.py                -> value objects (si aparecen en PoC)
- *_event.py             -> eventos (si aparecen en PoC)

## 3) Convenciones de nombres
- snake_case para funciones y variables.
- UpperCamelCase para clases.
- Constantes en UPPER_CASE.

## 4) Logging (consistencia)
- Siempre incluir: run_id, issue_key, step_name.
- No loggear payloads crudos si incluyen tokens/headers: usar redaction_service.

## 5) Tests (mínimo, pero útil)
- Tests deben centrarse en:
  - parsing + validación del contract
  - renderer determinista + expected_paths
  - orchestrator: happy path + 2 fallos principales
- Los tests NO deben pegar a Jira/GitLab reales: usar stubs/mocks.
