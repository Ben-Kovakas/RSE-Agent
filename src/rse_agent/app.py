from __future__ import annotations

import sys
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

if st.button("Generate & Validate"):
    if user_query:
        source_filename = ""
        source_code = ""
        if uploaded_py is not None:
            source_filename = uploaded_py.name
            source_code = uploaded_py.getvalue().decode("utf-8", errors="replace")

        # Prepare the initial state (in-memory stub demo)
        initial_input = {
            "task": user_query,
            "input_path": "(stub)",
            "source_filename": source_filename,
            "source_code": source_code,
            "code": "",
            "test_code": "",
            "stdout": "",
            "stderr": "",
            "error": "",
            "passed": False,
            "iteration": 0,
            "max_iterations": 3,
            "previous_attempts": [],
            "use_stubs": False,
        }
        
        # Run the Graph
        with st.status("Agent working..."):
            final_state = app.invoke(initial_input)
        
        # Display Results
        if source_code.strip():
            st.subheader("Original Script")
            if source_filename:
                st.caption(source_filename)
            st.code(source_code, language="python")

        st.subheader("Refactored Output")
        st.code(final_state.get("code", ""), language="python")

        error_msg = final_state.get("error", "")
        if error_msg:
            st.error(f"LLM/processing error: {error_msg}")

        st.subheader("Validation / Runner Output")
        st.code(final_state.get("test_code", ""), language="python")
        st.text(final_state.get("stdout", ""))

        st.success("Analysis Validated!" if final_state.get("passed") else "Validation Failed.")