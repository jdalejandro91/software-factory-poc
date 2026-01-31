from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class Repository(ABC, Generic[T]):
    """Abstract base class for persistence repositories."""

    @abstractmethod
    def save(self, entity: T) -> None:
        """Saves an entity."""
        pass

    @abstractmethod
    def find_by_id(self, id: str) ->Optional[ T]:
        """Finds an entity by its ID."""
        pass

    @abstractmethod
    def find_all(self) -> list[T]:
        """Retrieves all entities."""
        pass
