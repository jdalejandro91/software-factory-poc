---
name: domain-auditor
description: Audits the Domain layer for pure DDD compliance, zero I/O, and strict value objects. Use when modifying core business logic or checking architectural boundaries.
---
# Domain Layer Auditor Skill

## When to use this skill
- Use this when reviewing, refactoring, or creating domain entities and value objects in `core/domain/`.

## Review checklist (Fix immediately if any fail)
1. [ ] **Zero Dependencies**: Are there imports from `litellm`, `mcp`, `httpx`, or `infrastructure/`? -> **FAIL & FIX**. Domain must be pure.
2. [ ] **Cross-Layer Pollution**: Does the Domain import from `core/application/`? -> **FAIL & FIX**.
3. [ ] **Rich Value Objects**: Do Value Objects validate their own invariants (e.g., throwing a `DomainError` if empty) in `__post_init__`? -> **FAIL & FIX**.
4. [ ] **No Managers**: Are there classes named `Manager` or `Executor` here? -> **FAIL**. Move orchestration to `core/application/`.