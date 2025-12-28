import re


def slugify_for_branch(text: str) -> str:
    """
    Creates a slug suitable for git branches from the provided text.
    - Lowercase
    - Alphanumeric and hyphens only
    - Replaces consecutive hyphens with single hyphen
    - Trims leading/trailing hyphens
    - Max length 40 chars
    """
    if not text:
        return ""

    # Lowercase
    slug = text.lower()
    
    # Replace non-alphanumeric with hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', slug)
    
    # Collapse multiple hyphens
    slug = re.sub(r'-+', '-', slug)
    
    # Trim hyphens
    slug = slug.strip('-')
    
    # Truncate to max len 40
    if len(slug) > 40:
        slug = slug[:40]
        # Avoid cutting in middle of word if it leaves trailing hyphen?
        # The prompt says "trim" logic generally applies to result, so let's re-trim just in case
        slug = slug.strip('-')
        
    return slug
