"""SAT feasibility and monotone optimization of crossing time."""

from collections.abc import Sequence
from dataclasses import replace
from functools import reduce
from math import gcd

from pysat.solvers import Solver

from .encoding import Encoding, crossing_bounds
from .model import Crossing, Limits, Plan, SearchLimitExceeded, inputs, integer, verify_plan


def _shuttle(durations: tuple[int, ...], capacity: int) -> Plan:
    order = sorted(range(1, len(durations) + 1), key=lambda p: (durations[p - 1], p))
    fastest, others = order[0], list(reversed(order[1:]))
    groups = [others[i : i + capacity - 1] for i in range(0, len(others), capacity - 1)]
    trips = []
    elapsed = 0
    for index, group in enumerate(groups):
        passengers = (fastest, *group)
        trips.append(Crossing(elapsed, passengers))
        elapsed += max(durations[p - 1] for p in passengers)
        if index + 1 < len(groups):
            trips.append(Crossing(elapsed, (fastest,)))
            elapsed += durations[fastest - 1]
    plan = Plan(tuple(trips), elapsed)
    verify_plan(plan, durations, capacity)
    return plan


def _feasible(
    durations: tuple[int, ...], capacity: int, deadline: int, limits: Limits
) -> Plan | None:
    scale = reduce(gcd, durations) or 1
    encoded = Encoding(tuple(d // scale for d in durations), capacity, deadline // scale, limits)
    with Solver(name="g4", bootstrap_with=encoded.formula.clauses) as solver:
        solver.conf_budget(limits.max_conflicts)
        satisfiable = solver.solve_limited()
        if satisfiable is None:
            raise SearchLimitExceeded("SAT conflict limit reached; result is unknown")
        if not satisfiable:
            return None
        model = {literal for literal in solver.get_model() if literal > 0}
    elapsed = 0
    crossings = []
    for active, moves in zip(encoded.active, encoded.moves, strict=True):
        if active not in model:
            break
        passengers = tuple(i + 1 for i, move in enumerate(moves) if move in model)
        crossings.append(Crossing(elapsed, passengers))
        elapsed += max(durations[p - 1] for p in passengers)
    plan = Plan(tuple(crossings), elapsed)
    verify_plan(plan, durations, capacity, deadline)
    return plan


def solve(
    durations: Sequence[int],
    capacity: int,
    deadline: int | None = None,
    *,
    limits: Limits = Limits(),
) -> Plan | None:
    """Find a minimum-time plan, or any plan meeting an explicit deadline.

    Durations are nonnegative integers; passenger IDs are one-based. None means
    impossible. Resource exhaustion raises SearchLimitExceeded, never None.
    """
    values, capacity = inputs(durations, capacity)
    if not isinstance(limits, Limits):
        raise TypeError("limits must be a Limits instance")
    if deadline is not None:
        integer(deadline, "deadline")
    optimize = deadline is None
    if not values:
        plan = Plan((), 0, optimize)
        verify_plan(plan, values, capacity, deadline)
        return plan
    if deadline is not None and max(values) > deadline:
        return None
    if len(values) <= capacity:
        plan = Plan((Crossing(0, tuple(range(1, len(values) + 1))),), max(values), optimize)
        verify_plan(plan, values, capacity, deadline)
        return plan
    if capacity == 1:
        return None
    best = _shuttle(values, capacity)
    if deadline is not None:
        return best if best.duration <= deadline else _feasible(values, capacity, deadline, limits)
    cover_cost, groups, minimum_steps = crossing_bounds(values, capacity)
    low = cover_cost + (minimum_steps - groups) * min(values)
    high = best.duration - 1
    while low <= high:
        middle = (low + high) // 2
        candidate = _feasible(values, capacity, middle, limits)
        if candidate is None:
            low = middle + 1
        else:
            best = candidate
            high = best.duration - 1
    return replace(best, optimal=True)


def gen_solution(durations: Sequence[int], c: int, T: int) -> list[tuple[int, list[int]]] | None:
    """Compatibility API: return departure times and one-based passenger lists."""
    plan = solve(durations, c, T)
    return [(trip.start, list(trip.passengers)) for trip in plan.crossings] if plan else None


def find_duration(durations: Sequence[int], c: int) -> int:
    """Compatibility API: minimum duration, or -1 if crossing is impossible."""
    plan = solve(durations, c)
    return plan.duration if plan is not None else -1
