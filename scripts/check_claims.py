#!/usr/bin/env python3
"""Claim gate.

Three conditions, all of which have to hold:

  * every claim in docs/ledger/CLAIMS.md points at evidence that exists — an
    experiment directory carrying a manifest;
  * every claim id cited anywhere in the repository is defined in the ledger;
  * an active claim's run was recorded on a clean tree, and every file of this
    repository its command executes — the script and each local module it
    imports — is pinned by its manifest and hashes, in this checkout, to the
    recorded value, so the number reruns from the code as it stands. A claim whose code has changed is
    rerun and superseded, never left pointing at code that no longer exists.

Run from the repository root. Exits non-zero on any failure.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

from record_run import file_hash, local_code

LEDGER = Path("docs/ledger/CLAIMS.md")
CODE_PREFIXES = ("scripts/", "src/", "packages/")
CLAIM_ID = re.compile(r"\bC-\d{3,}\b")
EXPERIMENT_POINTER = re.compile(r"^experiments/[\w.\-]+/?$")

TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml", ".cff", ".ipynb"}


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=True
    ).stdout
    return [Path(name) for name in out.split("\0") if name]


def parse_ledger() -> tuple[dict[str, str], set[str], list[str]]:
    """Returns {claim id: evidence pointer}, the ids marked active, and a list
    of parse errors."""
    errors: list[str] = []
    claims: dict[str, str] = {}
    active: set[str] = set()
    if not LEDGER.exists():
        return claims, active, [f"{LEDGER}: missing"]

    for number, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if not cells or not CLAIM_ID.fullmatch(cells[0]):
            continue
        if len(cells) < 4:
            errors.append(f"{LEDGER}:{number}: row has {len(cells)} columns, expected at least 4")
            continue
        claim_id, evidence = cells[0], cells[3]
        if claim_id in claims:
            errors.append(f"{LEDGER}:{number}: {claim_id} defined twice")
        claims[claim_id] = evidence
        if len(cells) >= 5 and cells[4] == "active":
            active.add(claim_id)
    return claims, active, errors


def check_evidence(claim_id: str, evidence: str) -> list[str]:
    evidence = evidence.strip("`")
    if not EXPERIMENT_POINTER.match(evidence):
        return [f"{claim_id}: evidence {evidence!r} is not an experiment directory"]
    path = Path(evidence.rstrip("/"))
    if not path.is_dir():
        return [f"{claim_id}: {path} is not a directory"]
    if not (path / "manifest.json").exists():
        return [f"{claim_id}: {path}/manifest.json is missing"]
    return []


def check_code(claim_id: str, evidence: str, root: Path = Path(".")) -> list[str]:
    """An active claim reruns from this checkout: its run was clean, and every
    file of the repository its command executes is pinned by the manifest and
    unchanged since."""
    manifest = json.loads(
        (root / evidence.strip("`").rstrip("/") / "manifest.json").read_text(encoding="utf-8")
    )
    errors = []
    if manifest.get("git_dirty"):
        errors.append(f"{claim_id}: its run was recorded on a dirty tree")
    pinned = {
        **(manifest.get("input_sha256") or {}),
        **(manifest.get("library_sha256") or {}),
        **(manifest.get("code_sha256") or {}),
    }
    executed = local_code(manifest.get("command") or [], root.resolve())
    if not executed:
        errors.append(f"{claim_id}: no file of this repository found in its run's command")
    for path in executed:
        name = path.relative_to(root.resolve()).as_posix()
        if name not in pinned:
            errors.append(
                f"{claim_id}: {name} runs under its command but its manifest does not pin it; "
                "rerun under scripts/record_run.py and supersede the claim"
            )
        elif file_hash(path) != pinned[name]:
            errors.append(
                f"{claim_id}: {name} has changed since its run; rerun and supersede the claim"
            )
    return errors


def main() -> int:
    claims, active, errors = parse_ledger()

    for claim_id, evidence in sorted(claims.items()):
        found = check_evidence(claim_id, evidence)
        errors.extend(found)
        if not found and claim_id in active:
            errors.extend(check_code(claim_id, evidence))

    cited: dict[str, list[str]] = {}
    for path in tracked_files():
        if path.suffix not in TEXT_SUFFIXES or path == LEDGER:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            for claim_id in CLAIM_ID.findall(line):
                cited.setdefault(claim_id, []).append(f"{path.as_posix()}:{number}")

    for claim_id, sites in sorted(cited.items()):
        if claim_id not in claims:
            for site in sites:
                errors.append(f"{site}: cites {claim_id}, which the ledger does not define")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"\nclaims: {len(errors)} failure(s)", file=sys.stderr)
        return 1

    print(f"claims: {len(claims)} defined, {len(cited)} cited, all resolving")
    return 0


if __name__ == "__main__":
    sys.exit(main())
