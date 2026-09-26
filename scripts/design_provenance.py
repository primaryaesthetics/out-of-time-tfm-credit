#!/usr/bin/env python3
"""Provenance table of the design documents.

The public repository is a single snapshot of this record, so its history
cannot show that a design was written before the runs it governs. This script
writes the table that stands in for that history: for every version of every
design document, the commit of the record that holds it, the commit date, and
the sha256 of the file's bytes at that commit.

    python scripts/design_provenance.py                   # table to stdout
    python scripts/design_provenance.py --out PROVENANCE.md

A reader of the snapshot can hash a document and find its row; a reviewer
given the record can check any row with `git show <commit>:<path>`. Commit
dates are written by the committer and prove nothing on their own; the
external timestamps are the archive deposits named in the paper.

The design documents are the experiment designs (`docs/experiments/EXP-*.md`
less the template and the run logs), `docs/protocol/gates.md` and the decision
records (`docs/decisions/ADR-*.md`). A document renamed along the way is
followed through the rename and listed under its current path.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class Version:
    path: str
    path_at_commit: str
    commit: str
    date: str
    sha256: str


def git(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True).stdout


def design_documents(root: Path, rev: str) -> list[str]:
    tracked = git(root, "ls-tree", "-r", "--name-only", rev).decode("utf-8").splitlines()
    chosen = []
    for path in tracked:
        name = path.rsplit("/", 1)[-1]
        if path.startswith("docs/experiments/") and name.startswith("EXP-") and name.endswith(".md"):
            if name.startswith("EXP-000-") or name.endswith("-log.md"):
                continue
            chosen.append(path)
        elif path == "docs/protocol/gates.md" or path.startswith("docs/decisions/") and name.startswith("ADR-") and name.endswith(".md"):
            chosen.append(path)
    return sorted(chosen)


def versions(root: Path, path: str, rev: str) -> list[Version]:
    # One record per commit that touched the file, with the path the file had
    # in that commit. `--reverse` is not passed: combined with `--follow`, git
    # stops at the rename, so the order is reversed here instead.
    log = git(root, "log", "--follow", "--format=%x00%H %ct", "--name-status", rev, "--", path).decode("utf-8")
    out = []
    for record in reversed(log.split("\x00")[1:]):
        lines = [line for line in record.splitlines() if line.strip()]
        commit, stamp = lines[0].split()
        status = lines[-1].split("\t")
        if status[0].startswith("D"):
            continue
        path_at_commit = status[-1]
        blob = git(root, "show", f"{commit}:{path_at_commit}")
        date = dt.datetime.fromtimestamp(int(stamp), tz=dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        out.append(Version(path, path_at_commit, commit, date, hashlib.sha256(blob).hexdigest()))
    return out


def table(root: Path, rev: str) -> str:
    head = git(root, "rev-parse", rev).decode("ascii").strip()
    rows = [
        "# Provenance of the design documents",
        "",
        f"Record commit of this snapshot: `{head}`.",
        "",
        "One row per version of each document. `sha256` is taken over the file's bytes",
        "at that commit; the row marked `current` matches the file in this snapshot.",
        "Commit dates are as recorded by the committer.",
        "",
        "| document | version | commit | commit date (UTC) | sha256 | |",
        "|---|---:|---|---|---|---|",
    ]
    for path in design_documents(root, rev):
        history = versions(root, path, rev)
        current = hashlib.sha256(git(root, "show", f"{head}:{path}")).hexdigest()
        for number, version in enumerate(history, start=1):
            name = path if version.path_at_commit == path else f"{path} (as {version.path_at_commit})"
            mark = "current" if number == len(history) and version.sha256 == current else ""
            rows.append(
                f"| {name} | {number} | `{version.commit}` | {version.date} | `{version.sha256}` | {mark} |"
            )
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rev", default="HEAD", help="commit of the record to describe (default HEAD)")
    parser.add_argument("--out", type=Path, help="write the table here instead of stdout")
    args = parser.parse_args()

    text = table(ROOT, args.rev)
    if args.out is None:
        sys.stdout.write(text)
    else:
        args.out.write_text(text, encoding="utf-8", newline="\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
