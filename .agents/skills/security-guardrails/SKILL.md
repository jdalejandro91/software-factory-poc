---
name: security-guardrails
description: Enforces DevSecOps practices, token redaction, and policy guardrails. Use when handling sensitive data, logging, or preventing destructive actions by agents.
---
# Security & Guardrails Skill

## When to use this skill
- Use this when implementing observability, logging, or accessing credentials.

## Review checklist
1. [ ] **Token Redaction**: Do all logging mechanisms pass payloads through the `RedactionService`? Ensure API keys, `glpat-`, and Bearer tokens are masked as `***REDACTED***`.
2. [ ] **Secrets Management**: Are credentials accessed ONLY via Pydantic `Settings` in `infrastructure/configuration/`? No hardcoded strings.
3. [ ] **Destructive Autonomy**: Are destructive actions (delete branch, merge to main) explicitly blocked in the `policies/` layer? DO NOT expose these to the LLM during Act Loops.
4. [ ] **Prompt Injection**: Are user inputs treated as untrusted strings and placed inside secure XML-like delimiters (e.g., `<user_input>...</user_input>`) in prompts?