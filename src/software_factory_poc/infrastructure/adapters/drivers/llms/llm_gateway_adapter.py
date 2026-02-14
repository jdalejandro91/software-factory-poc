import json
import asyncio
from typing import Any, Callable, List, Dict
from software_factory_poc.application.ports.drivers.llm_driver_port import LlmDriverPort
from software_factory_poc.infrastructure.adapters.drivers.llms.gateway.composite_gateway import CompositeLlmGateway


class LlmGatewayAdapter(LlmDriverPort):
    def __init__(self, gateway: CompositeLlmGateway):
        self.gateway = gateway

    async def generate_structured(self, prompt: str, schema_cls: Any, system_prompt: str = "") -> Any:
        json_schema = schema_cls.model_json_schema()
        full_prompt = f"{system_prompt}\n\n{prompt}\n\nRESPONDE ÚNICAMENTE CON ESTE ESQUEMA JSON:\n{json.dumps(json_schema)}"
        response = await asyncio.to_thread(
            self.gateway.generate_code,
            prompt=full_prompt,
            context="",
            model_hints=[]
        )
        res_text = response.content[0].text if hasattr(response, "content") else str(response)
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0].strip()
        elif "```" in res_text:
            res_text = res_text.split("```")[1].strip()

        return schema_cls.model_validate_json(res_text)

    async def run_agentic_loop(self, prompt: str, tools: List[Dict], tool_executor: Callable) -> str:
        pass