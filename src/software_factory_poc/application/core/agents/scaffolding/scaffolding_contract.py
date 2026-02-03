import json
import re
from typing import Any, Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

from software_factory_poc.application.core.agents.scaffolding.exceptions.contract_parse_error import ContractParseError


class GitLabTargetModel(BaseModel):
    project_id:Optional[ int] = Field(None, description="Target GitLab project ID")
    project_path:Optional[ str] = Field(None, description="Target GitLab project path (e.g. group/project)", alias="gitlab_project_path")
    target_base_branch:Optional[ str] = Field(None, description="Base branch to branch off from (e.g. main)")
    branch_slug:Optional[ str] = Field(None, description="Branch slug for the feature branch")

    @field_validator("project_id")
    def validate_project_id(cls, v:Optional[ int]) ->Optional[ int]:
        if v is not None and v <= 0:
            raise ValueError("project_id must be positive")
        return v
    
    @model_validator(mode="after")
    def validate_project_identifier(self) -> "GitLabTargetModel":
        if not self.project_id and not self.project_path:
            raise ValueError("Must provide either 'project_id' or 'project_path' (or 'gitlab_project_path').")
        return self


class JiraTargetModel(BaseModel):
    comment_visibility:Optional[ str] = Field("public", description="e.g. 'public' or 'internal'")


class ScaffoldingContractModel(BaseModel):
    contract_version: str = Field(..., description="Version of the contract schema, e.g. '1.0'", alias="version")
    technology_stack: str = Field(..., description="Target technology stack (e.g., 'TypeScript with NestJS')")
    
    # Optional logic: Derived from parameters.service_name if not strict
    service_slug:Optional[ str] = Field(None, description="Slug for the new service, used in branch naming")
    
    gitlab: GitLabTargetModel = Field(..., alias="target")
    jira:Optional[ JiraTargetModel] = Field(default=None)
    
    vars: dict[str, Any] = Field(default_factory=dict, description="Variables for template rendering", alias="parameters")

    @field_validator("contract_version")
    def validate_version(cls, v: str) -> str:
        # Allow "1" or "1.0"
        if v not in ("1", "1.0"):
            raise ValueError("Only contract_version '1' or '1.0' is supported")
        return v

    @field_validator("technology_stack")
    def validate_technology_stack(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("technology_stack cannot be empty")
        return v.strip()

    @model_validator(mode="before")
    @classmethod
    def populate_service_slug(cls, data: Any) -> Any:
        # If input is dict
        if isinstance(data, dict):
            # Check if service_slug is present
            if not data.get("service_slug"):
                # Try to get from parameters/vars
                params = data.get("parameters") or data.get("vars") or {}
                if isinstance(params, dict) and params.get("service_name"):
                    data["service_slug"] = params.get("service_name")
        return data

    @model_validator(mode="after")
    def validate_service_slug_exists(self) -> "ScaffoldingContractModel":
        if not self.service_slug or not self.service_slug.strip():
             raise ValueError("service_slug is required (or must be derivable from parameters.service_name)")
        return self

    @classmethod
    def from_raw_text(cls, text: str) -> "ScaffoldingContractModel":
        """
        Parses a raw text string (e.g. Jira description) into a ScaffoldingContractModel.
        Strictly requires a code block (Markdown or Jira) to avoid false positives.
        """
        if not text:
            raise ContractParseError("Input text is empty.")

        # 1. Robust Regex for Markdown (```) and Jira ({code})
        # Supports: ```yaml, ```, {code:yaml}, {code}, {code:yaml|borderStyle=...}
        # Captures content in group(1).
        pattern = re.compile(
            r"(?:```(?:yaml|yml|scaffolding)?|\{code(?::(?:yaml|yml|scaffolding))?(?:\|[\w=]+)*\})\s*([\s\S]*?)\s*(?:```|\{code\})", 
            re.IGNORECASE | re.DOTALL
        )
        match = pattern.search(text)

        # 2. Strict Logic: No match = Error (No blind fallback)
        if not match:
            raise ContractParseError("No YAML code block found in description. Please wrap config in ```yaml or {code:yaml}.")

        # 3. Sanitization (Jira invisible chars)
        yaml_content = match.group(1).replace(u'\xa0', ' ').strip()

        try:
            # 4. Parse YAML
            data = yaml.safe_load(yaml_content)
            
            if not isinstance(data, dict):
                 # Case where YAML allows simple strings or lists, but we need a dict contract
                 raise ContractParseError("Parsed content is not a dictionary.", safe_snippet=yaml_content[:100])

            return cls(**data)

        except yaml.YAMLError as e:
            raise ContractParseError(
                f"Invalid YAML content: {e}",
                safe_snippet=yaml_content[:200]
            )
        except ValidationError as e:
            cleaned_errors = "; ".join([f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}" for err in e.errors()])
            raise ContractParseError(
                f"Contract validation failed: {cleaned_errors}", 
                safe_snippet=yaml_content[:200]
            ) from e



