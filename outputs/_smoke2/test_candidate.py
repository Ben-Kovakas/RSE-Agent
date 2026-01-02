import math
import pytest

import candidate


def test_metafunc_scale_and_shift():
    data = [1.0, -2.0, 0.0, 4.0, 3.5]
    s1 = candidate.compute_summary(data)

    # Scaling by various constants
    for c in [0.5, -2.0, 3.3]:
        scaled = [c * v for v in data]
        s2 = candidate.compute_summary(scaled)
        assert math.isclose(s2["count"], s1["count"], rel_tol=1e-12, abs_tol=0.0)
        assert math.isclose(s2["mean"], c * s1["mean"], rel_tol=1e-12, abs_tol=0.0)
        assert math.isclose(s2["stdev"], abs(c) * s1["stdev"], rel_tol=1e-12, abs_tol=0.0)

    # Shift by a constant delta
    delta = 5.0
    shifted = [v + delta for v in data]
    s3 = candidate.compute_summary(shifted)
    assert math.isclose(s3["mean"], s1["mean"] + delta, rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s3["stdev"], s1["stdev"], rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s3["count"], s1["count"], rel_tol=1e-12, abs_tol=0.0)


def test_metafunc_duplicate_invariance():
    data = [0.0, 1.0, 1.0, 3.0, -1.0]
    s = candidate.compute_summary(data)
    dup = data + data
    s_dup = candidate.compute_summary(dup)

    assert math.isclose(s_dup["mean"], s["mean"], rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s_dup["stdev"], s["stdev"], rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s_dup["count"], s["count"] * 2.0, rel_tol=1e-12, abs_tol=0.0)


def test_reordering_invariance():
    data = [1.0, -2.5, 3.3, 0.0, 4.4]
    s_orig = candidate.compute_summary(data)
    order = data[:]
    import random
    random.seed(0)
    random.shuffle(order)
    s_shuffled = candidate.compute_summary(order)

    assert math.isclose(s_shuffled["mean"], s_orig["mean"], rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s_shuffled["stdev"], s_orig["stdev"], rel_tol=1e-12, abs_tol=0.0)
    assert math.isclose(s_shuffled["count"], s_orig["count"], rel_tol=1e-12, abs_tol=0.0)


def test_consistency_across_runs_same_input():
    data = [0.2, -0.4, 1.2, 2.2, -1.1, 0.0]
    first = candidate.compute_summary(data)
    for _ in range(20):
        second = candidate.compute_summary(list(data))
        assert all(math.isclose(first[k], second[k], rel_tol=1e-12, abs_tol=0.0) for k in first)


def test_read_data_and_default_constants():
    arr = candidate.read_data()
    assert isinstance(arr, list)
    assert arr == list(candidate.DEFAULT_DATA)


def test_error_handling_non_numeric_and_nonfinite():
    with pytest.raises(TypeError):
        candidate.compute_summary([1, "a", 3.0])
    with pytest.raises(ValueError):
        candidate.compute_summary([1.0, float("inf")])


def test_error_handling_non_sequence_input():
    with pytest.raises(AssertionError):
        candidate.compute_summary(None)


def test_main_prints_output(capsys):
    candidate.main()
    captured = capsys.readouterr().out
    assert "summary:" in captured
    assert "formatted:" in captured