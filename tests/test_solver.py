import itertools
import random
from dataclasses import FrozenInstanceError

import pytest

from riverplan import Crossing, Limits, Plan, SearchLimitExceeded, solve, verify_plan
from riverplan.encoding import Encoding
from tests.oracle import minimum


def check_case(values, capacity):
    expected = minimum(tuple(values), capacity)
    plan = solve(values, capacity)
    if expected is None:
        assert plan is None
        return
    assert plan is not None and plan.optimal
    assert plan.duration == expected, (values, capacity)
    verify_plan(plan, values, capacity, expected)
    # Check the SAT decision path directly as well as the optimizer's shortcuts.
    if len(values) > capacity > 1 and expected:
        assert solve(values, capacity, expected - 1) is None
        decision = solve(values, capacity, expected)
        assert decision is not None and not decision.optimal
        verify_plan(decision, values, capacity, expected)


@pytest.mark.parametrize("size", range(1, 5))
def test_exhaustive_small_instances(size):
    for values in itertools.combinations_with_replacement(range(3), size):
        for capacity in range(1, size + 2):
            check_case(values, capacity)


def test_random_instances_against_dijkstra():
    rng = random.Random(81)
    for _ in range(45):
        values = tuple(rng.randrange(0, 15) for _ in range(rng.randrange(2, 6)))
        check_case(values, rng.randrange(1, len(values) + 2))


@pytest.mark.parametrize(
    "values, capacity, expected",
    [
        ([], 1, 0),
        ([0], 1, 0),
        ([0, 0, 0], 2, 0),
        ([1], 20, 1),
        ([4, 1, 4], 20, 4),
        ([10**12, 2 * 10**12, 5 * 10**12, 10 * 10**12], 2, 17 * 10**12),
        ([10**9 + 7, 10**9 + 9, 10**9 + 21], 2, 3 * 10**9 + 37),
    ],
)
def test_edge_cases_and_large_time_units(values, capacity, expected):
    plan = solve(values, capacity)
    assert plan.duration == expected
    verify_plan(plan, values, capacity)


@pytest.mark.parametrize(
    "values, capacity, deadline, error",
    [
        ([-1], 1, 0, ValueError),
        ([1], 0, 2, ValueError),
        ([1], -1, 2, ValueError),
        ([1], 1, -1, ValueError),
        ([True], 1, 2, TypeError),
        ([1.5], 1, 2, TypeError),
        ([1], True, 2, TypeError),
        ([1], 1.5, 2, TypeError),
        ([1], 1, True, TypeError),
        ([1], 1, 1.5, TypeError),
        ("123", 2, 3, TypeError),
        (None, 2, 3, TypeError),
    ],
)
def test_invalid_inputs(values, capacity, deadline, error):
    with pytest.raises(error):
        solve(values, capacity, deadline)


def test_input_and_results_are_independent():
    values = [1, 2, 5, 10]
    plan = solve(values, 2)
    assert values == [1, 2, 5, 10]
    original = plan.crossings
    values[0] = 100
    assert plan.crossings == original
    with pytest.raises(FrozenInstanceError):
        plan.duration = 999


@pytest.mark.parametrize(
    "limits",
    [
        Limits(max_variables=1),
        Limits(max_clauses=1),
    ],
)
def test_resource_exhaustion_is_not_an_impossibility(limits):
    with pytest.raises(SearchLimitExceeded):
        solve([1, 2, 5, 10], 2, 17, limits=limits)


def test_conflict_exhaustion_is_unknown(monkeypatch):
    class InterruptedSolver:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def conf_budget(self, budget):
            assert budget > 0

        def solve_limited(self):
            return None

    monkeypatch.setattr("riverplan.solver.Solver", InterruptedSolver)
    with pytest.raises(SearchLimitExceeded, match="unknown"):
        solve([1, 2, 5, 10], 2, 17)


def test_binary_time_encoding_does_not_expand_each_time_instant():
    encoding = Encoding((10**9 + 7, 10**9 + 9, 10**9 + 21), 2, 3 * 10**9 + 36, Limits())
    assert len(encoding.active) <= 3
    assert encoding.formula.pool.top < 1000


@pytest.mark.parametrize(
    "plan",
    [
        Plan((Crossing(0, (1, 1)),), 1),
        Plan((Crossing(0, (0,)),), 1),
        Plan((Crossing(0, (3,)),), 1),
        Plan((Crossing(0, (True,)),), 1),
        Plan((Crossing(0, (1, 2)),), 2),
        Plan((Crossing(0, (1,)), Crossing(0, (1,))), 1),
        Plan((Crossing(0, (1,)), Crossing(1, (2,))), 2),
        Plan((Crossing(0, ()),), 0),
        Plan((Crossing(-1, (1,)),), 0),
        Plan((), 0),
    ],
)
def test_verifier_rejects_invalid_trips(plan):
    with pytest.raises((TypeError, ValueError)):
        verify_plan(plan, [1, 2], 1)


def test_verifier_checks_final_duration_and_deadline():
    with pytest.raises(ValueError, match="last arrival"):
        verify_plan(Plan((Crossing(0, (1, 2)),), 99), [1, 2], 2)
    with pytest.raises(ValueError, match="deadline"):
        verify_plan(Plan((Crossing(0, (1, 2)),), 2), [1, 2], 2, 1)
    verify_plan(Plan((Crossing(5, (1, 2)),), 7), [1, 2], 2, 7)
