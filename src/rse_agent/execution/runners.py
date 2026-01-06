"""Code execution runners for E2B sandbox and local environments."""

from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from dotenv import load_dotenv


def run_e2b_execution(*, code: str, test_code: str) -> dict[str, str | bool]:
    """Execute code and tests in an E2B sandbox.
    
    This function creates an E2B sandbox, writes the code and tests,
    runs pytest, and returns the results.
    
    Args:
        code: The Python code to execute
        test_code: The test code to run
        
    Returns:
        Dictionary with keys: stdout, stderr, error, passed, runner
        
    Raises:
        RuntimeError: If E2B_API_KEY is not set or E2B import fails
    """
    try:
        from e2b_code_interpreter import Sandbox
    except ImportError as exc:
        raise RuntimeError(f"E2B not available: {exc}") from exc

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

        # Parse sentinel to extract exit code
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


def run_local_execution(*, code: str, test_code: str, previous_error: str = "") -> dict[str, str | bool]:
    """Execute code and tests locally using pytest.
    
    This function writes the code and tests to a temporary directory,
    runs pytest, and returns the results.
    
    Args:
        code: The Python code to execute
        test_code: The test code to run
        previous_error: Any previous error message to preserve
        
    Returns:
        Dictionary with keys: stdout, stderr, error, passed, runner
    """
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
            "error": "" if proc.returncode == 0 else (previous_error or "tests_failed"),
            "passed": proc.returncode == 0,
            "runner": "local",
        }


def execute_code(*, code: str, test_code: str, previous_error: str = "") -> dict[str, str | bool]:
    """Execute code and tests, preferring E2B sandbox when available.
    
    This is the main entry point for code execution. It will:
    1. Try E2B sandbox if E2B_API_KEY is set
    2. Fall back to local execution if E2B fails or is unavailable
    
    Args:
        code: The Python code to execute
        test_code: The test code to run
        previous_error: Any previous error message to preserve
        
    Returns:
        Dictionary with keys: stdout, stderr, error, passed, runner
    """
    load_dotenv()

    # Prefer E2B when available, but fall back to local.
    use_e2b = bool(os.getenv("E2B_API_KEY"))
    if use_e2b:
        try:
            return run_e2b_execution(code=code, test_code=test_code)
        except Exception as exc:
            # Fall back to local runner on any E2B error.
            fallback_error = f"e2b_failed:{exc}"
            combined_error = previous_error or fallback_error
            # Continue with local execution below
            return run_local_execution(code=code, test_code=test_code, previous_error=combined_error)

    # Local runner: write files to a temp dir and run pytest.
    return run_local_execution(code=code, test_code=test_code, previous_error=previous_error)

