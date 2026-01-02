from __future__ import annotations

import os

from dotenv import load_dotenv
from openai import OpenAI

from .state import ResearchState


def _call_openai_refactor(*, task: str, source_filename: str, source_code: str) -> str:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env or export it in your shell."
        )

    client = OpenAI()

    # Placeholder instructions: keep this short/strict so you can iterate later.
    prompt = f"""You are a senior Research Software Engineer.

Goal:
{task}

Input Python file name:
{source_filename or '(unknown)'}

Task:
- Refactor/clean up the Python code.
- Preserve behavior.
- Improve readability (functions, names, docstrings where helpful).
- Return ONLY the refactored Python code.

Python code to refactor:
```python
{source_code}
```
"""

    response = client.responses.create(
        model="gpt-5-nano",
        input=prompt,
    )
    text = response.output_text or ""

    # Defensive cleanup: if the model wraps in fences, strip them.
    if "```" in text:
        parts = text.split("```")
        if len(parts) >= 3:
            text = parts[1]
            if text.lstrip().startswith("python"):
                text = text.lstrip()[6:]
            text = text.strip()

    return text.strip() or source_code


def coder_node(state: ResearchState) -> dict:
    """Produce analysis code.

    Stub behavior (default): generate deterministic placeholder code.
    """
    if state.get("use_stubs", True):
        original_hint = ""
        if state.get("source_code", "").strip():
            original_hint = (
                "\n\n# --- user file (stub pass-through) ---\n"
                f"# filename: {state.get('source_filename', '(unknown)')}\n"
                "# (Not executing or importing user code yet.)\n"
                + "\n".join(f"# {line}" for line in state["source_code"].splitlines()[:30])
                + ("\n# ..." if len(state["source_code"].splitlines()) > 30 else "")
            )

        code = (
            "def analyze(data=None):\n"
            "    \"\"\"Stub analysis function for wiring validation.\"\"\"\n"
            "    return {'message': 'Hello, RSE Agent!', 'rows': 0 if data is None else len(data)}\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    print(analyze())\n"
        ) + original_hint
        return {
            "code": code,
            "iteration": state["iteration"] + 1,
            "error": "",
            "previous_attempts": state.get("previous_attempts", []) + [code],
        }

    # Real LLM path: send uploaded code to OpenAI for cleanup.
    if not state.get("source_code", "").strip():
        return {
            "code": "# No source_code provided. Upload a .py file to refactor.",
            "iteration": state["iteration"] + 1,
            "error": "missing_source_code",
            "previous_attempts": state.get("previous_attempts", []),
        }

    try:
        cleaned = _call_openai_refactor(
            task=state["task"],
            source_filename=state.get("source_filename", ""),
            source_code=state["source_code"],
        )
        return {
            "code": cleaned,
            "iteration": state["iteration"] + 1,
            "error": "",
            "previous_attempts": state.get("previous_attempts", []) + [cleaned],
        }
    except Exception as exc:
        return {
            "code": state.get("code", ""),
            "iteration": state["iteration"] + 1,
            "error": str(exc),
            "previous_attempts": state.get("previous_attempts", []),
        }


def tester_node(state: ResearchState) -> dict:
    """Produce test code for the analysis code.

    Stub behavior: produce a tiny always-pass pytest module.
    """
    if state.get("use_stubs", True):
        test_code = (
            "def test_stub_passes():\n"
            "    assert True\n"
        )
        return {"test_code": test_code}

    # Placeholder for real test generation. Keep the workflow running for now.
    return {"test_code": "# TODO: generate pytest tests with an LLM\n"}


def executor_node(state: ResearchState) -> dict:
    """Execute code + tests.

    Stub behavior: pretend execution succeeded and echo a predictable stdout.
    """
    if state.get("use_stubs", True):
        stdout = "[stub executor] ran code and tests successfully"
        return {"stdout": stdout, "stderr": "", "error": "", "passed": True}

    # Placeholder for real sandbox execution. Keep the workflow running for now.
    stdout = "[stub executor] (LLM mode) skipping execution for now"
    passed = state.get("error", "") == ""
    return {"stdout": stdout, "stderr": "", "error": state.get("error", ""), "passed": passed}
