"""Sample user script for Streamlit frontend wire validation.

This module provides a small, well-tested numerical kernel (compute_summary)
separated from I/O. It uses explicit input validation, descriptive variable names,
and a defensive programming style to improve sustainability of scientific software.

Why: The upstream app wires this module into a workflow; keeping the computation
pure and testable makes it easier to validate correctness and reproduce results
across environments.
"""

from __future__ import annotations

import math
from typing import Dict, Sequence


# Demonstration dataset used by the kernel. Replace with real data in production.
DEFAULT_DATA: tuple[float, ...] = (1.0, 2.0, 3.0, 4.0)


def compute_summary(values: Sequence[float]) -> Dict[str, float]:
    """Compute population statistics for a sequence of finite numbers.

    This function is the core kernel that should be deterministic and side-effect free.

    Args:
        values: A sequence of finite numeric values.

    Returns:
        A dictionary with keys:
          - "count": number of elements (as float for compatibility)
          - "mean": arithmetic mean
          - "stdev": population standard deviation
    """
    # Defensive checks
    assert isinstance(values, Sequence), "values must be a sequence"
    if len(values) == 0:
        return {"count": 0.0, "mean": float("nan"), "stdev": float("nan")}

    for idx, val in enumerate(values):
        if not isinstance(val, (int, float)):
            raise TypeError(f"values[{idx}] is not numeric: {type(val).__name__}")
        fval = float(val)
        if not math.isfinite(fval):
            raise ValueError(f"values[{idx}] is not finite: {val!r}")

    count = float(len(values))
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)  # population variance
    stdev = math.sqrt(variance)

    return {"count": count, "mean": mean, "stdev": stdev}


def read_data() -> list[float]:
    """Return a simple dataset used for demonstration and testing.

    This function isolates input data creation from computation to ease testing
    and reusability across different frontends or tests.
    """
    return list(DEFAULT_DATA)


def format_summary(summary: Dict[str, float]) -> str:
    """Format the summary dict into a human-readable string.

    This is purely for printing/debugging; the core tests should use
    compute_summary directly.
    """
    return "count={:.1f}, mean={:.6f}, stdev={:.6f}".format(
        summary["count"], summary["mean"], summary["stdev"]
    )


def main() -> None:
    """Main entry point for local execution and demonstration.

    Reads data via read_data, computes the summary via compute_summary, and prints
    a human-friendly representation.
    """
    data = read_data()
    summary = compute_summary(data)
    print("summary:", summary)
    print("formatted:", format_summary(summary))


if __name__ == "__main__":
    main()