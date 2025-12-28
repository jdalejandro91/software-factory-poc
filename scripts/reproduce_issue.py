import sys
from pathlib import Path

from fastapi.testclient import TestClient

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

import os

from software_factory_poc.api.app_factory import create_app
from software_factory_poc.config.settings_pydantic import Settings


def reproduce():
    # Mock env vars for Settings
    os.environ["JIRA_BASE_URL"] = "https://mock-jira.com"
    os.environ["JIRA_API_TOKEN"] = "mock-token"
    os.environ["JIRA_USER_EMAIL"] = "mock@example.com"
    os.environ["GITLAB_URL"] = "https://gitlab.com"
    os.environ["GITLAB_TOKEN"] = "mock-token"
    # Add other potentially required vars if needed
    
    print("🚀 Attempting to reproduce Jira Webhook 422 Error...")
    
    settings = Settings()
    app = create_app(settings)
    client = TestClient(app)
    
    # Payload similar to what Jira sends (nested)
    payload = {
        "issue": {
            "key": "POC-123",
            "fields": {
                "summary": "Test issue"
            }
        },
        "user": {
            "name": "jira_bot"
        },
        "webhookEvent": "jira:issue_created"
    }
    
    # Attempt POST to the corrected route
    url = "/api/v1/jira-webhook"
    print(f"📡 Sending POST to {url} with payload: {payload}")
    
    response = client.post(url, json=payload)
    
    print(f"📥 Response Code: {response.status_code}")
    print(f"📄 Response Body: {response.text}")
    
    if response.status_code == 200:
        print("✅ SUCCESS: Webhook processed correctly.")
        exit(0)
    elif response.status_code == 422:
        print("❌ FAILURE: 422 Unprocessable Entity (Schema Mismatch).")
        exit(1)
    else:
        print(f"⚠️ UNEXPECTED: {response.status_code}")
        exit(1)

if __name__ == "__main__":
    reproduce()
