
import pytest
import json
from software_factory_poc.infrastructure.configuration.scaffolding_config_loader import ScaffoldingConfigLoader
from software_factory_poc.application.core.agents.common.value_objects.model_id import ModelId

class TestConfigLoaderRobustness:
    def test_parses_clean_json_list(self):
        json_str = '["openai:model1", "deepseek:model2"]'
        result = ScaffoldingConfigLoader._parse_llm_priority(json_str)
        assert len(result) == 2
        assert result[0].name == "model1"

    def test_parses_single_quoted_env_var(self):
        # Simulates export VAR="'[...]'"
        json_str = "'[\"openai:model1\"]'"
        result = ScaffoldingConfigLoader._parse_llm_priority(json_str)
        assert len(result) == 1
        assert result[0].name == "model1"

    def test_parses_double_quoted_env_var(self):
        # Simulates export VAR="[...]" where quotes remain
        json_str = '"[\"openai:model1\"]"'
        result = ScaffoldingConfigLoader._parse_llm_priority(json_str)
        assert len(result) == 1
        assert result[0].name == "model1"

    def test_parses_mixed_whitespace_and_quotes(self):
        json_str = "  '[\"openai:model1\"]'  "
        result = ScaffoldingConfigLoader._parse_llm_priority(json_str)
        assert len(result) == 1

    def test_fallback_on_invalid_json(self):
        json_str = "invalid-json"
        # Should fallback to default list
        result = ScaffoldingConfigLoader._parse_llm_priority(json_str)
        assert len(result) > 0
        # Default list starts with gpt-4-turbo usually
        assert result[0].provider.value == "openai"
