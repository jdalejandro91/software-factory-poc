import json
import re
from typing import Optional

import yaml
from pydantic import ValidationError

from software_factory_poc.contracts.scaffolding_contract_model import ScaffoldingContractModel
from software_factory_poc.observability.logger_factory_service import build_logger

logger = build_logger(__name__)

# Constants for legacy delimiters
BLOCK_START = "--- SCAFFOLDING_CONTRACT:v1 ---"
BLOCK_END = "--- /SCAFFOLDING_CONTRACT ---"

class ContractParseError(Exception):
    """Raised when the contract cannot be parsed or validated."""
    def __init__(self, message: str, safe_snippet: str = ""):
        super().__init__(message)
        self.safe_snippet = safe_snippet


class ScaffoldingContractParserService:
    def parse(self, text: str) -> ScaffoldingContractModel:
        if not text:
            raise ContractParseError("Input text is empty.")

        # Normalizar saltos de línea para evitar problemas con \r\n vs \n
        cleaned_text = text.replace("\r\n", "\n")

        block_content = self._extract_block(cleaned_text)
        if not block_content:
            # Log de depuración para ver qué llegó realmente
            logger.warning(f"Failed to find block in text (len={len(text)}). First 100 chars: {text[:100]!r}")
            raise ContractParseError(
                f"Could not find contract block. Ensure you use ```scaffolding (code block) or delimiters '{BLOCK_START}'."
            )

        data = self._parse_structure(block_content)
        
        try:
            return ScaffoldingContractModel(**data)
        except ValidationError as e:
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
        Prioritizes standard Markdown code blocks with relaxed regex.
        """
        # 1. Try Markdown code blocks (```scaffolding, ```yaml, or just ```)
        # Regex Explanation:
        # ```                 -> Literal backticks
        # [ \t]* -> Optional spaces/tabs before language identifier
        # (?:scaffolding|yaml|json)? -> Optional language identifier
        # [ \t]* -> Optional spaces after identifier
        # \n                  -> Newline starting the block
        # (.*?)               -> THE CONTENT (Lazy match)
        # \n                  -> Newline ending the block
        # [ \t]* -> Optional spaces before closing backticks
        # ```                 -> Closing backticks
        
        block_pattern = r"```[ \t]*(?:scaffolding|yaml|json)?[ \t]*\n(.*?)\n[ \t]*```"
        match = re.search(block_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
             return match.group(1).strip()

        # 2. Legacy delimiters (Backup)
        pattern = re.escape(BLOCK_START) + r"\s*(.*?)\s*" + re.escape(BLOCK_END)
        match = re.search(pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return None

    def _parse_structure(self, content: str) -> dict:
        # Try YAML
        try:
            parsed = yaml.safe_load(content)
            if isinstance(parsed, dict):
                return parsed
        except yaml.YAMLError:
            pass

        # Try JSON
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        snippet = content[:200] + ("..." if len(content) > 200 else "")
        raise ContractParseError(
            "Could not parse valid YAML or JSON from contract block.",
            safe_snippet=snippet
        )
