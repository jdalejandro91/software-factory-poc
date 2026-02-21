# 60_observability_and_sre.md — SPEC: Observability, Logging & SRE (Puntored Standard)

## 1. The Trinity of Observability
BrahMAS relies on three distinct layers of observability. They must never be mixed or ignored:
* [cite_start]**Logs (`structlog`):** Detailed, structured narrative of events (JSON)[cite: 17].
* [cite_start]**Tracing (`opentelemetry`):** Distributed causal graph (`trace_id`, `span_id`)[cite: 19, 20].
* **Metrics (`prometheus_client`):** Aggregated health and LLM costs (counters, histograms, gauges).

---

## 2. Strict Logging Rule (NO STANDARD LOGGING)
* **PROHIBITED:** You MUST NEVER use Python's standard `logging` module (e.g., `import logging`, `logging.info()`) anywhere in the codebase.
* **MANDATORY:** You MUST exclusively use `structlog`. 
* **ASYNC/BACKGROUND CONTEXT:** In async endpoints or background tasks, you MUST use `structlog.contextvars.bind_contextvars()` to ensure `correlation_id` and context are preserved across asynchronous execution boundaries.

---

## 3. The Puntored JSON Schema & Implementation (MANDATORY)
[cite_start]In QA and Production, logs MUST strictly adhere to the nested JSON schema defined by Puntored's SRE team[cite: 18]. Flat root keys (other than the standard ones) are forbidden. 

The infrastructure `puntored_processor.py` handles the JSON nesting, but **you MUST provide the correct specific kwargs with prefixes to the logger** so the processor can group them properly.

### A. Root Level (Injected automatically by Middlewares & Processors)
* [cite_start]`timestamp` (ISO 8601 UTC), `level`, `service`, `environment`, `trace_id` (UUID), `correlation_id`, `span_id`, `version`, `region`[cite: 19, 20].

### B. Nested Objects (Passed as specific kwargs to structlog)
Use these precise kwargs prefixes:

1.  [cite_start]**Processing (`processing_`):** * `processing_status`: SUCCESS, ERROR, or TIMEOUT[cite: 20].
    * [cite_start]`processing_duration_ms`: MUST be numeric[cite: 20].
    * [cite_start]`processing_retries`: Numeric (optional)[cite: 20].
2.  [cite_start]**Error (`error_`):** * `error_type`: Exception class (e.g., `TimeoutError`)[cite: 324].
    * [cite_start]`error_code`: Business or protocol error code[cite: 326].
    * [cite_start]`error_details`: Stack trace or detailed message[cite: 328].
    * [cite_start]`error_retryable`: Boolean[cite: 330].
3.  [cite_start]**Event (`event_`):** * `event_eventId`: UUID (unique per event)[cite: 20].
    * [cite_start]`event_eventType`: e.g., `workflow.started`, `transaction.failed`[cite: 20].
    * [cite_start]`event_actorId`: User or system initiating the action[cite: 20].
    * [cite_start]`event_causationId`: ID of the previous event that triggered this one[cite: 20].
    * [cite_start]`event_topic`: Kafka topic (MANDATORY for Kafka)[cite: 99].
4.  **Context (`context_`):** * `context_component`: **MANDATORY FOR ALL LOGS** (e.g., `GitlabMcpClient`, `PaymentProcessor`). [cite_start]Reflects the functional layer (Controller, Service, Repository, etc.)[cite: 20, 433].
    * [cite_start]`context_endpoint`: HTTP route or gRPC method package[cite: 44, 67].
    * [cite_start]`context_method`: HTTP Verb (POST) or gRPC type (UNARY)[cite: 51, 68].
    * [cite_start]`context_client_ip`: IPv4/IPv6[cite: 52, 91].
    * [cite_start]`context_partition` / `context_offset`: MANDATORY for Kafka[cite: 99].
5.  [cite_start]**Metadata (`metadata_`):** * `metadata_source_system`: Source channel[cite: 20].
    * [cite_start]`metadata_tags`: List of strings for classification (e.g., `["rest", "timeout"]`)[cite: 21].

**Example Implementation in Python:**
```python
logger.error(
    "MS-PAYMENTS-POST/cashout -> Timeout al comunicarse con Gateway Daviplata",
    processing_status="ERROR",
    processing_duration_ms=5123,
    error_type=type(e).__name__,
    error_code="HTTP_TIMEOUT",
    error_details=str(e),
    error_retryable=True,
    event_eventId=str(uuid.uuid4()),
    event_eventType="transaction.failed",
    context_component="GitlabMcpClient",
    context_endpoint="/v1/payments/cashout",
    context_method="POST",
    metadata_tags=["rest", "timeout", "gateway-daviplata"]
)
```

