import json
import logging
from typing import Any

from mcp import ClientSession

from software_factory_poc.application.drivers import ResearchDriverPort
from software_factory_poc.application.drivers.common.exceptions.provider_error import ProviderError
from software_factory_poc.infrastructure.observability.redaction_service import RedactionService

logger = logging.getLogger(__name__)


class ConfluenceMcpAdapter(ResearchDriverPort):
    """Adaptador MCP para Confluence. Reemplaza al ConfluenceRestAdapter eliminando dependencias HTTP directas.

    Sigue el mismo patron de GitlabMcpAdapter: recibe una ClientSession MCP y traduce
    las intenciones del Dominio a llamadas call_tool del servidor MCP de Confluence.
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
    #  Implementacion de ResearchDriverPort
    # ──────────────────────────────────────────────

    async def get_architecture_context(self, project_context_id: str) -> str:
        """Obtiene el contexto arquitectonico desde una pagina de Confluence via MCP.

        Args:
            project_context_id: ID de la pagina de Confluence con las normas de arquitectura.

        Returns:
            Contenido textual de la pagina (body storage value).
        """
        logger.info(f"[ConfluenceMCP] Obteniendo contexto de arquitectura desde pagina {project_context_id}")

        response = await self._call_mcp("confluence_get_page", arguments={
            "page_id": project_context_id,
        })

        raw_text = self._extract_text(response)

        # El servidor MCP puede retornar JSON con la estructura de pagina o texto plano.
        # Intentamos parsear como JSON para extraer el body; si falla, retornamos el texto directo.
        try:
            data = json.loads(raw_text)
            return str(data.get("body", {}).get("storage", {}).get("value", raw_text))
        except (json.JSONDecodeError, TypeError):
            return raw_text
