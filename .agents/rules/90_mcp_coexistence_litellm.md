# 40_mcp_coexistence_litellm.md — Coexistence Routing, MCP, and LiteLLM

## 1. La Regla de Coexistencia Tecnológica (El Patrón Router)
La arquitectura DEBE soportar entornos corporativos mixtos (repositorios legacy en Bitbucket, repositorios nuevos en GitLab, o Jira junto a Azure DevOps simultáneamente).
- **Core (Application):** NUNCA sabe qué tecnología subyace. La capa de aplicación llama a `vcs_port.create_branch(repo_ref: RepoRef)`.
- **Infrastructure (`infrastructure/tools/vcs/`):** Implementa un **Router (Gateway de Coexistencia)** que cumple con la interfaz del puerto.
  - Al recibir una llamada, evalúa el origen en el Value Object (ej. `repo_ref.provider == "BITBUCKET"`).
  - Enruta dinámicamente la petición al Cliente MCP correspondiente (ej. `BitbucketMcpClient` o `GitlabMcpClient`).
  - **Resultado:** Añadir soporte para GitHub mañana implica crear un nuevo cliente MCP en infraestructura y agregarlo al Router. CERO impacto en la capa `core/`.

## 2. La Regla MCP (Tooling Plane)
**PROHIBIDO:** Escribir clientes REST manuales (`httpx`, `requests`), mappers complejos de payloads (como ADF builders para Jira), o parseadores de APIs específicas en Python.
- **SOLUCIÓN:** Usar EXCLUSIVAMENTE el SDK oficial `mcp` para Python (`mcp.client.stdio` o `sse`).
- Las clases en `infrastructure/tools/` actúan puramente como **MCP Clients**. Se conectan a servidores MCP externos (locales o remotos). En lugar de construir requests HTTP, el adaptador simplemente hace `session.call_tool("create_issue", arguments={...})`.
- Todo código antiguo que construya payloads HTTP o parsee respuestas REST es **Código Zombie** y debe ser eliminado.

## 3. La Regla LiteLLM (Brain Port)
**PROHIBIDO:** Usar los SDKs oficiales de OpenAI, Anthropic, Gemini o DeepSeek directamente, o crear bridges LLM manuales.
- **SOLUCIÓN:** Usar EXCLUSIVAMENTE la librería `litellm` (`litellm.completion`).
- `infrastructure/tools/llm/` implementa el `LlmPort` utilizando `litellm`. Esta librería estandariza nativamente el enrutamiento de modelos, retries, *Tool Calling* y validación de *Structured Outputs* (Pydantic schemas) unificando más de 100 proveedores de la industria detrás de una interfaz idéntica a la de OpenAI.