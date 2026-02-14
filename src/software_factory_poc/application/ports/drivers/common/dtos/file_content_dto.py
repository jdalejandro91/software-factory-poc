from dataclasses import dataclass

@dataclass(frozen=True)
class FileContentDTO:
    path: str
    content: str
