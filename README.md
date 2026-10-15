# Riverplan

A Python project for planning boat crossings with [PySAT](https://pysathq.github.io/). Passengers have different crossing times, and the boat has a limited capacity. Each trip takes as long as its slowest passenger.

## Run

Requires Python 3.12–3.14. Tested on Linux.

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -c requirements.lock -e '.[dev]'

riverplan 1 2 5 10 --capacity 2
riverplan 1 3 6 8 --deadline 18 --json
```

The first example finds a minimum duration of **17**, with a schedule showing departures, arrivals and passengers. Use `--deadline` to request any feasible schedule within a time limit. `python -m riverplan` works too.

## Rules

All passengers start on bank A and must reach bank B. The boat alternates direction and needs at least one passenger on every trip, including returns. Durations are nonnegative integers in the same unit. Passenger IDs start at 1.

The solver checks every returned schedule independently. Resource limits stop difficult calculations with an explicit error; they do not mean the problem is impossible. Large instances can still be expensive.

## Tests

```sh
pytest
ruff check .
ruff format --check .
```

The tests retain the original exercise cases and compare small instances against an independent shortest-path search. See [the model and Python API](docs/model.md) for details.
