import json
from typing import Any, Dict, List
from mcp import ClientSession
from software_factory_poc.application.ports.drivers.vcs_driver_port import VcsDriverPort
from software_factory_poc.domain.aggregates.commit_intent import CommitIntent
from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport
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

    async def get_merge_request_diff(self, mr_iid: str) -> str:
        """Extrae el diff proceduralmente vía herramienta MCP."""
        response = await self.mcp_session.call_tool(
            "gitlab_get_merge_request_changes",
            arguments={"project_id": self.project_id, "merge_request_iid": str(mr_iid)}
        )
        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(f"Error MCP GitLab Diff: {response.content}")
        return response.content[0].text

    async def publish_review(self, mr_iid: str, report: CodeReviewReport) -> None:
        """Pública el análisis usando herramientas MCP de GitLab (Comments/Approvals)."""
        status_icon = "✅ APROBADO" if report.is_approved else "❌ REQUIERE CAMBIOS"
        main_note = f"### BrahMAS Code Review: {status_icon}\n\n{report.summary}"

        # 1. Comentario General
        await self.mcp_session.call_tool("gitlab_create_merge_request_note", arguments={
            "project_id": self.project_id,
            "merge_request_iid": str(mr_iid),
            "body": main_note
        })

        # 2. Comentarios Inline
        for issue in report.comments:
            body = f"**[{issue.severity.value}]** {issue.description}\n\n*Sugerencia:* `{issue.suggestion}`"
            await self.mcp_session.call_tool("gitlab_create_merge_request_discussion", arguments={
                "project_id": self.project_id,
                "merge_request_iid": str(mr_iid),
                "file_path": issue.file_path,
                "line": issue.line_number if issue.line_number else 1,
                "body": body
            })

        # 3. Aprobar MR si está ok
        if report.is_approved:
            await self.mcp_session.call_tool("gitlab_approve_merge_request", arguments={
                "project_id": self.project_id,
                "merge_request_iid": str(mr_iid)
            })

    async def get_mcp_tools(self) -> List[Dict[str, Any]]:
        response = await self.mcp_session.list_tools()
        return [{"name": t.name.replace("gitlab_", "vcs_"), "description": t.description, "inputSchema": t.inputSchema}
                for t in response.tools if t.name.startswith("gitlab_")]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self.project_id

        safe_args = self.redactor.sanitize(arguments)
        response = await self.mcp_session.call_tool(real_tool_name, arguments=safe_args)

        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(response.content)
        return response.content[0].text