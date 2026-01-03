from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv

from .checks import (
    check_license,
    check_no_hardcoded_paths,
    check_separation_of_concerns,
    check_version_control_hygiene,
    safe_bool,
)
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
