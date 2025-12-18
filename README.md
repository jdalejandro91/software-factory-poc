# Software Factory PoC

Proof of Concept for an agentic Software Factory that scaffolds projects based on Jira tickets.

## 🚀 Quick Start

### 1. Environment Setup

Copy `.env.example` (if available) or set the following environment variables:

```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_API_TOKEN="your-api-token"
export JIRA_USER_EMAIL="email@example.com"
export GITLAB_BASE_URL="https://gitlab.com"
export GITLAB_TOKEN="your-gl-token"
```

### 2. Running the Server

You can run the development server using the provided script alias:

```bash
# If using uv/pip with project scripts installed:
uv run sf-poc-dev

# OR directly with uvicorn:
uv run uvicorn software_factory_poc.main:app --reload
```

## 🛠 Usage

### 1. Create a Jira Ticket

Create a new issue in your Jira project. In the **Description** field, paste the Scaffolding Contract block:

```yaml
--- SCAFFOLDING_CONTRACT:v1 ---
contract_version: "1"
template_id: "corp_nodejs_api"
service_slug: "my-awesome-service"
gitlab:
  project_id: 12345
  target_base_branch: "main"
vars:
  service_name: "My Awesome Service"
  owner_team: "Platform Engineering"
--- /SCAFFOLDING_CONTRACT ---
```

### 2. Trigger Scaffolding

Simulate the webhook trigger (or configure Jira Automation to POST to this endpoint):

```bash
curl -X POST http://localhost:8000/jira/scaffold-trigger \
  -H "Content-Type: application/json" \
  -d '{"issue_key": "PROJ-1"}'
```

### 3. Expected Outputs

If successful:
1.  **GitLab**: A new branch `scaffold/proj-1-my-awesome-service` is created with the rendered code.
2.  **GitLab**: A Merge Request is opened.
3.  **Jira**: A comment is posted on `PROJ-1`:
    > **Scaffolding Success 🚀**
    > **Merge Request**: [link-to-mr]
    > **Branch**: scaffold/proj-1-my-awesome-service
    > **Run ID**: ...

## ❓ Troubleshooting

### 1. "Template not in allowlist"
**Symptom**: Jira comment says "SCAFFOLDING FAILED (Policy Violation)".
**Fix**: Ensure `template_id` in your contract matches one of the IDs in `allowlists_config.py` (e.g., `corp_nodejs_api`).

### 2. "Could not find contract block"
**Symptom**: Jira comment says "Validation Error".
**Fix**: Ensure the contract in Jira Description is strictly wrapped with:
`--- SCAFFOLDING_CONTRACT:v1 ---` and `--- /SCAFFOLDING_CONTRACT ---`.
Check for extra spaces or formatting issues in Jira.

### 3. "GitLab Project ID not allowed"
**Symptom**: Policy Violation error regarding Project ID.
**Fix**: The PoC enforces specific GitLab Project IDs. Update `allowlists_config.py` with your target Project ID or use the default allowed IDs.

## 🧪 Testing

Run the test suite:

```bash
uv run sf-poc-test
# OR
pytest tests
```