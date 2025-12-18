# 30_mvp_flow_contract.md — Contrato del flujo PoC (inputs/outputs por step)

Objetivo: que el flujo sea 100% reproducible y verificable, sin “adivinar”.

## 1) Input del endpoint
Endpoint: POST /jira/scaffold-trigger
Body JSON:
- issue_key: string (obligatorio)
- event_id: string (opcional) -> para deduplicación externa si se desea

## 2) Scaffolding Contract (dentro del issue description)
Formato recomendado: bloque YAML delimitado.

Delimitadores (exactos):
--- SCAFFOLDING_CONTRACT:v1 ---
<yaml>
--- /SCAFFOLDING_CONTRACT ---

Campos mínimos (v1):
- contract_version: "1"
- template_id: string (debe existir en template_catalog/)
- service_slug: string (se usa en branch name / naming)
- gitlab:
  - project_id: int
  - target_base_branch: string (ej: main)
- jira:
  - comment_visibility: "public" | "internal" (PoC puede ignorar o mapear)
- vars: objeto libre (solo variables soportadas por el template)

## 3) Template manifest (en template_catalog/<template_id>/template_manifest.yaml)
Campos mínimos:
- template_version: "1"
- expected_paths: lista de rutas que deben existir tras render
- supported_vars: lista de vars soportadas (documentación)
- description: string corta

## 4) Output final (ArtifactResult)
El orchestrator debe devolver:
- run_id: string
- status: COMPLETED | FAILED | DUPLICATE
- issue_key: string
- mr_url: string | null
- branch_name: string | null
- jira_comment_id: string | null
- error_summary: string | null  (safe)

## 5) Steps obligatorios (orden)
step: jira_read_issue
- input: issue_key
- output: issue_data (description + summary + fields)

step: contract_parse_and_validate
- input: issue_data.description
- output: scaffolding_contract_model

step: idempotency_check
- input: issue_key + contract_version + template_version
- output: continue | DUPLICATE(existing_mr_url)

step: policy_checks
- input: contract + allowlists
- output: ok | FAILED(reason)

step: template_render
- input: template_id + vars
- output: files_map[path]=content + validated_expected_paths

step: gitlab_branch_create
- input: project_id + branch_name + base_branch
- output: branch created

step: gitlab_commit_multi_file
- input: branch_name + files_map
- output: commit sha

step: gitlab_mr_create
- input: source_branch + target_base_branch + title/description
- output: mr_url

step: jira_add_comment
- input: issue_key + comment_body(mr_url + summary + run_id)
- output: jira_comment_id

## 6) Fallos esperados (comportamiento)
- Contract inválido:
  - NO tocar GitLab
  - comentar Jira con lista de errores (safe)
- GitLab falla:
  - status FAILED
  - comentar Jira con diagnóstico safe
- Idempotencia DUPLICATE:
  - no crear MR
  - comentar Jira con MR existente
