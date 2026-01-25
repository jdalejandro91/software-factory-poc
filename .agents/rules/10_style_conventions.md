# 10_style_conventions.md — La Constitución del Código

Objetivo: Garantizar consistencia absoluta, legibilidad inmediata y cero ambigüedad en la estructura del código.

## 1. Reglas de Organización (The "Zero-Ambiguity" Law)

1.  **1 Clase = 1 Archivo**: Sin excepciones. Facilita la navegación y los tests.
2.  **Agrupación por Intención (Vertical Slicing)**:
    * NO agrupes por tipo técnico (`/controllers`, `/services`, `/models`).
    * SÍ agrupa por Dominio/Agente (`/scaffolding`, `/research`, `/vcs`).
3.  **Prohibido lo Genérico**:
    * Archivos prohibidos: `utils.py`, `common.py`, `helpers.py`, `constants.py` (si están en la raíz).
    * Solución: `date_formatter.py`, `string_sanitizer.py`, `reporter_constants.py`.
4.  **Capas Explícitas**:
    * El código de **Dominio** NUNCA importa código de **Infraestructura**.
    * El código de **Infraestructura** SIEMPRE importa interfaces (Ports) del **Dominio**.

---

## 2. Sufijos Obligatorios (Naming Strategy)

El nombre del archivo debe revelar su capa y responsabilidad.

### A. Capa de Aplicación (Core & UseCases)
| Sufijo | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `*_agent.py` | Orquestador de lógica de dominio (con state/workflow). | `scaffolding_agent.py` |
| `*_usecase.py` | Entrada de ejecución desde el exterior. | `create_scaffolding_usecase.py` |
| `*_gateway.py` | **Interfaz (Port)** abstracta para sistemas externos. | `vcs_gateway.py` |
| `*_tool.py` | Función pura o lógica auxiliar usada por un agente. | `artifact_parser.py` |
| `*_dto.py` | Data Transfer Object (Pydantic) puro. | `file_content_dto.py` |
| `*_vo.py` | Value Object (Inmutable, validación intrínseca). | `commit_hash_vo.py` |
| `*_error.py` | Excepción de dominio específica. | `contract_parse_error.py` |

### B. Capa de Infraestructura (The Dirty World)
| Sufijo | Descripción | Ejemplo |
| :--- | :--- | :--- |
| `*_provider_impl.py` | Implementación concreta de un Gateway. | `gitlab_provider_impl.py` |
| `*_settings.py` | Configuración (Pydantic BaseSettings). | `gitlab_settings.py` |
| `*_router.py` | FastAPI Router / Controller. | `jira_trigger_router.py` |
| `*_mapper.py` | Conversor de External-DTO a Domain-DTO. | `jira_payload_mapper.py` |
| `*_client.py` | Cliente HTTP/SDK de bajo nivel (wrapper). | `gitlab_http_client.py` |
| `*_factory.py` | Constructor complejo de dependencias. | `llm_provider_factory.py` |

---

## 3. Convenciones de Código (Coding Standards)

### A. Tipado (Typing)
* **Strict Typing**: Todo argumento y retorno debe tener type hint.
    * *Bien*: `def execute(self, order: ScaffoldingOrder) -> TaskResult:`
    * *Mal*: `def execute(self, order):`
* **No `Any`**: Evita `Any` a toda costa. Usa `Dict[str, Any]` solo si es un JSON sucio de entrada que vas a limpiar inmediatamente.

### B. Estilo Python
* **Snake Case (`snake_case`)**: Funciones, métodos, variables, nombres de archivo.
* **Pascal Case (`PascalCase`)**: Clases, Tipos, Enums.
* **Upper Case (`UPPER_CASE`)**: Constantes globales.

### C. Enums
* Usa `StrEnum` (Python 3.11+) o hereda de `str, Enum`.
* Nombres de archivo: `*_type.py` o `*_status.py`.
    * Ejemplo: `task_status.py` -> `class TaskStatus(str, Enum):`

---

## 4. Logging & Observability

* **Prohibido `print()`**: El uso de `print` es motivo de rechazo de PR automático.
* **Logger Inyectado**: Usa `logger_factory.get_logger(__name__)`.
* **Contexto Obligatorio**: Los logs de negocio deben incluir contexto trazable.
    * *Bien*: `logger.info("Branch created", extra={"branch": branch_name, "repo": repo_id})`
* **Redacción de Secretos**: JAMÁS loggees un objeto que pueda contener tokens. Usa `RedactionService` o loggea solo IDs.

---

## 5. Testing Strategy

### A. Unit Tests (`tests/unit/`)
* **Mock Everything External**: Si testeas un Agente, mockea sus Gateways.
* **No I/O**: Los unit tests no tocan disco ni red.
* **Foco**: Lógica de negocio, cambios de estado, manejo de errores de parsing.

### B. Integration Tests (`tests/integration/`)
* **Provider Validation**: Aquí testeamos `*_provider_impl.py`.
* **Real vs Fake**: Usa stubs o emuladores cuando sea posible. Si pegas a la API real, usa marcadores `@pytest.mark.external`.

---

## 6. Manejo de Errores (Error Handling)

1.  **Catch en Infra**: El Provider captura `requests.exceptions.ConnectionError`.
2.  **Raise Domain**: El Provider lanza `ProviderError` o `InfraError` (definidos en Dominio).
3.  **Handle en Agente**: El Agente captura `ProviderError`, decide si reintenta o falla la tarea, y reporta.
    * *Nunca* dejes subir una excepción cruda de librería (`KeyError`, `ValueError`) hasta el usuario final (API 500).