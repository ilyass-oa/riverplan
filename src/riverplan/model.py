"""Crossing plans and a verifier independent of the SAT encoding."""

from collections.abc import Sequence
from dataclasses import dataclass


def integer(value: int, name: str, *, minimum: int = 0) -> int:
    if type(value) is not int:
        raise TypeError(f"{name} must be an integer")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}")
    return value


def inputs(durations: Sequence[int], capacity: int) -> tuple[tuple[int, ...], int]:
    if not isinstance(durations, Sequence) or isinstance(durations, (str, bytes)):
        raise TypeError("durations must be a sequence of integers")
    values = tuple(integer(d, "duration") for d in durations)
    return values, integer(capacity, "capacity", minimum=1)


@dataclass(frozen=True, slots=True)
class Crossing:
    start: int
    passengers: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class Plan:
    crossings: tuple[Crossing, ...]
    duration: int
    optimal: bool = False


class SearchLimitExceeded(RuntimeError):
    """The calculation stopped without proving feasibility or optimality."""


@dataclass(frozen=True, slots=True)
class Limits:
    max_variables: int = 100_000
    max_clauses: int = 500_000
    max_conflicts: int = 200_000

    def __post_init__(self) -> None:
        for name in ("max_variables", "max_clauses", "max_conflicts"):
            integer(getattr(self, name), name, minimum=1)


def verify_plan(
    plan: Plan,
    durations: Sequence[int],
    capacity: int,
    deadline: int | None = None,
) -> None:
    """Raise ValueError/TypeError for an invalid schedule; allow waiting and zero times."""
    values, capacity = inputs(durations, capacity)
    if deadline is not None:
        integer(deadline, "deadline")
    if not isinstance(plan, Plan):
        raise TypeError("plan must be a Plan")
    integer(plan.duration, "plan duration")
    on_a = set(range(1, len(values) + 1))
    elapsed = 0
    for index, crossing in enumerate(plan.crossings):
        if not isinstance(crossing, Crossing):
            raise TypeError("each trip must be a Crossing")
        integer(crossing.start, "departure time")
        if crossing.start < elapsed:
            raise ValueError("crossings overlap or run backwards")
        passengers = crossing.passengers
        if not passengers or len(passengers) > capacity:
            raise ValueError("a crossing needs between one and capacity passengers")
        for passenger in passengers:
            integer(passenger, "passenger ID", minimum=1)
            if passenger > len(values):
                raise ValueError("passenger ID is out of range")
        if len(set(passengers)) != len(passengers):
            raise ValueError("a passenger cannot appear twice in a crossing")
        forward = index % 2 == 0
        if any((passenger in on_a) != forward for passenger in passengers):
            raise ValueError("a passenger is on the wrong bank")
        on_a.symmetric_difference_update(passengers)
        elapsed = crossing.start + max(values[p - 1] for p in passengers)
    if on_a:
        raise ValueError("not every passenger reached bank B")
    if plan.duration != elapsed:
        raise ValueError("plan duration does not match the last arrival")
    if deadline is not None and elapsed > deadline:
        raise ValueError("the plan exceeds its deadline")
