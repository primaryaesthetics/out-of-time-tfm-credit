#!/usr/bin/env python3
"""Sweep gate.

The expensive failure mode on this kind of project is not a wrong result. It is
a right result that somebody published while the work was in progress, and that
nobody looked for because the premise was set at the start and never
rechecked. That has already cost work on the predecessor projects. The
field this repository sits in moves monthly: TabPFN-2.5, TabICLv2 and LimiX-2M
all appeared inside a nine-month window.

So the literature sweep is a gate, not a habit. `docs/landscape/SWEEPS.md`
carries one dated entry per sweep, and this script fails when the newest entry
is older than the allowed age.

    python scripts/check_sweep.py            # 14 days
    python scripts/check_sweep.py --max-age 7
    python scripts/check_sweep.py --queries  # print the standing search list

A stale sweep does not block a commit that only cleans up code. It blocks
opening an experiment, writing a claim, and any public text - because each of
those asserts, implicitly, that the gap is still open.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SWEEPS = ROOT / "docs" / "landscape" / "SWEEPS.md"

HEADING = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\b")

# The standing list. A sweep runs all of it; anything new goes into
# docs/landscape/prior-art.md with a `verified` or `unverified` status, and
# anything that touches the premise goes into the sweep entry in words.
QUERIES = [
    "arXiv cs.LG + q-fin.RM listings: tabular foundation model credit / default / PD",
    "arXiv new since last sweep: TabPFN, TabICL, LimiX, tabular in-context learning",
    "calibration OR 'proper scoring' OR 'reliability diagram' + tabular foundation model",
    "'out-of-time' OR vintage OR 'temporal drift' + tabular foundation model",
    "population stability index OR PSI + critical values OR significance (new work)",
    "Prior Labs releases; TabICL repo releases; TabArena leaderboard changes",
    "Baesens / Lessmann / Verbeke / Bravo / Mues / Verdonck author pages and arXiv",
    "Edinburgh Credit Research Centre working papers; CRC conference programme",
    "PyPI: any package doing PSI critical values or PRS in Python",
    "GitHub: 'credit' + 'TabPFN' repos created since last sweep",
]


def newest_entry() -> tuple[dt.date, str] | None:
    if not SWEEPS.exists():
        return None
    for line in SWEEPS.read_text(encoding="utf-8").splitlines():
        if match := HEADING.match(line.strip()):
            try:
                return dt.date.fromisoformat(match.group(1)), line.strip()
            except ValueError:
                continue
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-age", type=int, default=14, help="days (default 14)")
    parser.add_argument("--queries", action="store_true", help="print the standing search list and exit")
    args = parser.parse_args()

    if args.queries:
        print("Standing sweep queries - run all of them:\n")
        for query in QUERIES:
            print(f"  - {query}")
        print(
            "\nRecord the result as a new `## <date>` section at the top of "
            f"{SWEEPS.relative_to(ROOT).as_posix()}, including the sweeps that "
            "found nothing: an empty sweep is evidence and a missing one is not."
        )
        return 0

    entry = newest_entry()
    if entry is None:
        print(
            f"sweep: {SWEEPS.relative_to(ROOT).as_posix()} has no dated entry. "
            "Run `python scripts/check_sweep.py --queries` and record one.",
            file=sys.stderr,
        )
        return 1

    date, heading = entry
    age = (dt.datetime.now().astimezone().date() - date).days
    if age > args.max_age:
        print(
            f"sweep: newest entry is {heading!r}, {age} days old, limit {args.max_age}.\n"
            "The premise of this repository is that a gap is open. That is a claim "
            "about the literature and it goes stale.\n"
            "Run `python scripts/check_sweep.py --queries`, do the sweep, record it.",
            file=sys.stderr,
        )
        return 1

    print(f"sweep: last run {date.isoformat()}, {age} days ago, within {args.max_age}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
