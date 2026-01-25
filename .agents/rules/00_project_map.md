# 00_project_map.md — El Mapa Mental del Proyecto (Manual de Supervivencia)

> **Contexto Técnico Obligatorio**: Python 3.12 (Tipado Estricto)
> **Arquitectura**: Clean Architecture + Domain-Driven Design (DDD) + Pattern de Agentes

---

## 🛑 1. Protocolo de Lectura (El "Bootloader" Mental)

**Objetivo:** Cargar el contexto correcto en tu memoria antes de escribir una sola línea de código. Si ignoras este orden, cometerás errores arquitectónicos.

### Paso 1: Entender el Propósito (`README.md`)
* **Qué buscar:** ¿Qué problema resuelve este repo? ¿Cómo se levanta en local?
* **Por qué:** Para no proponer soluciones que contradigan la visión del producto (Software Factory automatizada).

### Paso 2: Entender las Leyes Físicas (`ARCHITECTURE.md`)
* **Qué buscar:** El diagrama de capas, el flujo de los 12 pasos, y la "Screaming Architecture".
* **Por qué:** Este archivo define las fronteras. Si importas `infrastructure` dentro de `application`, rompes la ley física de este universo.
* **Concepto Clave:** "Dependency Rule" (Las flechas de dependencia solo apuntan hacia adentro).

### Paso 3: Conocer al CEO (`src/.../scaffolding/scaffolding_agent.py`)
* **Qué buscar:** El método `execute_flow`.
* **Por qué:** Este es el guion de la película. Define la secuencia exacta: *Validar -> Investigar -> Razonar -> Escribir -> Publicar*. Cualquier nueva funcionalidad debe encajar en uno de estos huecos o crear uno nuevo explícitamente orquestado aquí.

### Paso 4: Conocer el Cerebro (`src/.../resolution/provider_resolver.py`)
* **Qué buscar:** Cómo se inyectan las dependencias (Dependency Injection).
* **Por qué:** Aquí descubrirás que no se hace `new GitLabProvider()`. Se pide `resolver.resolve_vcs_provider()`. El sistema es dinámico y configurable por variables de entorno.

---

## 🔍 2. La Regla de Oro: Protocolo de Escaneo Previo (DRY Extremo)

**Instrucción para Antigravity:** Antes de crear un archivo nuevo, DEBES ejecutar este algoritmo mental de búsqueda. La duplicación de código es el enemigo #1.

1.  **Búsqueda Semántica:**
    * *Vas a crear un parser de código?* -> Busca `parser`, `extractor`, `analyzer` en `application/core/agents/common/tools`.
    * *Vas a limpiar strings?* -> Busca `sanitizer`, `formatter` en `infrastructure/common`.
    * *Vas a reintentar una llamada HTTP?* -> Busca `retry`, `backoff` en `infrastructure/common/retry`.

2.  **Verificación de DTOs:**
    * No crees `MyNewFileObject`. Revisa `application/core/agents/common/dtos/file_content_dto.py`. Es probable que la estructura de datos que necesitas ya exista y esté tipada.

3.  **Patrones Existentes:**
    * Si vas a crear un nuevo *Provider*, abre `infrastructure/providers/vcs/gitlab_provider_impl.py`. Copia su estructura: `__init__`, manejo de `logger`, conversión de excepciones (`try/except` que lanza errores de dominio). **Imita, no inventes.**

---

## 🏛️ 3. Los Principios de Poder (Arquitectura Inmutable)

### A. El Reino del Dominio (`application/core/`)
* **Quién vive aquí:** Agentes (`Scaffolding`, `Research`, `Vcs`), Entidades, Value Objects, Puertos (Interfaces).
* **Reglas de Fuego:**
    1.  **Ceguera Tecnológica:** El Dominio NO sabe que existe HTTP, JSON, SQL, AWS o Docker. Solo manipula objetos puros de Python.
    2.  **Lenguaje Ubicuo:** Los nombres de clases y métodos reflejan el negocio (`ScaffoldingOrder`, `create_merge_request`), no la técnica (`JsonPayload`, `post_request`).
    3.  **Dependencia Cero:** No importa nada de `infrastructure`. NADA.

### B. El Mundo Sucio de la Infraestructura (`infrastructure/`)
* **Quién vive aquí:** Implementaciones de bases de datos, clientes HTTP (Jira, GitLab, OpenAI), Framework Web (FastAPI), Configuraciones.
* **Reglas de Fuego:**
    1.  **Servidumbre:** Su único trabajo es cumplir los contratos (Interfaces) definidos por el Dominio.
    2.  **Traducción:** Convierte el "ruido" externo (JSONs complejos, errores HTTP 500) en "señales" de dominio (DTOs limpios, Excepciones tipadas como `ProviderError`).
    3.  **Inyección:** Nunca se instancia directamente en el dominio. Se inyecta a través del `ProviderResolver`.

### C. La Tiranía de la Configuración (`infrastructure/configuration/`)
* **Regla:** Todo comportamiento variable (URLs, Timeouts, Feature Flags, Modelos LLM) debe estar en una clase `Settings` (Pydantic) y cargarse via variables de entorno. **No hardcodeo de valores mágicos.**

