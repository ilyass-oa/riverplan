import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(*args):
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))
    return subprocess.run(
        [sys.executable, "-m", "riverplan", *args],
        env=env,
        text=True,
        capture_output=True,
        timeout=45,
    )


def test_json_optimum_can_be_replayed():
    result = run("1", "2", "5", "10", "--capacity", "2", "--json")
    assert result.returncode == 0 and not result.stderr
    data = json.loads(result.stdout)
    assert data["status"] == "optimal" and data["duration"] == 17
    on_a = {1, 2, 3, 4}
    elapsed = 0
    for i, trip in enumerate(data["crossings"]):
        people = trip["passengers"]
        assert 1 <= len(people) <= 2 and len(set(people)) == len(people)
        assert all((p in on_a) == (i % 2 == 0) for p in people)
        assert trip["direction"] == ("A->B" if i % 2 == 0 else "B->A")
        assert trip["departure"] == elapsed
        elapsed += max(data["durations"][p - 1] for p in people)
        assert trip["arrival"] == elapsed
        on_a.symmetric_difference_update(people)
    assert not on_a and elapsed == 17


def test_feasibility_does_not_claim_an_optimum():
    result = run("1", "2", "5", "10", "--deadline", "25", "--json")
    data = json.loads(result.stdout)
    assert result.returncode == 0 and data["status"] == "feasible"
    assert data["duration"] <= 25


def test_plain_schedule():
    result = run("1", "3", "6", "8")
    assert result.returncode == 0 and "Minimum duration: 18" in result.stdout
    assert "A->B" in result.stdout and "B->A" in result.stdout


@pytest.mark.parametrize(
    "args",
    [
        ("1", "2", "5", "10", "--deadline", "16"),
        ("1", "2", "--capacity", "1"),
    ],
)
def test_impossible_result(args):
    result = run(*args, "--json")
    assert result.returncode == 1 and not result.stderr
    assert json.loads(result.stdout)["status"] == "impossible"


def test_budget_exhaustion_has_a_separate_exit_code():
    result = run("1", "2", "5", "10", "--max-variables", "1", "--json")
    assert result.returncode == 3 and "limit" in result.stderr
    assert not result.stdout and "Traceback" not in result.stderr


@pytest.mark.parametrize(
    "args",
    [
        (),
        ("-1",),
        ("1.5",),
        ("nan",),
        ("one",),
        ("1", "--capacity", "0"),
        ("1", "--deadline", "-1"),
        ("1", "--max-variables", "0"),
        ("1", "--max-clauses", "0"),
        ("1", "--max-conflicts", "0"),
        ("1", "--unknown"),
    ],
)
def test_invalid_arguments(args):
    result = run(*args)
    assert result.returncode == 2 and "Traceback" not in result.stderr


def test_zero_duration_is_supported():
    result = run("0", "0", "0", "--json")
    assert result.returncode == 0 and json.loads(result.stdout)["duration"] == 0


def test_help_and_import_have_no_search_side_effect():
    assert run("--help").returncode == 0
    result = subprocess.run(
        [sys.executable, "-c", "import riverplan; import riverplan.cli"],
        text=True,
        capture_output=True,
        timeout=10,
    )
    assert result.returncode == 0 and not result.stdout and not result.stderr
