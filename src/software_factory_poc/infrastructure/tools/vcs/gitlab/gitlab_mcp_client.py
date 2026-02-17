import json
import logging
from typing import Any

from mcp import ClientSession

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.vcs_port import VcsPort
from software_factory_poc.core.domain.delivery.commit_intent import CommitIntent
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class GitlabMcpClient(VcsPort):
    """MCP client that abstracts the protocol and translates Domain intent."""

    def __init__(self, mcp_session: ClientSession, project_id: str, redactor: RedactionService):
        self.mcp_session = mcp_session
        self.project_id = project_id
        self.redactor = redactor

    # ── Helper interno ──

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Ejecuta una herramienta MCP y traduce errores a ProviderError de dominio."""
        try:
            response = await self.mcp_session.call_tool(tool_name, arguments=arguments)
        except Exception as exc:
            raise ProviderError(
                provider="GitLabMCP",
                message=f"Fallo de conexion MCP al invocar '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if hasattr(response, "isError") and response.isError:
            error_detail = str(response.content) if response.content else "Sin detalle"
            raise ProviderError(
                provider="GitLabMCP",
                message=f"Error en tool '{tool_name}': {error_detail}",
                retryable=False,
            )

        return response

    def _extract_text(self, response: Any) -> str:
        """Extrae el texto plano de la respuesta MCP de forma segura."""
        if response.content and len(response.content) > 0:
            first = response.content[0]
            return getattr(first, "text", str(first))
        return ""

    # ── Scaffolding Flow Operations ──

    async def validate_branch_existence(self, branch_name: str) -> bool:
        """Verifica si una rama existe en el proyecto GitLab via MCP."""
        logger.info(f"[GitLabMCP] Verificando existencia de rama '{branch_name}'")
        try:
            await self._call_mcp(
                "gitlab_get_branch",
                arguments={
                    "project_id": self.project_id,
                    "branch": branch_name,
                },
            )
            return True
        except ProviderError:
            return False

    async def create_branch(self, branch_name: str, ref: str = "main") -> str:
        """Crea una rama en GitLab via MCP. Retorna la URL de la rama."""
        logger.info(f"[GitLabMCP] Creando rama '{branch_name}' desde '{ref}'")
        response = await self._call_mcp(
            "gitlab_create_branch",
            arguments={
                "project_id": self.project_id,
                "branch": branch_name,
                "ref": ref,
            },
        )
        raw_text = self._extract_text(response)
        try:
            data = json.loads(raw_text)
            return data.get("web_url", "")
        except (json.JSONDecodeError, TypeError):
            return raw_text

    async def create_merge_request(
        self, source_branch: str, target_branch: str, title: str, description: str
    ) -> str:
        """Crea un Merge Request en GitLab via MCP. Retorna la URL del MR."""
        logger.info(f"[GitLabMCP] Creando MR: '{source_branch}' -> '{target_branch}'")
        response = await self._call_mcp(
            "gitlab_create_merge_request",
            arguments={
                "project_id": self.project_id,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "title": title,
                "description": description,
            },
        )
        raw_text = self._extract_text(response)
        try:
            data = json.loads(raw_text)
            return data.get("web_url", "")
        except (json.JSONDecodeError, TypeError):
            return raw_text

    # ── Commit Operation ──

    async def commit_changes(self, intent: CommitIntent) -> str:
        if intent.is_empty():
            raise ValueError("El commit no contiene archivos.")

        actions = [
            {
                "action": "create" if f.is_new else "update",
                "file_path": f.path,
                "content": f.content,
            }
            for f in intent.files
        ]

        mcp_args = {
            "project_id": self.project_id,
            "branch": intent.branch.value,
            "commit_message": intent.message,
            "actions": actions,
        }

        response = await self.mcp_session.call_tool("gitlab_create_commit", arguments=mcp_args)
        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(f"Error MCP GitLab: {response.content}")

        return json.loads(self._extract_text(response)).get("commit_hash")

    async def get_merge_request_diff(self, mr_iid: str) -> str:
        """Extrae el diff proceduralmente via herramienta MCP."""
        response = await self.mcp_session.call_tool(
            "gitlab_get_merge_request_changes",
            arguments={"project_id": self.project_id, "merge_request_iid": str(mr_iid)},
        )
        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(f"Error MCP GitLab Diff: {response.content}")
        return self._extract_text(response)

    async def publish_review(self, mr_iid: str, report: CodeReviewReport) -> None:
        """Publica el analisis usando herramientas MCP de GitLab."""
        status_icon = "APROBADO" if report.is_approved else "REQUIERE CAMBIOS"
        main_note = f"### BrahMAS Code Review: {status_icon}\n\n{report.summary}"

        await self.mcp_session.call_tool(
            "gitlab_create_merge_request_note",
            arguments={
                "project_id": self.project_id,
                "merge_request_iid": str(mr_iid),
                "body": main_note,
            },
        )

        for issue in report.comments:
            body = f"**[{issue.severity.value}]** {issue.description}\n\n*Sugerencia:* `{issue.suggestion}`"
            await self.mcp_session.call_tool(
                "gitlab_create_merge_request_discussion",
                arguments={
                    "project_id": self.project_id,
                    "merge_request_iid": str(mr_iid),
                    "file_path": issue.file_path,
                    "line": issue.line_number if issue.line_number else 1,
                    "body": body,
                },
            )

        if report.is_approved:
            await self.mcp_session.call_tool(
                "gitlab_approve_merge_request",
                arguments={"project_id": self.project_id, "merge_request_iid": str(mr_iid)},
            )

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        response = await self.mcp_session.list_tools()
        return [
            {
                "name": t.name.replace("gitlab_", "vcs_"),
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in response.tools
            if t.name.startswith("gitlab_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        real_tool_name = tool_name.replace("vcs_", "gitlab_")
        if "project_id" not in arguments:
            arguments["project_id"] = self.project_id

        safe_args = self.redactor.sanitize(arguments)
        response = await self.mcp_session.call_tool(real_tool_name, arguments=safe_args)

        if hasattr(response, "isError") and response.isError:
            raise RuntimeError(response.content)
        return self._extract_text(response)
