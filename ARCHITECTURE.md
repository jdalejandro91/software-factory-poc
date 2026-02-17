Aquí tienes la versión refinada y extendida de `ARCHITECTURE.md`. He reestructurado el documento para que funcione como un **Manual de Ingeniería "Antigravity"**, alineando estrictamente el código actual (Clean Architecture + DDD) con el flujo de negocio que has detallado.

Este archivo ahora no solo describe *qué* es el sistema, sino *cómo* extenderlo respetando las reglas de juego.

```markdown
# Software Factory PoC — Architecture Documentation

## 1. Architectural Philosophy: Screaming Architecture (DDD)

El proyecto sigue estrictamente los principios de **Domain-Driven Design (DDD)** y **Clean Architecture**. La estructura de carpetas "grita" la intención del negocio (Scaffolding, Research, Reporting) en lugar del framework (FastAPI, HTTP).

### 1.1 The "Dependency Rule"
La regla de oro es: **Las dependencias solo apuntan hacia adentro.**
* `Infrastructure` -> conoce a -> `Application`
* `Application (Use Cases)` -> conoce a -> `Domain (Agents/Entities)`
* `Domain` -> **NO CONOCE A NADIE**. Solo define entidades y objetos de valor.

### 1.2 Directory Map (Screaming Structure)

```text
software_factory/                              # Raíz del proyecto. Agrupa todas las capas (core, infraestructura, entrypoints) bajo un mismo bounded context.
├── core/                                      # Núcleo “limpio”: dominio + aplicación. No depende de frameworks ni de I/O concreto.
│   ├── domain/                                # Modelo del negocio: invariantes, VOs, entidades y agregados. Sin llamadas a APIs/DBs.
│   │   ├── mission/                           # Subdominio de intención: define “qué se quiere hacer” y con qué restricciones (Mission como Aggregate Root).
│   │   ├── run/                               # Subdominio de ejecución durable: modela un Run, sus pasos, estados, idempotencia y evidencias (audit trail).
│   │   ├── skill/                             # Subdominio de capacidades: definición/versionado/contratos/políticas de skills (qué existe y cómo se invoca).
│   │   ├── quality/                           # Subdominio de calidad: guardrails de revisión/código (incluye CodeReviewReport y severidades/comentarios).
│   │   ├── delivery/                          # Subdominio de entrega/cambios: intención de cambios VCS agnóstica (incluye CommitIntent y VOs de repo/branch/MR).
│   │   ├── work_tracking/                     # Subdominio de tracking: referencias y snapshots de tareas (Jira/otros) sin acoplarse a herramientas concretas.
│   │   └── shared/                            # Primitivas transversales del dominio: IDs, errores tipados, tiempo/clock, utilidades puras y estables.
│   └── application/                           # Coordinación de casos de uso: orquesta dominio + puertos. Aquí viven roles/agents y skills ejecutables.
│       ├── orchestration/                     # Servicios de alto nivel: crean Missions, inician/reanudan Runs, aplican macro-policies y controlan el flujo.
│       ├── agents/                            # Roles/orquestadores: deciden qué skill ejecutar, con qué input, cómo reaccionar a resultados/errores.
│       ├── skills/                            # Implementación de skills: unidades reutilizables que producen/consumen VOs del dominio y llaman puertos.
│       │   ├── scaffold/                      # Skills para scaffolding: planificar, generar y aplicar estructura/proyecto.
│       │   ├── review/                        # Skills de code review: obtener diffs, analizar, producir CodeReviewReport, publicar comentarios.
│       │   ├── change/                        # Skills de cambios: generar CommitIntent, aplicarlo vía VCS, abrir MR/PR.
│       │   └── diagnosis/                     # Skills de diagnóstico: recolectar logs, hallar causa raíz, proponer fix (sin ejecutar I/O directo).
│       ├── policies/                          # Políticas aplicadas en aplicación: quality gates, budgets, approvals, naming rules (no es dominio puro).
│       └── drivers/                           # Interfaces (contracts) hacia el mundo externo: LLM, VCS, tracker, docs, CI, stores (Run/Skill/Artifact).
└── infrastructure/                            # Mundo “sucio”: implementaciones concretas de puertos (I/O, HTTP, DB, cloud). Depende de vendors.
    ├── configuration/                           # Puntos de entrada (drivers inbound): donde llegan requests externas y se invoca la aplicación.
    ├── entrypoints/                           # Puntos de entrada (drivers inbound): donde llegan requests externas y se invoca la aplicación.
    │   ├── api/                               # API HTTP/webhooks: controladores que validan input, crean Mission, llaman MissionService/RunService.
    │   └── cli/                               # CLI: comandos locales para disparar missions/runs, debugging, operaciones internas o tooling.
    ├── drivers/                               # Integraciones operativas (drivers) para ejecutar acciones externas: LLMs, VCS, Tracker, Docs, CI.
    │   ├── llms/                              # Providers de LLM + helpers de salida estructurada/validación de schema, retries, timeouts, rate limits.
    │   ├── vcs/                               # Implementaciones Git (GitLab/GitHub/local): aplicar CommitIntent, gestionar branches, commits, MRs/PRs.
    │   ├── tracker/                           # Implementaciones de tracking (Jira, etc.): leer/actualizar tareas, traer contexto y estados.
    │   ├── research/                          # Implementaciones de docs (Confluence, etc.): leer/escribir páginas, adjuntos, referencias.
    │   └── knowledge/                         # Implementaciones CI/CD (GitLab CI, etc.): disparar pipelines, consultar estados, recolectar artefactos.
    └── persistence/                           # Persistencia concreta de estado durable y artefactos: DBs y storage (S3/filesystem).
        ├── run_store/                         # Almacenamiento de Runs y steps (durable execution): Mongo/Postgres u otras opciones.
        ├── artifact_store/                    # Almacenamiento de artefactos/evidencias (reports, diffs, logs, outputs): S3 o filesystem.
        └── skill_store/                       # Almacenamiento/registro versionado de skills/metadata/contratos: file/db.
