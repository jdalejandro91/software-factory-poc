import asyncio
from software_factory_poc.application.core.interfaces.llm_gateway import LLMGatewayPort, LLMError
from software_factory_poc.infrastructure.providers.facade.llm_bridge import LlmBridge
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

class LlmGatewayAdapter(LLMGatewayPort):
    def __init__(self, bridge: LlmBridge):
        self.bridge = bridge

    def generate_code(self, prompt: str, model: str) -> str:
        # Note: The existing LlmBridge uses async methods internally (via provider implementations)
        # But the specific method 'generate_scaffolding' or generic 'generate' is what we need.
        # The bridge has .gateway which is the LlmProvider.
        # LlmProvider interface has `generate(prompt: str) -> str` (async).
        # We need to bridge sync/async if this Port is sync.
        # The Port `generate_code` is defined as sync in the interface (def generate_code(...)).
        # So we run async loop here.
        
        try:
            # Depending on model name, we might switch provider if bridge supports it.
            # Currently bridge might be configured for one provider.
            # We will ignore 'model' arg if bridge is fixed, or map it.
            # Assuming bridge.gateway.generate handles it.
            
            result = asyncio.run(self.bridge.gateway.generate(prompt))
            return result
        except Exception as e:
            logger.error(f"LLM Adapter failed: {e}")
            raise LLMError(f"Failed to generate code: {e}") from e
