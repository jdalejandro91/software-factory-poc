---
name: observability-sre
description: Enforces the Puntored SRE standard for logging (structlog), tracing (OpenTelemetry), and metrics (Prometheus). Use when adding logs, handling errors, injecting context variables, or creating metrics/traces.
---
# Observability & SRE Auditor Skill

## When to use this skill
- Use this when modifying entrypoints (FastAPI middlewares/routers).
- Use this when adding logs to Agents, Workflows, or Infrastructure Tools.
- Use this when handling external exceptions (MCP/LLM) to report errors.
- Use this when tracking duration, LLM tokens, or outcomes via Prometheus.

## How to use it (Implementation Guide)
1. **Zero Standard Logging**: Always use `import structlog` and inject the logger from the Infrastructure layer.
2. **Context Injection**: Use `structlog.contextvars.bind_contextvars(correlation_id=..., trace_id=...)` at the boundary (API router or inside the background task entry) so all subsequent logs inherit these IDs.
3. **Puntored Kwargs**: Pass flat kwargs with prefixes so the infrastructure processor can nest them into the Puntored JSON Schema.
   - Example Error: `processing_status="ERROR"`, `error_type="McpError"`, `error_details="..."`
   - Example Context: `context_component="CodeReviewerAgent"`

## Decision Tree: Error Handling
- **Scenario: An external API or MCP call fails.**
  - *Action*: Catch the exception, wrap it in a `ProviderError`, and log it strictly as an error with the `error_` kwargs prefix.
  ```python
  except Exception as e:
      logger.error(
          "MCP Tool execution failed",
          processing_status="ERROR",
          error_type=type(e).__name__,
          error_details=str(e),
          error_retryable=False,
          context_component="VcsTool"
      )
      raise ProviderError(f"VCS failed: {str(e)}") from e
  ```

## Review checklist (Fix immediately if any fail)
1. [ ] **No Standard Logging**: Are there any `import logging` or `logging.getLogger()` calls? -> **FAIL & FIX**. Replace entirely with `structlog`.
2. [ ] **Cardinality Bomb**: Are there high-cardinality IDs (like UUIDs, issue keys, branch names) used as Prometheus labels? -> **FAIL & FIX**. Use only static bounds.
3. [ ] **Secret Leakage**: Are raw prompts, diffs, or headers logged without passing through `RedactionService.redact()`? -> **FAIL & FIX**.
4. [ ] **Background Context Loss**: Are you propagating context (`correlation_id`, `trace_id`) into async background tasks properly via `bind_contextvars`? -> **FAIL & FIX**.
5. [ ] **Puntored Schema Enforcement**: Are you passing flat data without prefixes (e.g., `status="ERROR"`)? -> **FAIL & FIX**. You must use `processing_status`, `error_type`, `context_component`, etc.
