# Software Factory PoC

Proof of Concept for an agentic Software Factory that scaffolds projects based on Jira tickets.
Built with **Clean Architecture** and **DDD**.

## 🚀 Quick Start

### 1. Environment Setup

Copy `.env.example` to `.env` and configure your keys.

**Critical Configuration**:
```bash
PORT=8000
LOG_LEVEL=DEBUG

# GITLAB
GITLAB_TOKEN=key-sample
GITLAB_BASE_URL=https://gitlab.com
ALLOWLISTED_GROUPS=sample-group

# JIRA
JIRA_API_TOKEN=key-sample
JIRA_WEBHOOK_SECRET=key-sample
JIRA_BASE_URL=https://sample.atlassian.net
JIRA_USER_EMAIL=sample@gmail.com
WORKFLOW_STATE_INITIAL="Por hacer"
WORKFLOW_STATE_SUCCESS="In review"

# CONFLUENCE
CONFLUENCE_USER_EMAIL=jacadenac@unal.edu.co
CONFLUENCE_API_TOKEN=key-sample
CONFLUENCE_BASE_URL=https://sample.atlassian.net/wiki
CONFLUENCE_SAMPLE_PATH=https://sample.atlassian.net/wiki/spaces/DDS/pages/3571713/Estructura+de+paquetes+-+carrito+de+compra
ARCHITECTURE_DOC_PAGE_ID=3571713

# LLMS
OPENAI_API_KEY=key-sample
GEMINI_API_KEY=key-sample
DEEPSEEK_API_KEY=key-sample
ANTHROPIC_API_KEY=key-sample

# EC2
EC2_USER=ubuntu
EC2_HOST=98.93.0.27

# Options: GITLAB, GITHUB, BITBUCKET
VCS_PROVIDER=GITLAB
SCAFFOLDING_VCS_PROVIDER=GITLAB

# Options: JIRA, AZURE_DEVOPS
TRACKER_PROVIDER=JIRA
SCAFFOLDING_TRACKER_PROVIDER=JIRA

# Options: CONFLUENCE, FILE_SYSTEM
KNOWLEDGE_PROVIDER=CONFLUENCE
SCAFFOLDING_KNOWLEDGE_PROVIDER=CONFLUENCE

# LLM Priority
LLM_ALLOWED_MODELS='["openai:gpt-4-turbo", "openai:gpt-4o", "deepseek:deepseek-coder", "gemini:gemini-1.5-pro", "gemini:gemini-3-flash-preview", "anthropic:claude-3-5-sonnet"]'
SCAFFOLDING_LLM_MODEL_PRIORITY='["gemini:gemini-3-flash-preview", "openai:gpt-4o", "openai:gpt-4-turbo", "anthropic:claude-3-opus", "deepseek:deepseek-coder"]'
CODE_REVIEW_LLM_MODEL_PRIORITY='["gemini:gemini-3-flash-preview", "openai:gpt-4-turbo", "openai:gpt-4o", "anthropic:claude-3-opus", "deepseek:deepseek-coder"]'
```

### 2. Running Locally (Simulation)
You can manually trigger the full orchestration flow without waiting for a real Jira webhook:

```bash
# Install dependencies
pip install -r requirements.txt # or using pyproject.toml

# Run the simulation CLI
python scripts/simulate_jira_webhook.py
```
This script will:
1. Load your `.env`.
2. Instantiate the agent logic.
3. Simulate a Jira request.
4. Attempt to generate code and create a Merge Request (Dry-run or Real depending on keys).

### 3. Running the Server (Production)
```bash
uvicorn src.software_factory_poc.main:app --host 0.0.0.0 --port 8000
```
Then configure your Jira Webhook to point to `http://<host>:8000/jira/scaffold-trigger`.

## 🏗 Architecture
See [ARCHITECTURE.md](ARCHITECTURE.md) for details on the Domain-Driven Design and Provider Resolution strategies.

## 🧪 Testing
```bash
# Run integration tests (Dry Run of the wiring)
pytest tests/integration/test_wiring.py

# Run unit tests
pytest tests/unit
```