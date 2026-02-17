from dataclasses import dataclass


@dataclass
class TaskUser:
    name: str
    display_name: str
    active: bool
    email: str | None = None
    self_url: str | None = None