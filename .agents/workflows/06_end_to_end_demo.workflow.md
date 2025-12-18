# 06_end_to_end_demo.workflow.md — End-to-end demo (issue -> MR -> comment)

## Objetivo
Implementar el orchestrator completo y demostrar el flujo en < 3 minutos.

## Entradas
- issue_key real o simulado
- Jira + GitLab configurados
- template_id existente en template_catalog

## Archivos a crear/modificar
- src/software_factory_poc/orchestration/scaffold_orchestrator_service.py
- src/software_factory_poc/orchestration/step_runner_service.py
- src/software_factory_poc/api/jira_trigger_router.py
- src/software_factory_poc/policy/poc_policy_service.py
- src/software_factory_poc/store/idempotency_* + run_result_store_*
- src/software_factory_poc/observability/logger_factory_service.py
- src/software_factory_poc/observability/redaction_service.py
- tests/test_orchestrator_happy_path.py
- tests/test_orchestrator_invalid_contract.py
- tests/test_orchestrator_gitlab_failure.py

## Pasos
1) Implementar run_id generator (estable y visible).
2) Implementar step runner:
   - log start/end por step
   - captura errores con contexto (safe)
3) Implementar policy checks:
   - allowlists (template_id, project_id, base_branch)
   - no merge, no main writes
4) Implementar idempotencia store:
   - check key
   - si existe => DUPLICATE + comentar Jira con MR existente
5) Orchestrator happy path:
   - jira read -> contract parse -> template render -> gitlab -> jira comment -> store result
6) Orchestrator fallos:
   - contract inválido => comentar Jira y salir sin tocar GitLab
   - gitlab falla => comentar Jira diagnóstico y marcar FAILED

## Criterios de aceptación (ver 40_definition_of_done.md)
- Happy path COMPLETED: MR + comentario Jira + run_id
- Contract inválido: no GitLab, sí comentario
- GitLab failure: comentario + FAILED
- Idempotencia: DUPLICATE no crea MR nuevo

## Comandos de validación
- uv run sf-poc-test
- uv run sf-poc-dev
- curl -X POST http://localhost:8000/jira/scaffold-trigger -H "Content-Type: application/json" -d '{"issue_key":"ABC-123"}'
