---
name: mcp-integration
description: Implements Model Context Protocol (MCP) clients. Use when interacting with external tools like Jira, GitLab, Bitbucket, or Confluence, or when migrating away from legacy REST APIs.
---
# MCP Integration Skill

## When to use this skill
- Use this when implementing Application Ports (e.g., `TrackerPort`, `VcsPort`) in the `infrastructure/` layer.

## How to use it
1. **Death to REST**: You DO NOT write REST calls (`httpx`). You DO NOT build Atlassian Document Formats (ADF) manually. Use the official `mcp` Python SDK (`mcp.client.stdio` or `mcp.client.sse`).
2. **Implementation Pattern**:
   - Receive pure Domain DTOs.
   - Call the tool: `await session.call_tool(name="create_issue", arguments={"project": "..."})`.
   - Parse the `CallToolResult.content` and map back to a Domain DTO.
   - Catch `mcp.types.McpError` and wrap it in a `ProviderError`.

## Decision Tree: Coexistence Routing
- **Is the application interacting with multiple tools of the same type (e.g., GitLab AND Bitbucket)?**
  - *Action*: Infrastructure Adapters (e.g., `VcsRouter`) MUST dynamically route requests based on the Domain Context (e.g., `repo_ref.provider`) to the correct specific MCP client instance, hiding this complexity from the Application layer.