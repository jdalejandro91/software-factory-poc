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
        Extracts scaffolding content using robust patterns.
        """
        if not text:
            return None

        # 1. Jira Wiki Markup ({code:yaml}...)
        jira_wiki_pattern = r"\{code(?:[:\w]+)?\}\s*(.*?)\s*\{code\}"
        match = re.search(jira_wiki_pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
             content = match.group(1).strip()
             if TextBlockExtractor._is_likely_scaffolding(content):
                 return content

        # 2. Markdown (```yaml...)
        # Relaxed regex: match any code block, then validate content.
        # ```                     -> Start
        # [ \t]*                  -> Optional spaces 
        # (?:[\w\-\+]+)?          -> Optional language tag (any word/+/-)
        # [ \t\r]*                -> Optional spaces/CR
        # \n                      -> Newline required to start content block
        # (.*?)                   -> Content (Non-greedy)
        # \n                      -> Newline required before end
        # [ \t\r]*                -> Optional whitespace
        # ```                     -> End
        markdown_pattern = r"```[ \t]*(?:[\w\-\+]+)?[ \t\r]*\n(.*?)\n[ \t\r]*```"
        
        # We search iteratively to find the *right* block if multiple exist
        for match in re.finditer(markdown_pattern, text, re.DOTALL | re.IGNORECASE):
            content = match.group(1).strip()
            if TextBlockExtractor._is_likely_scaffolding(content):
                return content

        # 3. Legacy delimiters
        legacy_pattern = re.escape(BLOCK_START) + r"\s*(.*?)\s*" + re.escape(BLOCK_END)
        match = re.search(legacy_pattern, text, re.DOTALL)
        if match:
             content = match.group(1).strip()
             if TextBlockExtractor._is_likely_scaffolding(content):
                return content
            
        return None

    @staticmethod
    def _is_likely_scaffolding(content: str) -> bool:
        """
        Basic heuristic check: does it look like our YAML?
        """
        # We don't do full YAML parsing here to avoid heavy dependencies in a helper,
        # but we check for key required fields.
        # Check for 'version:' and 'technology_stack:' or 'service_slug:'
        if "version:" in content and ("technology_stack:" in content or "service_slug:" in content):
            return True
        return False
