"""Unit tests — FetchScaffoldContextSkill (zero I/O, AsyncMock for Ports)."""

from unittest.mock import AsyncMock

from software_factory_poc.core.application.skills.scaffold.fetch_scaffold_context_skill import (
    FetchScaffoldContextSkill,
)


class TestFetchScaffoldContextSkill:
    async def test_delegates_to_docs_port(self) -> None:
        docs = AsyncMock()
        docs.get_architecture_context.return_value = "architecture: microservice"
        skill = FetchScaffoldContextSkill(docs=docs)

        result = await skill.execute("my-service")

        assert result == "architecture: microservice"
        docs.get_architecture_context.assert_awaited_once_with("my-service")

    async def test_returns_empty_string_when_docs_returns_empty(self) -> None:
        docs = AsyncMock()
        docs.get_architecture_context.return_value = ""
        skill = FetchScaffoldContextSkill(docs=docs)

        result = await skill.execute("unknown-service")

        assert result == ""
