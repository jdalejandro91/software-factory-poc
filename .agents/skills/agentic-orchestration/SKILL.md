---
name: agentic-orchestration
description: Designs and implements ReAct loops, deterministic flows, and progressive autonomy. Use when building Agent orchestration logic, execution modes, or tool routing in the application layer.
---
# Agentic Orchestration Skill

## When to use this skill
- Use this when implementing the `execute` methods of True Agents (`ScaffolderAgent`, `CodeReviewerAgent`).

## Decision Tree: Execution Mode
- **If `ExecutionMode.LINEAR_DETERMINISTIC`:**
  - *Action*: The Agent executes pure Python `Skills` sequentially from `core/application/skills/`. The LLM is used minimally via One-Shot calls.
- **If `ExecutionMode.AGENTIC_ACT_LOOP`:**
  - *Action*: The Agent enters a native Python `while` loop (`Think -> Act -> Observe`).

## How to use it (Act Loop Implementation)
1. **Tool Exposure**: Extract schemas from `ToolingPort`, filter them through `policies/`, and inject them into `BrainPort`.
2. **Safety First**: ALWAYS enforce a `max_iterations` limit (e.g., 5 or 10) to prevent infinite loops.
3. **Policy Gating**: BEFORE the Python loop executes an MCP tool requested by the LLM, call `policy.validate_tool_execution(tool_call)`. 
   - *Self-Healing*: If denied, append a `tool_result` to the LLM: *"Error: Policy Violation"* to let it self-correct. Do not crash the app.