---

## 🗺️ 4. Mapa de Calor: Dónde encontrar (y poner) cada cosa

Esta tabla es tu brújula. Úsala.

| Capa | Carpeta | Qué va aquí (y qué NO) |
| :--- | :--- | :--- |
| **Orquestación** | `application/core/agents/scaffolding/` | La lógica principal del flujo. El `ScaffoldingAgent` es el único que manda sobre los demás agentes. |
| **Inteligencia** | `application/core/agents/reasoner/` | Todo lo relacionado con LLMs: construcción de Prompts, parseo de respuestas, manejo de tokens. |
| **Interfaces** | `.../ports/` (dentro de cada agente) | Clases abstractas (`ABC`). Definen los métodos `generate_code`, `create_branch`. **Aquí no hay código real.** |
| **Implementaciones** | `infrastructure/providers/` | Código real que toca el mundo exterior. `gitlab_provider_impl.py`, `openai_provider_impl.py`. |
| **API Web** | `infrastructure/entrypoints/api/` | Routers de FastAPI. Solo reciben JSON, lo convierten a DTO y llaman a un `UseCase`. **No hay lógica de negocio aquí.** |
| **Herramientas** | `application/core/agents/common/tools/` | Funciones puras y deterministas: `ArtifactParser`, `TimeService`. Fáciles de testear. |
| **DTOs** | `application/core/agents/common/dtos/` | Estructuras de datos que viajan entre capas (`FileContentDTO`, `TaskResult`). |

---

## 🛠️ 5. Guía de Extensibilidad para Antigravity

¿Necesitas agregar algo nuevo? Sigue estos "Recetas de Cocina" paso a paso.

### Caso A: Agregar una nueva Integración (ej. GitHub)
1.  **Leer el Contrato:** Ve a `application/core/agents/vcs/ports/vcs_gateway.py`.
2.  **Crear la Clase:** Crea `infrastructure/providers/vcs/github_provider_impl.py`.
3.  **Implementar:** Hereda de `VcsGateway` e implementa todos los métodos abstractos.
4.  **Registrar:** Ve a `infrastructure/resolution/provider_resolver.py` y agrega la lógica: `if settings.vcs_type == "GITHUB": return GitHubProviderImpl(...)`.

### Caso B: Agregar un nuevo Paso al Flujo (ej. "Security Scan")
1.  **Definir el Puerto:** Crea `application/core/agents/security/ports/security_gateway.py`. Define `scan_code(files) -> ScanResult`.
2.  **Crear el Agente:** Crea `application/core/agents/security/security_agent.py`. Orquesta la lógica del escaneo.
3.  **Implementar el Adaptador:** Crea `infrastructure/providers/security/sonarqube_provider_impl.py`.
4.  **Inyectar:** Agrega el `SecurityAgent` al constructor de `ScaffoldingAgent`.
5.  **Ejecutar:** Llama a `security_agent.scan()` dentro de `ScaffoldingAgent.execute_flow`.

### Caso C: Crear un nuevo Endpoint (ej. Webhook de Slack)
1.  **Definir DTO:** Crea `infrastructure/entrypoints/api/dtos/slack_payload.py` (Pydantic).
2.  **Crear Mapper:** Crea `.../mappers/slack_mapper.py` para convertir `SlackPayload` -> `DomainCommand`.
3.  **Crear Router:** Crea `infrastructure/entrypoints/api/slack_router.py`.
4.  **Conectar UseCase:** El router llama a un `UseCase` existente o nuevo.

---

## ⛔ 6. Lista Negra de Anti-Patrones (Prohibiciones Estrictas)

Si haces esto, el PR será rechazado automáticamente (o fallarás tu misión):

1.  ❌ **Paquetes Genéricos ("Cajón de Sastre"):**
    * PROHIBIDO crear carpetas llamadas `utils`, `helpers`, `services` (a secas), `managers` o `commons` en la raíz.
    * *Correcto:* Agrupa por contexto semántico (`date_utils` -> `common/tools/time_service.py`).

2.  ❌ **Contaminación de Dominio:**
    * PROHIBIDO importar `requests`, `httpx`, `fastapi` o `pydantic_settings` dentro de `application/`. El dominio debe ser puro.

3.  ❌ **Lógica en los Controladores:**
    * Los endpoints de FastAPI (`*_router.py`) no deben tener `if/else` de negocio. Solo parsean, validan entrada y delegan al `UseCase`.

4.  ❌ **Excepciones Crudas:**
    * Nunca dejes que un `KeyError` o `ConnectionTimeout` suba hasta el usuario. Captúralo en el Provider y lánzalo como `ProviderError` o `DomainError` con un mensaje claro.

5.  ❌ **Ignorar Python 3.12:**
    * Usa las nuevas features de tipado.
    * *Bien:* `def procesar(items: list[str]) -> dict[str, int]:` (Usa genéricos nativos).
    * *Mal:* `def procesar(items: List[str]) -> Dict[str, int]:` (Importar `List`, `Dict` de `typing` es obsoleto en 3.12 para colecciones estándar).