from pydantic import ValidationError

from software_factory_poc.application.core.domain.entities.scaffolding.scaffolding_contract import (
    ScaffoldingContractModel,
)
from software_factory_poc.application.core.domain.exceptions.contract_parse_error import (
    ContractParseError,
)
from software_factory_poc.application.core.domain.services.helpers.text_block_extractor import (
    TextBlockExtractor,
)
from software_factory_poc.application.core.domain.services.helpers.yaml_json_parser import (
    YamlJsonParser,
)


class ScaffoldingContractParserService:
    def parse(self, text: str) -> ScaffoldingContractModel:
        if not text:
            raise ContractParseError("Input text is empty.")

        # Normalizar saltos de línea
        cleaned_text = text.replace("\r\n", "\n")

        block_content = TextBlockExtractor.extract_block(cleaned_text)
        
        # Determine what content to parse: Block content if found, else raw text (fallback)
        content_to_parse = block_content if block_content else cleaned_text

        try:
            data = YamlJsonParser.parse(content_to_parse)
        except ValueError:
            # If parsing failed and we didn't find a block explicitly, 
            # we assume the user intended to provide a block but failed delimiters,
            # OR the raw text was not a valid contract.
            # We revert to the original error about missing blocks for clarity in Jira context.
            if not block_content:
                raise ContractParseError(
                    "Could not find contract block (or valid raw YAML). Use Markdown code blocks (```) or Jira Wiki blocks ({code})."
                )
            
            # Construct snippet for error
            snippet = content_to_parse[:200] + ("..." if len(content_to_parse) > 200 else "")
            raise ContractParseError(
                "Could not parse valid YAML or JSON from contract block.",
                safe_snippet=snippet
            )
        
        try:
            return ScaffoldingContractModel(**data)
        except ValidationError as e:
            cleaned_errors = []
            for err in e.errors():
                loc = ".".join(str(l) for l in err["loc"])
                msg = err["msg"]
                cleaned_errors.append(f"{loc}: {msg}")
            
            error_msg = "; ".join(cleaned_errors)
            
            # Fallback to cleaned_text if block_content is None (e.g. raw parsing)
            ref_content = block_content if block_content else cleaned_text
            snippet = ref_content[:200] + ("..." if len(ref_content) > 200 else "")
            
            raise ContractParseError(
                f"Contract validation failed: {error_msg}", 
                safe_snippet=snippet
            ) from e
