from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import streamlit as st

# Streamlit runs this file as a script, so relative imports (from .graph ...) fail.
# Add the repo's `src/` directory to sys.path so `import rse_agent` works.
repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(repo_root / "src"))

from rse_agent.graph import app  # noqa: E402

st.title("🔬 RSE-Agent: Validated Analysis")

# 1. Sidebar for Setup
with st.sidebar:
    st.header("Research Configuration")
    uploaded_py = st.file_uploader("Upload a Python script", type=["py"])

# 2. Main Interface
user_query = st.text_area("What is your research goal for this data?")

# Initialize session state for results persistence
if "results" not in st.session_state:
    st.session_state.results = None
if "source_code" not in st.session_state:
    st.session_state.source_code = ""
if "source_filename" not in st.session_state:
    st.session_state.source_filename = ""

# Store uploaded file info in session state
if uploaded_py is not None:
    st.session_state.source_filename = uploaded_py.name
    st.session_state.source_code = uploaded_py.getvalue().decode("utf-8", errors="replace")

if st.button("Generate & Validate"):
    if user_query:
        # Use session state for source code
        source_filename = st.session_state.source_filename
        source_code = st.session_state.source_code

        # Prepare the initial state
        initial_input = {
            "task": user_query,
            "input_path": "(streamlit)",
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
            "max_iterations": 3,
            "previous_attempts": [],
            "use_stubs": True,
        }
        
        # Run the Graph with streaming to capture intermediate states
        latest_state = dict(initial_input)
        iteration_history = []  # Track each coder call for debugging
        executor_results = []  # Track executor results for each iteration
        
        with st.status("Agent working...") as status:
            for event in app.stream(initial_input):
                if not isinstance(event, dict) or not event:
                    continue
                node_name = next(iter(event.keys()))
                update = event[node_name]
                if isinstance(update, dict):
                    latest_state.update(update)
                
                # Track coder node calls to verify iterations
                if node_name == "coder":
                    iteration_history.append({
                        "iteration": latest_state.get("iteration", 0),
                        "code": latest_state.get("code", ""),
                        "code_hash": hash(latest_state.get("code", "")),
                        "previous_attempts_count": len(latest_state.get("previous_attempts", [])),
                        "error": latest_state.get("error", ""),
                    })
                
                # Track executor results for each iteration
                if node_name == "executor":
                    executor_results.append({
                        "iteration": latest_state.get("iteration", 0),
                        "passed": latest_state.get("passed", False),
                        "stdout": latest_state.get("stdout", ""),
                        "stderr": latest_state.get("stderr", ""),
                        "error": latest_state.get("error", ""),
                        "runner": latest_state.get("runner", ""),
                    })
                
                # Update status message
                iteration = latest_state.get("iteration", 0)
                status.update(label=f"Running iteration {iteration}... ({node_name} node)")
        
        final_state = latest_state
        
        # Store results in session state for persistence across reruns
        st.session_state.results = {
            "final_state": final_state,
            "iteration_history": iteration_history,
            "executor_results": executor_results,
            "source_code": source_code,
            "source_filename": source_filename,
        }
        
        # Trigger rerun to display results from session state
        st.rerun()

