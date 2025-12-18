# MODULES.md — Mapa de módulos/capas del PoC (sin DDD purista)

Este PoC prioriza velocidad + claridad. Mantiene separación básica por capas y contratos claros. :contentReference[oaicite:21]{index=21}

## src/software_factory_poc/main.py
- Composition root:
  - carga Settings
  - crea FastAPI app
  - conecta routers

## src/software_factory_poc/api/
- Responsabilidad: HTTP boundary
- Contiene:
  - app_factory.py (create_app)
  - health_router.py (GET /health)
  - jira_trigger_router.py (POST /jira/scaffold-trigger)
- No contiene:
  - llamadas directas a Jira/GitLab
  - render de templates
  - reglas de negocio

## src/software_factory_poc/config/
- Responsabilidad: configuración tipada
- Contiene:
  - settings_pydantic.py (URLs, tokens, allowlists, template root, base branch)
  - allowlists_config.py (allowlists PoC desde ENV o defaults)
- Regla:
  - ningún módulo debe leer env vars directamente: siempre vía Settings

## src/software_factory_poc/contracts/
- Responsabilidad: “contratos” del flujo
- Contiene:
  - scaffolding_contract_model.py (Pydantic del contract)
  - scaffolding_contract_parser_service.py (extrae bloque delimitado)
  - artifact_result_model.py (salida final para API + store)

## src/software_factory_poc/orchestration/
- Responsabilidad: use-case PoC end-to-end
- Contiene:
  - scaffold_orchestrator_service.py (execute(issue_key) -> ArtifactResult)
  - step_runner_service.py (ejecuta steps con logs consistentes)
- Regla:
  - aquí se aplica el orden del flujo y el manejo de errores por step :contentReference[oaicite:22]{index=22}

## src/software_factory_poc/policy/
- Responsabilidad: reglas duras PoC
- Contiene:
  - poc_policy_service.py (allowlists, no merge, no writes a main)
- No contiene:
  - lógica HTTP
  - lógica de integración

## src/software_factory_poc/integrations/
- Responsabilidad: adaptadores HTTP externos
- Contiene:
  - jira/jira_client.py + mapper de issue relevante
  - gitlab/gitlab_client.py + payload builder + result mapper
- Regla:
  - ningún “if de negocio” aquí; solo llamadas y mapeos

## src/software_factory_poc/templates/
- Responsabilidad: scaffolding determinista
- Contiene:
  - template_registry_service.py (template_id -> carpeta)
  - template_manifest_model.py (expected_paths + variables + version)
  - template_renderer_service.py (Jinja -> dict[path]=content)
  - template_file_loader_service.py (carga .j2 del disco)
  - template_catalog/ (plantillas locales versionadas)

## src/software_factory_poc/store/
- Responsabilidad: persistencia mínima
- Contiene:
  - idempotency_key_builder_service.py
  - idempotency_store_file_adapter.py (key->mr_url)
  - run_result_store_file_adapter.py (run_id->resultado)

## src/software_factory_poc/observability/
- Responsabilidad: logs + redacción
- Contiene:
  - logger_factory_service.py (logger con run_id/step/issue_key)
  - redaction_service.py (oculta tokens/secrets)

## src/software_factory_poc/utils/
- Responsabilidad: helpers concretos
- Contiene:
  - time_service.py
  - slugify_service.py

## tests/
- Responsabilidad: pruebas mínimas de lo crítico
- Enfoque:
  - parser/validation de contract
  - renderer (expected_paths)
  - orchestrator (happy path + fallos principales)
