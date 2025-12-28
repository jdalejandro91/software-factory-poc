from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from llm_bridge.core.entities.llm_request import LlmRequest
from llm_bridge.core.entities.llm_response import LlmResponse
from llm_bridge.core.exceptions.configuration_error import ConfigurationError
from llm_bridge.core.value_objects.provider_name import ProviderName
from llm_bridge.providers.anthropic.anthropic_client_factory import AnthropicClientFactory
from llm_bridge.providers.anthropic.anthropic_config import AnthropicConfig
from llm_bridge.providers.anthropic.anthropic_provider import AnthropicProvider
from llm_bridge.providers.anthropic.anthropic_request_mapper import AnthropicRequestMapper
from llm_bridge.providers.anthropic.anthropic_response_mapper import AnthropicResponseMapper
from llm_bridge.providers.deepseek.deepseek_client_factory import DeepSeekClientFactory
from llm_bridge.providers.deepseek.deepseek_config import DeepSeekConfig
from llm_bridge.providers.deepseek.deepseek_provider import DeepSeekProvider
from llm_bridge.providers.deepseek.deepseek_request_mapper import DeepSeekRequestMapper
from llm_bridge.providers.deepseek.deepseek_response_mapper import DeepSeekResponseMapper
from llm_bridge.providers.gateway.llm_gateway import LlmGateway
from llm_bridge.providers.gateway.model_allowlist import ModelAllowlist
from llm_bridge.providers.gemini.gemini_client_factory import GeminiClientFactory
from llm_bridge.providers.gemini.gemini_config import GeminiConfig
from llm_bridge.providers.gemini.gemini_provider import GeminiProvider
from llm_bridge.providers.gemini.gemini_request_mapper import GeminiRequestMapper
from llm_bridge.providers.gemini.gemini_response_mapper import GeminiResponseMapper
from llm_bridge.providers.logging.correlation_id_context import CorrelationIdContext
from llm_bridge.providers.logging.logging_configurator import LoggingConfigurator
from llm_bridge.providers.openai.openai_client_factory import OpenAiClientFactory
from llm_bridge.providers.openai.openai_config import OpenAiConfig
from llm_bridge.providers.openai.openai_provider import OpenAiProvider
from llm_bridge.providers.openai.openai_request_mapper import OpenAiRequestMapper
from llm_bridge.providers.openai.openai_response_mapper import OpenAiResponseMapper
from llm_bridge.providers.ports.llm_provider import LlmProvider
from llm_bridge.providers.retry.retry_policy import RetryPolicy


@dataclass(frozen=True, slots=True)
class LlmBridge:
    gateway: LlmGateway
    correlation: CorrelationIdContext

    async def generate(self, request: LlmRequest) -> LlmResponse:
        return await self.gateway.generate(request)

    def configure_default_logging(self, level: str = "INFO") -> None:
        LoggingConfigurator(self.correlation).configure(level)

    @staticmethod
    def from_env() -> "LlmBridge":
        correlation = CorrelationIdContext()
        allowlist = ModelAllowlist(allowed=_read_allowlist())
        retry = RetryPolicy(max_attempts=int(os.getenv("LLM_BRIDGE_RETRY_ATTEMPTS", "3")))
        providers = _build_providers(retry, correlation)
        return LlmBridge(gateway=LlmGateway(allowlist=allowlist, providers=providers), correlation=correlation)


def _read_allowlist() -> frozenset[str]:
    raw = os.getenv("LLM_BRIDGE_ALLOWED_MODELS", "").strip()
    if not raw:
        raise ConfigurationError("LLM_BRIDGE_ALLOWED_MODELS is required (comma-separated qualified names)")
    return frozenset([m.strip() for m in raw.split(",") if m.strip()])


def _build_providers(retry: RetryPolicy, correlation: CorrelationIdContext) -> Mapping[ProviderName, LlmProvider]:
    providers: dict[ProviderName, LlmProvider] = {}
    _maybe_add_openai(providers, retry, correlation)
    _maybe_add_anthropic(providers, retry, correlation)
    _maybe_add_gemini(providers, retry, correlation)
    _maybe_add_deepseek(providers, retry, correlation)
    return providers


def _maybe_add_openai(dst: dict[ProviderName, LlmProvider], retry: RetryPolicy, correlation: CorrelationIdContext) -> None:
    if not os.getenv("OPENAI_API_KEY"):
        return
    client = OpenAiClientFactory(OpenAiConfig.from_env()).create()
    dst[ProviderName.OPENAI] = OpenAiProvider(client=client, retry=retry, request_mapper=OpenAiRequestMapper(), response_mapper=OpenAiResponseMapper(), correlation=correlation)


def _maybe_add_anthropic(dst: dict[ProviderName, LlmProvider], retry: RetryPolicy, correlation: CorrelationIdContext) -> None:
    if not os.getenv("ANTHROPIC_API_KEY"):
        return
    client = AnthropicClientFactory(AnthropicConfig.from_env()).create()
    dst[ProviderName.ANTHROPIC] = AnthropicProvider(client=client, retry=retry, request_mapper=AnthropicRequestMapper(), response_mapper=AnthropicResponseMapper(), correlation=correlation)


def _maybe_add_gemini(dst: dict[ProviderName, LlmProvider], retry: RetryPolicy, correlation: CorrelationIdContext) -> None:
    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
        return
    client = GeminiClientFactory(GeminiConfig.from_env()).create()
    dst[ProviderName.GEMINI] = GeminiProvider(client=client, retry=retry, request_mapper=GeminiRequestMapper(), response_mapper=GeminiResponseMapper(), correlation=correlation)


def _maybe_add_deepseek(dst: dict[ProviderName, LlmProvider], retry: RetryPolicy, correlation: CorrelationIdContext) -> None:
    if not os.getenv("DEEPSEEK_API_KEY"):
        return
    client = DeepSeekClientFactory(DeepSeekConfig.from_env()).create()
    dst[ProviderName.DEEPSEEK] = DeepSeekProvider(client=client, retry=retry, request_mapper=DeepSeekRequestMapper(), response_mapper=DeepSeekResponseMapper(), correlation=correlation)
