import pytest
import respx
from unittest.mock import patch, MagicMock
import os
import json

from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver
from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import VcsProviderType
import dataclasses

# Run synchronously to allow CompositeGateway to use asyncio.run()
def test_scaffolding_e2e_happy_path(tmp_path):
    # 1. Setup Environment
    env_vars = {
        "JIRA_BASE_URL": "https://jira.mock.com",
        "JIRA_API_TOKEN": "mock-token",
        "JIRA_USER_EMAIL": "user@mock.com",
        "GITLAB_BASE_URL": "https://gitlab.mock.com",
        "GITLAB_TOKEN": "mock-gl-token",
        "OPENAI_API_KEY": "sk-mock-key",
        "SCAFFOLDING_ARCHITECTURE_PAGE_ID": "1111",
        "WORK_DIR": str(tmp_path),
        "VCS_PROVIDER": "GITLAB",
        "CONFLUENCE_BASE_URL": "https://confluence.mock.com",
        "CONFLUENCE_API_TOKEN": "mock-conf-token",
        "CONFLUENCE_USER_EMAIL": "user@mock.com"
    }
    
    with patch.dict(os.environ, env_vars):
        
        # LLM Response Content
        llm_content = (
            "<<<FILE:main.py>>>\n"
            "print('Hello Scaffolding')\n"
            "<<<END>>>\n"
            "<<<FILE:README.md>>>\n"
            "# Readme\n"
            "<<<END>>>"
        )
        
        # 2. Mock ALL Network Transport with RESPRX
        # assert_all_called=False because checking explicitly
        with respx.mock(assert_all_called=False) as respx_mock:
            
            # --- OPENAI Mock ---
            respx_mock.post(url__regex=r"https://api.openai.com/v1/chat/completions").respond(200, json={
                 "choices": [
                     {"message": {"content": llm_content}}
                 ]
            })

            # --- CONFLUENCE Mock ---
            respx_mock.get(url__regex=r"https://confluence.mock.com.*search.*").respond(200, json={
                "results": [
                     {"id": "111", "title": "Arch Doc", "body": {"storage": {"value": "<p>Use Flask Blueprint</p>"}}}
                ]
            })

            # --- GITLAB Mock ---
            # Resolve Project ID via Namespace
            respx_mock.get(url__regex=r"https://gitlab.mock.com/api/v4/projects/[^/]+$").respond(200, json={"id": 100})
            
            # Check Branch Exists (404 = Not found)
            respx_mock.get(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/branches/.*").respond(404)
            
            # Create Branch
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/branches.*").respond(201, json={"name": "feature/KAN-123/scaffolding"})
            
            # File HEAD Checks (Smart Commit) -> 404 Not Found (Implies Create)
            respx_mock.head(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/files/.*").respond(404)
            
            # Commit
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/commits").respond(201, json={"id": "commit-sha"})
            
            # Merge Request
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/merge_requests").respond(201, json={"web_url": "http://gitlab/mr/1"})

            # --- JIRA Mock ---
            # Add Comment (Start)
            respx_mock.post(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/comment").respond(201, json={"id": "comment-id"})
            
            # Transitions (Get Available)
            respx_mock.get(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/transitions").respond(200, json={
                "transitions": [
                    {"id": "51", "name": "In Review", "to": {"name": "In Review"}},
                    {"id": "11", "name": "Por hacer", "to": {"name": "Por hacer"}}
                ]
            })
            
            # Transition (Execute)
            respx_mock.post(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/transitions").respond(204)

            
            # 3. Initialization
            settings = Settings()
            
            # Load config and override VCS Provider type manually
            config = ScaffoldingConfigLoader.load_config()
            config = dataclasses.replace(config, vcs_provider=VcsProviderType.GITLAB)
            
            resolver = ProviderResolver(config, settings)
            usecase = CreateScaffoldingUseCase(config, resolver)
            
            request = ScaffoldingRequest(
                issue_key="KAN-123",
                raw_instruction="Create Flask App",
                technology_stack="Python",
                repository_url="http://gitlab/group/repo",
                project_id="100"
            )
            
            # 4. Execution
            usecase.execute(request)
            
            # 5. Assertions
            
            # Verify OpenAI
            openai_calls = [c for c in respx_mock.calls if "api.openai.com" in str(c.request.url)]
            assert len(openai_calls) >= 1, "OpenAI API not called"
            
            req_body = json.loads(openai_calls[0].request.read())
            messages = req_body.get("messages", [])
            # Check prompt context
            assert any("Create Flask App" in str(m.get("content", "")) for m in messages), "Instruction not found in prompt"
            
            # Verify GitLab MR
            mr_calls = [c for c in respx_mock.calls if c.request.method == "POST" and "merge_requests" in str(c.request.url)]
            assert len(mr_calls) == 1, f"Expected 1 MR creation call, found {len(mr_calls)}"
            
            # Verify Jira Final Comment
            jira_comments = [c for c in respx_mock.calls if c.request.method == "POST" and "/comment" in str(c.request.url)]
            assert len(jira_comments) >= 1
            
            last_comment_body = jira_comments[-1].request.read().decode('utf-8')
            assert "http://gitlab/mr/1" in last_comment_body, "MR Link not found in final comment"
            # assert "✅" in last_comment_body 
            # Provider translates emoji to ADF 'success' panel
