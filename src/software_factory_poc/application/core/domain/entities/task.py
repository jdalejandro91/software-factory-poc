from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class TaskDescription(BaseModel):
    """
    Value Object representing the description of a Task.
    Separates human-written content from machine-generated automation metadata.
    """
    model_config = ConfigDict(frozen=True)

    human_text: str = Field(..., description="The description text written by a human user.")
    automation_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Structured metadata for automation.")

    def has_metadata(self) -> bool:
        """Checks if the description contains automation metadata."""
        return self.automation_metadata is not None and len(self.automation_metadata) > 0


class Task(BaseModel):
    """
    Domain Entity representing a Task in the issue tracker.
    """
    id: str = Field(..., description="Unique identifier of the task (e.g., KAN-6)")
    summary: str = Field(..., description="Summary or title of the task")
    status: str = Field(..., description="Current status of the task")
    description: TaskDescription = Field(..., description="Rich description object")

    def update_metadata(self, context: Dict[str, Any]) -> "Task":
        """
        Creates a new Task instance with updated automation metadata,
        preserving the original human text and other attributes.
        Implements immutability.
        """
        new_description = TaskDescription(
            human_text=self.description.human_text,
            automation_metadata=context
        )
        
        return self.model_copy(update={"description": new_description})
