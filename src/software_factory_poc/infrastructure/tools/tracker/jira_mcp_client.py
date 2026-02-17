import json
import logging
from typing import Any

from mcp import ClientSession

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.tracker_port import TrackerPort
from software_factory_poc.core.domain.mission.entities.mission import Mission, TaskDescription
from software_factory_poc.core.domain.quality.code_review_report import CodeReviewReport
from software_factory_poc.infrastructure.adapters.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class JiraMcpClient(TrackerPort):
    """MCP client for Jira. Replaces JiraRestAdapter removing direct HTTP dependencies.

    Receives a MCP ClientSession and translates Domain intentions to call_tool
    calls against the Jira MCP server.
    """

    def __init__(
        self,
        mcp_session: ClientSession,
        desc_mapper: JiraDescriptionMapper,
        transition_in_review: str,
        redactor: RedactionService,
    ):
        self.mcp_session = mcp_session
        self.desc_mapper = desc_mapper
        self.transition_in_review = transition_in_review
        self.redactor = redactor

    # ──────────────────────────────────────────────
    #  Helper interno para llamadas MCP con manejo de errores
    # ──────────────────────────────────────────────

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        """Ejecuta una herramienta MCP y traduce errores a ProviderError de dominio."""
        try:
            response = await self.mcp_session.call_tool(tool_name, arguments=arguments)
        except Exception as exc:
            raise ProviderError(
                provider="JiraMCP",
                message=f"Fallo de conexion MCP al invocar '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if hasattr(response, "isError") and response.isError:
            error_detail = str(response.content) if response.content else "Sin detalle"
            raise ProviderError(
                provider="JiraMCP",
                message=f"Error en tool '{tool_name}': {error_detail}",
                retryable=False,
            )

        return response

    def _extract_text(self, response: Any) -> str:
        """Extrae el texto plano de la respuesta MCP de forma segura."""
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""

    def _parse_json(self, raw_text: str, context: str) -> dict[str, Any]:
        """Parsea JSON de respuesta MCP con manejo de errores limpio."""
        try:
            return json.loads(raw_text)
        except (json.JSONDecodeError, TypeError) as exc:
            raise ProviderError(
                provider="JiraMCP",
                message=f"Respuesta no-JSON en '{context}': {raw_text[:200]}",
            ) from exc

    # ──────────────────────────────────────────────
    #  Implementacion de TrackerPort
    # ──────────────────────────────────────────────

    async def get_task(self, ticket_id: str) -> Mission:
        """Obtiene una tarea de Jira via MCP y la mapea a la entidad de dominio Mission."""
        logger.info(f"[JiraMCP] Obteniendo tarea {ticket_id}")

        response = await self._call_mcp("jira_get_issue", arguments={"issue_key": ticket_id})
        raw_text = self._extract_text(response)
        data = self._parse_json(raw_text, context=f"get_task({ticket_id})")

        fields = data.get("fields", {})
        summary = fields.get("summary", "")
        status = fields.get("status", {}).get("name", "OPEN")
        project_key = fields.get("project", {}).get("key", "")
        issue_type = fields.get("issuetype", {}).get("name", "Task")

        adf_description = fields.get("description", {})
        task_description: TaskDescription = self.desc_mapper.to_domain(
            {"content": adf_description.get("content", [])} if adf_description else {"content": []}
        )

        return Mission(
            id=data.get("id", ticket_id),
            key=data.get("key", ticket_id),
            summary=summary,
            status=status,
            project_key=project_key,
            issue_type=issue_type,
            description=task_description,
        )

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        """Agrega un comentario a una tarea de Jira via MCP.

        The MCP server accepts Markdown and handles conversion to ADF/Wiki internally.
        """
        logger.info(f"[JiraMCP] Agregando comentario a {ticket_id}")

        await self._call_mcp("jira_add_comment", arguments={
            "issue_key": ticket_id,
            "comment": comment,
        })

    async def update_status(self, ticket_id: str, status: str) -> None:
        """Transiciona el estado de una tarea en Jira via MCP."""
        logger.info(f"[JiraMCP] Transicionando {ticket_id} -> '{status}'")

        await self._call_mcp("jira_transition_issue", arguments={
            "issue_key": ticket_id,
            "transition_name": status,
        })

    async def update_task_description(self, ticket_id: str, description: str) -> None:
        """Updates a task description in Jira via MCP.

        The description should be in Markdown format. The MCP server converts it
        to ADF (Cloud) or Wiki Markup (Server/DC) internally.
        """
        logger.info(f"[JiraMCP] Actualizando descripcion de {ticket_id}")

        await self._call_mcp("jira_update_issue", arguments={
            "issue_key": ticket_id,
            "fields": {"description": description},
        })

    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        """Posts the Code Review summary as a Markdown comment via MCP.

        The MCP server accepts Markdown and converts to ADF/Wiki internally.
        No ADF builders needed on our side.
        """
        logger.info(f"[JiraMCP] Publicando resumen de review en {ticket_id}")

        emoji = "APROBADO" if report.is_approved else "REQUIERE CAMBIOS"

        lines = [
            f"## BrahMAS Code Review: {emoji}",
            "",
            report.summary,
        ]

        if report.comments:
            lines.append("")
            lines.append("### Hallazgos")
            lines.append("")
            lines.append("| Severidad | Archivo | Descripcion |")
            lines.append("|-----------|---------|-------------|")
            for issue in report.comments:
                line_ref = f":{issue.line_number}" if issue.line_number else ""
                lines.append(
                    f"| **{issue.severity.value}** "
                    f"| `{issue.file_path}{line_ref}` "
                    f"| {issue.description} |"
                )

        comment_md = "\n".join(lines)

        # 1. Transition status
        transition = self.transition_in_review if report.is_approved else "In Progress"
        await self.update_status(ticket_id, transition)

        # 2. Post Markdown comment
        await self._call_mcp("jira_add_comment", arguments={
            "issue_key": ticket_id,
            "comment": comment_md,
        })

    # ──────────────────────────────────────────────
    #  Soporte Agentic Mode (MCP tool discovery + execution)
    # ──────────────────────────────────────────────

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        """Retorna las herramientas MCP disponibles del servidor Jira, normalizando prefijos."""
        response = await self.mcp_session.list_tools()
        return [
            {
                "name": t.name.replace("jira_", "tracker_"),
                "description": t.description,
                "inputSchema": t.inputSchema,
            }
            for t in response.tools
            if t.name.startswith("jira_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict) -> Any:
        """Proxy seguro para ejecutar herramientas MCP de Jira en modo agentico."""
        real_tool_name = tool_name.replace("tracker_", "jira_")
        safe_args = self.redactor.sanitize(arguments)

        response = await self._call_mcp(real_tool_name, arguments=safe_args)
        return self._extract_text(response)
