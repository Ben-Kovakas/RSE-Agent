from typing import Any, Dict, List, TypedDict


class ResearchState(TypedDict):
    """Shared state passed between LangGraph nodes.

    This is the canonical state contract used by the graph router, nodes,
    and (for now) the Streamlit demo.
    """

    # User intent / inputs
    task: str
    input_path: str  # placeholder for now; keep until file I/O is added
    source_filename: str
    source_code: str

    # Artifacts produced by the agent
    code: str
    test_code: str

    # Carver checklist / compliance
    compliance_score: Dict[str, Any]

    # Execution results
    stdout: str
    stderr: str
    error: str
    passed: bool

    # Runner metadata
    runner: str  # e.g. "e2b" or "local"

    # Control + audit
    iteration: int
    max_iterations: int
    previous_attempts: List[str]

    # Demo mode: when True, nodes do not call external services
    use_stubs: bool