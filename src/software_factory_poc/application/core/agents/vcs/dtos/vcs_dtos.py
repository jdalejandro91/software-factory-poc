from dataclasses import dataclass

@dataclass(frozen=True)
class MergeRequestDTO:
    id: str
    web_url: str
    state: str = "opened"

@dataclass(frozen=True)
class BranchDTO:
    name: str
    web_url: str

@dataclass(frozen=True)
class CommitResultDTO:
    id: str
    web_url: str
