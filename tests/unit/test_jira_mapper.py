import pytest
from software_factory_poc.infrastructure.entrypoints.api.dtos.jira_webhook_dto import (
    JiraWebhookDTO, JiraIssueDTO, JiraIssueFieldsDTO, JiraUserDTO, JiraProjectDTO
)
from software_factory_poc.infrastructure.entrypoints.api.mappers.jira_mapper import JiraMapper

def test_map_webhook_to_command_scaffolding_block():
    description = """
    Algun texto de intro.
    ```scaffolding
    instruction: "Create an app"
    components: 
      - name: api
    ```
    Fin.
    """
    
    dto = JiraWebhookDTO(
        webhookEvent="jira:issue_created",
        timestamp=123456,
        user=JiraUserDTO(name="dev", displayName="Developer"),
        issue=JiraIssueDTO(
            key="PROJ-123",
            fields=JiraIssueFieldsDTO(
                summary="Scaffold Request",
                description=description,
                project=JiraProjectDTO(key="PROJ", name="Project")
            )
        )
    )
    
    mapper = JiraMapper()
    cmd = mapper.map_webhook_to_command(dto)
    
    assert cmd.issue_key == "PROJ-123"
    assert cmd.project_key == "PROJ"
    assert cmd.reporter == "Developer"
    assert 'instruction: "Create an app"' in cmd.raw_instruction
    assert "components:" in cmd.raw_instruction
    # Ensure delimiters are removed
    assert "```scaffolding" not in cmd.raw_instruction

def test_map_webhook_to_command_generic_block():
    description = """
    ```yaml
    some: yaml
    ```
    """
    dto = JiraWebhookDTO(
        issue=JiraIssueDTO(
            key="A-1",
            fields=JiraIssueFieldsDTO(description=description)
        )
    )
    
    mapper = JiraMapper()
    cmd = mapper.map_webhook_to_command(dto)
    assert "some: yaml" in cmd.raw_instruction
