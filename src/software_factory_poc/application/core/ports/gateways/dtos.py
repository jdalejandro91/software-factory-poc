from dataclasses import dataclass


@dataclass(frozen=True)
class FileContent:
    path: str
    content: str

@dataclass(frozen=True)
class Task:
    id: str
    title: str
    status: str
    description: str
