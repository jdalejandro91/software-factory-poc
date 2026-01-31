from dataclasses import dataclass

@dataclass(frozen=True)
class TaskDTO:
    id: str
    title: str
    status: str
    description: str
