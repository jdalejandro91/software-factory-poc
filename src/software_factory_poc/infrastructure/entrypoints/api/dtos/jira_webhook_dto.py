from typing import Optional
from pydantic import BaseModel, Field

class JiraUserDTO(BaseModel):
    name: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    active: Optional[bool] = None

class JiraProjectDTO(BaseModel):
    key: str
    name: Optional[str] = None

class JiraIssueFieldsDTO(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    project: Optional[JiraProjectDTO] = None

class JiraIssueDTO(BaseModel):
    id: Optional[str] = None
    key: str
    fields: Optional[JiraIssueFieldsDTO] = None

class JiraChangelogItem(BaseModel):
    field: Optional[str] = None
    fieldtype: Optional[str] = None
    fromString: Optional[str] = None
    toString: Optional[str] = None

class JiraChangelog(BaseModel):
    id: Optional[str] = None
    items: list[JiraChangelogItem] = []

class JiraWebhookDTO(BaseModel):
    webhook_event: Optional[str] = Field(None, alias="webhookEvent")
    timestamp: Optional[int] = None
    user: Optional[JiraUserDTO] = None
    issue: JiraIssueDTO
    changelog: Optional[JiraChangelog] = None
