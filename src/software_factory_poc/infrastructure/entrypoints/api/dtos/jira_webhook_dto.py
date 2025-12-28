from pydantic import BaseModel, Field

class JiraUserDTO(BaseModel):
    name: str | None = None
    display_name: str | None = Field(None, alias="displayName")
    active: bool | None = None

class JiraIssueFieldsDTO(BaseModel):
    summary: str | None = None
    description: str | None = None

class JiraIssueDTO(BaseModel):
    id: str | None = None
    key: str
    fields: JiraIssueFieldsDTO | None = None

class JiraWebhookDTO(BaseModel):
    webhook_event: str | None = Field(None, alias="webhookEvent")
    timestamp: int | None = None
    user: JiraUserDTO | None = None
    issue: JiraIssueDTO
