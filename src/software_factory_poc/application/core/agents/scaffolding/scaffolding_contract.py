import re
import json
import yaml
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator, ValidationError

from software_factory_poc.application.core.agents.scaffolding.exceptions.contract_parse_error import ContractParseError


class GitLabTargetModel(BaseModel):
    project_id: int | None = Field(None, description="Target GitLab project ID")
    project_path: str | None = Field(None, description="Target GitLab project path (e.g. group/project)", alias="gitlab_project_path")
    target_base_branch: str | None = Field(None, description="Base branch to branch off from (e.g. main)")
    branch_slug: str | None = Field(None, description="Branch slug for the feature branch")

    @field_validator("project_id")
    def validate_project_id(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("project_id must be positive")
        return v
    
    @model_validator(mode="after")
    def validate_project_identifier(self) -> "GitLabTargetModel":
        if not self.project_id and not self.project_path:
            raise ValueError("Must provide either 'project_id' or 'project_path' (or 'gitlab_project_path').")
        return self


class JiraTargetModel(BaseModel):
    comment_visibility: str | None = Field("public", description="e.g. 'public' or 'internal'")


class ScaffoldingContractModel(BaseModel):
    contract_version: str = Field(..., description="Version of the contract schema, e.g. '1.0'", alias="version")
    technology_stack: str = Field(..., description="Target technology stack (e.g., 'TypeScript with NestJS')")
    
    # Optional logic: Derived from parameters.service_name if not strict
    service_slug: str | None = Field(None, description="Slug for the new service, used in branch naming")
    
    gitlab: GitLabTargetModel = Field(..., alias="target")
    jira: JiraTargetModel | None = Field(default=None)
    
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
        Handles block extraction (Markdown/Jira) and YAML/JSON parsing.
        """
        if not text:
            raise ContractParseError("Input text is empty.")

        cleaned_text = text.replace("\r\n", "\n")
        block_content = cls._extract_block(cleaned_text)
        
        # Use block content if found, else try raw text
        content_to_parse = block_content if block_content else cleaned_text
        
        try:
            data = cls._parse_yaml_json(content_to_parse)
        except ValueError:
            # If parsing failed and we didn't find a block explicitly, 
            # assume user intended to provide a block but failed delimiters.
            if not block_content:
                msg = "Could not find contract block (or valid raw YAML). Use Markdown code blocks (```) or Jira Wiki blocks ({code})."
                raise ContractParseError(msg)
            
            snippet = content_to_parse[:200] + ("..." if len(content_to_parse) > 200 else "")
            raise ContractParseError(
                "Could not parse valid YAML or JSON from contract block.",
                safe_snippet=snippet
            )

        try:
            return cls(**data)
        except ValidationError as e:
            cleaned_errors = []
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                msg = err["msg"]
                cleaned_errors.append(f"{loc}: {msg}")
            
            error_msg = "; ".join(cleaned_errors)
            snippet = content_to_parse[:200] + ("..." if len(content_to_parse) > 200 else "")
            
            raise ContractParseError(
                f"Contract validation failed: {error_msg}", 
                safe_snippet=snippet
            ) from e

    @staticmethod
    def _extract_block(text: str) -> str | None:
        """
        Extracts content from Markdown (```...```) or Jira ({code}...) blocks.
        """
        if not text:
            return None

        # 1. Jira Wiki Markup
        jira_wiki_pattern = r"\{code(?:[:\w]+)?\}\s*(.*?)\s*\{code\}"
        match = re.search(jira_wiki_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
             content = match.group(1).strip()
             if ScaffoldingContractModel._is_likely_scaffolding(content):
                 return content

        # 2. Markdown (```yaml...)
        markdown_pattern = r"```[ \t]*(?:[\w\-\+]+)?[ \t\r]*\n(.*?)\n[ \t\r]*```"
        for match in re.finditer(markdown_pattern, text, re.DOTALL | re.IGNORECASE):
            content = match.group(1).strip()
            if ScaffoldingContractModel._is_likely_scaffolding(content):
                return content
            
        # 3. Legacy (kept for backward compat if needed, simplified here)
        legacy_start = "--- SCAFFOLDING_CONTRACT:v1 ---"
        legacy_end = "--- /SCAFFOLDING_CONTRACT ---"
        legacy_pattern = re.escape(legacy_start) + r"\s*(.*?)\s*" + re.escape(legacy_end)
        match = re.search(legacy_pattern, text, re.DOTALL)
        if match:
             content = match.group(1).strip()
             if ScaffoldingContractModel._is_likely_scaffolding(content):
                return content
                
        return None

    @staticmethod
    def _is_likely_scaffolding(content: str) -> bool:
        if "version:" in content and ("technology_stack:" in content or "service_slug:" in content):
            return True
        return False

    @staticmethod
    def _parse_yaml_json(content: str) -> dict[str, Any]:
        # Try YAML
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
        except yaml.YAMLError:
            pass

        # Try JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        raise ValueError("Could not parse valid YAML or JSON.")



