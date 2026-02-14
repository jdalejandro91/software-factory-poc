import json
from typing import Any, Dict, List
from mcp import ClientSession
from software_factory_poc.application.ports.drivers.vcs_driver_port import VcsDriverPort
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService


class GitlabMcpAdapter(VcsDriverPort):
    """Adaptador MCP que abstrae el protocolo y traduce la intención del Dominio."""

    def __init__(self, mcp_session: ClientSession, project_id: str, redactor: RedactionService):
        self.mcp_session = mcp_session
        self.project_id = project_id
        self.redactor = redactor

    async def commit_changes(self, intent: CommitIntent) -> str:
        if intent.is_empty(): raise ValueError("El commit no contiene archivos.")

        # Traducción del Dominio al formato rígido de la tool de GitLab MCP
        actions = [
            {"action": "create" if f.is_new else "update", "file_path": f.path, "content": f.content}
            for f in intent.files
        ]

        mcp_args = {
            "project_id": self.project_id,
            "branch": intent.branch.value,
            "commit_message": intent.message,
            "actions": actions
        }

        # LLAMADA AL SERVIDOR MCP (Reemplaza a tu viejo gitlab_http_client.py)
        response = await self.mcp_session.call_tool("gitlab_create_commit", arguments=mcp_args)
        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(f"Error MCP GitLab: {response.content}")

        return json.loads(response.content[0].text).get("commit_hash")

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        response = await self.mcp_session.list_tools()
        tools = []
        for t in response.tools:
            if t.name.startswith("gitlab_"):
                # MAGIA MCP: Ocultamos que es 'gitlab' usando 'vcs'. Evita vendor lock-in en el prompt.
                normalized_name = t.name.replace("gitlab_", "vcs_")
                tools.append({"name": normalized_name, "description": t.description, "inputSchema": t.inputSchema})
        return tools

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self.project_id

        safe_args = self.redactor.sanitize(arguments)
        response = await self.mcp_session.call_tool(real_tool_name, arguments=safe_args)

        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(response.content)
        return response.content[0].text