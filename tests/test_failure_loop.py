"""Test the loop behavior when tests fail (simulating real LLM scenario)."""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))


def test_loop_with_simulated_failure() -> None:
    """Simulate a scenario where executor fails to test the loop."""
    from rse_agent.graph import app
    from rse_agent.nodes import executor_node
    
    # Create a mock executor that fails on first attempt, passes on second
    call_count = {"count": 0}
    original_executor = executor_node
    
    def mock_executor(state):
        call_count["count"] += 1
        if call_count["count"] == 1:
            # First call: fail
            return {
                "stdout": "test failed",
                "stderr": "AssertionError",
                "error": "tests_failed",
                "passed": False,
                "runner": "mock",
            }
        else:
            # Subsequent calls: pass
            return original_executor(state)
    
    # Monkey patch executor
    import rse_agent.nodes
    rse_agent.nodes.executor_node = mock_executor
    
    try:
        initial_state = {
            "task": "test: simulated failure",
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
            "use_stubs": True,  # Use stubs for coder/tester/reviewer
        }
        
        latest_state = dict(initial_state)
        coder_calls = []
        executor_calls = []
        
        for event in app.stream(initial_state):
            if not isinstance(event, dict) or not event:
                continue
            node_name = next(iter(event.keys()))
            update = event[node_name]
            if isinstance(update, dict):
                latest_state.update(update)
            
            if node_name == "coder":
                coder_calls.append({
                    "iteration": latest_state.get("iteration", 0),
                    "code": latest_state.get("code", ""),
                    "error": latest_state.get("error", ""),
                    "previous_attempts_count": len(latest_state.get("previous_attempts", [])),
                })
            elif node_name == "executor":
                executor_calls.append({
                    "iteration": latest_state.get("iteration", 0),
                    "passed": latest_state.get("passed", False),
                    "error": latest_state.get("error", ""),
                })
        
        print("\n=== FAILURE LOOP TEST ===")
        print(f"Coder called {len(coder_calls)} times")
        print(f"Executor called {len(executor_calls)} times")
        print(f"Final passed: {latest_state.get('passed', False)}")
        print(f"Final iteration: {latest_state.get('iteration', 0)}")
        print(f"Final previous_attempts: {len(latest_state.get('previous_attempts', []))}")
        
        for i, call in enumerate(coder_calls):
            print(f"  Coder call {i+1}: iter={call['iteration']}, attempts={call['previous_attempts_count']}, "
                  f"error={call['error'][:30] if call['error'] else 'none'}")
        
        for i, call in enumerate(executor_calls):
            print(f"  Executor call {i+1}: iter={call['iteration']}, passed={call['passed']}, "
                  f"error={call['error'][:30] if call['error'] else 'none'}")
        
        # Verify loop behavior
        assert len(coder_calls) >= 2, "Expected at least 2 coder calls (initial + retry)"
        assert len(executor_calls) >= 2, "Expected at least 2 executor calls"
        
        # Verify iterations increment
        iterations = [c["iteration"] for c in coder_calls]
        assert iterations == sorted(set(iterations)), f"Iterations not in order: {iterations}"
        assert max(iterations) == len(coder_calls), f"Max iteration should match call count"
        
        # Verify previous_attempts grows
        attempt_counts = [c["previous_attempts_count"] for c in coder_calls]
        assert attempt_counts == list(range(1, len(attempt_counts) + 1)), \
            f"previous_attempts should increment: {attempt_counts}"
        
        # Verify error flows from executor to coder
        if len(executor_calls) > 0 and not executor_calls[0]["passed"]:
            # After first failure, next coder call should see the error
            if len(coder_calls) > 1:
                assert coder_calls[1]["error"] or latest_state.get("error"), \
                    "Error should flow from executor to next coder call"
        
        # Check for duplicate code
        codes = [c["code"] for c in coder_calls if c["code"]]
        if len(codes) > 1:
            unique_codes = list(set(codes))
            if len(unique_codes) < len(codes):
                print(f"⚠️  WARNING: Duplicate code detected! {len(codes)} total, {len(unique_codes)} unique")
            else:
                print("✓ All code versions are unique")
        
        print("=" * 50)
        
    finally:
        # Restore original
        rse_agent.nodes.executor_node = original_executor


if __name__ == "__main__":
    test_loop_with_simulated_failure()

