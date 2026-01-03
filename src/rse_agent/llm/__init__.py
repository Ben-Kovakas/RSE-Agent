"""LLM integration for code refactoring and test generation.

This module provides functions for interacting with OpenAI's API to refactor
code and generate tests based on research software engineering best practices.
"""

from .client import call_openai_generate_tests, call_openai_refactor
from .utils import strip_markdown_fences

__all__ = [
    "call_openai_generate_tests",
    "call_openai_refactor",
    "strip_markdown_fences",
]

