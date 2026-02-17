from abc import ABC, abstractmethod

from software_factory_poc.core.domain.shared.skill_type import SkillType


class BaseSkill[T_Input, T_Output](ABC):
    """Abstract base for typed, domain-level skills.

    Subclasses define a concrete input/output contract enforced at compile time.
    """

    @property
    @abstractmethod
    def skill_type(self) -> SkillType: ...

    @abstractmethod
    async def execute(self, input_data: T_Input) -> T_Output:
        """Run the skill logic and return a typed result."""
