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
src/software_factory_poc/
├── domain/                         # Capa de Dominio
│   ├── aggregates/                 # 
│   ├── entities/                   # Abarca todos los Agentes
│   └── value_objects/              # Drivers (Interfaces)
├── application/                    # Lógica de Negocio Pura (Independiente de Frameworks)
│   ├── agents/                     # Abarca todos los Agentes
│   │   ├── common/                 # Agentes de Dominio (Expertos en una tarea)
│   │   ├── scaffolder/             # Agente de creación de scaffoldings
│   │   │   ├── config/             # Configuración del Agente
│   │   │   ├── contracts/          # Contratos
│   │   │   ├── prompt_templates/   # Plantillas de Prompt
│   │   │   └── exceptions/         # Excepciones personalizadas del Agente
│   │   └── code_reviewer/          # Agente de revisión de código
│   │       ├── config/             # Configuración del Agente
│   │       ├── contracts/          # Contratos
│   │       ├── prompt_templates/   # Plantillas de Prompt
│   │       └── exceptions/         # Excepciones personalizadas del Agente
│   └── drivers/                    # Drivers (Interfaces)
│       ├── common/                 # herramientas comunes entre los drivers
│       ├── research                # driver de investigación
│       ├── vcs                     # driver de control de versiones
│       └── tracker/                # driver de seguimiento
│
├── infrastructure/            # El mundo "Sucio" (I/O, DB, API)
│   ├── configuration/         # Configuración centralizada
│   ├── entrypoints/           # API (FastAPI) y CLI.
│   ├── providers/             # Implementaciones de Puertos (Adapters).
│   │   ├── tracker/jira/      # Implementación real de Jira.
│   │   ├── vcs/gitlab/        # Implementación real de GitLab.
│   │   └── llms/              # Implementaciones de OpenAI, DeepSeek, etc.
│   └── resolution/            # ProviderResolver (Fábrica de Inyección de Dependencias).

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

**Dónde:** `application/core/agents/security_scanner/`

1. Definir el **Port** (Interfaz): `SecurityScannerGateway` (ej. `scan_code(files) -> Report`).
2. Crear el **Agent**: `SecurityScannerAgent`.
3. Implementar el **Provider** en Infra: `infrastructure/providers/security/sonarqube/`.
4. Conectar en `ProviderResolver`.
5. Agregar el paso en `ScaffoldingAgent.execute_flow`.

### Scenario B: Cambiar de GitLab a GitHub

**Dónde:** `infrastructure/providers/vcs/github/`

1. **NO tocar el Dominio**: `VcsAgent` y `VcsGateway` no cambian.
2. Crear `GitHubProviderImpl` que implemente `VcsGateway`.
3. Actualizar `ProviderResolver` para que lea `VCS_PROVIDER=GITHUB` e instancie la nueva clase.

### Scenario C: Mejorar el Prompt o el Parsing

**Dónde:** `application/core/agents/scaffolding/tools/`

1. Modificar `ScaffoldingPromptBuilder` para alterar cómo se le habla al LLM.
2. Modificar `ArtifactParser` si cambia el formato de respuesta esperado (ej. de JSON a XML).

* *Nota*: Estas son funciones puras, fáciles de testear unitariamente.

### Scenario D: Agregar un nuevo LLM (ej. Claude 3.5)

**Dónde:** `infrastructure/providers/llms/anthropic/`

1. Implementar `LlmProvider` para Anthropic.
2. Agregarlo al `LlmProviderFactory`.
3. El `CompositeGateway` lo recogerá automáticamente basado en la configuración.

---

## 4. Key Rules for Agents

### 4.1 Domain Agents (`application/core/agents/*`)

* **Responsabilidad**: Solo lógica de negocio y coordinación.
* **Prohibido**:
* Importar librerías HTTP (`httpx`, `requests`).
* Leer variables de entorno (`os.getenv`). Usar `Config` inyectada.
* Conocer detalles de implementación (ej. "Jira API v3").


* **Permitido**:
* Usar `Tools` internas.
* Llamar a métodos definidos en `Gateways` (Interfaces).



### 4.2 Infrastructure Providers (`infrastructure/providers/*`)

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