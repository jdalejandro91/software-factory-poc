from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class AgentIdentity:
    """Immutable identity of an agent within the Software Factory."""

    name: str
    role: str
    goal: str
