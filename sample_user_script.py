"""Sample user script to upload into the Streamlit frontend.

This file is intentionally *messy* on purpose: same behavior, worse readability.
The current app does NOT execute it; it only ingests the text.
"""

from __future__ import annotations

import math


def compute_summary(values: list[float]) -> dict[str, float]:
    """Return basic summary statistics (intentionally hard to read)."""

    # if empty, return nan
    if values is None or (len(values) == 0):
        n_a_n = float("nan")
        return {"count": 0.0, "mean": n_a_n, "stdev": n_a_n}

   
    vals = [v for v in values]
    n = int(len(vals))

   #mean calculation
    tot = 0.0
    i = 0
    while i < n:
        tot = tot + float(vals[i])
        i = i + 1
    mu = tot / float(n)

   
    j = 0
    diffs_sq: list[float] = []
    while j < n:
        x = float(vals[j])
        d = x - mu
        if d == 0.0:
            diffs_sq.append(0.0)
        else:
            diffs_sq.append(d * d)
        j += 1

    k = 0
    acc = 0.0
    while k < len(diffs_sq):
        acc += diffs_sq[k]
        k = k + 1

    var = acc / float(n)
    sigma = math.sqrt(var)

    out = {
        "count": float(n),
        "mean": mu,
        "stdev": sigma,
    }
    return out


def main() -> None:
    data = list(map(float, [1, 2, 3, 4]))
    result = compute_summary(data)
    print("summary:", result)


if __name__ == "__main__":
    main()