```

---

## 2. The Scaffolding Flow (Business Logic)

El flujo de negocio está centralizado en el `ScaffoldingAgent` (Dominio) pero orquestado inicialmente por el `CreateScaffoldingUseCase` (Aplicación).

### Phase 1: Initiation (Infrastructure -> Use Case)

1. **Trigger**: Jira envía un Webhook a `JiraTriggerRouter`.
2. **Mapping**: `JiraPayloadMapper` convierte el JSON sucio de Jira en un `ScaffoldingOrder` (Dominio).
3. **Wiring**: `CreateScaffoldingUseCase` usa el `ProviderResolver` para instanciar los agentes con sus implementaciones concretas (ej. `VcsAgent` con `GitLabProvider`).

### Phase 2: Domain Orchestration (`ScaffoldingAgent.execute_flow`)

El `ScaffoldingAgent` recibe a sus "subordinados" (Reporter, VCS, Researcher, Reasoner) y ejecuta el guion:

4. **Report Start**: Invoca a `ReporterAgent` → "🤖 Iniciando tarea...".
5. **Branch Validation**: Invoca a `VcsAgent` para verificar si la rama existe.
* *Decision Point*: Si existe, reporta éxito (informativo) y **DETIENE** el flujo para evitar duplicados.


6. **Research Context**: Invoca a `ResearchAgent`.
* Este agente decide si busca en Confluence (RAG) o usa conocimiento base, usando `ResearchGateway`.


7. **Prompt Engineering**: Usa su tool `ScaffoldingPromptBuilder` para mezclar la instrucción del usuario + contexto investigado + reglas de seguridad.
8. **Reasoning (LLM)**: Invoca a `ReasonerAgent`.
* El `ReasonerAgent` no sabe qué modelo usa; delega al `LlmGateway` (Infra) que maneja prioridades (ej. OpenAI falla -> DeepSeek).


9. **Parsing**: Usa su tool `ArtifactParser` para convertir el texto del LLM en objetos `FileContentDTO`.
10. **Branch Creation**: Invoca a `VcsAgent.create_branch`.
11. **Commit**: Invoca a `VcsAgent.commit_files`.
12. **Merge Request**: Invoca a `VcsAgent.create_merge_request`.
13. **Final Report**: Invoca a `ReporterAgent` para notificar éxito ("✅ MR Created") y transicionar la tarea a `IN REVIEW`.

---

## 3. Extensibility Guide (For Antigravity)

Esta sección define dónde y cómo agregar nueva funcionalidad sin romper la arquitectura.

### Scenario A: Agregar una nueva capacidad al Agente (ej. "Security Scan")

**Dónde:** `core/application/agents/security_scanner/`

1. Definir el **Port** (Interfaz): `SecurityScannerGateway` (ej. `scan_code(files) -> Report`).
2. Crear el **Agent**: `SecurityScannerAgent`.
3. Implementar el **Provider** en Infra: `infrastructure/drivers/security/sonarqube/`.
4. Conectar en `ProviderResolver`.
5. Agregar el paso en `ScaffoldingAgent.execute_flow`.

### Scenario B: Cambiar de GitLab a GitHub

**Dónde:** `infrastructure/drivers/vcs/github/`

1. **NO tocar el Dominio**: `VcsAgent` y `VcsGateway` no cambian.
2. Crear `GitHubProviderImpl` que implemente `VcsGateway`.
3. Actualizar `ProviderResolver` para que lea `VCS_PROVIDER=GITHUB` e instancie la nueva clase.

### Scenario C: Mejorar el Prompt o el Parsing

**Dónde:** `core/application/agents/scaffolding/tools/`

1. Modificar `ScaffoldingPromptBuilder` para alterar cómo se le habla al LLM.
2. Modificar `ArtifactParser` si cambia el formato de respuesta esperado (ej. de JSON a XML).

* *Nota*: Estas son funciones puras, fáciles de testear unitariamente.

### Scenario D: Agregar un nuevo LLM (ej. Claude 3.5)

**Dónde:** `infrastructure/drivers/llms/anthropic/`

1. Implementar `LlmProvider` para Anthropic.
2. Agregarlo al `LlmProviderFactory`.
3. El `CompositeGateway` lo recogerá automáticamente basado en la configuración.

---

## 4. Key Rules for Agents

### 4.1 Domain Agents (`core/application/agents/*`)

* **Responsabilidad**: Solo lógica de negocio y coordinación.
* **Prohibido**:
* Importar librerías HTTP (`httpx`, `requests`).
* Leer variables de entorno (`os.getenv`). Usar `Config` inyectada.
* Conocer detalles de implementación (ej. "Jira API v3").


* **Permitido**:
* Usar `Tools` internas.
* Llamar a métodos definidos en `Gateways` (Interfaces).



### 4.2 Infrastructure Providers (`infrastructure/drivers/*`)

* **Responsabilidad**: Hablar con el mundo exterior y traducir al lenguaje del dominio.
* **Prohibido**:
* Tomar decisiones de negocio (ej. "Si falla el commit, crea un ticket"). Eso lo hace el Agente.


* **Obligatorio**:
* Implementar la interfaz del Gateway estrictamente.
* Manejar excepciones de red y lanzar `ProviderError` (capturable por el dominio).

---

## 5. Configuration & Wiring (`ProviderResolver`)

El sistema se ensambla dinámicamente en tiempo de ejecución.

* **`ScaffoldingAgentConfig`**: Define *qué* queremos hacer (feature flags, timeouts).
* **`AppConfig` (Settings)**: Define *credenciales* y *endpoints*.
* **`ProviderResolver`**: Es el único lugar donde el código conoce las implementaciones concretas (`Impl`). Actúa como el "Mainboard" donde se conectan los componentes.

### Ejemplo de Resolución:

```python
# ProviderResolver decide qué "cerebro" darle al agente
def resolve_llm_gateway(self) -> LlmGateway:
    # 1. Carga configs
    # 2. Instancia CompositeLlmGateway
    # 3. Inyecta OpenAI, DeepSeek, etc.
    return CompositeLlmGateway(...)

```