"""MCP-stdio client that translates Domain intent into Confluence tool calls."""

import os
from typing import Any

import structlog
from mcp.client.stdio import StdioServerParameters

from software_factory_poc.core.application.tools import DocsTool
from software_factory_poc.infrastructure.tools.common.base_mcp_client import BaseMcpClient
from software_factory_poc.infrastructure.tools.docs.confluence.config.confluence_settings import (
    ConfluenceSettings,
)
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_html_cleaner import (
    clean_html_and_truncate,
)
from software_factory_poc.infrastructure.tools.docs.confluence.confluence_search_parser import (
    extract_first_page_id,
    extract_page_list,
)

logger = structlog.get_logger()

class ConfluenceMcpClient(BaseMcpClient, DocsTool):
    _PROVIDER: str = "ConfluenceMCP"
    _METRICS_LABEL: str = "confluence"

    def __init__(self, settings: ConfluenceSettings) -> None:
        super().__init__()
        self._settings = settings

    def _server_params(self) -> StdioServerParameters:
        env = os.environ.copy()
        if self._settings.api_token:
            env["CONFLUENCE_API_TOKEN"] = self._settings.api_token.get_secret_value()
        env["CONFLUENCE_USERNAME"] = self._settings.user_email
        env["CONFLUENCE_URL"] = self._settings.base_url
        return StdioServerParameters(
            command=self._settings.mcp_atlassian_command,
            args=self._settings.mcp_atlassian_args,
            env=env,
        )

    async def get_architecture_context(self, page_id: str) -> str:
        logger.info("Fetching architecture page", page_id=page_id, source_system="ConfluenceMCP")
        result = await self._invoke_tool("confluence_get_page", {"page_id": page_id})
        return clean_html_and_truncate(self._extract_text(result))

    async def get_project_context(self, service_name: str) -> str:
        logger.info(
            "Fetching project context", service_name=service_name, source_system="ConfluenceMCP"
        )
        parent_id = await self._search_parent_page(service_name)
        if not parent_id:
            return f"No project documentation found for '{service_name}'."
        content = await self._fetch_children_content(parent_id)
        return clean_html_and_truncate(content)

    async def get_mcp_tools(self) -> list[dict[str, Any]]:
        response = await self._list_tools_response()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name.replace("confluence_", "docs_"),
                    "description": t.description or "",
                    "parameters": t.inputSchema or {},
                },
            }
            for t in response.tools
            if t.name.startswith("confluence_")
        ]

    async def execute_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        real_tool_name = tool_name.replace("docs_", "confluence_")
        safe_args = self._redactor.sanitize(arguments)
        result = await self._invoke_tool(real_tool_name, safe_args)
        return self._extract_text(result)

    async def _search_parent_page(self, service_name: str) -> str | None:
        query = f'title="{service_name}"'
        result = await self._invoke_tool("confluence_search", {"query": query})
        return extract_first_page_id(self._extract_text(result))

    async def _fetch_children_content(self, parent_id: str) -> str:
        query = f'ancestor="{parent_id}"'
        result = await self._invoke_tool("confluence_search", {"query": query})
        children = extract_page_list(self._extract_text(result))
        if not children:
            return f"Parent page {parent_id} has no child documents."
        return await self._collect_children_sections(children)

    async def _collect_children_sections(self, children: list[dict[str, str]]) -> str:
        sections: list[str] = []
        for child in children:
            content = await self._fetch_page_content(child["id"], child.get("title", "Untitled"))
            sections.append(content)
        return "\n\n".join(sections)

    async def _fetch_page_content(self, page_id: str, title: str) -> str:
        result = await self._invoke_tool("confluence_get_page", {"page_id": page_id})
        content = self._extract_text(result)
        return f"--- Document: {title} ---\n{content}"