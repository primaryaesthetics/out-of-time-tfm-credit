#!/usr/bin/env python3
"""Runs a list of scoring jobs on a node, one after another, and keeps the tally.

The grid is many bundles and, for one of the models, two passes over each,
and a node runs through them unattended: a laptop through a night, a hosted
notebook until its session is taken away. The scorer already survives that
per cell; this runs it per job and survives it per job. Every job in the list
is one call of the scorer on one bundle into one output directory, in the
order the list gives, and a job whose tally entry says it finished is not
started again. A job that fails stops the list, because the jobs after it
would fail the same way and the log is easier to read with one failure in it.

    python node_jobs.py jobs.json
    python node_jobs.py jobs.json --command "./run-score.sh"

The list is `jobs.json` from `pack_node_run.py`: the command the scorer is
started with, and the jobs, each with a name, a bundle directory, an output
directory and the scorer's options. The command can be replaced on the line,
which is how a machine that wraps the scorer in its own environment runs the
same list. The tally is `jobs-done.json` beside the list and holds, per
finished job, when it finished and how long it took.

This file travels to the node with the scorer and imports nothing but the
standard library.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import json
import shlex
import subprocess
import sys
import time
from pathlib import Path

TALLY_FILE = "jobs-done.json"


def read_jobs(path: Path) -> dict:
    listing = json.loads(path.read_text(encoding="utf-8"))
    for key in ("name", "command", "jobs"):
        if key not in listing:
            raise SystemExit(f"{path} has no '{key}'; not a list from pack_node_run.py")
    names = [job["name"] for job in listing["jobs"]]
    if len(set(names)) != len(names):
        raise SystemExit(f"{path} names a job twice")
    for job in listing["jobs"]:
        for key in ("name", "bundle", "out", "args"):
            if key not in job:
                raise SystemExit(f"job {job.get('name', '?')} in {path} has no '{key}'")
    return listing


def read_tally(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def command_line(command: list[str], job: dict) -> list[str]:
    return [*command, job["bundle"], "--out-dir", job["out"], *job["args"]]


def run_jobs(listing: dict, command: list[str], *, cwd: Path, log: Path | None,
             dry: bool = False) -> int:
    tally_path = cwd / TALLY_FILE
    tally = read_tally(tally_path)
    jobs = listing["jobs"]
    done = [j for j in jobs if j["name"] in tally]
    print(f"{listing['name']}: {len(jobs)} jobs, {len(done)} already finished", flush=True)
    for number, job in enumerate(jobs, start=1):
        line = command_line(command, job)
        if job["name"] in tally:
            print(f"[{number}/{len(jobs)}] {job['name']}: finished "
                  f"{tally[job['name']]['finished']}, skipped", flush=True)
            continue
        print(f"[{number}/{len(jobs)}] {job['name']}: {shlex.join(line)}", flush=True)
        if dry:
            continue
        if not (cwd / job["bundle"]).is_dir():
            print(f"  the bundle directory {job['bundle']} is not under {cwd}", file=sys.stderr)
            return 2
        started = time.time()
        with open(log, "a", encoding="utf-8") if log else contextlib.nullcontext() as sink:
            if sink:
                sink.write(f"\n### {job['name']}: {shlex.join(line)}\n")
                sink.flush()
            process = subprocess.Popen(line, cwd=cwd, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                       errors="replace")
            assert process.stdout is not None
            for text in process.stdout:
                sys.stdout.write(text)
                sys.stdout.flush()
                if sink:
                    sink.write(text)
                    sink.flush()
            code = process.wait()
        elapsed = round(time.time() - started, 1)
        if code != 0:
            print(f"  {job['name']} failed with exit code {code} after {elapsed:.0f} s; "
                  f"the jobs after it are not started", file=sys.stderr, flush=True)
            return code
        tally[job["name"]] = {
            "finished": dt.datetime.now(dt.UTC).isoformat(timespec="seconds"),
            "seconds": elapsed, "out": job["out"],
        }
        tally_path.write_text(json.dumps(tally, indent=2) + "\n", encoding="utf-8")
        print(f"  {job['name']} finished in {elapsed:.0f} s", flush=True)
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("jobs", type=Path, help="jobs.json from pack_node_run.py")
    parser.add_argument("--command", default=None,
                        help="what to start the scorer with, replacing the list's own; "
                             "the bundle, --out-dir and the job's options follow it")
    parser.add_argument("--log", type=Path, default=None,
                        help="append every job's console output here as well")
    parser.add_argument("--list", choices=("bundles", "outputs"), default=None,
                        help="print the bundle or output directories the list names, one per "
                             "line, and run nothing")
    parser.add_argument("--dry-run", action="store_true",
                        help="print every command that would run and run nothing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    listing = read_jobs(args.jobs)
    if args.list is not None:
        key = "bundle" if args.list == "bundles" else "out"
        for value in dict.fromkeys(job[key] for job in listing["jobs"]):
            print(value)
        return 0
    command = shlex.split(args.command) if args.command else list(listing["command"])
    return run_jobs(listing, command, cwd=args.jobs.resolve().parent, log=args.log,
                    dry=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
