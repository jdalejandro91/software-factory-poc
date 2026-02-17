from abc import ABC, abstractmethod


class BaseSkill[T_Input, T_Output](ABC):
    """Abstract base for typed, domain-level skills.

    Subclasses define a concrete input/output contract enforced at compile time.
    """

    @abstractmethod
    async def execute(self, input_data: T_Input) -> T_Output:
        """Run the skill logic and return a typed result."""
