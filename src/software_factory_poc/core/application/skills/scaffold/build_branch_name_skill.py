import re
from typing import Any

from software_factory_poc.core.application.skills.skill import SkillAdapter, SkillToolSpec


def build_branch_name_skill() -> SkillAdapter:
    async def handler(payload: dict[str, Any]) -> str:
        task_key = str(payload.get("task_key", "")).strip()
        service_name = str(payload.get("service_name", "")).strip()

        safe_key = re.sub(r"[^a-z0-9\-]", "", task_key.lower())
        if not safe_key:
            raise ValueError("task_key is required to build branch name")

        if service_name:
            safe_service = re.sub(r"[^a-z0-9\-]", "-", service_name.lower().strip())
            return f"feature/{safe_key}-{safe_service}"

        return f"feature/{safe_key}-scaffolder"

    return SkillAdapter(
        spec=SkillToolSpec(
            name="build_branch_name",
            description="Builds a deterministic and safe branch name from task_key and optional service_name.",
            input_schema={
                "type": "object",
                "properties": {
                    "task_key": {"type": "string"},
                    "service_name": {"type": "string"},
                },
                "required": ["task_key"],
            },
        ),
        handler=handler,
    )
