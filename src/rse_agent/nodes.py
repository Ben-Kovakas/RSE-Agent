from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from .checks import (
    check_license,
    check_no_hardcoded_paths,
    check_separation_of_concerns,
    check_version_control_hygiene,
    safe_bool,
)
from .state import ResearchState


def _call_openai_refactor(
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
- Use plain ASCII quotes in code (', ") and avoid “smart quotes”.
- Keep computation separate from I/O; move file reading/writing under functions or a main-guard.
"""

    response = client.responses.create(
        model="gpt-5-nano",
        input=prompt,
    )
    text = response.output_text or ""

    cleaned = _strip_markdown_fences(text)
    return cleaned or source_code


def _strip_markdown_fences(text: str) -> str:
    if "```" not in text:
        return text.strip()
    parts = text.split("```")
    if len(parts) >= 3:
        body = parts[1]
        if body.lstrip().startswith("python"):
            body = body.lstrip()[6:]
        return body.strip()
    return text.strip()


def _call_openai_generate_tests(*, task: str, source_filename: str, code: str) -> str:
    load_dotenv()

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to your .env or export it in your shell."
        )

    client = OpenAI()

    prompt = f"""You are a senior Research Software Engineer.

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

    response = client.responses.create(
        model="gpt-5-nano",
        input=prompt,
    )
    text = response.output_text or ""
    return _strip_markdown_fences(text) or "# failed to generate tests\n"


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
            previous_candidate=state.get("code", ""),
            last_error=state.get("error", ""),
            last_stdout=state.get("stdout", ""),
            last_stderr=state.get("stderr", ""),
            compliance_score=state.get("compliance_score", {}) or {},
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

    code = (state.get("code") or "").strip()
    if not code:
        return {"test_code": "# no code available to test\n"}

    try:
        test_code = _call_openai_generate_tests(
            task=state.get("task", ""),
            source_filename=state.get("source_filename", ""),
            code=code,
        )
        return {"test_code": test_code}
    except Exception as exc:
        return {"test_code": "# test generation failed\n", "error": str(exc)}


def reviewer_node(state: ResearchState) -> dict:
    """Compute a Carver-style compliance checklist before execution.

    This is intentionally deterministic and fast.
    """

    if state.get("use_stubs", True):
        return {
            "compliance_score": {
                "checks": {
                    "no_hardcoded_paths": {"pass": True, "detail": "stub"},
                    "version_control_hygiene": {"pass": True, "detail": "stub"},
                    "separation_of_concerns": {"pass": True, "detail": "stub"},
                    "license_check": {"pass": True, "detail": "stub"},
                },
                "score": 1.0,
                "blocking": False,
            }
        }

    code = (state.get("code") or "").strip()
    if not code:
        compliance = {
            "checks": {},
            "score": 0.0,
            "blocking": True,
            "summary": "no code to review",
        }
        return {"compliance_score": compliance, "error": "compliance:no_code"}

    repo_root = Path(__file__).resolve().parents[2]

    checks: dict[str, dict[str, object]] = {}

    ok, detail = check_no_hardcoded_paths(code)
    checks["no_hardcoded_paths"] = {"pass": ok, "detail": detail}

    ok, detail = check_version_control_hygiene(code)
    checks["version_control_hygiene"] = {"pass": ok, "detail": detail}

    ok, detail = check_separation_of_concerns(code)
    checks["separation_of_concerns"] = {"pass": ok, "detail": detail}

    ok, detail = check_license(repo_root)
    checks["license_check"] = {"pass": ok, "detail": detail}

    passed_count = sum(1 for v in checks.values() if safe_bool(v.get("pass")))
    score = passed_count / max(len(checks), 1)

    # Strict-but-practical: block execution only on issues the agent can reasonably
    # fix by changing the code artifact (not repository-level metadata).
    blocking_failures = [
        key
        for key, v in checks.items()
        if not safe_bool(v.get("pass")) and key in {"no_hardcoded_paths", "separation_of_concerns"}
    ]
    blocking = len(blocking_failures) > 0

    compliance = {
        "checks": checks,
        "score": score,
        "blocking": blocking,
        "blocking_failures": blocking_failures,
    }

    # If blocking, set a structured error string the coder can react to.
    if blocking:
        return {
            "compliance_score": compliance,
            "error": "compliance:blocking:" + json.dumps(blocking_failures),
        }

    return {"compliance_score": compliance}


def executor_node(state: ResearchState) -> dict:
    """Execute code + tests.

    Stub behavior: pretend execution succeeded and echo a predictable stdout.
    """
    if state.get("use_stubs", True):
        stdout = "[stub executor] ran code and tests successfully"
        return {"stdout": stdout, "stderr": "", "error": "", "passed": True, "runner": "stub"}

    # Allow configuration via .env (E2B_API_KEY, etc.)
    load_dotenv()

    compliance = state.get("compliance_score") or {}
    if isinstance(compliance, dict) and compliance.get("blocking") is True:
        return {
            "stdout": "[reviewer] blocking execution due to checklist failures",
            "stderr": "",
            "error": state.get("error", "compliance:blocking"),
            "passed": False,
            "runner": "none",
        }

    code = (state.get("code") or "").strip()
    test_code = (state.get("test_code") or "").strip()
    if not code or not test_code:
        return {
            "stdout": "",
            "stderr": "",
            "error": "missing_code_or_tests",
            "passed": False,
            "runner": "none",
        }

    # Prefer E2B when available, but fall back to local.
    use_e2b = bool(os.getenv("E2B_API_KEY"))
    if use_e2b:
        try:
            from e2b_code_interpreter import Sandbox

            sandbox = Sandbox.create(timeout=300)
            try:
                payload_json = json.dumps({"code": code, "tests": test_code}, ensure_ascii=False)
                payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")

                runner_snippet = (
                    "import base64, json, subprocess, sys\n"
                    f"payload = json.loads(base64.b64decode('{payload_b64}').decode('utf-8'))\n"
                    "open('candidate.py','w',encoding='utf-8').write(payload['code'])\n"
                    "open('test_candidate.py','w',encoding='utf-8').write(payload['tests'])\n"
                    "subprocess.run([sys.executable,'-m','pip','install','-q','pytest'], capture_output=True, text=True)\n"
                    "p = subprocess.run([sys.executable,'-m','pytest','-qq','--color=no'], capture_output=True, text=True)\n"
                    "sys.stdout.write(p.stdout or '')\n"
                    "sys.stderr.write(p.stderr or '')\n"
                    "print('\\n__RSE_AGENT_RESULT__' + json.dumps({'exit_code': int(p.returncode)}))\n"
                )

                stdout_lines: list[str] = []
                stderr_lines: list[str] = []

                def _on_stdout(msg):
                    line = getattr(msg, "line", None)
                    if line is not None:
                        stdout_lines.append(str(line))

                def _on_stderr(msg):
                    line = getattr(msg, "line", None)
                    if line is not None:
                        stderr_lines.append(str(line))

                execution = sandbox.run_code(
                    runner_snippet,
                    language="python",
                    on_stdout=_on_stdout,
                    on_stderr=_on_stderr,
                )

                stdout_text_all = "".join(stdout_lines)
                stderr_text_all = "".join(stderr_lines)
                err = getattr(execution, "error", None)
                if err:
                    return {
                        "stdout": stdout_text_all.strip(),
                        "stderr": stderr_text_all.strip(),
                        "error": str(err),
                        "passed": False,
                        "runner": "e2b",
                    }

                # Parse sentinel
                sentinel = "__RSE_AGENT_RESULT__"
                exit_code: int | None = None
                for line in reversed(stdout_text_all.splitlines()):
                    if sentinel in line:
                        try:
                            payload = line.split(sentinel, 1)[1].strip()
                            exit_code = int(json.loads(payload)["exit_code"])
                        except Exception:
                            exit_code = None
                        break

                if exit_code is None:
                    return {
                        "stdout": stdout_text_all.strip(),
                        "stderr": stderr_text_all.strip(),
                        "error": "e2b_parse_failure",
                        "passed": False,
                        "runner": "e2b",
                    }

                # Remove sentinel line from displayed stdout
                cleaned_stdout = "\n".join(
                    line for line in stdout_text_all.splitlines() if sentinel not in line
                ).strip()

                return {
                    "stdout": cleaned_stdout,
                    "stderr": stderr_text_all.strip(),
                    "error": "",
                    "passed": exit_code == 0,
                    "runner": "e2b",
                }
            finally:
                try:
                    sandbox.kill()
                except Exception:
                    pass
        except Exception as exc:
            # Fall back to local runner on any E2B error.
            fallback_error = f"e2b_failed:{exc}"
            state_error = state.get("error", "")
            combined = state_error or fallback_error
            # keep going with local below
            state = {**state, "error": combined}

    # Local runner: write files to a temp dir and run pytest.
    with tempfile.TemporaryDirectory(prefix="rse-agent-") as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "candidate.py").write_text(code, encoding="utf-8")
        (tmp_path / "test_candidate.py").write_text(test_code, encoding="utf-8")

        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-qq", "--color=no"],
            cwd=str(tmp_path),
            capture_output=True,
            text=True,
        )

        return {
            "stdout": (proc.stdout or "").strip(),
            "stderr": (proc.stderr or "").strip(),
            "error": "" if proc.returncode == 0 else (state.get("error", "") or "tests_failed"),
            "passed": proc.returncode == 0,
            "runner": "local",
        }
