"""Pure functions for building Markdown review summaries for GitLab MR notes."""

from software_factory_poc.core.domain.quality import CodeReviewReport, ReviewComment, ReviewSeverity


def build_review_summary(report: CodeReviewReport) -> str:
    """Build severity-grouped Markdown summary note."""
    verdict = "APPROVED" if report.is_approved else "CHANGES REQUESTED"
    header = f"## BrahMAS Code Review: {verdict}\n\n{report.summary}\n"
    if not report.comments:
        return f"{header}\n> No issues found."
    grouped = _group_by_severity(report.comments)
    sections = [header]
    for severity in (
        ReviewSeverity.CRITICAL,
        ReviewSeverity.WARNING,
        ReviewSeverity.SUGGESTION,
    ):
        items = grouped.get(severity, [])
        if items:
            sections.append(_format_severity_group(severity, items))
    return "\n".join(sections)


def format_inline_comment(issue: ReviewComment) -> str:
    """Format a single inline discussion body."""
    return (
        f"**[{issue.severity.value}]** {issue.description}\n\n**Suggestion:** `{issue.suggestion}`"
    )


def _group_by_severity(
    comments: list[ReviewComment],
) -> dict[ReviewSeverity, list[ReviewComment]]:
    """Group comments by severity level."""
    grouped: dict[ReviewSeverity, list[ReviewComment]] = {}
    for c in comments:
        grouped.setdefault(c.severity, []).append(c)
    return grouped


def _format_severity_group(severity: ReviewSeverity, items: list[ReviewComment]) -> str:
    """Format a single severity group as a Markdown section."""
    lines = [f"### {severity.value} ({len(items)})"]
    for item in items:
        loc = f":`{item.line_number}`" if item.line_number else ""
        lines.append(f"- **`{item.file_path}`{loc}** — {item.description}")
    return "\n".join(lines)
