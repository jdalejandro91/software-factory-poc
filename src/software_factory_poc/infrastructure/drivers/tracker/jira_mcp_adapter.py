import json
import logging
from typing import Any

from mcp import ClientSession

from software_factory_poc.application.drivers.tracker.tracker_driver import TrackerDriver
from software_factory_poc.application.drivers.common.exceptions.provider_error import ProviderError
from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport
from software_factory_poc.domain.entities.task import Task, TaskDescription
from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_adf_builder import JiraAdfBuilder
from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_description_mapper import (
    JiraDescriptionMapper,
)
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class JiraMcpAdapter(TrackerDriver):
    """Adaptador MCP para Jira. Reemplaza al JiraRestAdapter eliminando dependencias HTTP directas.

    Sigue el mismo patrón de GitlabMcpAdapter: recibe una ClientSession MCP y traduce
    las intenciones del Dominio a llamadas call_tool del servidor MCP de Jira.
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
    #  Implementacion de TrackerDriverPort
    # ──────────────────────────────────────────────

    async def get_task(self, ticket_id: str) -> Task:
        """Obtiene una tarea de Jira via MCP y la mapea a la entidad de dominio Task."""
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

        return Task(
            id=data.get("id", ticket_id),
            key=data.get("key", ticket_id),
            summary=summary,
            status=status,
            project_key=project_key,
            issue_type=issue_type,
            description=task_description,
        )

    async def add_comment(self, ticket_id: str, comment: str) -> None:
        """Agrega un comentario de texto plano a una tarea de Jira via MCP."""
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

    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        """Publica el resumen del Code Review como panel ADF en Jira y transiciona el estado."""
        logger.info(f"[JiraMCP] Publicando resumen de review en {ticket_id}")

        title = "Code Review Aprobado" if report.is_approved else "Code Review Rechazado"

        details = f"{report.summary}\n\n"
        for issue in report.comments:
            line_info = f":{issue.line_number}" if issue.line_number else ""
            details += f"- [{issue.severity.value}] {issue.file_path}{line_info} -> {issue.description}\n"

        if report.is_approved:
            adf_json = JiraAdfBuilder.build_success_panel(title=title, summary=report.summary, links={})
            transition = self.transition_in_review
        else:
            adf_json = JiraAdfBuilder.build_error_panel(error_summary=report.summary, technical_detail=details)
            transition = "In Progress"

        # 1. Transicionar estado
        await self.update_status(ticket_id, transition)

        # 2. Publicar comentario ADF estructurado
        adf_body = json.dumps(adf_json)
        await self._call_mcp("jira_add_comment", arguments={
            "issue_key": ticket_id,
            "comment": adf_body,
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
