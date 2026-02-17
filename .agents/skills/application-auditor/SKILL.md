---
name: application-auditor
description: Audits the Application layer for proper Port definitions, Policy enforcement, and workflow orchestration. Use when reviewing use cases, agents, skills, or ports.
---
# Application Layer Auditor Skill

## When to use this skill
- Use this when modifying Orchestration, Agents, Skills, Policies, and Ports in `core/application/`.

## Review checklist (Fix immediately if any fail)
1. [ ] **Dependency Direction**: Does it import anything from `infrastructure/`? -> **FAIL & FIX**. It must only define and use `ports/`.
2. [ ] **Ports as ABCs**: Are all files in `ports/` Abstract Base Classes (`abc.ABC`) returning ONLY Domain objects? -> **FAIL & FIX**.
3. [ ] **Policy Enforcement**: Do Agents consult `core/application/policies/` BEFORE invoking a state-mutating Port? -> **FAIL & FIX**.
4. [ ] **Idempotency**: Does the flow check `RunStorePort` before executing external actions to prevent duplicate MRs or comments? -> **FAIL & FIX**.