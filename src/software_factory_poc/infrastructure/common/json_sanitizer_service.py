import re
import logging
from typing import Type, TypeVar, Any
from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

class JsonParsingError(Exception):
    """Raised when JSON content cannot be extracted or parsed from text."""
    pass

class SchemaValidationError(Exception):
    """Raised when extracted JSON does not match the Pydantic schema."""
    pass

class JsonSanitizerService:
    @staticmethod
    def extract_and_validate_json(text: str, model: Type[T]) -> T:
        """
        Extracts JSON from a (potentially dirty) string and validates it against a Pydantic model.
        
        Args:
            text: The raw input string (e.g., from an LLM).
            model: The Pydantic V2 model class to validate against.
            
        Returns:
            An instance of the Pydantic model.
            
        Raises:
            JsonParsingError: If no JSON object can be found or parsed.
            SchemaValidationError: If the JSON is valid but does not match the schema.
        """
        clean_text = text.strip()
        
        # 1. Attempt Regex extraction (First { to last })
        # DOTALL allows . to match newlines, important for multi-line JSON
        match = re.search(r"(\{.*\})", clean_text, re.DOTALL)
        
        content_to_parse = ""
        
        if match:
            content_to_parse = match.group(1)
        else:
            # 2. Fallback: Clean Markdown Code Blocks if Regex failed
            # Sometimes LLMs format weirdly, so we try stripping delimiters manually
            # if the strict curly brace finder didn't work (e.g. if it's a list []? But requirements say object {})
            # Requirement says: "Si no encuentra llaves, lanzar JsonParsingError"
            # But also: "Si el regex falla, intentar limpiar bloques de código comunes"
            # So if regex fails, we assume maybe the regex was too strict or the start/end was ambiguous?
            # Actually, standard JSON object MUST have braces. 
            # If regex didn't find braces, it's NOT a JSON object.
            # But let's try the markdown strip just in case the braces were somehow not captured or input is just blocks?
            # If input is ```json ... ```, regex match r"(\{.*\})" SHOULD find it inside.
            # Let's stick to the user instruction: 
            # 1. Regex. 2. If regex fails, try cleanup. 
            # If I cleanup ` ```json { ... } ``` `, I get `{ ... }`. Then I can try regex again or parse directly.
            
            logger.debug("Regex extraction failed. Attempting MarkDown cleanup.")
            stripped = clean_text
            if stripped.startswith("```"):
                stripped = re.sub(r"^```(json)?", "", stripped, flags=re.IGNORECASE)
                stripped = re.sub(r"```$", "", stripped)
                stripped = stripped.strip()
            
            # After strip, check for braces again or try parsing directly?
            # User said: "Si el regex falla, intentar limpiar...".
            # If we stripped it, maybe it is now pure JSON.
            content_to_parse = stripped
            
            # One final emptiness check
            if not content_to_parse:
                 raise JsonParsingError("Could not find any content resembling JSON.")

        # 3. Pydantic Validation
        try:
            # model_validate_json performs JSON parsing AND validation in one go (using Rust)
            return model.model_validate_json(content_to_parse)
        except ValidationError as e:
            # Check if it is a JSON syntax error
            # Pydantic V2 uses 'json_invalid' type for syntax errors
            for err in e.errors():
                if err.get('type') == 'json_invalid':
                     logger.error(f"JSON syntax error: {e}")
                     raise JsonParsingError(f"Invalid JSON Syntax: {e}")

            logger.error(f"Validation failed for content: {content_to_parse[:100]}... Error: {e}")
            raise SchemaValidationError(f"JSON Structure Invalid: {e}")
        except Exception as e:
            # If it's a raw JSONDecodeError (not sure if Pydantic wraps it always)
            logger.error(f"JSON parsing failed: {e}")
            raise JsonParsingError(f"Failed to parse JSON content: {e}")
