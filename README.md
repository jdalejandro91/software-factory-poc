# Software Factory PoC

Proof of Concept for an agentic Software Factory that scaffolds projects based on Jira tickets.
Built with **Clean Architecture** and **DDD**.

## 🚀 Quick Start

### 1. Environment Setup

Copy `.env.example` to `.env` and configure your keys.

**Critical Configuration**:
```bash
# Provider Selection
VCS_PROVIDER=gitlab
TRACKER_PROVIDER=jira
KNOWLEDGE_PROVIDER=file_system  # or confluence

# LLM Priority (JSON) - The agent will try these in order
LLM_MODEL_PRIORITY='[{"provider": "openai", "model": "gpt-4"}, {"provider": "deepseek", "model": "coder"}]'

# Credentials
JIRA_BASE_URL="https://your-domain.atlassian.net"
JIRA_API_TOKEN="..."
JIRA_USER_EMAIL="..."
GITLAB_TOKEN="..."
OPENAI_API_KEY="..."
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