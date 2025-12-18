# Software Factory PoC

## Descripción
Este proyecto es una Prueba de Concepto (PoC) para una "Software Factory" automatizada. Su objetivo es demostrar cómo se pueden integrar agentes de IA, herramientas de desarrollo y flujos de trabajo automatizados para acelerar la creación de software.

## Objetivo
Cuando un issue de Jira cumple un “Scaffolding Contract”, este servicio genera scaffolding desde una plantilla local (determinista), crea un Merge Request en GitLab y comenta el issue con un resumen + link al MR, dejando evidencia mínima con `run_id`.
## Qué demuestra (en demo)
End-to-end:
1) Jira Automation dispara un webhook al servicio
2) El servicio lee el issue, extrae y valida un Scaffolding Contract
3) Renderiza scaffolding desde plantilla local (determinista)
4) GitLab: crea branch + commit multi-archivo + Merge Request
5) Jira: publica comentario con resumen + link al MR
6) Registra evidencia mínima (logs + run_id) y maneja fallos explicables :contentReference[oaicite:2]{index=2}

## Alcance PoC (IN / OUT)
IN:
- 1 endpoint REST: `POST /jira/scaffold-trigger`
- Parser del contract (bloque delimitado en la descripción)
- Validación del contract (Pydantic)
- Render determinista de plantilla local
- GitLab: create branch, commit multi-file, create MR
- Jira: comment con resumen + link MR
- Idempotencia simple por `issueKey + contract_version + template_version`
- Logs estructurados con `run_id` :contentReference[oaicite:3]{index=3}

OUT:
- MCP server completo (opcional; no necesario para la PoC)
- RAG / knowledge corporativo complejo
- Motor de planes con LLM (innecesario; aquí el plan es fijo)
- Políticas enterprise completas (se simulan con “reglas duras”) :contentReference[oaicite:4]{index=4}

## Requisitos
- Python 3.12.x (ver `.python-version`)
- Acceso a Jira (Cloud o DC/Server) con credenciales REST (read issue + add comment)
- Acceso a GitLab con token de bot (permisos mínimos) :contentReference[oaicite:5]{index=5}

## Quickstart (local)
### 1) Crear entorno e instalar dependencias
Opción A (uv recomendado):
1. `uv venv`
2. `uv pip install -e ".[dev]"`
3. `cp .env.example .env`  (crea el archivo si aún no existe)
4. Edita `.env` con tus valores

Opción B (pip):
1. `python -m venv .venv`
2. Activa el venv
3. `pip install -e ".[dev]"`
4. `cp .env.example .env`
5. Edita `.env`

### 2) Ejecutar el servicio
- `uv run sf-poc-dev`
o
- `uv run sf-poc-run`

Verifica:
- `GET http://localhost:8000/health`

### 3) Lint / format / tests
- `uv run sf-poc-lint`
- `uv run sf-poc-format`
- `uv run sf-poc-test`

