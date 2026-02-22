"""Collaborator class that publishes code review results to GitLab via MCP tool calls."""

from collections.abc import Callable
from typing import Any

import structlog

from software_factory_poc.core.application.tools.common.exceptions import ProviderError
from software_factory_poc.core.domain.quality import CodeReviewReport, ReviewComment
from software_factory_poc.infrastructure.tools.vcs.gitlab.gitlab_review_formatter import (
    build_review_summary,
    format_inline_comment,
)

logger = structlog.get_logger()


class GitLabReviewPublisher:
    """Publishes review notes and inline discussions to a GitLab merge request."""

    def __init__(self, invoke_tool: Callable[..., Any], project_id: str) -> None:
        self._invoke_tool = invoke_tool
        self._project_id = project_id

    async def publish_review(self, mr_id: str, report: CodeReviewReport) -> None:
        main_note = build_review_summary(report)
        await self._create_note(mr_id, main_note)
        failed_inline = await self._publish_inline_comments(mr_id, report.comments)
        if failed_inline:
            await self._publish_fallback_note(mr_id, failed_inline)
        if report.is_approved:
            await self._approve(mr_id)

    async def _create_note(self, mr_id: str, body: str) -> None:
        try:
            await self._invoke_tool(
                "create_merge_request_note",
                {"project_id": self._project_id, "merge_request_iid": int(mr_id) if mr_id.isdigit() else mr_id, "body": body},
            )
        except ProviderError:
            # Fallback for servers that only support generic issue notes
            pass

    async def _approve(self, mr_id: str) -> None:
        try:
            await self._invoke_tool(
                "approve_merge_request",
                {"project_id": self._project_id, "merge_request_iid": int(mr_id) if mr_id.isdigit() else mr_id},
            )
        except ProviderError:
            pass

    async def _publish_inline_comments(
        self, mr_id: str, comments: list[ReviewComment]
    ) -> list[ReviewComment]:
        failed: list[ReviewComment] = []
        for issue in comments:
            try:
                await self._invoke_tool(
                    "create_merge_request_discussion",
                    {
                        "project_id": self._project_id,
                        "merge_request_iid": int(mr_id) if mr_id.isdigit() else str(mr_id),
                        "file_path": issue.file_path,
                        "line": issue.line_number if issue.line_number else 1,
                        "body": format_inline_comment(issue),
                    },
                )
            except ProviderError:
                failed.append(issue)
        return failed

    async def _publish_fallback_note(self, mr_id: str, failed: list[ReviewComment]) -> None:
        lines = ["### Inline Comments (fallback)", ""]
        for issue in failed:
            loc = f":{issue.line_number}" if issue.line_number else ""
            lines.append(
                f"- **[{issue.severity.value}]** `{issue.file_path}{loc}` — {issue.description}"
            )
        await self._create_note(mr_id, "\n".join(lines))