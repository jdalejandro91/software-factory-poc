from software_factory_poc.domain.aggregates.code_review_report import CodeReviewReport
from abc import ABC, abstractmethod
from typing import Any, Dict, List
from software_factory_poc.domain.entities.task import Task

class TrackerDriverPort(ABC):
    @abstractmethod
    async def get_task(self, ticket_id: str) -> Task: pass

    @abstractmethod
    async def update_status(self, ticket_id: str, status: str) -> None: pass

    @abstractmethod
    async def post_review_summary(self, ticket_id: str, report: CodeReviewReport) -> None: pass

    @abstractmethod
    async def add_comment(self, ticket_id: str, comment: str) -> None:
        pass

    @abstractmethod
    async def get_mcp_tools(self) -> List[Dict[str, Any]]: pass

    @abstractmethod
    async def execute_tool(self, tool_name: str, arguments: dict) -> Any: pass
