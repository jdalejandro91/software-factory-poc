import httpx
from software_factory_poc.infrastructure.configuration.tool_settings import ToolSettings
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService

logger = LoggerFactoryService.build_logger(__name__)


class ConfluenceHttpClient:
    def __init__(self, settings: ToolSettings) -> None:
        self.base_url = settings.confluence_base_url.rstrip("/")
        self.auth = (
            settings.confluence_user_email,
            settings.confluence_api_token.get_secret_value(),
        )
        self.timeout = 30.0

    def get(self, path: str, params: dict = None) -> httpx.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        logger.info(f"GET {url}")
        with httpx.Client(timeout=self.timeout) as client:
            return client.get(url, auth=self.auth, params=params)

    def get_page(self, page_id: str) -> dict:
        """Obtiene el contenido de una página por su ID."""
        path = f"rest/api/content/{page_id}"
        response = self.get(path, params={"expand": "body.storage,body.view"})
        response.raise_for_status()
        return response.json()

    def search(self, query: str) -> list[dict]:
        """Busca páginas usando CQL (Confluence Query Language)."""
        # Asumimos búsqueda por título o texto si no es CQL puro
        cql_expression = f'text ~ "{query}"' if "=" not in query else query
        
        path = "rest/api/content/search"
        response = self.get(path, params={"cql": cql_expression, "limit": 1, "expand": "body.storage,body.view"})
        response.raise_for_status()
        data = response.json()
        return data.get("results", [])
