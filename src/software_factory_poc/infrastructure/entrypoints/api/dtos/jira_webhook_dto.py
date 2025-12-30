
from pydantic import BaseModel, Field


class JiraUserDTO(BaseModel):
    name: str | None = None
    display_name: str | None = Field(None, alias="displayName")
    active: bool | None = None

class JiraProjectDTO(BaseModel):
    key: str
    name: str | None = None

class JiraIssueFieldsDTO(BaseModel):
    summary: str | None = None
    description: str | None = None
    project: JiraProjectDTO | None = None

class JiraIssueDTO(BaseModel):
    id: str | None = None
    key: str
    fields: JiraIssueFieldsDTO | None = None

class JiraChangelogItem(BaseModel):
    field: str | None = None
    fieldtype: str | None = None
    fromString: str | None = None
    toString: str | None = None

class JiraChangelog(BaseModel):
    id: str | None = None
    items: list[JiraChangelogItem] = []

class JiraWebhookDTO(BaseModel):
    webhook_event: str | None = Field(None, alias="webhookEvent")
    timestamp: int | None = None
    user: JiraUserDTO | None = None
    issue: JiraIssueDTO
    changelog: JiraChangelog | None = None
