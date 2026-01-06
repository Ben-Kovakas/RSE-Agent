"""Code execution module for running tests in sandboxed or local environments.

This module provides functions for executing Python code and tests using
either E2B sandbox (when available) or local pytest execution.
"""

from .runners import execute_code, run_e2b_execution, run_local_execution

__all__ = [
    "execute_code",
    "run_e2b_execution",
    "run_local_execution",
]

