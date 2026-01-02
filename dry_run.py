"""Dry-run the LangGraph workflow using in-memory stub nodes.

Run:
  /Users/benko/Developer/rse-agent/.venv/bin/python dry_run.py
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    # Ensure `src/` is importable when running from the repo root.
    repo_root = Path(__file__).resolve().parent
    src_dir = repo_root / "src"
    sys.path.insert(0, str(src_dir))

    from rse_agent.graph import app

    initial_state = {
        "task": "Stub demo: verify wiring end-to-end",
        "input_path": "(stub)",
        "source_filename": "demo_user_script.py",
        "source_code": "print('hello from user file')\n",
        "code": "",
        "test_code": "",
        "compliance_score": {},
        "stdout": "",
        "stderr": "",
        "error": "",
        "passed": False,
        "runner": "",
        "iteration": 0,
        "max_iterations": 3,
        "previous_attempts": [],
        "use_stubs": True,
    }

    final_state = app.invoke(initial_state)

    print("=== DRY RUN COMPLETE ===")
    print(f"passed: {final_state['passed']}")
    print(f"iteration: {final_state['iteration']}")
    print(f"stdout: {final_state.get('stdout','')}")
    print("\n--- code ---\n")
    print(final_state.get("code", ""))
    print("\n--- test_code ---\n")
    print(final_state.get("test_code", ""))


if __name__ == "__main__":
    main()
