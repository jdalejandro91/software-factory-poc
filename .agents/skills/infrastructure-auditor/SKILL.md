---
name: infrastructure-auditor
description: Audits the Infrastructure layer for proper adapter implementation, MCP usage, and coexistence routing. Use when modifying drivers, entrypoints, or removing legacy HTTP clients.
---
# Infrastructure Layer Auditor Skill

## When to use this skill
- Use this when validating the "Dirty World" implementations in `infrastructure/`.

## Review checklist (Fix immediately if any fail)
1. [ ] **Zombie Code Purge**: Are there any manual HTTP clients (`_http_client.py`) or ADF Builders for services that should be using MCP? -> **DELETE THEM**.
2. [ ] **Zero Business Logic**: Does the adapter contain business rules (e.g., "if ticket is bug, name branch X")? -> **FAIL & FIX**. Move logic to Application `skills/`.
3. [ ] **Error Normalization**: Are raw external exceptions (`mcp`, `litellm`, `httpx` errors) bubbling up? -> **FAIL & FIX**. Catch and wrap them in `ProviderError` or `InfraError` preserving the stack trace.
4. [ ] **Coexistence Routing**: Are Routers dynamically delegating to specific MCP clients based on the Domain Context?