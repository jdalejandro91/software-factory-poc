import json
import os
from pathlib import Path
from typing import Any

from software_factory_poc.application.core.domain.agents.common.value_objects.model_id import ModelId
from software_factory_poc.application.core.domain.agents.scaffolding.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.application.core.domain.agents.reporter.config.task_tracker_type import (
    TaskTrackerType,
)
from software_factory_poc.application.core.domain.agents.vcs.config.vcs_provider_type import (
    VcsProviderType,
)
from software_factory_poc.application.core.domain.agents.research.config.research_provider_type import (
    ResearchProviderType,
)
from software_factory_poc.application.core.domain.agents.common.config.llm_provider_type import (
    LlmProviderType,
)
from software_factory_poc.infrastructure.observability.logger_factory_service import (
    LoggerFactoryService,
)

logger = LoggerFactoryService.build_logger(__name__)


class ScaffoldingConfigLoader:
    """
    Loader for ScaffoldingAgentConfig that implements a hierarchical fallback strategy:
    1. Agent-Specific Env Var (e.g., SCAFFOLDING_VCS_PROVIDER)
    2. Global Env Var (e.g., VCS_PROVIDER)
    3. Hardcoded Default
    """

    @staticmethod
    def load_config() -> ScaffoldingAgentConfig:
        try:
            # 1. VCS Provider
            vcs_provider = ScaffoldingConfigLoader._load_vcs_provider()

            # 2. Tracker Provider
            tracker_provider = ScaffoldingConfigLoader._load_tracker_provider()

            # 3. Knowledge Provider
            research_provider = ScaffoldingConfigLoader._load_research_provider()

            # 4. LLM Priority List
            llm_priority_list = ScaffoldingConfigLoader._load_llm_priority()

            # 5. Work Dir
            work_dir = Path(os.getenv("WORK_DIR", "/tmp/scaffolding_workspace"))

            # 6. Secure Mode
            enable_secure = os.getenv("ENABLE_SECURE_MODE", "True").lower() == "true"

            # 7. Architecture Page ID (Configuration Injection)
            arch_page_id = ScaffoldingConfigLoader._get_value(
                "SCAFFOLDING_ARCHITECTURE_PAGE_ID", "ARCHITECTURE_DOC_PAGE_ID", "3571713"
            )

            # 8. Project Allowlist
            allowlist_str = ScaffoldingConfigLoader._get_value(
                "SCAFFOLDING_ALLOWLISTED_GROUPS", "ALLOWLISTED_GROUPS", ""
            )
            project_allowlist = [g.strip() for g in allowlist_str.split(",") if g.strip()]

            return ScaffoldingAgentConfig(
                vcs_provider=vcs_provider,
                tracker_provider=tracker_provider,
                research_provider=research_provider,
                llm_model_priority=llm_priority_list,
                work_dir=work_dir,
                architecture_page_id=arch_page_id,
                enable_secure_mode=enable_secure,
                project_allowlist=project_allowlist,
            )
        except Exception as e:
            logger.error(f"Failed to load scaffolding config: {e}")
            raise ValueError(f"Invalid Configuration: {e}") from e

    @staticmethod
    def _get_value(specific_key: str, global_key: str, default: Any) -> str:
        """Helper to implement precedence rule."""
        if val := os.getenv(specific_key):
            return val
        if val := os.getenv(global_key):
            return val
        return str(default)

    @staticmethod
    def _load_vcs_provider() -> VcsProviderType:
        val = ScaffoldingConfigLoader._get_value(
            "SCAFFOLDING_VCS_PROVIDER", "VCS_PROVIDER", VcsProviderType.GITLAB.value
        )
        return VcsProviderType(val.lower())

    @staticmethod
    def _load_tracker_provider() -> TaskTrackerType:
        val = ScaffoldingConfigLoader._get_value(
            "SCAFFOLDING_TRACKER_PROVIDER",
            "TRACKER_PROVIDER",
            TaskTrackerType.JIRA.value,
        )
        return TaskTrackerType(val.lower())

    @staticmethod
    def _load_research_provider() -> ResearchProviderType:
        val = ScaffoldingConfigLoader._get_value(
            "SCAFFOLDING_RESEARCH_PROVIDER",
            "KNOWLEDGE_PROVIDER",
            ResearchProviderType.CONFLUENCE.value,
        )
        return ResearchProviderType(val.lower())

    @staticmethod
    def _load_llm_priority() -> list[ModelId]:
        default_list = [
            "openai:gpt-4-turbo",
            "openai:gpt-4o",
            "gemini:gemini-1.5-flash",
            "deepseek:deepseek-coder",
            "anthropic:claude-3-5-sonnet",
        ]
        # We manually serialize default list to JSON string to use same parsing logic if needed,
        # or simplified flow:
        
        json_str = ScaffoldingConfigLoader._get_value(
            "SCAFFOLDING_LLM_MODEL_PRIORITY",
            "LLM_MODEL_PRIORITY",
            json.dumps(default_list),
        )

        return ScaffoldingConfigLoader._parse_llm_priority(json_str)

    @staticmethod
    def _parse_llm_priority(json_str: str) -> list[ModelId]:
        # Pre-process cleanup for robust handling of shell quotes
        clean_content = json_str.strip()
        # Remove surrounding single quotes if present (e.g. "'[...]'" -> "[...]")
        if clean_content.startswith("'") and clean_content.endswith("'"):
            clean_content = clean_content[1:-1]
        # Remove surrounding double quotes if present (e.g. '"[...]"' -> "[...]")
        elif clean_content.startswith('"') and clean_content.endswith('"'):
            clean_content = clean_content[1:-1]
            
        try:
            raw_list = json.loads(clean_content)
            if not isinstance(raw_list, list):
                # If parsing fails or not a list, revert to default? Or error?
                # The requirements imply robust defaults.
                logger.warning(
                    f"Parsed LLM priority is not a list: {type(raw_list)}. Using default."
                )
                return ScaffoldingConfigLoader._parse_llm_priority(
                    json.dumps(
                        [
                            "openai:gpt-4-turbo",
                            "openai:gpt-4o",
                            "gemini:gemini-1.5-flash",
                            "deepseek:deepseek-coder",
                            "anthropic:claude-3-5-sonnet",
                        ]
                    )
                )

            model_ids = []
            for item in raw_list:
                try:
                    # Expecting format "provider:model_name"
                    if ":" not in item:
                        logger.warning(
                            f"Invalid model string format '{item}'. Expected 'provider:model'. Skipping."
                        )
                        continue
                        
                    provider_str, model_name = item.split(":", 1)
                    
                    # Validate provider against Enum
                    # Enum lookup by name or value. 
                    # LlmProviderType.OPENAI.value = 'openai'
                    # We expect provider_str to be 'openai' or 'OPENAI'
                    try:
                        provider = LlmProviderType(provider_str.lower())
                    except ValueError:
                         # Try upper case just in case? Or log error
                         logger.warning(f"Unknown provider '{provider_str}' in LLM config. Skipping.")
                         continue

                    model_ids.append(ModelId(provider=provider, name=model_name))
                except Exception as e:
                    logger.warning(f"Error parsing model item '{item}': {e}")
                    continue

            if not model_ids:
                logger.warning("LLM Priority list empty after parsing. Using fallback.")
                return [
                     ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-turbo")
                ]

            return model_ids

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON for LLM_MODEL_PRIORITY: {json_str}")
            # Robust fallback
            return [ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-turbo")]
