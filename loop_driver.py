"""CLI loop driver for rse-agent.

Runs the LangGraph workflow, prints per-node progress, and writes artifacts:
- candidate.py (refactored code)
- test_candidate.py (generated tests)
- audit.md (peer-review style audit summary)

Usage:
  poetry run python loop_driver.py --task "Refactor for clarity" --in path/to/script.py

Notes:
- Uses E2B when `E2B_API_KEY` is set (picked up via .env), otherwise runs pytest locally.
- Output folder defaults to ./outputs/<timestamp>/
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


@dataclass(frozen=True)
class RunResult:
    out_dir: Path
    passed: bool


def _repo_root() -> Path:
    return Path(__file__).resolve().parent


def _ensure_src_on_path() -> None:
    repo_root = _repo_root()
    sys.path.insert(0, str(repo_root / "src"))


def _load_source(input_path: Path) -> tuple[str, str]:
    source_filename = input_path.name
    source_code = input_path.read_text(encoding="utf-8", errors="replace")
    return source_filename, source_code


def _format_audit_md(state: Dict[str, Any]) -> str:
    compliance = state.get("compliance_score") or {}
    checks = (compliance.get("checks") if isinstance(compliance, dict) else None) or {}

    def yesno(v: Any) -> str:
        return "PASS" if v else "FAIL"

    lines: list[str] = []
    lines.append("# RSE-Agent Peer Review Audit")
    lines.append("")
    lines.append("## Run Summary")
    lines.append(f"- Passed: `{state.get('passed')}`")
    lines.append(f"- Iterations: `{state.get('iteration')}` / `{state.get('max_iterations')}`")
    lines.append(f"- Runner: `{state.get('runner')}`")
    if state.get("error"):
        lines.append(f"- Error: `{state.get('error')}`")
    lines.append("")

    lines.append("## Validation Output")
    stdout = (state.get("stdout") or "").strip()
    stderr = (state.get("stderr") or "").strip()
    lines.append("### stdout")
    lines.append("```text")
    lines.append(stdout)
    lines.append("```")
    lines.append("### stderr")
    lines.append("```text")
    lines.append(stderr)
    lines.append("```")
    lines.append("")

    lines.append("## Carver Checklist (Deterministic)")
    score = compliance.get("score") if isinstance(compliance, dict) else None
    if score is not None:
        lines.append(f"- Score: `{score}`")
    blocking = compliance.get("blocking") if isinstance(compliance, dict) else None
    if blocking is not None:
        lines.append(f"- Blocking: `{blocking}`")
    lines.append("")

    if checks:
        for key, info in checks.items():
            passed = bool(info.get("pass")) if isinstance(info, dict) else False
            detail = (info.get("detail") if isinstance(info, dict) else "") or ""
            lines.append(f"- `{key}`: **{yesno(passed)}** — {detail}")
    else:
        lines.append("- (No checklist results available)")

    lines.append("")
    lines.append("## Artifacts")
    lines.append("- `candidate.py`: refactored code")
    lines.append("- `test_candidate.py`: generated tests")
    lines.append("")

    return "\n".join(lines)


def run(*, task: str, input_path: Path, max_iterations: int, out_dir: Path) -> RunResult:
    _ensure_src_on_path()

    from rse_agent.graph import app  # imported after sys.path update

    source_filename, source_code = _load_source(input_path)

    out_dir.mkdir(parents=True, exist_ok=True)

    initial_state: Dict[str, Any] = {
        "task": task,
        "input_path": str(input_path),
        "source_filename": source_filename,
        "source_code": source_code,
        "code": "",
        "test_code": "",
        "compliance_score": {},
        "stdout": "",
        "stderr": "",
        "error": "",
        "passed": False,
        "runner": "",
        "iteration": 0,
        "max_iterations": max_iterations,
        "previous_attempts": [],
        "use_stubs": False,
    }

    print(f"[rse-agent] task: {task}")
    print(f"[rse-agent] input: {input_path}")
    print(f"[rse-agent] max_iterations: {max_iterations}")
    print(f"[rse-agent] out_dir: {out_dir}")
    print("")

    latest_state: Dict[str, Any] = dict(initial_state)

    for event in app.stream(initial_state):
        if not isinstance(event, dict) or not event:
            continue
        node_name = next(iter(event.keys()))
        update = event[node_name]
        if isinstance(update, dict):
            latest_state.update(update)

        if node_name == "coder":
            print(f"- coder: iteration={latest_state.get('iteration')} error={latest_state.get('error')!r}")
        elif node_name == "tester":
            preview = (latest_state.get("test_code") or "").splitlines()[:1]
            print(f"- tester: generated tests ({len((latest_state.get('test_code') or '').splitlines())} lines) {preview}")
        elif node_name == "reviewer":
            comp = latest_state.get("compliance_score") or {}
            blocking = comp.get("blocking")
            score = comp.get("score")
            failures = comp.get("blocking_failures")
            suffix = f" failures={failures}" if failures else ""
            print(f"- reviewer: blocking={blocking} score={score}{suffix}")
        elif node_name == "executor":
            print(f"- executor: runner={latest_state.get('runner')} passed={latest_state.get('passed')}")
        else:
            print(f"- {node_name}: updated")

    # Write artifacts
    (out_dir / "candidate.py").write_text(latest_state.get("code", ""), encoding="utf-8")
    (out_dir / "test_candidate.py").write_text(latest_state.get("test_code", ""), encoding="utf-8")
    (out_dir / "audit.md").write_text(_format_audit_md(latest_state), encoding="utf-8")
    (out_dir / "final_state.json").write_text(json.dumps(latest_state, indent=2, ensure_ascii=False), encoding="utf-8")

    print("")
    print(f"[rse-agent] wrote: {out_dir / 'candidate.py'}")
    print(f"[rse-agent] wrote: {out_dir / 'test_candidate.py'}")
    print(f"[rse-agent] wrote: {out_dir / 'audit.md'}")
    print(f"[rse-agent] wrote: {out_dir / 'final_state.json'}")

    return RunResult(out_dir=out_dir, passed=bool(latest_state.get("passed")))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run rse-agent in a loop and write artifacts.")
    parser.add_argument("--task", required=True, help="Research goal / refactor intent")
    parser.add_argument("--in", dest="input_path", required=True, help="Path to a Python script")
    parser.add_argument("--max-iterations", type=int, default=3)
    parser.add_argument(
        "--out",
        dest="out_dir",
        default="",
        help="Output directory (default: ./outputs/<timestamp>)",
    )

    args = parser.parse_args()

    input_path = Path(args.input_path).expanduser().resolve()
    if not input_path.exists():
        raise SystemExit(f"input file does not exist: {input_path}")

    if args.out_dir:
        out_dir = Path(args.out_dir).expanduser().resolve()
    else:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_dir = (_repo_root() / "outputs" / stamp).resolve()

    result = run(
        task=args.task,
        input_path=input_path,
        max_iterations=args.max_iterations,
        out_dir=out_dir,
    )

    raise SystemExit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
