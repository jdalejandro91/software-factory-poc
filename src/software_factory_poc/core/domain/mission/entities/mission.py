from dataclasses import dataclass

from software_factory_poc.core.domain.mission.value_objects.task_description import TaskDescription
from software_factory_poc.core.domain.mission.value_objects.task_user import TaskUser


@dataclass
class Mission:
    id: str
    key: str
    summary: str
    status: str
    project_key: str
    issue_type: str
    description: TaskDescription
    reporter: TaskUser | None = None
    event_type: str | None = None
    created_at: int | None = None
