import json
import re
from typing import Optional

import yaml
from pydantic import ValidationError

from software_factory_poc.contracts.scaffolding_contract_model import ScaffoldingContractModel
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

# Constants for delimiters
BLOCK_START = "--- SCAFFOLDING_CONTRACT:v1 ---"
BLOCK_END = "--- /SCAFFOLDING_CONTRACT ---"

class ContractParseError(Exception):
    """Raised when the contract cannot be parsed or validated."""
    def __init__(self, message: str, safe_snippet: str = ""):
        super().__init__(message)
        self.safe_snippet = safe_snippet


class ScaffoldingContractParserService:
    def parse(self, text: str) -> ScaffoldingContractModel:
        """
        Extracts the scaffolding contract block from text, parses it (YAML/JSON),
        and validates it against the Pydantic model.
        """
        if not text:
            raise ContractParseError("Input text is empty.")

        block_content = self._extract_block(text)
        if not block_content:
            raise ContractParseError(
                f"Could not find contract block. Use ```scaffolding or start with '{BLOCK_START}' and end with '{BLOCK_END}'."
            )

        data = self._parse_structure(block_content)
        
        try:
            return ScaffoldingContractModel(**data)
        except ValidationError as e:
            # Format validation errors safely
            cleaned_errors = []
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                msg = err["msg"]
                cleaned_errors.append(f"{loc}: {msg}")
            
            error_msg = "; ".join(cleaned_errors)
            snippet = block_content[:200] + ("..." if len(block_content) > 200 else "")
            
            raise ContractParseError(
                f"Contract validation failed: {error_msg}", 
                safe_snippet=snippet
            ) from e

    def _extract_block(self, text: str) -> Optional[str]:
        """
        Finds the content between start and end delimiters.
        Prioritizes standard Markdown code blocks: ```scaffolding ... ```
        Falls back to legacy delimiters.
        """
        # 1. Try Markdown code blocks (```scaffolding, ```yaml, or just ```)
        # Matches ```optional_lang\n ...content... ```
        block_pattern = r"```(?:scaffolding|yaml|json)?\n(.*?)\n?```"
        match = re.search(block_pattern, text, re.DOTALL)
        if match:
             return match.group(1).strip()

        # 2. Legacy delimiters
        # Escape markers just in case they contain regex meta-characters
        pattern = re.escape(BLOCK_START) + r"\s*(.*?)\s*" + re.escape(BLOCK_END)
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return None

    def _parse_structure(self, content: str) -> dict:
        """
        Tries to parse content as YAML first, then JSON.
        """
        # Try YAML
        try:
            # safe_load is recommended for untrusted input
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
            # If yaml parsed but isn't a dict (e.g. a string or list), fail
        except yaml.YAMLError:
            # Not valid YAML, fall through to try JSON
            pass

        # Try JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        # If both fail
        snippet = content[:200] + ("..." if len(content) > 200 else "")
        raise ContractParseError(
            "Could not parse valid YAML or JSON from contract block.",
            safe_snippet=snippet
        )
