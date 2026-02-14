import json
from typing import Any, Callable, List, Dict
from software_factory_poc.application.ports.drivers.reasoner.llm_driver_port import LlmDriverPort

class LlmGatewayAdapter(LlmDriverPort):
    def __init__(self, composite_gateway):
        self.gateway = composite_gateway

    async def generate_structured(self, prompt: str, schema_cls: Any) -> Any:
        json_schema = schema_cls.model_json_schema()
        system = f"Responde ÚNICAMENTE en este JSON: {json_schema}"
        response_text = await self.gateway.generate(prompt=prompt, system_prompt=system)

        return schema_cls(**json.loads(response_text))

    async def run_agentic_loop(self, prompt: str, tools: List[Dict], tool_executor: Callable) -> str:
        # Bucle ReAct usando tu gateway actual (pendiente de implementación)
        pass