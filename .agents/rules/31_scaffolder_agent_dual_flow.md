# ScaffolderAgent Dual-Flow Rule (MCP-Only)

## Scope
Applies to: `core/application/agents/scaffolder_agent.py` and any code it orchestrates (skills, ports, policies, prompt builders).
This rule is mandatory: do not omit any step or invariant described below.

## Goal
Implement and maintain ScaffolderAgent so it supports TWO execution modes:
- A) `LINEAR_DETERMINISTIC` (cheap, auditable, predictable pipeline)
- B) `AGENTIC_ACT_LOOP` (ReAct loop for complex/ambiguous/self-healing missions)

Both modes MUST interact with external systems ONLY via Ports whose infrastructure adapters call MCP tools.
Manual REST API calls from application/domain code are forbidden.

## Non-Negotiables (Invariants)
1) MCP-only outbound:
   - Any interaction with GitLab/Jira/Confluence must go through `VcsPort`, `TrackerPort`, `DocsPort` (and/or MCP tool exposure via `get_mcp_tools/execute_tool`).
   - No hand-written REST calls in agent/application/domain code.
2) Deterministic mode control:
   - In `LINEAR_DETERMINISTIC`, the LLM NEVER controls the flow.
   - LLM usage is one-shot, structured output only (Pydantic schema).
3) Agentic mode sandbox:
   - In `AGENTIC_ACT_LOOP`, the LLM may choose tools, but only after:
     - tools are collected from Ports,
     - tools are filtered by policies (deny destructive/high-risk ops),
     - Python runtime executes tool calls and returns observations to LLM.
4) Idempotency:
   - Branch existence check is mandatory.
   - If branch already exists, the agent must short-circuit and finish safely.
5) Reporting:
   - Always report start.
   - Always report success or failure with actionable details.
   - Never leak secrets.
6) Configuration:
   - Everything variable must come from ENV (provider selection, URLs, tokens, workflow states, model priority, Confluence page IDs).
   - No hardcoded IDs/URLs/models/tokens.

## Inputs (expected)
From Jira webhook payload:
- Issue key
- Issue description containing YAML "scaffolding" block with:
  - version
  - technology_stack
  - target.gitlab_project_path
  - target.branch_slug
  - parameters.service_name
  - parameters.description
  - parameters.owner_team

From ENV:
- SCAFFOLDING_VCS_PROVIDER, SCAFFOLDING_TRACKER_PROVIDER, SCAFFOLDING_KNOWLEDGE_PROVIDER
- WORKFLOW_STATE_INITIAL, WORKFLOW_STATE_SUCCESS
- ARCHITECTURE_DOC_PAGE_ID
- SCAFFOLDING_LLM_MODEL_PRIORITY
- All required provider credentials (GitLab/Jira/Confluence) and base URLs

## Mode Selection
Default to `LINEAR_DETERMINISTIC`.
Use `AGENTIC_ACT_LOOP` ONLY if:
- mission is explicitly marked as agentic, OR
- deterministic execution failed and recovery/self-healing is enabled, OR
- task is ambiguous/exploratory by design.

## A) LINEAR_DETERMINISTIC — Step-by-step (Do not skip)
1) Parse + validate YAML
   Why: fail fast, avoid external calls with invalid inputs.
   - Extract branch_slug, project_path, service_name, owner_team, etc.
   - If missing/invalid → report failure and stop.

2) Report start (TrackerPort.add_comment)
   Why: traceability and user feedback in Jira.

3) Idempotency guard (VcsPort.validate_branch_existence)
   Why: Jira webhooks can be retried; prevent duplicate scaffolding.
   - If branch exists:
     - TrackerPort.add_comment explaining branch already exists
     - TrackerPort.update_status to WORKFLOW_STATE_SUCCESS (In Review)
     - STOP (no docs fetch, no LLM, no VCS writes)

