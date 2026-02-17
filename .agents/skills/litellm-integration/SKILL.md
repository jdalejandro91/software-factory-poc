---
name: litellm-integration
description: Integrates Large Language Models using the LiteLLM library. Use when adding AI generation, tool calling (MCP), or structured outputs to the BrainPort in the infrastructure layer.
---
# LiteLLM Integration Skill

## When to use this skill
- Use this exclusively when implementing the `BrainPort` in `infrastructure/tools/llm/`.

## How to use it
- **The Universal Call**: ALWAYS use `litellm.completion(model=..., messages=...)`. Delete direct `openai` or `anthropic` SDK imports.
- **Dynamic Routing**: Inject the `model` string dynamically from configuration to support fallback routing.
- **Resilience**: Wrap calls in `try/except litellm.exceptions.OpenAIError`. Raise a domain `ProviderError`.

## Decision Tree: LLM Modalities
- **Scenario 1: You need a guaranteed JSON structure (Deterministic Flow).**
  - *Action*: Pass a Pydantic class to the `response_format` parameter. Catch `pydantic.ValidationError` and wrap it in `ProviderError`.
- **Scenario 2: You are executing an Agentic Act Loop.**
  - *Action*: Pass MCP schemas to the `tools=[...]` parameter. Handle `tool_calls` in the response, yield control to the Python orchestrator to execute the tool, and append the `tool_result` message to the history.