import json
import os
from pathlib import Path
from typing import Any, cast

from software_factory_poc.core.application.agents.scaffolder.config.scaffolding_agent_config import (
    ScaffoldingAgentConfig,
)
from software_factory_poc.core.domain.value_objects.llm.llm_provider_type import LlmProviderType
from software_factory_poc.core.domain.value_objects.llm.model_id import ModelId
from software_factory_poc.core.domain.value_objects.research.research_provider_type import (
    ResearchProviderType,
)
from software_factory_poc.core.domain.value_objects.task.task_tracker_type import TaskTrackerType
from software_factory_poc.core.domain.value_objects.vcs.vcs_provider_type import VcsProviderType
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
            vcs_provider = ScaffoldingConfigLoader._load_vcs_provider()
            tracker_provider = ScaffoldingConfigLoader._load_tracker_provider()
            research_provider = ScaffoldingConfigLoader._load_research_provider()
            llm_priority_list = ScaffoldingConfigLoader._load_llm_priority()
            work_dir = Path(os.getenv("WORK_DIR", "/tmp/scaffolding_workspace"))
            enable_secure = os.getenv("ENABLE_SECURE_MODE", "True").lower() == "true"
            arch_page_id = ScaffoldingConfigLoader._get_value(
                "SCAFFOLDING_ARCHITECTURE_PAGE_ID", "ARCHITECTURE_DOC_PAGE_ID", "3571713"
            )
            raw_allowlist = ScaffoldingConfigLoader._get_value(
                "SCAFFOLDING_ALLOWLISTED_GROUPS", "ALLOWLISTED_GROUPS", ""
            )

            return ScaffoldingAgentConfig(
                vcs_provider=vcs_provider,
                tracker_provider=tracker_provider,
                research_provider=research_provider,
                llm_model_priority=llm_priority_list,
                work_dir=work_dir,
                architecture_page_id=arch_page_id,
                enable_secure_mode=enable_secure,
                project_allowlist=cast(Any, raw_allowlist),
            )
        except Exception as e:
            logger.error(f"Failed to load scaffolding config: {e}")
            raise ValueError(f"Invalid Configuration: {e}") from e

    @staticmethod
    def _get_value(specific_key: str, global_key: str, default: Any) -> str:
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

        json_str = ScaffoldingConfigLoader._get_value(
            "SCAFFOLDING_LLM_MODEL_PRIORITY",
            "LLM_MODEL_PRIORITY",
            json.dumps(default_list),
        )

        return ScaffoldingConfigLoader._parse_llm_priority(json_str)

    @staticmethod
    def _parse_llm_priority(json_str: str) -> list[ModelId]:
        clean_content = json_str.strip()
        if clean_content.startswith("'") and clean_content.endswith("'"):
            clean_content = clean_content[1:-1]
        elif clean_content.startswith('"') and clean_content.endswith('"'):
            clean_content = clean_content[1:-1]

        try:
            raw_list = json.loads(clean_content)
            if not isinstance(raw_list, list):
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
                    if ":" not in item:
                        logger.warning(
                            f"Invalid model string format '{item}'. Expected 'provider:model'. Skipping."
                        )
                        continue

                    provider_str, model_name = item.split(":", 1)

                    try:
                        provider = LlmProviderType(provider_str.lower())
                    except ValueError:
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

        except json.JSONDecodeError:
            logger.error(f"Invalid JSON for LLM_MODEL_PRIORITY: {json_str}")
            return [ModelId(provider=LlmProviderType.OPENAI, name="gpt-4-turbo")]
