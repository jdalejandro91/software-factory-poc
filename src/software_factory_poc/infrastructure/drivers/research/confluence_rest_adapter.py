"""
DEPRECATED: Este adaptador REST ha sido reemplazado por ConfluenceMcpAdapter.

Usa `infrastructure.adapters.drivers.research.confluence_mcp_adapter.ConfluenceMcpAdapter` en su lugar.
Este archivo se mantiene temporalmente para compatibilidad y sera eliminado en una futura iteracion.
"""
import warnings

from software_factory_poc.application.drivers import ResearchDriverPort


class ConfluenceRestAdapter(ResearchDriverPort):
    """DEPRECATED: Usar ConfluenceMcpAdapter. Este adaptador HTTP sera eliminado."""

    def __init__(self, confluence_http_client):
        warnings.warn(
            "ConfluenceRestAdapter esta deprecado. Usar ConfluenceMcpAdapter.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.client = confluence_http_client

    async def get_architecture_context(self, project_context_id: str) -> str:
        page_data = await self.client.get_page(project_context_id)
        return str(page_data.get("body", {}).get("storage", {}).get("value", ""))