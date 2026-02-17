# CodeReviewerAgent Dual-Flow Rule (MCP-Only)

## Scope
Applies to: `core/application/agents/code_reviewer_agent.py` (or equivalent) and any code it orchestrates (ports, policies, prompt builders).
This rule is mandatory: do not omit any step or invariant described below.

## Goal
Implement and maintain CodeReviewerAgent so it supports TWO execution modes:
- A) `LINEAR_DETERMINISTIC` (cheap, auditable code review pipeline)
- B) `AGENTIC_ACT_LOOP` (ReAct loop for large diffs, diagnostics, retries, exploration)

Both modes MUST interact with external systems ONLY via Ports whose infrastructure adapters call MCP tools.
Manual REST API calls from application/domain code are forbidden.

## Non-Negotiables (Invariants)
1) MCP-only outbound:
   - GitLab/Jira/Confluence interactions via Ports only.
2) Deterministic mode control:
   - In `LINEAR_DETERMINISTIC`, LLM NEVER controls the flow.
   - LLM usage is one-shot, structured output only (CodeReviewReport schema).
3) Agentic mode sandbox:
   - Tools are collected from Ports, filtered by policies, then exposed to LLM.
   - Python runtime executes tool calls, not the LLM.
4) Provider support:
   - If VCS_PROVIDER is not supported (e.g., BITBUCKET for now), raise a clear error.
   - Agent must catch and report failure to Jira.
5) Reporting:
   - Always report start.
   - Always report success/failure with actionable detail.
6) Configuration:
   - Everything variable must come from ENV; no hardcoded IDs/URLs/models/tokens.

## Inputs (expected)
From Jira webhook payload:
- Issue key
- Issue description containing YAML with `code_review_params`:
  - gitlab_project_id
  - source_branch_name
  - review_request_url
  - generated_at

From ENV:
- VCS_PROVIDER (currently: GITLAB supported; others must fail clearly)
- CODE_REVIEW_LLM_MODEL_PRIORITY
- ARCHITECTURE_DOC_PAGE_ID
- Provider credentials and base URLs

## Mode Selection
Default to `LINEAR_DETERMINISTIC`.
Use `AGENTIC_ACT_LOOP` ONLY if:
- diff is too large for one-shot review,
- deterministic review/publish failed and recovery/self-healing is enabled,
- mission is explicitly marked as agentic.

## A) LINEAR_DETERMINISTIC — Step-by-step (Do not skip)
1) Parse + validate YAML (code_review_params)
   Why: without MR metadata, review cannot proceed.
   - If missing/invalid → report failure and stop.

2) Report start (TrackerPort.add_comment)
   Why: traceability.

3) Validate existence (branch and MR)
   Why: avoid wasting calls and provide early failure clarity.
   - If branch or MR missing → report failure and stop.

4) Fetch knowledge context (DocsPort)
   Why: review must check compliance against real standards.
   - DocsPort.get_project_context(service_name if available, else derive from ticket context)
   - DocsPort.get_architecture_context(ARCHITECTURE_DOC_PAGE_ID)

5) Obtain MR diff (VcsPort)
   Why: diff is the primary object of review.
   - VcsPort.get_merge_request_diff(mr_id derived from review_request_url)

6) Build review prompt (code_review_prompt_builder)
   Why: stable prompt → stable structured report.
   Prompt MUST include:
   - mission intent and ticket requirements
   - architecture/standards context
   - diff content
   - strict evaluation dimensions:
     - correctness vs requirement
     - security/vulnerabilities
     - SOLID / Clean Code / naming
     - API usage correctness
     - tests & documentation
   - required structured output schema:
     - severity levels
     - findings grouped by file/line when possible
     - actionable recommendations
     - summary and next steps

7) One-shot structured LLM call (BrainPort.generate_structured)
   Why: produce a machine-usable CodeReviewReport.

8) Publish review to VCS (VcsPort.publish_review)
   Why: place feedback where developers act (MR).
   - Mapping to provider-specific format must occur in infrastructure/provider layer.

9) Report success to Jira (TrackerPort.post_review_summary or add_comment)
   Why: close the loop and provide link to MR.
   - Include MR URL and brief summary (counts by severity).

10) Error handling (global)
   Why: never silently fail.
   - On any exception: TrackerPort.add_comment with failure reason and minimal debug context.
   - Do not proceed after failure.

## B) AGENTIC_ACT_LOOP — Step-by-step (Do not skip)
1) Parse + validate YAML; report start (same reasons as deterministic)

2) Gather MCP tools from Ports
   Why: LLM can only act via explicit tools.
   - tools_tracker = TrackerPort.get_mcp_tools()
   - tools_vcs = VcsPort.get_mcp_tools()
   - tools_docs (if DocsPort exposes tools) OR prefetch docs deterministically before loop

3) Policy filter tools
   Why: safety and scope control.
   - Deny destructive ops (merge, approve, delete branches, irreversible transitions unless explicitly allowed)
   - Allow read-only inspection and controlled publish ops

4) Build agentic mission prompt
   Why: guide tool usage and enforce report shape.
   Must include:
   - Goal: produce CodeReviewReport and publish review to MR
   - Constraints: no destructive actions, no secrets, adhere to standards
   - Stop conditions: iteration limit, cost limit
   - Required final output: structured CodeReviewReport (even if publish fails)

5) Run loop (BrainPort.run_agentic_loop)
   Why: LLM chooses next action, Python executes.
   - Python tool_executor routes calls to Port.execute_tool(...)
   - Observations are fed back into the loop until success or abort

6) Publish + Jira report
   Why: close the workflow.
   - Ensure review is published if possible; otherwise publish summary to Jira explaining inability.

7) Error handling
   Why: same as deterministic.
   - Report failure; stop.

## Acceptance Checklist (must pass)
- Both modes implemented and testable.
- Deterministic mode is explicit, auditable, and one-shot structured LLM only.
- Agentic mode exposes only policy-filtered tools; Python executes calls.
- Provider-not-supported path is explicit and reported to Jira.
- All outbound side-effects go through Ports → MCP adapters.
- All mutable settings are ENV-driven.
- Start/success/failure reporting is always performed.
