import json
import logging
from typing import Any

from mcp import ClientSession

from software_factory_poc.core.application.ports.common.exceptions.provider_error import (
    ProviderError,
)
from software_factory_poc.core.application.ports.docs_port import DocsPort
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class ConfluenceMcpClient(DocsPort):
    """MCP client for Confluence. Replaces ConfluenceRestAdapter removing direct HTTP dependencies.

    Receives a MCP ClientSession and translates Domain intentions to call_tool
    calls against the Confluence MCP server.
    """

    def __init__(self, mcp_session: ClientSession, redactor: RedactionService):
        self.mcp_session = mcp_session
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
                provider="ConfluenceMCP",
                message=f"Fallo de conexion MCP al invocar '{tool_name}': {exc}",
                retryable=True,
            ) from exc

        if hasattr(response, "isError") and response.isError:
            error_detail = str(response.content) if response.content else "Sin detalle"
            raise ProviderError(
                provider="ConfluenceMCP",
                message=f"Error en tool '{tool_name}': {error_detail}",
                retryable=False,
            )

        return response

    def _extract_text(self, response: Any) -> str:
        """Extrae el texto plano de la respuesta MCP de forma segura."""
        if response.content and len(response.content) > 0:
            return response.content[0].text
        return ""

    # ──────────────────────────────────────────────
    #  Implementacion de DocsPort
    # ──────────────────────────────────────────────

    async def get_project_context(self, service_name: str) -> str:
        """Obtiene el contexto de un proyecto desde Confluence via MCP."""
        logger.info(f"[ConfluenceMCP] Obteniendo contexto de proyecto para {service_name}")

        response = await self._call_mcp(
            "confluence_search",
            arguments={
                "query": service_name,
            },
        )
        return self._extract_text(response)

    async def get_architecture_context(self, project_context_id: str) -> str:
        """Obtiene el contexto arquitectonico desde una pagina de Confluence via MCP."""
        logger.info(
            f"[ConfluenceMCP] Obteniendo contexto de arquitectura desde pagina {project_context_id}"
        )

        response = await self._call_mcp(
            "confluence_get_page",
            arguments={
                "page_id": project_context_id,
            },
        )

        raw_text = self._extract_text(response)

        try:
            data = json.loads(raw_text)
            return str(data.get("body", {}).get("storage", {}).get("value", raw_text))
        except (json.JSONDecodeError, TypeError):
            return raw_text
