from datetime import UTC, datetime
from typing import Any

from software_factory_poc.core.application.skills.skill import SkillAdapter, SkillToolSpec


def build_metadata_comment_skill() -> SkillAdapter:
    async def handler(payload: dict[str, Any]) -> str:
        gitlab_project_id = str(payload.get("gitlab_project_id", "")).strip()
        branch_name = str(payload.get("branch_name", "")).strip()
        mr_url = str(payload.get("mr_url", "")).strip()

        if not gitlab_project_id or not branch_name or not mr_url:
            raise ValueError("gitlab_project_id, branch_name and mr_url are required")

        generated_at = datetime.now(UTC).isoformat()
        return (
            "BrahMAS Automation Metadata:\n"
            "```yaml\n"
            "code_review_params:\n"
            f"  gitlab_project_id: \"{gitlab_project_id}\"\n"
            f"  source_branch_name: \"{branch_name}\"\n"
            f"  review_request_url: \"{mr_url}\"\n"
            f"  generated_at: \"{generated_at}\"\n"
            "```"
        )

    return SkillAdapter(
        spec=SkillToolSpec(
            name="build_metadata_comment",
            description="Builds the YAML metadata comment to inject into the tracker task.",
            input_schema={
                "type": "object",
                "properties": {
                    "gitlab_project_id": {"type": "string"},
                    "branch_name": {"type": "string"},
                    "mr_url": {"type": "string"},
                },
                "required": ["gitlab_project_id", "branch_name", "mr_url"],
            },
        ),
        handler=handler,
    )
