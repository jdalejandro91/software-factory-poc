from typing import List

from pydantic import BaseModel, Field, field_validator


class TemplateManifestModel(BaseModel):
    template_version: str = Field(..., description="Version of the template schema, e.g. '1'")
    description: str = Field(..., description="Short description of the template")
    expected_paths: List[str] = Field(..., description="List of relative paths that must exist after rendering")
    supported_vars: List[str] = Field(default_factory=list, description="List of variables supported by the template")

    @field_validator("template_version")
    def validate_version(cls, v: str) -> str:
        if v != "1":
            raise ValueError("Only template_version '1' is supported")
        return v

    @field_validator("expected_paths")
    def validate_expected_paths(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("expected_paths cannot be empty")
        return v
