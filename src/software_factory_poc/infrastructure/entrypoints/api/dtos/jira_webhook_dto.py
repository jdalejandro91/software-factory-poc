from typing import Optional, List

from pydantic import BaseModel, Field, ConfigDict


class JiraUserDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    active: Optional[bool] = None


class JiraProjectDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    key: str
    name: Optional[str] = None


class JiraIssueFieldsDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    summary: Optional[str] = None
    description: Optional[str] = None
    project: Optional[JiraProjectDTO] = None


class JiraIssueDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: Optional[str] = None  # Optional for automation payloads
    key: str
    fields: Optional[JiraIssueFieldsDTO] = None


class JiraChangelogItem(BaseModel):
    model_config = ConfigDict(extra='ignore')
    field: Optional[str] = None
    fieldtype: Optional[str] = None
    fromString: Optional[str] = None
    toString: Optional[str] = None


class JiraChangelog(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: Optional[str] = None
    items: List[JiraChangelogItem] = []


class JiraWebhookDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    webhook_event: Optional[str] = Field(None, alias="webhookEvent")
    timestamp: Optional[int] = None
    user: Optional[JiraUserDTO] = None
    issue: JiraIssueDTO
    changelog: Optional[JiraChangelog] = None
