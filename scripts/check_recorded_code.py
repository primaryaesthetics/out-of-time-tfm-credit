#!/usr/bin/env python3
"""Recorded-code gate.

Every manifest under `experiments/` names the commit it ran at and the sha256
of the code it ran: the script on its command line, the library modules and,
in manifests that carry them, the files its command executes. Code keeps changing after a run, so the file at HEAD differing from
the manifest is the normal case and not a defect. What must hold is that the
manifest points at code the record actually contains: the file at the run's
commit hashes to the recorded value.

Each code file of each run is put in one class:

  identical     the file at HEAD hashes to the recorded value
  changed       the file at the run's commit does; the file at HEAD does not
  crlf          the recorded value is the hash of the commit's file with CRLF
                endings, the convention of manifests written before hashing
                normalised line endings
  dirty         the run was recorded on a dirty tree, which its manifest
                states, and the file at its commit does not match
  unresolved    a clean run whose commit is missing from the record or whose
                file at that commit does not hash to the recorded value

`unresolved` fails the gate. Runs cited from the claim ledger are held to the
stricter rule in `scripts/check_claims.py`: their code in the checkout is
identical to what ran.

    python scripts/check_recorded_code.py                  # summary, exit 1 on unresolved
    python scripts/check_recorded_code.py --verbose        # every file not identical
    python scripts/check_recorded_code.py --table CODE.md  # per-run table for a snapshot

The gate needs the history of the record, so it runs on the record and not on
a snapshot; the table it writes is what a snapshot carries instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CODE_PREFIXES = ("scripts/", "src/", "packages/")
CLASSES = ("identical", "changed", "crlf", "dirty", "unresolved")


@dataclass(frozen=True)
class Entry:
    run: str
    commit: str
    path: str
    status: str


def normalised(data: bytes) -> bytes:
    return data if b"\0" in data[:8192] else data.replace(b"\r\n", b"\n")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def code_hashes(manifest: dict) -> dict[str, str]:
    """The code files a manifest pins: command-line inputs under the code
    directories, the library modules, and the files its command executes."""
    code = {
        path: value
        for path, value in (manifest.get("input_sha256") or {}).items()
        if path.startswith(CODE_PREFIXES)
    }
    code.update(manifest.get("library_sha256") or {})
    code.update(manifest.get("code_sha256") or {})
    return code


class Record:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._blobs: dict[tuple[str, str], bytes | None] = {}

    def blob(self, rev: str, path: str) -> bytes | None:
        key = (rev, path)
        if key not in self._blobs:
            done = subprocess.run(
                ["git", "-C", str(self.root), "show", f"{rev}:{path}"],
                capture_output=True,
                check=False,
            )
            self._blobs[key] = done.stdout if done.returncode == 0 else None
        return self._blobs[key]


def classify(record: Record, manifest: dict, path: str, recorded: str) -> str:
    head = record.blob("HEAD", path)
    if head is not None and sha256(normalised(head)) == recorded:
        return "identical"
    at_run = record.blob(manifest.get("git_sha", ""), path)
    if at_run is not None:
        lf = normalised(at_run)
        if sha256(lf) == recorded:
            return "changed"
        if sha256(lf.replace(b"\n", b"\r\n")) == recorded:
            return "crlf"
    return "dirty" if manifest.get("git_dirty") else "unresolved"


def survey(root: Path) -> list[Entry]:
    record = Record(root)
    entries = []
    for manifest_path in sorted((root / "experiments").glob("*/manifest.json")):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run = manifest_path.parent.name
        for path, recorded in sorted(code_hashes(manifest).items()):
            status = classify(record, manifest, path, recorded)
            entries.append(Entry(run, manifest.get("git_sha", ""), path, status))
    return entries


def table(entries: list[Entry]) -> str:
    runs: dict[str, list[Entry]] = {}
    for entry in entries:
        runs.setdefault(entry.run, []).append(entry)
    rows = [
        "# Code of the recorded runs",
        "",
        "Each run's manifest names the commit of the study's working record it ran",
        "at and the sha256 of every code file it ran. This table says, per run,",
        "whether that code is identical in this snapshot or was changed after the",
        "run, and names the files that were. Changed files are available at the",
        "named commit of the record.",
        "",
        "| run | record commit | code files | identical here | changed since the run |",
        "|---|---|---:|---:|---|",
    ]
    for run, items in runs.items():
        same = sum(item.status == "identical" for item in items)
        other = [
            f"`{item.path}`" + ("" if item.status == "changed" else f" ({item.status})")
            for item in items
            if item.status != "identical"
        ]
        rows.append(
            f"| {run} | `{items[0].commit[:12]}` | {len(items)} | {same} | {', '.join(other)} |"
        )
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--verbose", action="store_true", help="list every file not identical")
    parser.add_argument("--table", type=Path, help="write the per-run table here")
    args = parser.parse_args()

    entries = survey(ROOT)
    counts = Counter(entry.status for entry in entries)
    runs = len({entry.run for entry in entries})

    for entry in entries:
        if entry.status == "unresolved" or (args.verbose and entry.status != "identical"):
            stream = sys.stderr if entry.status == "unresolved" else sys.stdout
            print(f"{entry.status:<10} {entry.run}: {entry.path} @ {entry.commit[:12]}", file=stream)

    if args.table is not None:
        args.table.write_text(table(entries), encoding="utf-8", newline="\n")

    summary = ", ".join(f"{counts[name]} {name}" for name in CLASSES)
    print(f"recorded code: {len(entries)} files over {runs} runs: {summary}")
    if counts["unresolved"]:
        print(
            "recorded code: a clean run's manifest names code the record does not hold",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
