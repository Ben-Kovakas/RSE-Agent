from __future__ import annotations

import sys
from pathlib import Path


def test_stub_graph_reaches_end() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root / "src"))

    from rse_agent.graph import app

    initial_state = {
        "task": "test: wiring",
        "input_path": "(stub)",
        "source_filename": "demo.py",
        "source_code": "print('x')\n",
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

    assert final_state["passed"] is True
    assert final_state["iteration"] >= 1
    assert "stub executor" in final_state.get("stdout", "")
