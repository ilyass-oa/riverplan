import pytest

from project import find_duration, gen_solution


def test_empty_crossing_needs_no_trip():
    assert gen_solution([], 2, 0) == []


def test_empty_minimum_is_zero():
    assert find_duration([], 2) == 0


def test_negative_duration_is_rejected():
    with pytest.raises(ValueError):
        gen_solution([-1], 1, 0)


def test_capacity_must_be_positive():
    with pytest.raises(ValueError):
        gen_solution([1, 2], 0, 4)


def test_boolean_deadline_is_rejected():
    with pytest.raises(TypeError):
        gen_solution([1], 1, True)
