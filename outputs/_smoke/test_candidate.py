import math
import statistics

import pytest

from candidate import compute_statistics, read_sample_data, format_summary_text


def test_empty_input_returns_nan():
    summary = compute_statistics([])
    assert summary["count"] == 0.0
    assert math.isnan(summary["mean"])
    assert math.isnan(summary["stdev"])


def test_permutation_invariance():
    a = [1.0, 2.0, 3.0, 4.0]
    b = [4.0, 2.0, 3.0, 1.0]
    s1 = compute_statistics(a)
    s2 = compute_statistics(b)
    assert s1["count"] == s2["count"]
    assert math.isclose(s1["mean"], s2["mean"], rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(s1["stdev"], s2["stdev"], rel_tol=1e-12, abs_tol=1e-12)


def test_scaling_metamorphic_relation():
    base = [1.0, 2.0, 3.0, 4.0]
    s_base = compute_statistics(base)
    for k in [0.5, 2.0, -3.0, 1.0]:
        scaled = [k * x for x in base]
        s_scaled = compute_statistics(scaled)
        assert s_scaled["count"] == s_base["count"]
        assert math.isclose(s_scaled["mean"], k * s_base["mean"], rel_tol=1e-12, abs_tol=1e-12)
        assert math.isclose(s_scaled["stdev"], abs(k) * s_base["stdev"], rel_tol=1e-12, abs_tol=1e-12)


def test_constant_input_invariant():
    data = [5.0, 5.0, 5.0]
    s = compute_statistics(data)
    assert s["count"] == float(len(data))
    assert math.isclose(s["mean"], 5.0, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(s["stdev"], 0.0, rel_tol=1e-12, abs_tol=1e-12)


def test_against_python_pstdev():
    data = [0.5, 2.0, -1.5, 3.0]
    s = compute_statistics(data)
    expected_mean = sum(data) / len(data)
    expected_stdev = math.sqrt(sum((x - expected_mean) ** 2 for x in data) / len(data))
    assert math.isclose(s["mean"], expected_mean, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(s["stdev"], expected_stdev, rel_tol=1e-12, abs_tol=1e-12)

    # Compare to Python's built-in pstdev for an additional guard
    expected_pstdev = statistics.pstdev(data)
    assert math.isclose(s["stdev"], expected_pstdev, rel_tol=1e-12, abs_tol=1e-12)


def test_read_sample_data_and_basic_form():
    data = read_sample_data()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(x, (int, float)) for x in data)

    s = compute_statistics(data)
    expected_mean = sum(data) / len(data)
    expected_stdev = math.sqrt(sum((x - expected_mean) ** 2 for x in data) / len(data))
    assert math.isclose(s["mean"], expected_mean, rel_tol=1e-12, abs_tol=1e-12)
    assert math.isclose(s["stdev"], expected_stdev, rel_tol=1e-12, abs_tol=1e-12)


def test_format_summary_text_contains_keywords():
    data = [1.0, 2.0, 3.0]
    summary = compute_statistics(data)
    text = format_summary_text(summary)
    assert isinstance(text, str)
    assert text.startswith("summary ->")
    assert "count=" in text and "mean=" in text and "stdev=" in text


def test_read_sample_data_deterministic_runs():
    # Smoke test for determinism: multiple runs should yield identical outputs
    for _ in range(5):
        data = read_sample_data()
        s = compute_statistics(data)
        s2 = compute_statistics(list(data))  # copy to simulate a fresh sequence
        assert math.isclose(s["mean"], s2["mean"], rel_tol=1e-15, abs_tol=0.0)
        assert math.isclose(s["stdev"], s2["stdev"], rel_tol=1e-15, abs_tol=0.0)
        assert s["count"] == s2["count"]