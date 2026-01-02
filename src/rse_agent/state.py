from typing import TypedDict, List

class AgentState(TypedDict):
    task: str
    input_path: str

    code: str
    test_code: str

    stdout: str
    stderr: str
    error: str

    iteration: int
    max_iterations: int
    previous_attempts: List[str]
    passed: bool