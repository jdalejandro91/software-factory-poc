# 00_project_map.md — Cómo recorrer el repo (mapa mental en 2 minutos)

Objetivo: entender el PoC y ubicar “dónde va cada cosa” sin perderse.

## 1) Empieza por aquí (orden obligatorio)
1. README.md
   - Qué hace el PoC, quickstart, demo script.
2. ARCHITECTURE.md
   - Flujo end-to-end y reglas duras (no merge, no main writes, allowlists, idempotencia).
3. MODULES.md
   - Qué contiene cada carpeta/capa.
4. Código “core del flujo”:
   - src/software_factory_poc/orchestration/scaffold_orchestrator_service.py
5. Contratos:
   - src/software_factory_poc/contracts/scaffolding_contract_model.py
   - src/software_factory_poc/contracts/scaffolding_contract_parser_service.py
   - src/software_factory_poc/contracts/artifact_result_model.py
6. Integraciones:
   - src/software_factory_poc/integrations/jira/jira_client.py
   - src/software_factory_poc/integrations/gitlab/gitlab_client.py
7. Templates:
   - src/software_factory_poc/templates/template_renderer_service.py
   - src/software_factory_poc/templates/template_catalog/<template_id>/

## 2) “Lo que manda” en este repo
- El contract (entrada) y el artifact result (salida) son la fuente de verdad del flujo.
- El orchestrator define el orden y el comportamiento (happy path + fallos).
- Las integraciones NO toman decisiones de negocio.
- El renderer debe ser determinista (misma entrada -> misma salida).

## 3) Dónde agregar cosas (regla práctica)
- Nuevo endpoint: src/software_factory_poc/api/
- Nueva regla dura: src/software_factory_poc/policy/
- Nuevo campo del contract: src/software_factory_poc/contracts/
- Nueva integración externa: src/software_factory_poc/integrations/<tool>/
- Nuevo template: src/software_factory_poc/templates/template_catalog/<new_template>/
- Nuevo tipo de evidencia (store): src/software_factory_poc/store/

## 4) Qué NO hacer
- No crear nuevos módulos masivos.
- No introducir planner con LLM.
- No meter lógica de negocio en integrations/.
- No loggear secretos.
