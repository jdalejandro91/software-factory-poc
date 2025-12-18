# 50_debug_playbook.md — Playbook de depuración (rápido y repetible)

## 1) Dónde mirar primero
1) Logs del servicio (buscar run_id y step_name)
2) runtime_data/ (stores JSON):
   - idempotency_store.json (o nombre que definas)
   - run_results.json (o nombre que definas)

## 2) Errores comunes y cómo reproducir
### A) No encuentra contract en Jira description
Síntoma:
- FAILED en step contract_parse_and_validate
Acción:
- Verifica delimitadores exactos:
  --- SCAFFOLDING_CONTRACT:v1 ---
  --- /SCAFFOLDING_CONTRACT ---
- Asegura que el bloque sea YAML válido

### B) Template no existe
Síntoma:
- FAILED en template_registry
Acción:
- Verifica carpeta:
  src/software_factory_poc/templates/template_catalog/<template_id>/
- Verifica template_manifest.yaml

### C) expected_paths falla
Síntoma:
- FAILED después de render
Acción:
- Ajustar manifest expected_paths o asegurar que .j2 renderiza el path correcto

### D) GitLab 401/403
Síntoma:
- FAILED en gitlab_* steps
Acción:
- Token con scopes mínimos correctos (api/write_repository según instancia)
- Confirmar project_id y base_branch
- Confirmar URL del GitLab (self-hosted vs gitlab.com)

### E) Jira 401/403
Síntoma:
- FAILED en jira_read_issue o jira_add_comment
Acción:
- Confirmar auth (email+api_token o bearer según Jira Cloud/DC)
- Confirmar endpoint base URL
- Confirmar permisos del usuario/bot

## 3) Cómo correr checks rápido
- Tests: `uv run sf-poc-test`
- Lint: `uv run sf-poc-lint`
- Servidor: `uv run sf-poc-dev`

## 4) Cómo aislar integraciones
- Para tests: usar mocks/stubs de Jira/GitLab (no pegar a internet)
- Para debug manual: usar curl con issue_key conocido

## 5) Regla de seguridad durante debug
- Nunca pegues en logs tokens/headers completos
- Usa redaction_service antes de imprimir payloads
