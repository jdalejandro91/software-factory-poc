import json
import re

import yaml
from pydantic import ValidationError

from software_factory_poc.application.core.entities.scaffolding.scaffolding_contract import ScaffoldingContractModel
from software_factory_poc.infrastructure.observability.logger_factory_service import build_logger

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

        # Normalizar saltos de línea
        cleaned_text = text.replace("\r\n", "\n")

        block_content = self._extract_block(cleaned_text)
        
        # Determine what content to parse: Block content if found, else raw text (fallback)
        content_to_parse = block_content if block_content else cleaned_text

        try:
            data = self._parse_structure(content_to_parse)
        except ContractParseError:
            # If parsing failed and we didn't find a block explicitly, 
            # we assume the user intended to provide a block but failed delimiters,
            # OR the raw text was not a valid contract.
            # We revert to the original error about missing blocks for clarity in Jira context.
            if not block_content:
                logger.warning(f"Failed to find block and raw text is not valid contract. Content preview: {cleaned_text[:200]!r}")
                raise ContractParseError(
                    "Could not find contract block (or valid raw YAML). Use Markdown code blocks (```) or Jira Wiki blocks ({code})."
                )
            raise
        
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

    def _extract_block(self, text: str) -> str | None:
        """
        Finds the content using multiple patterns (Markdown, Jira Wiki, Legacy).
        Relaxed regex to handle missing newlines or tight spacing.
        """
        # 1. Jira Wiki Markup ({code:yaml}...)
        # Explicación Regex:
        # \{code(?:[:\w]+)?\} -> Busca {code} o {code:yaml} o {code:json}
        # \s* -> Cero o más espacios/saltos de línea (permisivo)
        # (.*?)               -> El contenido (Non-greedy)
        # \s* -> Cero o más espacios/saltos de línea
        # \{code\}            -> Cierre
        jira_wiki_pattern = r"\{code(?:[:\w]+)?\}\s*(.*?)\s*\{code\}"
        match = re.search(jira_wiki_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            logger.info("Found block using Jira Wiki {code} pattern")
            return match.group(1).strip()

        # 2. Markdown (```yaml...)
        # Igual de permisivo: ``` seguido de algo opcional, espacios opcionales, contenido...
        markdown_pattern = r"```(?:[\w]+)?\s*(.*?)\s*```"
        match = re.search(markdown_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            logger.info("Found block using Markdown ``` pattern")
            return match.group(1).strip()

        # 3. Legacy delimiters
        legacy_pattern = re.escape(BLOCK_START) + r"\s*(.*?)\s*" + re.escape(BLOCK_END)
        match = re.search(legacy_pattern, text, re.DOTALL)
        if match:
            logger.info("Found block using Legacy delimiters")
            return match.group(1).strip()
            
        return None

    def _parse_structure(self, content: str) -> dict:
        # Try YAML (Priority)
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
