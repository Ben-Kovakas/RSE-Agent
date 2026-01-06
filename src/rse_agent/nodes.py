from __future__ import annotations

import json
from pathlib import Path

from .checks import (
    check_license,
    check_no_hardcoded_paths,
    check_separation_of_concerns,
    check_version_control_hygiene,
    safe_bool,
)
from .execution import execute_code
from .llm import call_openai_generate_tests, call_openai_refactor
from .state import ResearchState




def coder_node(state: ResearchState) -> dict:
    """Produce analysis code.

    Stub behavior (default): generate deterministic placeholder code.
    """
    if state.get("use_stubs", True):
        code = (
            "def analyze(data=None):\n"
            "    \"\"\"Stub analysis function for wiring validation.\"\"\"\n"
            "    return {'message': 'Hello, RSE Agent!', 'rows': 0 if data is None else len(data)}\n"
            "\n"
            "if __name__ == '__main__':\n"
            "    print(analyze())\n"
        )
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
        cleaned = call_openai_refactor(
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
        test_code = call_openai_generate_tests(
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

    # Use the execution module to run code and tests
    previous_error = state.get("error", "")
    return execute_code(code=code, test_code=test_code, previous_error=previous_error)
