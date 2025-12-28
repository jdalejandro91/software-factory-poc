from __future__ import annotations

import asyncio
import json
import logging
import re

from software_factory_poc.application.core.entities.llm_request import LlmRequest
from software_factory_poc.application.core.exceptions.llm_bridge_error import LlmBridgeError
from software_factory_poc.application.core.value_objects.generation_config import GenerationConfig
from software_factory_poc.application.core.value_objects.message import Message
from software_factory_poc.application.core.value_objects.message_role import MessageRole
from software_factory_poc.application.core.value_objects.model_id import ModelId
from software_factory_poc.application.core.value_objects.output_constraints import OutputConstraints
from software_factory_poc.application.core.value_objects.output_format import OutputFormat
from software_factory_poc.application.core.value_objects.provider_name import ProviderName
from software_factory_poc.application.ports.llms.llm_provider import LlmProvider
from software_factory_poc.application.usecases.knowledge.architecture_knowledge_service import (
    ArchitectureKnowledgeService,
)

logger = logging.getLogger(__name__)


class GenaiScaffoldingService:
    def __init__(
        self,
        llm: LlmProvider,
        knowledge_service: ArchitectureKnowledgeService,
    ) -> None:
        self.llm = llm
        self.knowledge_service = knowledge_service
        # Hardcoding model as requested, but could be config
        self.model = ModelId(ProviderName.OPENAI, "gpt-4o")

    async def generate_scaffolding(self, issue_key: str, issue_description: str) -> dict[str, str]:
        """
        Generates scaffolding code for a given issue using a 2-phase GenAI process.
        
        Phase 1: Planning (Architect) - Determines file structure.
        Phase 2: Coding (Developer) - Generates code for each file in parallel.
        
        Returns:
            Dict[str, str]: Mapping of file_path -> code_content.
        """
        logger.info(f"[{issue_key}] Starting scaffolding generation.")
        
        # 0. Context Loading
        logger.info(f"[{issue_key}] Loading architecture context...")
        architecture_text = self.knowledge_service.get_architecture_guidelines()
        
        # 1. Phase 1: Planning
        logger.info(f"[{issue_key}] Phase 1: Planning structure...")
        file_paths = await self._plan_structure(issue_description, architecture_text)
        logger.info(f"[{issue_key}] Planned {len(file_paths)} files: {file_paths}")
        
        # 2. Phase 2: Coding
        logger.info(f"[{issue_key}] Phase 2: Generating code for {len(file_paths)} files...")
        results = await self._generate_code_parallel(file_paths, issue_description, architecture_text)
        
        return results

    async def _plan_structure(self, issue_description: str, architecture_text: str) -> list[str]:
        system_prompt = f"Actúa como un Arquitecto de Software Experto. Tu biblia es:\n{architecture_text}"
        user_prompt = (
            f"Analiza este requerimiento: {issue_description}.\n"
            "Genera un JSON con la lista de rutas de archivos (file paths) necesarias para implementar la solución bajo la arquitectura Modular Monolith descrita.\n"
            "NO generes código aún, solo la estructura de archivos.\n"
            "Formato esperado: JSON Array de strings, ejemplo: [\"src/pkg/module/file.py\", ...]"
        )
        
        request = LlmRequest(
            model=self.model,
            messages=(
                Message(MessageRole.SYSTEM, system_prompt),
                Message(MessageRole.USER, user_prompt),
            ),
            generation=GenerationConfig(temperature=0.2), # Low temp for structural consistency
            output=OutputConstraints(format=OutputFormat.JSON_OBJECT) # Hint JSON mode if supported
        )
        
        try:
            response = await self.llm.generate(request)
            content = self._clean_json_markdown(response.content)
            
            # Flexible parsing: expecting {"files": [...]} or just [...]
            data = json.loads(content)
            if isinstance(data, list):
                return [str(item) for item in data]
            elif isinstance(data, dict):
                # Try to find a list value suitable
                for key, val in data.items():
                    if isinstance(val, list):
                        return [str(item) for item in val]
                # Fallback if no list found in dict
                logger.warning("JSON dict returned but no list found. Returning keys.")
                return list(data.keys())
            else:
                raise ValueError("Unexpected JSON format from planner.")
                
        except (LlmBridgeError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Planning failed: {e}")
            raise

    async def _generate_code_parallel(
        self, file_paths: list[str], issue_description: str, architecture_text: str
    ) -> dict[str, str]:
        tasks = [
            self._generate_single_file(path, issue_description, architecture_text)
            for path in file_paths
        ]
        
        # Run all generation tasks in parallel
        # return_exceptions=False to let it fail fast or handle individually?
        # Requirement says "Maneja excepciones de LlmBridge". 
        # If one file fails, maybe we should fail the whole batch or return partial?
        # Assuming we want full success for scaffolding.
        generated_files = await asyncio.gather(*tasks)
        
        return {path: content for path, content in generated_files}

    async def _generate_single_file(
        self, path: str, issue_description: str, architecture_text: str
    ) -> tuple[str, str]:
        logger.info(f"Generating code for {path}...")
        
        system_prompt = f"Contexto Arquitectura: {architecture_text}"
        user_prompt = (
            f"Tarea: Genera el código Python para el archivo \"{path}\" basado en el requerimiento \"{issue_description}\".\n"
            "Reglas: Código listo para producción, type hints, SOLID, clases < 120 líneas.\n"
            "Solo devuelve el código, sin markdown formatting si es posible, o en bloque ```python."
        )
        
        request = LlmRequest(
            model=self.model,
            messages=(
                Message(MessageRole.SYSTEM, system_prompt),
                Message(MessageRole.USER, user_prompt),
            ),
            generation=GenerationConfig(temperature=0.0) # Code generation needs precision
        )
        
        try:
            response = await self.llm.generate(request)
            code = self._clean_python_markdown(response.content)
            return path, code
        except LlmBridgeError as e:
            logger.error(f"Failed to generate {path}: {e}")
            raise # Propagate up to gather

    def _clean_json_markdown(self, text: str) -> str:
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _clean_python_markdown(self, text: str) -> str:
        # Strip markdown code blocks if present
        text = text.strip()
        # Handle ```python or ```
        match = re.search(r"```(?:python)?\n(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback for simple stripping if regex fails or no tags
        if text.startswith("```python"):
            text = text[9:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
