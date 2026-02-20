"""Pure function for stripping HTML tags and truncating Confluence page content."""

import re


def clean_html_and_truncate(html_content: str, max_chars: int = 20000) -> str:
    """Strip HTML tags, normalize whitespace, and truncate to save LLM context tokens."""
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()
    if len(text) > max_chars:
        return text[:max_chars] + "... [CONTENIDO TRUNCADO POR LIMITE DE CONTEXTO]"
    return text
