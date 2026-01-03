"""Prompt templates for LLM interactions.

These functions build prompts for code refactoring and test generation
based on research software engineering best practices.
"""

from __future__ import annotations

import json


def build_refactor_prompt(
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
    """Build a prompt for code refactoring.
    
    This prompt instructs the LLM to refactor code according to research
    software engineering best practices (Dr. Jeffrey Carver's guidelines).
    
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
        The formatted prompt string
    """
    return f"""You are a senior Research Software Engineer.

Goal:
{task}

Input Python file name:
{source_filename or '(unknown)'}

You are a Research Software Engineer (RSE) acting as an automated peer reviewer. 
Your goal is not just "clean code," but "sustainable scientific software" based on Dr. Jeffrey Carver's guidelines.

CRITICAL INSTRUCTIONS:
1. READABILITY OVER CLEVERNESS: 
   - Research code is read more than it is written. Refactor complex list comprehensions into explicit loops if it aids clarity.
   - Rename single-letter variables (e.g., 'T', 'p') to descriptive physical quantities (e.g., 'temperature_kelvin', 'pressure_pascal') unless they are standard mathematical notation in the domain.

2. DOCUMENTATION (The "Why"):
   - Do not just document *what* the code does. Document *why* it does it. 
   - If a constant is used (e.g., 9.81), extract it to a named constant and cite the source or physical reason.

3. MODULARITY:
   - Break long simulation loops into testable "kernels" or "update_steps".
   - Isolate Input/Output code from Computation code (crucial for testing reproducibility).

4. DEFENSIVE CODING:
   - Add assertions for physical constraints (e.g., `assert mass > 0`).
   - Explicitly handle floating-point comparison (use `math.isclose` or `numpy.allclose` instead of `==`).

Python code to refactor:
```python
{source_code}
```

If provided, you MUST treat the following as the current candidate implementation and apply targeted edits
to address failures (tests, checklist blocking issues, runtime errors). Avoid redoing everything from scratch.

Current candidate implementation (if empty, ignore):
```python
{previous_candidate}
```

Failure signals from last iteration (fix these):
- error: {last_error}
- stdout (pytest/runner output):
```text
{last_stdout}
```
- stderr:
```text
{last_stderr}
```
- compliance_score (Carver checklist):
```json
{json.dumps(compliance_score, ensure_ascii=False)}
```

Hard requirements:
- Output ONLY valid Python source code (no markdown).
- Use plain ASCII quotes in code (', ") and avoid "smart quotes".
- Keep computation separate from I/O; move file reading/writing under functions or a main-guard.
"""


def build_test_prompt(*, task: str, source_filename: str, code: str) -> str:
    """Build a prompt for test generation.
    
    This prompt instructs the LLM to generate scientific validation tests
    using metamorphic relations, pseudo-oracles, and smoke tests.
    
    Args:
        task: The research goal or task description
        source_filename: Name of the source file (for context)
        code: The code to generate tests for
        
    Returns:
        The formatted prompt string
    """
    return f"""You are a senior Research Software Engineer.

Goal:
{task}

You are writing SCIENTIFIC VALIDATION tests for research code.

CRITICAL REQUIREMENTS:
- Output ONLY a single Python pytest module. No markdown, no explanations.
- Import the code-under-test from a module named `candidate`.
- Avoid asserting exact numeric results unless they are guaranteed invariants.
- Prefer tests that validate *relationships* and *invariants*.

You MUST include these three categories when applicable:

A) Metamorphic Relations
- Since we don't know if a single output is "correct", test input-output relationships.
- Example pattern: scaling, monotonicity, symmetry, invariance under equivalent transformations.

B) Pseudo-Oracles / Conservation Laws
- Identify physical invariants (mass/energy/momentum/probability normalization, etc.)
- Use floating point tolerant comparisons (math.isclose / numpy.allclose).

C) Smoke Tests for Non-Determinism
- If the code appears stochastic, write a statistical smoke test:
  run >= 100 trials and assert the mean is within ~3 standard deviations.
- If it appears deterministic, write a robustness smoke test instead (e.g., repeated runs equal).

Additional guardrails:
- Tests must be self-contained and not require network access.
- Do not read external files; generate minimal synthetic inputs.
- If the module exposes no clear public function(s), at least test that it imports and that key functions/classes exist.

Candidate file name (context only): {source_filename or '(unknown)'}

Python code under test (module `candidate.py`):
```python
{code}
```
"""

