"""
DEPRECATED: Este adaptador REST ha sido reemplazado por JiraMcpAdapter.

Usa `infrastructure.adapters.drivers.tracker.jira_mcp_adapter.JiraMcpAdapter` en su lugar.
Este archivo se mantiene temporalmente para compatibilidad y sera eliminado en una futura iteracion.
"""
import warnings

from software_factory_poc.domain.mission.entities.mission import Mission
from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport
from software_factory_poc.application.drivers.tracker.tracker_driver import TrackerDriver

from software_factory_poc.infrastructure.drivers.tracker.clients.jira_http_client import JiraHttpClient
from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_description_mapper import \
    JiraDescriptionMapper
from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_panel_factory import JiraPanelFactory
from software_factory_poc.infrastructure.drivers.tracker.mappers.jira_adf_builder import JiraAdfBuilder


class JiraRestAdapter(TrackerDriver):
    """DEPRECATED: Usar JiraMcpAdapter. Este adaptador HTTP sera eliminado."""
    def __init__(self, client: JiraHttpClient, desc_mapper: JiraDescriptionMapper, panel_factory: JiraPanelFactory,
                 transition_in_review: str):
        warnings.warn(
            "JiraRestAdapter esta deprecado. Usar JiraMcpAdapter.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.client = client
        self.desc_mapper = desc_mapper
        self.panel_factory = panel_factory
        self.transition_in_review = transition_in_review

    async def get_task(self, ticket_id: str) -> Mission:
        data = await self.client.get_issue(ticket_id)

        summary = data.get("fields", {}).get("summary", "")
        status = data.get("fields", {}).get("status", {}).get("name", "OPEN")

        # 🟢 USAMOS TU MAPPER ADF PARA EXTRAER EL YAML A UNA ENTIDAD DE DOMINIO
        adf_description = data.get("fields", {}).get("description", {})
        task_description = self.desc_mapper.to_domain({"content": adf_description.get("content", [])})

        return Mission(
            ticket_id=ticket_id,
            title=summary,
            description=task_description,
            status=status
        )

    async def update_status(self, ticket_id: str, status: str) -> None:
        await self.client.transition_issue(ticket_id, status)

    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None:
        """🟢 USAMOS TU BUILDER ADF PARA PANELES VISUALES DE ERROR/SUCCESS"""
        title = "✅ Code Review Aprobado" if report.is_approved else "❌ Code Review Rechazado"

        details = f"{report.summary}\n\n"
        for issue in report.comments:
            line_info = f":{issue.line_number}" if issue.line_number else ""
            details += f"- [{issue.severity.value}] {issue.file_path}{line_info} -> {issue.description}\n"

        if not report.is_approved:
            # Usa el JiraAdfBuilder original para pintar panel de error
            adf_json = JiraAdfBuilder.build_error_panel(error_summary=report.summary, technical_detail=details)
            transition = "In Progress"
        else:
            # Usa el JiraAdfBuilder original para pintar panel de éxito
            adf_json = JiraAdfBuilder.build_success_panel(title=title, summary=report.summary, links={})
            transition = self.transition_in_review

        await self.client.transition_issue(ticket_id, transition)
        await self.client.add_adf_comment(ticket_id, adf_json)

    async def get_mcp_tools(self) -> list:
        return []

    async def execute_tool(self, tool_name: str, arguments: dict):
        pass