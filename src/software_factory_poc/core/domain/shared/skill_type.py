from enum import StrEnum, auto


class SkillType(StrEnum):
    """Classifies every discrete unit of business logic an agent can invoke."""

    # Scaffold skills
    GENERATE_SCAFFOLD_PLAN = auto()

    # Code review skills
    ANALYZE_CODE_REVIEW = auto()
