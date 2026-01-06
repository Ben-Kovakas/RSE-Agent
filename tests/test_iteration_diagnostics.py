"""Diagnostic tests to identify issues with iteration tracking and state updates."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))


def test_diagnose_iteration_flow() -> None:
    """Diagnostic test to trace exactly what happens during iterations."""
    from rse_agent.graph import app

    initial_state = {
        "task": "test: diagnose flow",
        "input_path": "(test)",
        "source_filename": "test.py",
        "source_code": "def test(): pass\n",
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

    latest_state = dict(initial_state)
    event_log = []

    for event in app.stream(initial_state):
        if not isinstance(event, dict) or not event:
            continue
        node_name = next(iter(event.keys()))
        update = event[node_name]
        if isinstance(update, dict):
            latest_state.update(update)
        
        # Log important state changes
        if node_name in ("coder", "executor"):
            event_log.append({
                "node": node_name,
                "iteration": latest_state.get("iteration", 0),
                "code": latest_state.get("code", "")[:50] + "..." if len(latest_state.get("code", "")) > 50 else latest_state.get("code", ""),
                "code_hash": hash(latest_state.get("code", "")),
                "previous_attempts_count": len(latest_state.get("previous_attempts", [])),
                "passed": latest_state.get("passed", False),
                "error": latest_state.get("error", "")[:50] if latest_state.get("error") else "",
            })

    # Print diagnostic information
    print("\n=== ITERATION FLOW DIAGNOSTICS ===")
    print(f"Total events logged: {len(event_log)}")
    print(f"Final iteration: {latest_state.get('iteration', 0)}")
    print(f"Final previous_attempts count: {len(latest_state.get('previous_attempts', []))}")
    print(f"Final passed: {latest_state.get('passed', False)}")
    print("\nEvent sequence:")
    for i, event in enumerate(event_log):
        print(f"  {i+1}. {event['node']} (iter={event['iteration']}, attempts={event['previous_attempts_count']}, "
              f"code_hash={event['code_hash']}, passed={event['passed']})")
    
    # Check for issues
    coder_events = [e for e in event_log if e["node"] == "coder"]
    executor_events = [e for e in event_log if e["node"] == "executor"]
    
    print(f"\nCoder called {len(coder_events)} times")
    print(f"Executor called {len(executor_events)} times")
    
    # Check for duplicate code hashes in coder events
    code_hashes = [e["code_hash"] for e in coder_events]
    unique_hashes = set(code_hashes)
    if len(code_hashes) != len(unique_hashes):
        print(f"⚠️  WARNING: Duplicate code detected! {len(code_hashes)} total, {len(unique_hashes)} unique")
        for i, hash_val in enumerate(code_hashes):
            if code_hashes.count(hash_val) > 1:
                print(f"    Hash {hash_val} appears {code_hashes.count(hash_val)} times (iterations: {[j+1 for j, h in enumerate(code_hashes) if h == hash_val]})")
    else:
        print("✓ All code versions are unique")
    
    # Verify previous_attempts matches coder calls
    final_attempts = latest_state.get("previous_attempts", [])
    if len(final_attempts) != len(coder_events):
        print(f"⚠️  WARNING: previous_attempts count ({len(final_attempts)}) doesn't match coder calls ({len(coder_events)})")
    else:
        print(f"✓ previous_attempts count matches coder calls: {len(final_attempts)}")
    
    # Check iteration progression
    iterations = [e["iteration"] for e in coder_events]
    if iterations != sorted(set(iterations)):
        print(f"⚠️  WARNING: Iterations not in order: {iterations}")
    else:
        print(f"✓ Iterations are in order: {iterations}")
    
    print("=" * 50)


if __name__ == "__main__":
    test_diagnose_iteration_flow()

