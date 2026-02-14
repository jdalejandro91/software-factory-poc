from typing import Optional

from pydantic import BaseModel, Field

from software_factory_poc.application.ports.drivers.common.dtos.change_type import ChangeType


class FileChangesDTO(BaseModel):
    """
    Represents changes in a single file with all necessary context for Code Review.
    """
    model_config = {"frozen": True}

    file_path: str = Field(..., description="The path of the file (Legacy support, alias for new_path).")
    new_path: str = Field(..., description="The new path of the file.")
    old_path: Optional[str] = Field(None, description="The previous path of the file if RENAMED or MODIFIED.")
    
    change_type: ChangeType
    
    # Flags
    is_new_file: bool = Field(False, description="True if the file was created in this MR.")
    is_deleted_file: bool = Field(False, description="True if the file was deleted in this MR.")
    is_binary: bool = Field(False, description="Flag to indicate if the file is binary or too large.")
    
    # Content
    diff_patch: Optional[str] = Field(None, description="The raw diff/patch content from VCS.")
    diff_content: Optional[str] = Field(None, description="Legacy alias for diff_patch.")
    new_content: Optional[str] = Field(None, description="The full content of the file after changes (if available and text).")
    
    additions: int = Field(0, description="Number of lines added.")
    deletions: int = Field(0, description="Number of lines deleted.")

    def get_primary_path(self) -> str:
        """
        Returns the most relevant path for display or logging.
        Prefer current path, fallback to old path (e.g., if deleted and file_path is somehow missing, though file_path is required).
        """
        return self.file_path or self.old_path or "unknown_path"
