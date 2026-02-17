
from pydantic import BaseModel, ConfigDict, Field


class JiraUserDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    name: str | None = None
    display_name: str | None = Field(None, alias="displayName")
    active: bool | None = None


class JiraProjectDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    key: str
    name: str | None = None


class JiraIssueFieldsDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    summary: str | None = None
    description: str | None = None
    project: JiraProjectDTO | None = None


class JiraIssueDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str | None = None  # Optional for automation payloads
    key: str
    fields: JiraIssueFieldsDTO | None = None
    project: JiraProjectDTO | None = None


class JiraChangelogItem(BaseModel):
    model_config = ConfigDict(extra='ignore')
    field: str | None = None
    fieldtype: str | None = None
    fromString: str | None = None
    toString: str | None = None


class JiraChangelog(BaseModel):
    model_config = ConfigDict(extra='ignore')
    id: str | None = None
    items: list[JiraChangelogItem] = []


class JiraWebhookDTO(BaseModel):
    model_config = ConfigDict(extra='ignore')
    webhook_event: str | None = Field(None, alias="webhookEvent")
    timestamp: int | None = None
    user: JiraUserDTO | None = None
    issue: JiraIssueDTO
    changelog: JiraChangelog | None = None
