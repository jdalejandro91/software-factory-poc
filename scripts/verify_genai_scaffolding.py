
import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from software_factory_poc.application.core.entities.llm_response import LlmResponse
from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.scaffolding.genai_scaffolding_service import GenaiScaffoldingService


class TestGenaiScaffolding(unittest.TestCase):
    def setUp(self):
        self.mock_bridge = MagicMock()
        # bridge.generate is async
        self.mock_bridge.generate = AsyncMock()
        
        self.mock_knowledge = MagicMock()
        self.mock_knowledge.get_architecture_guidelines.return_value = "Architecture Rules..."
        
        self.service = GenaiScaffoldingService(self.mock_bridge, self.mock_knowledge)

    def test_scaffolding_flow(self):
        async def run_test():
            # Setup Mock Responses
            
            # Response 1: Planning (JSON list)
            response_plan = LlmResponse(
                model=ModelId(ProviderName.OPENAI, "gpt-4o"),
                content='["src/main.py", "src/utils.py"]'
            )
            
            # Response 2: Code for main.py
            response_code_main = LlmResponse(
                model=ModelId(ProviderName.OPENAI, "gpt-4o"),
                content='print("Hello Main")'
            )
            
            # Response 3: Code for utils.py
            response_code_utils = LlmResponse(
                model=ModelId(ProviderName.OPENAI, "gpt-4o"),
                content='def util(): pass'
            )
            
            # Configure side_effect for the async method
            # Note: The service calls generate 3 times.
            # 1. Planning
            # 2. Main.py (parallel)
            # 3. Utils.py (parallel)
            # Order of parallel calls isn't guaranteed, but planning is first.
            
            # We can use a side_effect function to check the request prompt to decide return value
            async def generate_side_effect(request):
                # Simple heuristic based on prompt content
                user_msg = request.messages[1].content
                if "Genera un JSON" in user_msg:
                    return response_plan
                elif "src/main.py" in user_msg:
                    return response_code_main
                elif "src/utils.py" in user_msg:
                    return response_code_utils
                else:
                    raise ValueError(f"Unexpected prompt: {user_msg}")

            self.mock_bridge.generate.side_effect = generate_side_effect
            
            # Execute
            result = await self.service.generate_scaffolding("ISSUE-123", "Build a hello world")
            
            # Verify
            self.assertEqual(len(result), 2)
            self.assertEqual(result["src/main.py"], 'print("Hello Main")')
            self.assertEqual(result["src/utils.py"], 'def util(): pass')
            
            # Validation assertions
            print("Successfully generated scaffolding for 2 files.")
            print("Result keys:", result.keys())

        # Run async test
        asyncio.run(run_test())

if __name__ == "__main__":
    unittest.main()
