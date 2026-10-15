"""Command-line crossing schedules."""

import argparse
import json
import sys

from .model import Limits, SearchLimitExceeded
from .solver import solve


def _nonnegative(value: str) -> int:
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected an integer") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return result


def _positive(value: str) -> int:
    result = _nonnegative(value)
    if result == 0:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan boat crossings using SAT constraints.")
    parser.add_argument("durations", nargs="+", type=_nonnegative, help="time for each passenger")
    parser.add_argument("--capacity", "-c", type=_positive, default=2)
    parser.add_argument("--deadline", type=_nonnegative, help="find any plan within this time")
    parser.add_argument("--max-variables", type=_positive, default=100_000)
    parser.add_argument("--max-clauses", type=_positive, default=500_000)
    parser.add_argument("--max-conflicts", type=_positive, default=200_000)
    parser.add_argument("--json", action="store_true", help="print a machine-readable result")
    args = parser.parse_args(argv)
    try:
        limits = Limits(args.max_variables, args.max_clauses, args.max_conflicts)
        plan = solve(args.durations, args.capacity, args.deadline, limits=limits)
    except SearchLimitExceeded as exc:
        print(f"Search stopped: {exc}", file=sys.stderr)
        return 3
    except (TypeError, ValueError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Interrupted", file=sys.stderr)
        return 130
    result = {
        "status": "impossible" if plan is None else "optimal" if plan.optimal else "feasible",
        "durations": args.durations,
        "capacity": args.capacity,
        "deadline": args.deadline,
        "duration": plan.duration if plan else None,
        "crossings": [],
    }
    if plan is not None:
        result["crossings"] = [
            {
                "departure": trip.start,
                "arrival": trip.start + max(args.durations[p - 1] for p in trip.passengers),
                "direction": "A->B" if i % 2 == 0 else "B->A",
                "passengers": list(trip.passengers),
            }
            for i, trip in enumerate(plan.crossings)
        ]
    if args.json:
        print(json.dumps(result))
    elif plan is None:
        print("No crossing plan exists within these constraints.")
    else:
        label = "Minimum duration" if plan.optimal else "Feasible duration"
        print(f"{label}: {plan.duration} ({len(plan.crossings)} crossings)")
        for trip in result["crossings"]:
            people = ", ".join(map(str, trip["passengers"]))
            print(f"{trip['departure']:>5} -> {trip['arrival']:<5} {trip['direction']}  [{people}]")
    return 1 if plan is None else 0