# Display results from session state (persists across reruns)
if st.session_state.results is not None:
    results = st.session_state.results
    final_state = results["final_state"]
    iteration_history = results["iteration_history"]
    executor_results = results["executor_results"]
    source_code = results["source_code"]
    source_filename = results["source_filename"]
    
    # Debug information (can be hidden with expander)
    with st.expander("🔍 Debug: Iteration Tracking", expanded=False):
        st.write(f"**Coder calls:** {len(iteration_history)}")
        st.write(f"**Executor calls:** {len(executor_results)}")
        st.write(f"**Final previous_attempts count:** {len(final_state.get('previous_attempts', []))}")
        
        # Explain iteration count
        if len(iteration_history) == 1:
            st.info("ℹ️ **Why only 1 iteration?** The tests passed on the first attempt, so the loop stopped. "
                   "If tests fail, the agent will retry up to `max_iterations` times.")
        
        for i, hist in enumerate(iteration_history):
            st.write(f"**Coder call {i+1}:**")
            st.write(f"- Iteration: {hist['iteration']}")
            st.write(f"- Code hash: {hist['code_hash']}")
            st.write(f"- Previous attempts: {hist['previous_attempts_count']}")
            st.write(f"- Error: {hist['error'][:100] if hist['error'] else 'none'}")
        
        # Show executor results
        if executor_results:
            st.write("**Executor Results:**")
            for i, result in enumerate(executor_results):
                st.write(f"**Iteration {result['iteration']}:**")
                st.write(f"- Passed: {result['passed']}")
                st.write(f"- Runner: {result['runner']}")
                if result['error']:
                    st.write(f"- Error: {result['error'][:100]}")
        
        # Check for duplicates
        if len(iteration_history) > 1:
            code_hashes = [h["code_hash"] for h in iteration_history]
            unique_hashes = set(code_hashes)
            if len(code_hashes) != len(unique_hashes):
                st.warning(f"⚠️ Duplicate code detected! {len(code_hashes)} calls, {len(unique_hashes)} unique code versions")
                duplicates = [h for h in iteration_history if code_hashes.count(h["code_hash"]) > 1]
                st.write("**Duplicate iterations:**")
                for dup in duplicates:
                    st.write(f"- Iteration {dup['iteration']} (hash: {dup['code_hash']})")
            else:
                st.success("✓ All code versions are unique")
    
    # Display Results
    if source_code.strip():
        with st.expander("Original Script", expanded=False):
            if source_filename:
                st.caption(source_filename)
            st.code(source_code, language="python")
    
    # Display Code Iterations with test results
    previous_attempts = final_state.get("previous_attempts", [])
    if previous_attempts:
        with st.expander("Code Iterations", expanded=False):
            if len(previous_attempts) == 1:
                st.info(
                    "ℹ️ Only 1 iteration: Tests passed on first attempt. The agent will retry if tests fail."
                )

            # Create tabs for each iteration with test results
            if len(previous_attempts) > 1:
                tabs = st.tabs(
                    [
                        f"{i+1}{'st' if i == 0 else 'nd' if i == 1 else 'rd' if i == 2 else 'th'} iteration"
                        for i in range(len(previous_attempts))
                    ]
                )
                for idx, (tab, code_version) in enumerate(zip(tabs, previous_attempts)):
                    with tab:
                        st.code(code_version, language="python")
                        # Show executor result for this iteration if available
                        iter_num = idx + 1
                        result = next(
                            (r for r in executor_results if r["iteration"] == iter_num),
                            None,
                        )
                        if result:
                            if result["passed"]:
                                st.success(f"✓ Tests passed (Runner: {result['runner']})")
                            else:
                                st.error(f"✗ Tests failed (Runner: {result['runner']})")
                                if result["error"]:
                                    st.caption(f"Error: {result['error']}")
            else:
                # Single iteration - show code and test result
                st.code(previous_attempts[0], language="python")
                if executor_results:
                    result = executor_results[0]
                    if result["passed"]:
                        st.success(f"✓ Tests passed on first attempt (Runner: {result['runner']})")
                    else:
                        st.error(f"✗ Tests failed (Runner: {result['runner']})")
    
    # Show final refactored output (same as last iteration)
    st.subheader("Final Refactored Output")
    refactored_code = final_state.get("code", "")
    st.code(refactored_code, language="python")
    
    # Download button for refactored code
    if refactored_code.strip():
        # Determine filename - use original filename with _refactored suffix, or default
        if source_filename:
            download_filename = source_filename.replace(".py", "_refactored.py")
        else:
            download_filename = "refactored_code.py"
        
        st.download_button(
            label="Download Refactored Code",
            data=refactored_code,
            file_name=download_filename,
            mime="text/x-python",
        )

    error_msg = final_state.get("error", "")
    if error_msg:
        st.error(f"LLM/processing error: {error_msg}")

    # Test Code (in expander)
    test_code = final_state.get("test_code", "")
    if test_code:
        with st.expander("📝 Generated Test Code", expanded=False):
            st.code(test_code, language="python")
            st.download_button(
                label="Download Test Code",
                data=test_code,
                file_name="test_candidate.py",
                mime="text/x-python",
                key="download_test",
            )

    # Test Execution Results
    st.subheader("🧪 Test Execution Results")
    
    # Get final executor result
    final_result = executor_results[-1] if executor_results else {
        "passed": final_state.get("passed", False),
        "stdout": final_state.get("stdout", ""),
        "stderr": final_state.get("stderr", ""),
        "error": final_state.get("error", ""),
        "runner": final_state.get("runner", ""),
    }
    
    # Show test status
    if final_result["passed"]:
        st.success(f"✅ All tests passed! (Runner: {final_result['runner']})")
    else:
        st.error(f"❌ Tests failed (Runner: {final_result['runner']})")
        if final_result["error"]:
            st.error(f"Error: {final_result['error']}")
    
    # Show stdout (test output)
    if final_result["stdout"]:
        st.write("**Test Output (stdout):**")
        st.code(final_result["stdout"], language="text")
    else:
        st.info("No stdout output from tests")
    
    # Show stderr (test errors)
    if final_result["stderr"]:
        st.write("**Test Errors (stderr):**")
        st.code(final_result["stderr"], language="text")
    
    # Comparison: Original vs Refined Results
    if source_code.strip() and refactored_code.strip():
        st.subheader("📊 Comparison: Original vs Refined")
        
        # Run original script to get its output
        original_output = ""
        original_error = ""
        try:
            with tempfile.TemporaryDirectory(prefix="rse-agent-orig-") as tmp:
                tmp_path = Path(tmp)
                (tmp_path / "original.py").write_text(source_code, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, str(tmp_path / "original.py")],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                original_output = proc.stdout.strip()
                original_error = proc.stderr.strip()
        except subprocess.TimeoutExpired:
            original_error = "Execution timed out"
        except Exception as e:
            original_error = f"Error running original: {str(e)}"
        
        # Run refined script to get its output
        refined_output = ""
        refined_error = ""
        try:
            with tempfile.TemporaryDirectory(prefix="rse-agent-refined-") as tmp:
                tmp_path = Path(tmp)
                (tmp_path / "refined.py").write_text(refactored_code, encoding="utf-8")
                proc = subprocess.run(
                    [sys.executable, str(tmp_path / "refined.py")],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                refined_output = proc.stdout.strip()
                refined_error = proc.stderr.strip()
        except subprocess.TimeoutExpired:
            refined_error = "Execution timed out"
        except Exception as e:
            refined_error = f"Error running refined: {str(e)}"
        
        # Display comparison
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("**Original Script Output:**")
            if original_output:
                st.code(original_output, language="text")
            else:
                st.info("No output")
            if original_error:
                st.warning(f"Errors: {original_error[:200]}")
        
        with col2:
            st.write("**Refined Script Output:**")
            if refined_output:
                st.code(refined_output, language="text")
            else:
                st.info("No output")
            if refined_error:
                st.warning(f"Errors: {refined_error[:200]}")
        
        # Compare outputs
        if original_output and refined_output:
            if original_output == refined_output:
                st.success("✓ Outputs match - behavior preserved!")
            else:
                st.warning("⚠️ Outputs differ - check if this is expected")
                st.write("**Differences:**")
                st.code(f"Original: {original_output[:100]}...\nRefined:  {refined_output[:100]}...", language="text")
        elif original_output or refined_output:
            st.info("One script produced output, the other didn't")
    
    # Final status
    if final_state.get("passed"):
        st.success("🎉 Analysis Validated! All tests passed.")
    else:
        st.error("❌ Validation Failed. Check test results above.")
    
    # Add a button to clear results
    if st.button("🔄 Clear Results and Start Over"):
        st.session_state.results = None
        st.session_state.source_code = ""
        st.session_state.source_filename = ""
        st.rerun()