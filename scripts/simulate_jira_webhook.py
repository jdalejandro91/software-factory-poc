
"""
Script to simulate a Jira Webhook event triggering the new Clean Architecture Scaffolding Use Case.
Usage: python scripts/simulate_jira_webhook.py
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_request import (
    ScaffoldingRequest,
)
from software_factory_poc.application.usecases.scaffolding.create_scaffolding_usecase import (
    CreateScaffoldingUseCase,
)
from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import (
    ScaffoldingConfigLoader,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import LoggerFactoryService
from software_factory_poc.infrastructure.resolution.provider_resolver import ProviderResolver

# Setup Logging
logger = LoggerFactoryService.build_logger("simulate_jira")

def main():
    logger.info("🚀 Starting Scaffolding Simulation...")
    
    try:
        # 1. Load Config
        # Ensure env vars are loaded (python-dotenv usually handled by user or loaded here)
        from dotenv import load_dotenv
        load_dotenv()
        
        config = ScaffoldingConfigLoader.load_config()
        from software_factory_poc.infrastructure.configuration.main_settings import Settings
        settings = Settings()
        
        logger.info(f"Loaded Config: VCS={config.vcs_provider}, Tracker={config.tracker_provider}, LLM_Priority={len(config.llm_model_priority)}")
        
        # 2. Build Resolver
        resolver = ProviderResolver(config, settings)
        
        # 3. Instantiate Use Case
        use_case = CreateScaffoldingUseCase(config, resolver)
        
        # 4. Prepare Request
        request = ScaffoldingRequest(
            issue_key="SIM-101",
            raw_instruction="Create a simple Python Flask API with a hello world endpoint.",
            technology_stack="Python/Flask",
            repository_url="https://gitlab.com/simulate/repo",
            project_id="123456",
            summary="Simulation Task",
            reporter="Simulated User"
        )
        
        # 5. Execute
        logger.info(f"Executing Use Case for {request.issue_key}...")
        use_case.execute(request)
        
        logger.info("✅ Simulation Complete.")
        
    except Exception as e:
        logger.error(f"❌ Simulation Failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
