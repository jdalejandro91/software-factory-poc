"""
Script to simulate a Jira Webhook event triggering the BrahMAS Scaffolding Agent.
Usage: python scripts/simulate_jira_webhook.py
"""

import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from software_factory_poc.infrastructure.configuration.agents.scaffolder.scaffolding_config_loader import (
    ScaffoldingConfigLoader,
)

from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

# Setup Logging
logger = LoggerFactoryService.build_logger("simulate_jira")


def main():
    logger.info("Starting Scaffolding Simulation...")

    try:
        from dotenv import load_dotenv

        load_dotenv()

        config = ScaffoldingConfigLoader.load_config()

        logger.info(
            f"Loaded Config: VCS={config.vcs_provider}, Tracker={config.tracker_provider}, LLM_Priority={len(config.llm_model_priority)}"
        )

        logger.info("Simulation config loaded successfully. Agent wiring requires MCP sessions.")

    except Exception as e:
        logger.error(f"Simulation Failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
