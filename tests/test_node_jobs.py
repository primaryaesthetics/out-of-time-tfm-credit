"""The job runner, on what would lose a night on a node.

A node walks a list of jobs unattended, and the two ways that goes wrong are
starting a finished job again after an interruption and carrying on past a
failure into jobs that fail the same way. Neither needs a model: the scorer
is replaced with a script that records how it was called.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import node_jobs

FAKE_SCORER = '''
import sys, pathlib
args = sys.argv[1:]
bundle, out = args[0], args[args.index("--out-dir") + 1]
if "bad" in bundle:
    print("refused", file=sys.stderr)
    sys.exit(3)
pathlib.Path(out).mkdir(exist_ok=True)
(pathlib.Path(out) / "called.txt").write_text(" ".join(args), encoding="utf-8")
print("scored", bundle, "into", out)
'''


def listing(tmp_path: Path, bundles: tuple[str, ...], jobs: list[dict] | None = None) -> Path:
    fake = tmp_path / "fake_scorer.py"
    fake.write_text(FAKE_SCORER, encoding="utf-8")
    for bundle in bundles:
        (tmp_path / bundle).mkdir()
    if jobs is None:
        jobs = [{"name": f"a@{b}", "bundle": b, "out": f"{b}-scored-a", "args": ["--models", "x"]}
                for b in bundles]
    path = tmp_path / "jobs.json"
    path.write_text(json.dumps({"name": "test", "command": [sys.executable, str(fake)],
                                "bundles": list(bundles), "jobs": jobs}), encoding="utf-8")
    return path


def run(path: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPTS / "node_jobs.py"), str(path), *extra],
                          capture_output=True, text=True, cwd=path.parent, check=False)


def test_every_job_runs_in_order_and_the_tally_says_so(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1", "b2"))
    result = run(path, "--log", "score.log")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "b1-scored-a" / "called.txt").read_text() == \
        "b1 --out-dir b1-scored-a --models x"
    assert (tmp_path / "b2-scored-a" / "called.txt").exists()
    tally = json.loads((tmp_path / node_jobs.TALLY_FILE).read_text())
    assert list(tally) == ["a@b1", "a@b2"]
    assert tally["a@b1"]["out"] == "b1-scored-a"
    log = (tmp_path / "score.log").read_text()
    assert log.index("### a@b1") < log.index("scored b1") < log.index("### a@b2")
    assert result.stdout.index("[1/2] a@b1") < result.stdout.index("[2/2] a@b2")


def test_a_second_start_skips_what_finished(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1", "b2"))
    assert run(path).returncode == 0
    (tmp_path / "b1-scored-a" / "called.txt").unlink()
    result = run(path)
    assert result.returncode == 0, result.stderr
    assert "a@b1: finished" in result.stdout and "skipped" in result.stdout
    assert not (tmp_path / "b1-scored-a" / "called.txt").exists()


def test_a_failure_stops_the_list(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1", "bad2", "b3"))
    result = run(path)
    assert result.returncode == 3
    assert "a@bad2 failed with exit code 3" in result.stderr
    assert (tmp_path / "b1-scored-a" / "called.txt").exists()
    assert not (tmp_path / "b3-scored-a").exists()
    tally = json.loads((tmp_path / node_jobs.TALLY_FILE).read_text())
    assert list(tally) == ["a@b1"]


def test_a_bundle_that_is_not_there_is_refused_before_anything_runs(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1",))
    (tmp_path / "b1").rmdir()
    result = run(path)
    assert result.returncode == 2
    assert "b1 is not under" in result.stderr
    assert not (tmp_path / node_jobs.TALLY_FILE).exists()


def test_the_command_can_be_replaced_on_the_line(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1",))
    other = tmp_path / "other_scorer.py"
    other.write_text(FAKE_SCORER.replace('"called.txt"', '"other.txt"'), encoding="utf-8")
    result = run(path, "--command", f'"{sys.executable}" "{other}"')
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "b1-scored-a" / "other.txt").exists()


def test_dry_run_and_the_listings_run_nothing(tmp_path: Path) -> None:
    path = listing(tmp_path, ("b1", "b2"))
    dry = run(path, "--dry-run")
    assert dry.returncode == 0 and "b1 --out-dir b1-scored-a --models x" in dry.stdout
    assert run(path, "--list", "bundles").stdout.split() == ["b1", "b2"]
    assert run(path, "--list", "outputs").stdout.split() == ["b1-scored-a", "b2-scored-a"]
    assert not (tmp_path / "b1-scored-a").exists()
    assert not (tmp_path / node_jobs.TALLY_FILE).exists()


def test_a_list_that_names_a_job_twice_is_refused(tmp_path: Path) -> None:
    jobs = [{"name": "same", "bundle": "b1", "out": "o1", "args": []},
            {"name": "same", "bundle": "b1", "out": "o2", "args": []}]
    path = listing(tmp_path, ("b1",), jobs)
    with pytest.raises(SystemExit, match="twice"):
        node_jobs.read_jobs(path)
