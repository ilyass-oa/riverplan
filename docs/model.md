# Model and API

## Crossing rules

All passengers and the boat start on bank A. A nonempty group of at most `capacity` passengers moves from the boat's current bank to the other bank. A trip costs the largest individual duration in its group. Trips alternate direction; passengers can return. The objective is to move everyone to bank B.

Times are nonnegative integers in any consistent unit. Zero-time trips are supported, and their order still matters. Empty input needs no trip and has duration zero. Capacity must be a positive integer. Capacity one cannot transport multiple passengers because someone must row every return. Booleans are rejected as numeric input.

## SAT encoding

The formula uses passenger positions before and after each trip, an active prefix of trips, passenger selections and one choice of trip duration. Clauses enforce capacity, departures from the correct bank, position changes and the exact maximum duration of the selected passengers. Inactive trips select nobody and preserve positions. The last state places everyone on B.

Waiting cannot help under these rules, so decoded trips start immediately after the preceding arrival. Binary adders accumulate selected durations; overflow is forbidden and the final sum is bounded by the deadline. Dividing times by their greatest common divisor preserves feasibility; the deadline is rounded down accordingly. This avoids allocating a variable for every unit of elapsed time.

The horizon is complete rather than an arbitrary multiple of the passenger count. A state consists of passenger positions and the boat's bank: at most `2^(n+1)` states. Removing a repeated-state cycle cannot increase nonnegative cost, so a feasible plan exists with at most `2^(n+1)-1` trips.

For positive minimum duration `a`, a cost bound further reduces this horizon. Sort durations in descending order, let `q = ceil(n/capacity)`, and sum every `capacity`-th duration to obtain `cover`. This is the cheapest grouping cost that covers all passengers. With `m` trips, mandatory forward coverage plus the minimum cost of the other movements gives `cost >= cover + (m-q)*a`. The number of trips is odd, and capacity implies at least `2*ceil((n-1)/(capacity-1))-1` trips. These bounds reduce the formula before solving.

A constructive shuttle plan supplies a feasible upper bound. Binary search then asks SAT feasibility questions for smaller deadlines. A minimum is reported only after all smaller deadlines are excluded. Explicit-deadline mode returns a feasible plan without claiming optimality. Every decoded SAT schedule is replayed by a separate verifier.

## Python API

```python
from riverplan import solve, verify_plan

plan = solve([1, 2, 5, 10], capacity=2)
assert plan.duration == 17
verify_plan(plan, [1, 2, 5, 10], capacity=2)

feasible = solve([1, 2, 5, 10], capacity=2, deadline=18)
```

Plans and crossings are immutable dataclasses. Passenger IDs are one-based. `solve` returns `None` only for a proved impossibility under the requested constraints. `verify_plan` raises `ValueError` or `TypeError` for invalid schedules, including overlaps, duplicate/unknown passengers and incorrect capacity or arrival times.

In the checkout, `project.py` preserves the original imports after installation: `gen_solution(durations, c, T)` returns departure/passenger pairs or `None`; `find_duration(durations, c)` returns a minimum duration or `-1` if impossible. Installed packages expose these functions through `riverplan` too.

## Limits and CLI codes

`Limits` bounds variables, clauses and solver conflicts per feasibility call. Exhaustion raises `SearchLimitExceeded`; it is never treated as unsatisfiable. Conflict budgets depend on solver checkpoints and are not wall-clock deadlines. Encoding and state spaces can still be large.

CLI codes: `0` success/help, `1` impossible, `2` invalid arguments, `3` search limit, `130` interrupted. `--json` prints a result with status, duration and ordered crossings; errors go to stderr.

The solver backend is Glucose4 through [PySAT's solver API](https://pysathq.github.io/docs/html/api/solvers.html). Dependencies are pinned, including the explicitly versioned [PySAT prerelease](https://pypi.org/project/python-sat/1.9.dev15/).
