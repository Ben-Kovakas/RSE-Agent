"""Utility functions for LLM interactions."""


def strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from LLM response text.
    
    LLM responses often include markdown code fences (```python ... ```).
    This function extracts just the code content.
    
    Args:
        text: Text that may contain markdown code fences
        
    Returns:
        The text with markdown fences removed, or the original text if no fences found
    """
    if "```" not in text:
        return text.strip()
    parts = text.split("```")
    if len(parts) >= 3:
        body = parts[1]
        if body.lstrip().startswith("python"):
            body = body.lstrip()[6:]
        return body.strip()
    return text.strip()

