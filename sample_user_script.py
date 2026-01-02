"""Sample user script to upload into the Streamlit frontend.

This file is intentionally simple. The current app does NOT execute it; it only
ingests the text and passes it through the workflow for wiring validation.
"""

from __future__ import annotations

import math


def compute_summary(values: list[float]) -> dict[str, float]:
    """Return basic summary statistics."""
    if not values:
        return {"count": 0.0, "mean": float("nan"), "stdev": float("nan")}

    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / len(values)
    return {"count": float(len(values)), "mean": mean, "stdev": math.sqrt(var)}


def main() -> None:
    data = [1.0, 2.0, 3.0, 4.0]
    summary = compute_summary(data)
    print("summary:", summary)


if __name__ == "__main__":
    main()