---

## 4. Message Standards & Severity Levels
* **Format Standard:** `[Servicio] - [Acción] → [Resultado/Causa]`. 
    * [cite_start]*Example:* `MS-PAYMENTS-POST/cashout → Timeout al comunicarse con Gateway Daviplata (30s)`[cite: 406].
* **No Generic Messages:** Avoid "Error occurred". [cite_start]Use structured business codes (e.g., `E-TRX-001`)[cite: 407].

| Level | Recommended Use |
| :--- | :--- |
| **DEBUG** | [cite_start]Technical info for debugging (solo en entornos de desarrollo)[cite: 389, 394]. |
| **INFO** | [cite_start]Business events or normal application flow[cite: 390, 397]. |
| **WARN** | [cite_start]Unusual behaviors that do NOT interrupt the operation[cite: 391, 399]. |
| **ERROR** | [cite_start]Functional or technical failures that are recoverable or localized[cite: 392, 401]. |
| **CRITICAL**| [cite_start]Severe failures impacting overall availability or integrity[cite: 403, 404]. |

---

## 5. Mandatory Minimum Events to Log
You MUST log at least the following events in any flow:
1.  [cite_start]Inicio y fin de operaciones[cite: 409].
2.  [cite_start]Errores de validación (input/output)[cite: 410].
3.  [cite_start]Errores de comunicación (timeouts, fallos de red)[cite: 411].
4.  [cite_start]Eventos de seguridad (autenticación, autorización)[cite: 412].
5.  [cite_start]Acciones administrativas o cambios de configuración[cite: 413].
6.  [cite_start]Flujos de negocio críticos (creación o cancelación de transacciones)[cite: 414].

---

## 6. OpenTelemetry (Tracing) Rules
* Every Agent step and MCP tool invocation MUST be wrapped in a trace span (e.g., `@trace_operation(...)` or `with tracer.start_as_current_span(...)`).
* The `trace_id` MUST be dynamically injected into the `structlog` context so logs and traces map 1:1.

---

## 7. Prometheus (Metrics) Cardinality Rule
* **High Cardinality Ban:** You MUST NEVER inject dynamic IDs (UUIDs, `issue_key`, `commit_hash`, `branch_name`) into Prometheus label values. This crashes the TSDB.
* **Allowed Labels:** Only use bounded enums: `agent`, `flow_mode`, `provider`, `tool`, `model`, `outcome` (success/error).

---

## 8. Security & Compliance (Secrets Redaction)
* **Redaction Mandatory:** You MUST pass any LLM Prompt, API response, or Jira payload containing sensitive data (PII, credentials) through `RedactionService.redact(...)` BEFORE logging it.
* No API keys, passwords, or cleartext tokens are allowed in the console or logs. [cite_start]Comply with Habeas Data, GDPR, and ISO 27001[cite: 416].

---

## 9. Antipatterns to Avoid (Checklist)
Before committing log-related code, ensure you are NOT doing the following:
* [cite_start][ ] **Logging excesivo/redundante:** Affects performance and storage[cite: 418].
* [cite_start][ ] **Logs sin estructura:** Dificulta análisis y trazabilidad[cite: 418].
* [cite_start][ ] **Duplicar eventos:** Genera ruido y confusión[cite: 418].
* [cite_start][ ] **Logs en bucles intensivos:** Degrada la performance[cite: 418].
* [cite_start][ ] **Logs de debug en producción:** Increases risk of data leaks[cite: 418].

---

## 10. SRE / Observability FAQ (Puntored Guidelines)

* **Difference between `logger` and `context.component`?**
    * [cite_start]`logger` is the technical class/module[cite: 433].
    * `context.component` is the functional/semantic layer (e.g., `interface`, `application`, `domain`, `infrastructure` in DDD). [cite_start]Both must be maintained[cite: 433].
* **How are Trace IDs handled?**
    * [cite_start]`trace_id`: Represents the entire technical execution across micros[cite: 433].
    * [cite_start]`span_id`: Represents a single internal operation (Controller, Service)[cite: 433].
    * [cite_start]`correlation_id`: Ties multiple `trace_id`s together for a single business transaction[cite: 433].
* **Trace ID vs Event ID?**
    * [cite_start]`trace_id` is for the whole request execution[cite: 434].
    * [cite_start]`event.eventId` marks a *specific action* within that trace (e.g., DB insert, Kafka publish)[cite: 434].
* **What is Causation ID?**
    * [cite_start]`event.causationId` indicates which event triggered the current one (e.g., Event 001 caused Event 002)[cite: 434].