import pytest
import respx
from unittest.mock import patch, MagicMock
import os
import json
import dataclasses

from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import CreateScaffoldingUseCase
from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import ScaffoldingRequest
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver
from software_factory_poc.infrastructure.configuration.main_settings import Settings
from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
from software_factory_poc.application.core.domain.configuration.vcs_provider_type import VcsProviderType

# Helper to build OpenAI response content
def build_llm_content():
    return (
        "<<<FILE:main.py>>>\n"
        "print('Hello Scaffolding')\n"
        "<<<END>>>\n"
        "<<<FILE:README.md>>>\n"
        "# Readme\n"
        "<<<END>>>"
    )

def test_scaffolding_full_flow_guarantee(tmp_path):
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
        
        # 2. Mock Network Transport with RESPRX (Jira, GitLab, Confluence, OpenAI)
        with respx.mock(assert_all_called=False) as respx_mock:
            
            # --- CONFLUENCE (Step 3: Retrieve Context) ---
            # Mock Search
            respx_mock.get(url__regex=r"https://confluence.mock.com.*search.*").respond(200, json={
                "results": [
                     {"id": "111", "title": "Arch Doc", "body": {"storage": {"value": "<p>Use Flask Blueprint</p>"}}}
                ]
            })

            # --- OPENAI (Step 4: Reasoning) ---
            # Using respx to mock the HTTP call directly is more robust for 'mocked IO' context
            respx_mock.post(url__regex=r"https://api.openai.com/v1/chat/completions").respond(200, json={
                 "choices": [
                     {"message": {"content": build_llm_content()}}
                 ]
            })

            # --- GITLAB (Step 2, 6, 7, 8, 9) ---
            # Resolve Project
            respx_mock.get(url__regex=r"https://gitlab.mock.com/api/v4/projects/[^/]+$").respond(200, json={"id": 100})
            
            # Step 2: Check Branch Exists (404 = Not found, proceed to create)
            respx_mock.get(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/branches/.*").respond(404)
            
            # Step 7: Create Branch
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/branches.*").respond(201, json={"name": "feature/KAN-123/scaffolding"})
            
            # Step 8 prep: Check File Existence (HEAD -> 404)
            respx_mock.head(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/files/.*").respond(404)
            
            # Step 8: Commit
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/repository/commits").respond(201, json={"id": "commit-sha"})
            
            # Step 9: Merge Request
            respx_mock.post(url__regex=r"https://gitlab.mock.com/api/v4/projects/100/merge_requests").respond(201, json={"web_url": "http://gitlab/mr/1"})

            # --- JIRA (Step 1, 10, 10b) ---
            # Step 1: Announce Start (Add Comment)
            respx_mock.post(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/comment").respond(201, json={"id": "comment-id"})
            
            # Step 10b prep: Get Transitions
            respx_mock.get(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/transitions").respond(200, json={
                "transitions": [
                    {"id": "51", "name": "In Review", "to": {"name": "In Review"}},
                    {"id": "11", "name": "Por hacer", "to": {"name": "Por hacer"}}
                ]
            })
            
            # Step 10b: Execute Transition
            respx_mock.post(url__regex=r"https://jira.mock.com/rest/api/3/issue/KAN-123/transitions").respond(204)

            # 3. Execution
            settings = Settings()
            # Force GITLAB provider
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
            
            usecase.execute(request)
            
            # 4. Verifications (Asserts)
            
            # P3: Verify Call to Confluence (Context)
            conf_calls = [c for c in respx_mock.calls if "confluence.mock.com" in str(c.request.url)]
            assert len(conf_calls) >= 1, "Failed Step 3: Confluence Context Retrieval not called."
            
            # P4: Verify Call to OpenAI (Reasoning) with Prompt containing Context
            openai_calls = [c for c in respx_mock.calls if "api.openai.com" in str(c.request.url)]
            assert len(openai_calls) >= 1, "Failed Step 4: OpenAI Reasoning not called."
            
            openai_req = json.loads(openai_calls[0].request.read())
            prompt_content = openai_req["messages"][0]["content"]
            assert "Use Flask Blueprint" in prompt_content, "Failed Step 4: Prompt doesn't contain Retrieval Context."
            assert "Create Flask App" in prompt_content, "Failed Step 4: Prompt doesn't contain User Instruction."

            # P7: Verify Call to Create Branch
            branch_calls = [c for c in respx_mock.calls if c.request.method == "POST" and "/branches" in str(c.request.url)]
            assert len(branch_calls) == 1, "Failed Step 7: Create Branch not called."

            # P8: Verify Call to Commit (Code Publication)
            commit_calls = [c for c in respx_mock.calls if c.request.method == "POST" and "/commits" in str(c.request.url)]
            assert len(commit_calls) == 1, "Failed Step 8: Commit Code not called."
            
            # Verify payload contains 'main.py'
            commit_payload = json.loads(commit_calls[0].request.read())
            file_actions = commit_payload.get("actions", [])
            assert any(action["file_path"] == "main.py" for action in file_actions), "Failed Step 5/8: deserialized file 'main.py' not found in Commit payload."

            # P9: Verify Call to Create MR
            mr_calls = [c for c in respx_mock.calls if c.request.method == "POST" and "merge_requests" in str(c.request.url)]
            assert len(mr_calls) == 1, "Failed Step 9: Create Merge Request not called."

            # P10: Verify Report to Jira (Last Comment contains MR link)
            jira_comments = [c for c in respx_mock.calls if c.request.method == "POST" and "/comment" in str(c.request.url)]
            assert len(jira_comments) >= 1
            last_comment = jira_comments[-1].request.read().decode('utf-8')
            assert "http://gitlab/mr/1" in last_comment, "Failed Step 10: Final Jira comment does not include MR URL."

            # P10b: Verify Jira Transition
            transition_calls = [c for c in respx_mock.calls if c.request.method == "POST" and "/transitions" in str(c.request.url)]
            assert len(transition_calls) == 1, "Failed Step 10b: Jira Transition not called."
