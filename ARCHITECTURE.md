# ARCHITECTURE.md — Arquitectura PoC (1 sprint)

## 1) Objetivo arquitectónico
Probar el flujo end-to-end, con código legible, contratos claros, idempotencia simple y evidencia mínima (`run_id`). :contentReference[oaicite:15]{index=15}

## 2) Flujo end-to-end (secuencia)
Trigger externo (ideal: Jira Automation) -> Servicio PoC:
1) POST /jira/scaffold-trigger (issue_key)
2) Jira read: get issue -> description + fields
3) Parse & validate: extraer Scaffolding Contract desde descripción (bloque delimitado) + validación Pydantic
4) Idempotencia: key = issue_key + contract_version + template_version
   - Si existe: marcar DUPLICATE y comentar Jira con MR existente
5) Policy checks (“reglas duras”)
6) Render determinista desde plantilla local:
   - template_id -> carpeta local
   - render -> dict[path] = content
   - validar expected_paths del manifest
7) GitLab:
   - create branch scaffold/<issueKey>-<slug>
   - commit multi-file (acciones create)
   - create MR (no merge)
8) Jira write:
   - add comment con MR link + resumen + próximos pasos
9) Persistencia mínima:
   - store idempotency key -> MR url
   - store run_id -> resultado (status, errores) :contentReference[oaicite:16]{index=16}

## 3) Reglas duras (obligatorias)
Estas reglas viven como checks simples (PoC) antes de tocar GitLab:
- Nunca commitear en main
- Nunca hacer merge (solo MR)
- Solo repos allowlisted
- Solo templates allowlisted :contentReference[oaicite:17]{index=17}

## 4) Capas (dependencias permitidas)
Regla: `api -> orchestration -> (integrations, templates, store, policy)`

- api
  - SOLO HTTP (FastAPI): request/response y validación superficial
  - NO lógica de negocio

- orchestration
  - Orquesta el flujo (use-case PoC)
  - Decide orden de steps, manejo de errores y logging

- contracts
  - Define el contract de entrada y el resultado final (modelos Pydantic)
  - Parser del bloque en Jira description

- policy
  - Implementa checks “duros” PoC (allowlists, no-merge, no-writes a main)

- integrations
  - Jira/GitLab clients (HTTP) + mappers/payload builders
  - NO reglas de negocio

- templates
  - Registro de templates locales + manifest + renderer determinista

- store
  - Persistencia mínima (archivo JSON) para idempotencia y resultados por run

- observability
  - Logger consistente (run_id, step_name, issue_key) + redacción

- utils
  - Helpers pequeños y testeables (time, slugify)

## 5) Manejo de fallos (filosofía PoC)
- Si falla Jira read: FAILED y log; comentar Jira solo si es posible (depende del fallo).
- Si contract inválido: FAILED, comentar Jira con lista de errores, no tocar GitLab. :contentReference[oaicite:18]{index=18}
- Si falla GitLab: FAILED, comentar Jira con diagnóstico sin exponer secretos. :contentReference[oaicite:19]{index=19}
- Si ya existía idempotencia key: DUPLICATE, comentar Jira con MR existente. :contentReference[oaicite:20]{index=20}

## 6) Idempotencia (simple, suficiente para PoC)
- Key: issue_key + contract_version + template_version
- Store: archivo JSON (rápido para 1 sprint)
- El key builder debe ser estable y testeable.

## 7) Evidencia mínima
- Todos los runs deben tener `run_id`
- Logs estructurados por step (jira_read, contract_parse, policy, render, gitlab_branch, gitlab_commit, gitlab_mr, jira_comment)
- Guardar resultado final por run_id (para demo y debugging)
