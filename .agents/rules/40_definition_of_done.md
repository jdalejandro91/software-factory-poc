# 40_definition_of_done.md — Definition of Done (PoC)

El PoC se considera “DONE” cuando cumple lo siguiente:

## 1) Happy path (obligatorio)
Dado un issue con contract válido:
- Se crea un branch scaffold/<issueKey>-<slug>
- Se commitean múltiples archivos de scaffolding (desde template local)
- Se crea un Merge Request (sin merge automático)
- Se agrega comentario en Jira con:
  - link del MR
  - run_id
  - resumen safe (sin secretos)
- El endpoint responde COMPLETED con mr_url y jira_comment_id

## 2) Contract inválido (obligatorio)
Dado un issue con contract inválido:
- NO se llama a GitLab
- Se comenta Jira con:
  - “Contract inválido”
  - lista de errores de validación
  - run_id
- El endpoint responde FAILED con error_summary

## 3) GitLab falla (obligatorio)
Simular fallo GitLab:
- Se comenta Jira con diagnóstico safe
- El endpoint responde FAILED
- Queda evidencia en store/run_result

## 4) Idempotencia (obligatorio)
Re-ejecutar el mismo issue_key + contract_version + template_version:
- NO crea segundo MR
- Responde DUPLICATE con mr_url existente
- Comenta Jira indicando “ya existía MR”

## 5) Tests mínimos (obligatorio)
- Parser de contract (casos borde)
- Validación Pydantic
- Renderer determinista + expected_paths
- Orchestrator: happy + invalid contract + gitlab failure

## 6) Demo en < 3 minutos
Desde trigger (manual o Jira Automation) a MR + comentario en Jira, sin pasos manuales extra.
