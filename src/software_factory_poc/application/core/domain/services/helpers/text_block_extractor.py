import re

# Constants for legacy delimiters
BLOCK_START = "--- SCAFFOLDING_CONTRACT:v1 ---"
BLOCK_END = "--- /SCAFFOLDING_CONTRACT ---"


class TextBlockExtractor:
    """
    Finds the content using multiple patterns (Markdown, Jira Wiki, Legacy).
    """
    
    @staticmethod
    def extract_block(text: str) -> str | None:
        """
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
            return match.group(1).strip()

        # 2. Markdown (```yaml...)
        # Igual de permisivo: ``` seguido de algo opcional, espacios opcionales, contenido...
        markdown_pattern = r"```(?:[\w]+)?\s*(.*?)\s*```"
        match = re.search(markdown_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 3. Legacy delimiters
        legacy_pattern = re.escape(BLOCK_START) + r"\s*(.*?)\s*" + re.escape(BLOCK_END)
        match = re.search(legacy_pattern, text, re.DOTALL)
        if match:
            return match.group(1).strip()
            
        return None