## Endpoint principal
### POST /jira/scaffold-trigger
Body (JSON):
```json
{
  "issue_key": "ABC-123",
  "event_id": "optional-string-from-jira"
}
Respuesta (ejemplo):

json
Copiar código
{
  "run_id": "01J...XYZ",
  "status": "COMPLETED",
  "issue_key": "ABC-123",
  "mr_url": "https://gitlab.example.com/group/repo/-/merge_requests/12",
  "branch_name": "scaffold/ABC-123-invoice-service",
  "jira_comment_id": "123456"
}
Demo script (paso a paso)
Objetivo: que en 2–3 minutos exista MR en GitLab y comentario en Jira con link y resumen. 
Prueba de concepto


Paso 0 — Preparar Jira Automation
Crea una regla (Jira Automation):

Trigger: Issue created o transición a estado “Ready for scaffolding”

Action: “Send web request” a:

POST https://<tu-host>/jira/scaffold-trigger

body: { "issue_key": "{{issue.key}}" }
(En PoC, basta con dispararlo manualmente con curl si aún no configuras Jira Automation.)

Paso 1 — Crear un issue “scaffold-ready”
Crea un issue en Jira y pega en la descripción un bloque delimitado con el contract.

Ejemplo (bloque YAML recomendado):

yaml
Copiar código
--- SCAFFOLDING_CONTRACT:v1 ---
contract_version: "1"
template_id: "corp_nodejs_api"
service_slug: "invoice-service"
gitlab:
  project_id: 123
  target_base_branch: "main"
jira:
  comment_visibility: "public"
vars:
  owner_team: "payments"
  runtime: "nodejs"
  port: 3000
--- /SCAFFOLDING_CONTRACT ---
Paso 2 — Disparar el flujo
Opción A: transiciona el issue a “Ready for scaffolding” (si ya tienes regla).
Opción B: dispara manualmente:

curl -X POST http://localhost:8000/jira/scaffold-trigger -H "Content-Type: application/json" -d '{"issue_key":"ABC-123"}'

Paso 3 — Validar resultados
Ver en logs el run_id y pasos.

Ver MR creado (branch scaffold/<issueKey>-<slug>).

Ver comentario en Jira con:

Link al MR

Resumen del scaffolding

Próximos pasos 
Prueba de concepto


Reglas duras (PoC)
Nunca commitear directamente en main

Nunca hacer merge (solo abrir MR)

Solo repos allowlisted

Solo templates allowlisted 
Prueba de concepto


Estructura del repo (alto nivel)
Lee:

ARCHITECTURE.md (flujo end-to-end + reglas duras)

MODULES.md (qué vive en cada capa)

AGENTS.md (cómo deben operar los agentes de Antigravity en este repo)

Notas operativas
Idempotencia: issue_key + contract_version + template_version evita duplicar MRs. 
Prueba de concepto


Si GitLab falla, el run debe quedar en FAILED y el comentario en Jira debe explicar el diagnóstico sin exponer secretos. 
Prueba de concepto


yaml
Copiar código

---

## AGENTS.md

```md
# AGENTS.md — Reglas para agentes (Antigravity) en este repo

Este repo es una PoC de 1 sprint. El objetivo es un flujo end-to-end entendible y demostrable (Jira -> Contract -> Template -> GitLab MR -> Jira comment + run_id).

## 1) Orden de lectura (no improvisar)
1. README.md (quickstart + demo script)
2. ARCHITECTURE.md (flujo + reglas duras)
3. MODULES.md (mapa de módulos/capas)
4. src/software_factory_poc/orchestration/scaffold_orchestrator_service.py (corazón del flujo)
5. src/software_factory_poc/contracts (contract y parser)
6. src/software_factory_poc/integrations (Jira/GitLab clients)
7. src/software_factory_poc/templates (registry/manifest/renderer)

## 2) Convenciones obligatorias (para no perderse)
- 1 clase / 1 enum por archivo.
- Nombres con sufijos explícitos:
  - *_router.py, *_service.py, *_client.py, *_model.py, *_adapter.py
  - *_entity.py, *_enum.py, *_vo.py, *_event.py (si aplica en PoC)
- Evitar archivos “contenedor” tipo entities.py / models.py gigantes.

## 3) Límites de la PoC (no sobre-ingeniería)
- No introducir DDD purista ni microservicios.
- No introducir un “planner con LLM”: aquí el plan es fijo/determinista.
- No introducir MCP server completo (opcional; fuera del cierre del sprint).
- Mantener el flujo lineal, con steps claros y logging por step.

## 4) Seguridad y manejo de secretos (regla de hierro)
- Nunca hardcodear tokens.
- Nunca imprimir tokens en logs.
- Nunca incluir secretos en comentarios Jira.
- Siempre usar redacción (redaction_service) antes de loggear payloads/respuestas.
- No modificar archivos del sistema del contenedor/host; solo trabajar dentro del repo.

## 5) Estilo de cambios (para merges limpios)
- Cambios pequeños y revisables.
- Cada PR debe incluir:
  - tests mínimos de lo tocado
  - actualización de README.md si cambia quickstart o demo
- No mezclar refactors grandes con features.

## 6) Definición de “funciona” (DoD PoC)
Se considera DONE cuando:
1) Con un issue válido, en 2–3 minutos hay MR en GitLab y comentario en Jira con link+resumen.
2) Con contract inválido, NO se toca GitLab y se comenta Jira con errores claros.
3) Con GitLab caído, se comenta Jira con diagnóstico y el run queda FAILED.

## 7) Dónde NO tocar
- No expandir estructura a decenas de módulos.
- No mover paquetes a librerías externas en la PoC.
- No agregar frameworks nuevos sin justificación clara.