4) Fetch knowledge context (DocsPort)
   Why: scaffolding must comply with project standards.
   - DocsPort.get_project_context(service_name)
   - DocsPort.get_architecture_context(ARCHITECTURE_DOC_PAGE_ID)

5) Build prompt (scaffolding_prompt_builder)
   Why: stable prompt → stable structured output.
   Prompt MUST include:
   - mission intent and extracted YAML config
   - relevant architecture/standards context
   - hard constraints (no secrets, correct paths, deterministic directory structure)
   - required output schema (files: [{path,name,content}], plus any metadata)

6) One-shot structured LLM call (BrainPort.generate_structured)
   Why: convert intent → executable artifact plan.
   - Must return a Pydantic-validated structure (no freeform).

7) Validate scaffold plan (local validation)
   Why: prevent committing corrupt or unsafe outputs.
   - Paths must be within repository scope.
   - No secrets/tokens in generated files.
   - No empty files unless explicitly allowed.
   - No writing to forbidden paths (e.g., `.env` with real secrets).

8) Create branch (VcsPort.create_branch)
   Why: isolate changes and enable MR review.

9) Commit files (VcsPort.commit_changes)
   Why: persist scaffolding.
   - Commit message must be deterministic and include ticket key.

10) Create Merge Request (VcsPort.create_merge_request)
   Why: enable code review workflow.

11) Update Jira task description with automation state (TrackerPort.update_task_description)
   Why: the subsequent Code Review flow depends on these fields existing.
   Must append:
   - gitlab_project_id
   - source_branch_name (branch_slug)
   - review_request_url (MR URL)
   - generated_at (ISO timestamp)

12) Report success (TrackerPort.add_comment)
   Why: link user to MR and confirm outcome.
   Must include:
   - MR URL
   - branch name
   - timestamp

13) Transition Jira status (TrackerPort.update_status)
   Why: move ticket to WORKFLOW_STATE_SUCCESS (In Review) to trigger next automation.

14) Error handling (global)
   Why: never silently fail.
   - On any exception: TrackerPort.add_comment with failure reason and minimal debug context.
   - Do not proceed with remaining steps after a failure.

## B) AGENTIC_ACT_LOOP — Step-by-step (Do not skip)
1) Parse + validate YAML; report start (same reasons as deterministic)

2) Gather MCP tools from Ports
   Why: LLM can only act via explicit tools.
   - tools_tracker = TrackerPort.get_mcp_tools()
   - tools_vcs = VcsPort.get_mcp_tools()
   - tools_docs (if DocsPort exposes tools) OR prefetch docs deterministically before loop

3) Policy filter tools
   Why: safety guardrails.
   - Deny destructive ops (delete branch, force merge, overwrite, irreversible transitions)
   - Allow read-only + controlled write ops needed for mission

4) Preload critical context (recommended)
   Why: reduce ambiguity and cost.
   - Fetch architecture context deterministically OR allow only safe docs tools.

5) Build agentic mission prompt
   Why: align LLM behavior with constraints and success criteria.
   Must include:
   - Goal: generate scaffolding, create branch/commit/MR, update Jira, transition to In Review
   - Idempotency rule: if branch exists → report and stop
   - Tool safety rules: no destructive actions, no secrets
   - Stop conditions: iteration limit, cost limit, success condition

6) Run loop (BrainPort.run_agentic_loop)
   Why: LLM chooses next action, Python executes.
   - Python tool_executor routes calls to the correct Port.execute_tool(...)
   - Observations are fed back into the loop until success.

7) Final report + status transition
   Why: close the loop, maintain workflow continuity.

8) Error handling
   Why: same as deterministic.
   - Report failure; stop.

## Acceptance Checklist (must pass)
- Both modes implemented and testable.
- Deterministic mode has explicit step sequence with idempotent short-circuit.
- Agentic mode only exposes policy-filtered tools.
- All outbound side-effects go through Ports → MCP adapters.
- All mutable settings are ENV-driven.
- Start/success/failure reporting is always performed.
