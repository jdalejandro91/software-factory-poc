from software_factory_poc.application.ports.drivers.research_driver_port import ResearchDriverPort

class ConfluenceRestAdapter(ResearchDriverPort):
    def __init__(self, confluence_http_client):
        self.client = confluence_http_client

    async def get_architecture_context(self, project_context_id: str) -> str:
        # Llamada a tu lógica REST original
        page_data = await self.client.get_page(project_context_id)
        return str(page_data.get("body", {}).get("storage", {}).get("value", ""))