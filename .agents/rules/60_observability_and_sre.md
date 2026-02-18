# 60_observability_and_sre.md — SPEC: Observability, Logging & SRE (Puntored Standard)

## 1. The Trinity of Observability
BrahMAS relies on three distinct layers of observability. They must never be mixed or ignored:
- **Logs (`structlog`):** Detailed, structured narrative of events (JSON).
- **Tracing (`opentelemetry`):** Distributed causal graph (`trace_id`, `span_id`).
- **Metrics (`prometheus_client`):** Aggregated health and LLM costs (counters, histograms, gauges).

## 2. Strict Logging Rule (NO STANDARD LOGGING)
**PROHIBITED:** You MUST NEVER use Python's standard `logging` module (e.g., `import logging`, `logging.info()`) anywhere in the codebase.
**MANDATORY:** You MUST exclusively use `structlog`. In async endpoints or background tasks, you MUST use `structlog.contextvars.bind_contextvars()` to ensure correlation_id context is preserved.

## 3. The Puntored JSON Schema (MANDATORY)
In QA and Production, logs MUST strictly adhere to the nested JSON schema defined by Puntored's SRE team. Flat root keys (other than the standard ones) are forbidden. The infrastructure `puntored_processor.py` handles the JSON nesting, but you MUST provide the correct specific kwargs with prefixes to the logger:

### Root Level (Injected by Middlewares & Processors)
- `timestamp` (ISO 8601 UTC), `level`, `service`, `environment`, `trace_id` (UUID), `correlation_id`, `span_id`.

### Nested Objects (Passed as specific kwargs to structlog)
Use these precise kwargs so the processor can group them into nested objects:
1. **Processing (`processing_`):** `processing_status` (SUCCESS/ERROR/TIMEOUT), `processing_duration_ms` (MUST be numeric), `processing_retries`.
2. **Error (`error_`):** `error_type` (Exception class), `error_code`, `error_details` (stack trace/message), `error_retryable` (boolean).
3. **Event (`event_`):** `event_eventId` (UUID), `event_eventType` (e.g., `workflow.started`), `event_actorId`, `event_causationId`.
4. **Context (`context_`):** `context_component` (e.g., `GitlabMcpClient` - MANDATORY for all logs), `context_endpoint`, `context_method`, `context_client_ip`.
5. **Metadata (`metadata_`):** `metadata_source_system`, `metadata_tags` (list of strings).

*Example Usage:* 
`logger.error("VCS Tool failed", processing_status="ERROR", error_type=type(e).__name__, error_details=str(e), context_component="GitlabMcpClient")`

## 4. OpenTelemetry (Tracing) Rules
- Every Agent step and MCP tool invocation MUST be wrapped in a trace span (e.g., `@trace_operation(...)` or `with tracer.start_as_current_span(...)`).
- The `trace_id` MUST be dynamically injected into structlog context so logs and traces map 1:1.

## 5. Prometheus (Metrics) Cardinality Rule
- **High Cardinality Ban:** You MUST NEVER inject dynamic IDs (UUIDs, `issue_key`, `commit_hash`, `branch_name`) into Prometheus label values. This crashes the TSDB.
- **Allowed Labels:** Only use bounded enums: `agent`, `flow_mode`, `provider`, `tool`, `model`, `outcome` (success/error).

## 6. Secrets Redaction (Security)
- You MUST pass any LLM Prompt, API response, or Jira payload containing sensitive data through `RedactionService.redact(...)` BEFORE logging it. No API keys or cleartext tokens in the console.
