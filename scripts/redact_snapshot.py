#!/usr/bin/env python3
"""Home directories and host names in the public snapshot.

A recorded run states the machine it ran on, and on a borrowed machine that
statement includes the account name of its owner. `manifest.json` carries the
interpreter's absolute path in `command` and again as a key of
`input_sha256`; a warning printed by a library carries the path of the file
that raised it. Those names belong to people who lent a laptop, not to this
record, and the public snapshot must not carry them.

The `host` field names people and businesses the same way. macOS sets a
machine's network name from its owner's name, so a manifest written on a
borrowed Mac reads `MacBook-Pro-<name>.local`; a manifest written on a rented
machine may open with the domain of the business that rented it out,
`"host": "<domain> rented instance, ..."`. Neither is a property of the
computation.

A recorded run is never edited, so nothing here rewrites the record. The
snapshot is an export, and this runs on the export:

    python scripts/redact_snapshot.py --check <export>    # exit 1 on a finding
    python scripts/redact_snapshot.py --write <export>    # rewrite, then check

`--allow NAME` declares a name that is not a finding, repeatably: an account
name, the name segment of a macOS host name, or a domain. Both modes print one
line per distinct finding with the number of files and occurrences, so the
release procedure sees who is in the export before deciding. `--write`
replaces

- the account segment of every home path, leaving the rest of the path alone:
  a manifest keeps the shape of its command and the hash beside it, and only
  the name of the account goes;
- the name segment of a macOS host name, in either form the system sets
  (`<Model>-<name>.local` and `<name>-<Model>.local`, in any case, and either
  without `.local` when it is the whole value of a `host` field), by the
  placeholder;
- a domain that opens a `host` value and is followed by "rented", by nothing,
  so the value opens with "Rented" as the other rented hosts do.

The record itself reads red here, and that is the intended reading: it holds
the true paths and host names, and the export is where they stop.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PLACEHOLDER = "node"

TEXT_SUFFIXES = {
    ".md", ".py", ".toml", ".yml", ".yaml", ".sh", ".ipynb", ".cfg",
    ".cff", ".txt", ".json", ".html", ".css", ".js", ".log", ".csv", ".tex",
}

SKIP_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules"}

# The account segment of a home directory, on either platform and with either
# separator: /Users/<name>, /home/<name>, C:/Users/<name>, C:\Users\<name>.
# The name is captured so that only it is replaced.
HOME = re.compile(
    r"(?:[A-Za-z]:)?[\\/](?:Users|home)[\\/]([A-Za-z0-9._-]+)(?=[\\/])"
)

# A Mac's network name as the system derives it from the owner's name. The
# system writes the owner's name after the model (MacBook-Pro-<name>.local) or
# before it (<name>-MacBook-Pro.local, or -2.local and so on when the name is
# taken on the network). Both patterns start only where a host name starts,
# so neither reads the other form's model or number as a name, and a bare
# model, numbered or not (MacBook-Pro.local, MacBook-Pro-2.local), carries no
# name at all. Longer models come first in the alternation; case is ignored.
#
# Without the ".local" suffix the same name is read only as the whole value of
# a JSON "host" field ("host": "MacBook-Pro-<name>"), which is how a bare host
# name stands in a manifest; elsewhere a model joined to a word, in running
# text or in any other string, is not taken for a host name.
MAC_MODEL = (
    r"(?:MacBook-Pro|MacBook-Air|MacBook|iMac-Pro|iMac|Mac-mini|Mac-Pro"
    r"|Mac-Studio|Mac)"
)
HOST_START = r"(?<![A-Za-z0-9.-])"
QUOTED = r'(?P<quoted>"host"\s*:\s*")?'
MAC_END = r'(?(quoted)(?:\.local\b|(?="))|\.local\b)'
NOT_A_NAME = r'(?:(?:Pro|Air|mini|Studio)(?:-[0-9]+)?|[0-9]+)(?:\.local\b|")'
NAME = r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)"
MAC_HOST_MODEL_FIRST = re.compile(
    QUOTED + HOST_START + MAC_MODEL + r"-(?!" + NOT_A_NAME + r")" + NAME + MAC_END,
    re.IGNORECASE,
)
MAC_HOST_OWNER_FIRST = re.compile(
    QUOTED + HOST_START + r"(?P<name>[A-Za-z0-9][A-Za-z0-9-]*?)-" + MAC_MODEL
    + r"(?:-[0-9]+)?" + MAC_END,
    re.IGNORECASE,
)

# A domain opening the value of a JSON "host" field, followed by "rented" in
# any case.
RENTED_HOST = re.compile(
    r'("host"\s*:\s*")'
    r"([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,})"
    r"\s+(?i:rented)\b"
)


def text_files(target: Path) -> list[Path]:
    found = []
    for path in sorted(target.rglob("*")):
        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue
        if path.is_file() and path.suffix.lower() in TEXT_SUFFIXES:
            found.append(path)
    return found


def read(path: Path) -> str:
    """Read without translating line endings, so that a file this rewrites
    keeps the endings it had and only the name moves."""
    with path.open(encoding="utf-8", newline="") as handle:
        return handle.read()


def names_in(text: str) -> Counter[str]:
    return Counter(match.group(1) for match in HOME.finditer(text))


def hosts_in(text: str, allowed: set[str] | frozenset[str] = frozenset()) -> Counter[str]:
    """Each host name that names a person or a business, as written.

    The placeholder a rewrite leaves behind is not a name, so a rewritten
    export reads clean."""
    skip = set(allowed) | {PLACEHOLDER}
    found: Counter[str] = Counter()
    for pattern in (MAC_HOST_MODEL_FIRST, MAC_HOST_OWNER_FIRST):
        for match in pattern.finditer(text):
            if match.group("name") not in skip:
                found[match.group(0)[len(match.group("quoted") or ""):]] += 1
    for match in RENTED_HOST.finditer(text):
        if match.group(2) not in skip:
            found[match.group(2)] += 1
    return found


def _replace_group(match: re.Match[str], group: int | str, by: str) -> str:
    start, end = match.span(group)
    whole = match.group(0)
    return whole[: start - match.start()] + by + whole[end - match.start():]


def redact(text: str, allowed: set[str]) -> str:
    def name(group: int | str) -> Callable[[re.Match[str]], str]:
        def replace(match: re.Match[str]) -> str:
            if match.group(group) in allowed:
                return match.group(0)
            return _replace_group(match, group, PLACEHOLDER)

        return replace

    def rented(match: re.Match[str]) -> str:
        if match.group(2) in allowed:
            return match.group(0)
        return match.group(1) + "Rented"

    text = HOME.sub(name(1), text)
    text = MAC_HOST_MODEL_FIRST.sub(name("name"), text)
    text = MAC_HOST_OWNER_FIRST.sub(name("name"), text)
    return RENTED_HOST.sub(rented, text)


def survey(
    target: Path,
    allowed: set[str],
    finder: Callable[[str], Counter[str]] = names_in,
) -> dict[str, tuple[int, int]]:
    """Per finding, the number of files it appears in and of occurrences.

    The placeholder a rewrite leaves behind is not an account, so a rewritten
    export reads clean; an account genuinely named that would be missed."""
    allowed = allowed | {PLACEHOLDER}
    files: Counter[str] = Counter()
    occurrences: Counter[str] = Counter()
    for path in text_files(target):
        try:
            text = read(path)
        except (OSError, UnicodeDecodeError):
            continue
        counts = finder(text)
        for name, count in counts.items():
            if name in allowed:
                continue
            files[name] += 1
            occurrences[name] += count
    return {name: (files[name], occurrences[name]) for name in sorted(files)}


def write(target: Path, allowed: set[str]) -> list[Path]:
    changed = []
    for path in text_files(target):
        try:
            text = read(path)
        except (OSError, UnicodeDecodeError):
            continue
        replaced = redact(text, allowed)
        if replaced != text:
            with path.open("w", encoding="utf-8", newline="") as handle:
                handle.write(replaced)
            changed.append(path)
    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", type=Path, metavar="DIR", help="report and exit 1 on a finding")
    mode.add_argument("--write", type=Path, metavar="DIR", help="rewrite, then report")
    parser.add_argument(
        "--allow", action="append", default=[], metavar="NAME",
        help="an account, host or domain name that is not a finding; repeatable",
    )
    args = parser.parse_args(argv)

    target = (args.check or args.write).resolve()
    if not target.is_dir():
        print(f"{target} is not a directory", file=sys.stderr)
        return 2
    allowed = set(args.allow)

    if args.write is not None:
        if target == ROOT or ROOT in target.parents or target in ROOT.parents:
            print(
                "refusing to rewrite inside the record: a recorded run is never "
                "edited, and this runs on an export of it",
                file=sys.stderr,
            )
            return 2
        for path in write(target, allowed):
            print(f"rewrote {path.relative_to(target).as_posix()}")

    accounts = survey(target, allowed)
    hosts = survey(target, allowed, lambda text: hosts_in(text, allowed))
    for name, (files, occurrences) in accounts.items():
        print(f"{name}: {occurrences} occurrence(s) in {files} file(s)", file=sys.stderr)
    for name, (files, occurrences) in hosts.items():
        print(f"host {name}: {occurrences} occurrence(s) in {files} file(s)", file=sys.stderr)
    if accounts or hosts:
        print(
            f"\nsnapshot: {len(accounts)} account name(s) in home paths, "
            f"{len(hosts)} host name(s) naming a person or a business",
            file=sys.stderr,
        )
        return 1
    print("snapshot: no home path names an account and no host names a person or a business")
    return 0


if __name__ == "__main__":
    sys.exit(main())
