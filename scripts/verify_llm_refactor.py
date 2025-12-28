
import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from pydantic import SecretStr
from software_factory_poc.config.settings_pydantic import Settings
from software_factory_poc.providers.facade.llm_bridge import LlmBridge
from software_factory_poc.core.value_objects.provider_name import ProviderName

def verify():
    print("Verifying LlmBridge instantiation with Settings...")
    
    # Create fake settings
    settings = Settings(
        jira_webhook_secret=SecretStr("dummy"),
        jira_base_url="https://dummy.atlassian.net",
        openai_api_key=SecretStr("sk-dummy-key"),
        llm_allowed_models=["gpt-4o", "gpt-3.5-turbo"]
    )
    
    # Instantiate Bridge
    bridge = LlmBridge.from_settings(settings)
    print("LlmBridge instantiated successfully.")
    
    # Check if OpenAI provider is present
    providers = bridge.gateway.providers
    if ProviderName.OPENAI in providers:
        print("OpenAI provider is present.")
    else:
        print("ERROR: OpenAI provider is MISSING.")
        sys.exit(1)
        
    print("Verification Passed!")

if __name__ == "__main__":
    verify()
