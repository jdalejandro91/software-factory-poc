# 02_jira_integration.workflow.md — Jira integration (read issue + add comment)

## Objetivo
Implementar Jira client con dos operaciones:
- get_issue(issue_key)
- add_comment(issue_key, comment_body)

## Entradas
- JIRA_BASE_URL
- JIRA_AUTH_MODE (cloud_api_token | bearer | basic)
- JIRA_USER_EMAIL (si aplica)
- JIRA_API_TOKEN o JIRA_BEARER_TOKEN

## Archivos a crear/modificar
- src/software_factory_poc/integrations/jira/jira_client.py
- src/software_factory_poc/integrations/jira/jira_issue_mapper_service.py
- src/software_factory_poc/config/settings_pydantic.py
- tests/test_jira_client_stubbed.py (mock httpx)

## Pasos
1) Implementar JiraClient con httpx.
2) Implementar auth según modo (mínimo 1 modo para PoC).
3) Implementar get_issue: retornar JSON raw.
4) Implementar mapper: extraer description, summary y campos relevantes.
5) Implementar add_comment: POST comment.
6) Tests: mockear httpx para validar URL/headers.

## Criterios de aceptación
- JiraClient puede obtener un issue (manual test) o pasa tests stubbed
- JiraClient puede crear comentario (manual test) o pasa tests stubbed
- No se loggean secretos

## Comandos de validación
- uv run sf-poc-test
