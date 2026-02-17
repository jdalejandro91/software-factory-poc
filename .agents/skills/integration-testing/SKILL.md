---
name: integration-testing
description: Creates integration tests for the Infrastructure layer using stubs. Use when testing MCP clients, LiteLLM adapters, coexistence routers, or dependency injection wiring.
---
# Integration Testing Skill

## When to use this skill
- Use this when writing tests for `infrastructure/` adapters and the DI Container (`ProviderResolver`).

## How to use it
1. **No Real APIs**: DO NOT hit real Jira/GitLab/Confluence APIs in standard test runs.
2. **Testing MCP Clients**: Mock the `mcp.client.session.ClientSession`. Assert that `call_tool` is invoked with the EXACT JSON-RPC payload expected by the MCP server.
3. **Testing LiteLLM**: Use `unittest.mock.patch('litellm.completion')` to return fake `ModelResponse` objects.
4. **Testing Coexistence Routing**: Verify that routers (e.g., `VcsRouter`) properly route a request with `repo_ref.provider == "GITLAB"` to the GitLab MCP client, and `BITBUCKET` to the Bitbucket client.