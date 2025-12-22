# 05_gitlab_integration.workflow.md — GitLab (branch + commit multi-file + MR)

## Objetivo
Implementar GitLab client para:
- create_branch(project_id, branch_name, ref)
- commit_files(project_id, branch_name, files_map, commit_message)
- create_merge_request(project_id, source_branch, target_branch, title, description)

## Entradas
- GITLAB_BASE_URL
- GITLAB_TOKEN (bot)
- project_id, base_branch, branch_name
- files_map[path]=content

## Archivos a crear/modificar
- src/software_factory_poc/integrations/gitlab/gitlab_client.py
- src/software_factory_poc/integrations/gitlab/gitlab_payload_builder_service.py
- src/software_factory_poc/integrations/gitlab/gitlab_result_mapper_service.py
- src/software_factory_poc/config/settings_pydantic.py
- tests/test_gitlab_client_stubbed.py (mock httpx)

## Pasos
1) Implementar GitLabClient con httpx.
2) Implementar create_branch:
   - manejar “branch exists” como caso controlado si aplica
3) Implementar commit multi-file:
   - usar API commits con actions (create)
4) Implementar create MR:
   - title y description deben incluir issue_key y run_id
5) Tests stubbed:
   - validar endpoint paths, headers, payload shapes

## Criterios de aceptación
- Con mocks, se valida payload correcto y orden de llamadas
- Errores GitLab se convierten en error safe para Jira comment
- No se loggean secretos

## Comandos de validación
- uv run sf-poc-test
