"""The 24 checks from the original exercise, now with failing exit status."""

import pytest

from project import find_duration, gen_solution
from riverplan import Crossing, Plan, verify_plan

CASES = [
    ([1, 3, 6, 8], 2, 18),
    ([1, 1], 2, 1),
    ([1, 1, 1, 1], 4, 1),
    ([1, 1, 1, 1], 2, 5),
    ([2, 3, 4], 2, 9),
    ([1, 2, 5, 10], 2, 17),
    ([1, 4, 10, 12, 5], 2, 31),
    ([1, 3, 6, 8, 2, 10, 4, 12, 15], 2, 52),
]
IMPOSSIBLE = [
    ([1, 1, 1, 1], 3, 1),
    ([1, 1, 1, 1], 2, 4),
    ([2, 3, 4], 2, 8),
    ([1, 2, 5, 10], 2, 16),
    ([1, 4, 10, 12, 5], 2, 15),
    ([1, 4, 10, 12, 5], 2, 30),
    ([1, 3, 6, 8, 2, 10, 4, 12, 15], 2, 26),
    ([1, 3, 6, 8, 2, 10, 4, 12, 15], 2, 51),
]


@pytest.mark.parametrize("durations, capacity, deadline", CASES)
def test_original_feasibility(durations, capacity, deadline):
    schedule = gen_solution(durations, capacity, deadline)
    assert schedule is not None
    trips = tuple(Crossing(time, tuple(passengers)) for time, passengers in schedule)
    last = trips[-1]
    duration = last.start + max(durations[p - 1] for p in last.passengers)
    verify_plan(Plan(trips, duration), durations, capacity, deadline)


@pytest.mark.parametrize("durations, capacity, expected", CASES)
def test_original_minimum(durations, capacity, expected):
    assert find_duration(durations, capacity) == expected


@pytest.mark.parametrize("durations, capacity, deadline", IMPOSSIBLE)
def test_original_impossible(durations, capacity, deadline):
    assert gen_solution(durations, capacity, deadline) is None
