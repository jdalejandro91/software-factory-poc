from pydantic import BaseModel


class JiraUserNode(BaseModel):
    name: str | None = None
    displayName: str | None = None
    active: bool | None = None

class JiraIssueFields(BaseModel):
    summary: str | None = None
    description: str | None = None
    # Add other fields as needed for the PoC context

class JiraIssueNode(BaseModel):
    id: str | None = None
    key: str
    fields: JiraIssueFields | None = None

class JiraWebhookModel(BaseModel):
    webhookEvent: str | None = None
    timestamp: int | None = None
    user: JiraUserNode | None = None
    issue: JiraIssueNode
