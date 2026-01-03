"""OpenAI API client for code refactoring and test generation."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from .prompts import build_refactor_prompt, build_test_prompt
from .utils import strip_markdown_fences


def call_openai_refactor(
    *,
    task: str,
    source_filename: str,
    source_code: str,
    previous_candidate: str,
    last_error: str,
    last_stdout: str,
    last_stderr: str,
    compliance_score: dict,
) -> str:
    """Call OpenAI API to refactor code.
    
    This function sends code to OpenAI for refactoring according to research
    software engineering best practices.
    
    Args:
        task: The research goal or refactoring intent
        source_filename: Name of the source file being refactored
        source_code: The original source code to refactor
        previous_candidate: Previous attempt at refactoring (if any)
        last_error: Error message from last iteration (if any)
        last_stdout: Standard output from last execution (if any)
        last_stderr: Standard error from last execution (if any)
        compliance_score: Compliance checklist results
        
    Returns:
        The refactored code (with markdown fences removed)
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
    """
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env or export it in your shell."
        )

    client = OpenAI()

    prompt = build_refactor_prompt(
        task=task,
        source_filename=source_filename,
        source_code=source_code,
        previous_candidate=previous_candidate,
        last_error=last_error,
        last_stdout=last_stdout,
        last_stderr=last_stderr,
        compliance_score=compliance_score,
    )

    response = client.responses.create(
        model="gpt-5-nano",
        input=prompt,
    )
    text = response.output_text or ""

    cleaned = strip_markdown_fences(text)
    return cleaned or source_code


def call_openai_generate_tests(*, task: str, source_filename: str, code: str) -> str:
    """Call OpenAI API to generate test code.
    
    This function sends code to OpenAI to generate scientific validation tests
    using metamorphic relations, pseudo-oracles, and smoke tests.
    
    Args:
        task: The research goal or task description
        source_filename: Name of the source file (for context)
        code: The code to generate tests for
        
    Returns:
        The generated test code (with markdown fences removed)
        
    Raises:
        RuntimeError: If OPENAI_API_KEY is not set
    """
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env or export it in your shell."
        )

    client = OpenAI()

    prompt = build_test_prompt(
        task=task,
        source_filename=source_filename,
        code=code,
    )

    response = client.responses.create(
        model="gpt-5-nano",
        input=prompt,
    )
    text = response.output_text or ""
    return strip_markdown_fences(text) or "# failed to generate tests\n"

