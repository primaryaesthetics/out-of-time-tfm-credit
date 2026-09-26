#!/usr/bin/env python3
"""Every figure of a drafted claim must come out of a place that row cites.

`check_claims.py` verifies that a row's evidence directory exists, was recorded
from a clean tree and pins its code. It never opens an output file, so a figure
read off the wrong row, the wrong build or the wrong key reaches the ledger
with every gate green. This closes that: for each drafted row it collects the
values reachable from the places the row's own provenance table names, and
reports every number in the Statement that none of them produces.

The provenance table is four columns — what the figure is, the file, the scope,
and where in the file. The last column is either line numbers into a CSV
(`245`, `338-340`, `3047, 3335`) or backticked key paths into a JSON
(`windows.12.relief_counts.label`). A file named without a locator degrades to
"the number appears somewhere in that file", which is weak and is reported as
such in the summary line.

Figures a run does not store but that follow from it by a named rule — a share
summed over a year's quarters, a difference between two recorded counts — are
admitted only through that rule. The rules live beside the draft, in a
`derivations.py` next to it exporting `derive(load, path) -> iterable[float]`,
where `load` resolves a key path in the run's summary. A draft with no such
file admits no derived figure.

A run that stores a pair the other way round from the Statement (`B - A` where
the text quotes `A − B`) is cited with `(reversed)` in the locator column:
`245, 248 (reversed)`. Every measure on those lines is then admitted negated,
and only negated, so the sign check still holds on them.

    python scripts/check_figures.py <draft>.md            # every row in it
    python scripts/check_figures.py <draft>.md C-014      # one row
    python scripts/check_figures.py <draft>.md --explain  # the places that bind each figure

A single figure binds to the row's cited places as a set: a figure flipped
onto a value another cited line holds is admitted by that line. An interval
is held to more. Every `v [lo, hi]` of the Statement, and every `[lo, hi]`
written without a figure before it, must be produced whole by one cited
place — one CSV line, one JSON object under a cited key path, the derived
values of one key path, or one line of a text file — at the written precision
and sign. Where the place names its bounds (`ci_lo` and `ci_hi`, `auc_min`
and `auc_max`, `cox_slope_lo` and `cox_slope_hi`, a two-element list `ci`)
they must come from one such pair, lower from lower and upper from upper,
and the figure from the pair's own column (`cox_slope`, `auc_mean`) or, when
the pair has none, from a column that is neither a bound nor another pair's
figure. Where it names none, each part must come from a column of its own.
Under `(reversed)` the pair turns over with its sign: the written lower bound
is the negated upper one. A bound taken from another line, or flipped onto the value
another line holds, fails here though each figure alone is admitted. An
interval with a figure that is unbound on its own is reported once, as that
figure.

`--explain` prints, under each row, every figure with the file, line and
column (or key path) that admits it, and every interval with the one place
that produces it whole. A figure admitted only by a line or column other than
the one its sentence quotes is bound by coincidence; the list is there so a
reader can see that without recomputing.

Exit code is non-zero when any row has a figure no cited place produces, or
an interval no single cited place produces, so a draft cannot reach the ledger
with an unbound number in it.
"""
from __future__ import annotations

import csv
import functools
import importlib.util
import itertools
import json
import pathlib
import re
import sys

# Columns that identify a row rather than measure it: a literal matching one of
# these is a label, not a figure, and admitting it would let any 2-digit number
# pass on a file with a seed column.
KEY_COLUMNS = frozenset({
    "arm", "cohorts", "draw", "scope", "metric", "pair", "is_difference",
    "alpha", "resamples", "seed", "excludes_zero", "reads_derived",
    "bootstrap_seed", "kind", "model", "build",
})
# Measures no Statement quotes. A standard error sits beside every value and
# interval of a paired table and, at three or four decimals, coincides with
# some other figure of the row often enough to admit it under either sign.
UNQUOTED_COLUMNS = frozenset({"se"})
REVERSED = re.compile(r"\(reversed\)")

SECTION = re.compile(r"^## (C-\d+)\s+—", re.MULTILINE)
EVIDENCE = re.compile(r"\*\*Evidence\*\*\s+`([^`]+)`")
PROVENANCE = re.compile(
    r"^\| (?!number|---)(?P<what>.+?) \| `?(?P<file>[\w./@-]+\.(?:csv|json|txt))`? \| "
    r"(?P<scope>.+?) \| (?P<where>.+?) \|$",
    re.MULTILINE)
# Every body line of a table in the row's section. One the provenance pattern
# does not read (two files in one cell, a missing column) would otherwise drop
# out silently, and the figures it was meant to bind would pass or fail on the
# other rows alone.
TABLE_ROW = re.compile(r"^\| (?!number|---).*\|$", re.MULTILINE)
KEY_PATH = re.compile(r"`([A-Za-z_][\w.]*)`")
LINE_SPEC = re.compile(r"(\d+)\s*[–—-]\s*(\d+)|(\d+)")
# A figure in prose: thousands-separated, decimal, or percentage, with the sign
# it is written with. A bare year and a cohort label (2007Q3) are neither. The
# signs read are `+` and the typographic minus this project writes its negative
# figures with; the hyphen is not one, because it names models (`GBM-50k`) and
# reading it as a sign would make every such name a negative figure.
MINUS = "−"
FIGURE = re.compile(rf"[+{MINUS}]?(?:\d[\d,]*\.\d+|\d[\d,]*(?:\.\d+)?%|\d[\d,]*)")
COHORT = re.compile(r"\b(19|20)\d{2}Q[1-4]\b")
# A date names a day, and its month and day pieces are not figures: read as
# figures they are reported unbound, or bound by any cited 09 or 12.
DATE = re.compile(r"\b(19|20)\d{2}-\d{2}(?:-\d{2})?(?!\d)")
# The base of a power of ten, as in 1.36 × 10⁻⁷.
POWER_BASE = re.compile(r"\A[⁻⁰¹²³⁴⁵⁶⁷⁸⁹^]")
YEAR = re.compile(r"^(19|20)\d{2}$")
# Digits inside a name are not figures: the 50 of `GBM-50k`, the 0006 of
# `ADR-0006`, the 2 of `2004H2`. Reported as unbound they are noise, and noise
# in this report teaches the reader to skim past the finding it exists for.
# `\Z` and not `$`: `$` also matches before a trailing newline, so a figure
# opening a wrapped line whose previous line ends in a letter would be read as
# a name digit and never checked at all — the checker would report fewer
# figures than the statement holds and call itself green.
NAME_LEFT = re.compile(r"[A-Za-z]-?\Z")
NAME_RIGHT = re.compile(r"\A[A-Za-z]")
# "the 95th percentile" counts nothing; it names a place in an order.
ORDINAL = re.compile(r"\d(?:st|nd|rd|th)\b")
# The longest run of lines a range may expand to. A wider one is read as two
# endpoints rather than as every line between them, so a careless "1-99999"
# cannot admit a whole file.
MAX_RANGE = 400
# An interval as this project writes it: `−0.0412 [−0.0885, +0.0181]`, the
# bounds alone `[+0.0012, +0.0040]`, or a percentage `1.919% [1.795, 2.052]`.
# An `&` between the figure and the bracket is a LaTeX table's cell boundary,
# a value column beside an interval column. The figure may not continue a name
# or a number (`2014H1 [`, `GBM-50 [`); the bounds are then read alone.
NUMBER = rf"[+{MINUS}-]?\d+(?:,\d{{3}})*(?:\.\d+)?%?"
INTERVAL = re.compile(
    rf"(?:(?<![\w.,{MINUS}+-])(?P<value>{NUMBER})\s*(?:&\s*)?)?"
    rf"\[\s*(?P<lo>{NUMBER})\s*,\s*(?P<hi>{NUMBER})\s*\]")
# A named pair of bounds in a CSV header: `ci_lo`/`ci_hi`, `auc_min`/`auc_max`.
BOUND = re.compile(r"^(?P<prefix>.+)_(?P<end>lo|hi|min|max|lower|upper)$")
UPPER_OF = {"lo": "hi", "min": "max", "lower": "upper"}


def token(written: str) -> str:
    """A written figure as `figures` reads it: ASCII sign, no percent."""
    return written.replace(MINUS, "-").rstrip("%")


def intervals(text: str) -> list[tuple[str | None, str, str, str, int]]:
    """(figure or None, lower, upper, as written, offset) for every interval of a text."""
    return [(token(m.group("value")) if m.group("value") else None,
             token(m.group("lo")), token(m.group("hi")), " ".join(m.group(0).split()),
             m.start())
            for m in INTERVAL.finditer(text)]


def bound_pairs(columns) -> list[tuple[str, str, list[str]]]:
    """(lower, upper, figure columns) for every named pair of bounds among columns.

    A pair is named in a CSV header (`ci_lo` and `ci_hi`, `auc_min` and
    `auc_max`) or is a two-element list of a JSON record (`ci.0` and `ci.1`).
    The figure of a pair is its own column (`cox_slope` beside `cox_slope_lo`),
    or its mean (`auc_mean` beside `auc_min`); a pair with neither, as `ci_lo`
    and `ci_hi` beside `value`, takes any column that is neither a bound nor
    another pair's own figure.
    """
    names = list(columns)
    pairs = []
    for name in names:
        match = BOUND.match(name)
        if match and match.group("end") in UPPER_OF:
            prefix = match.group("prefix")
            upper = f"{prefix}_{UPPER_OF[match.group('end')]}"
            if upper in columns:
                pairs.append((name, upper, prefix))
        elif name.endswith(".0"):
            prefix = name[:-2]
            if f"{prefix}.1" in columns and f"{prefix}.2" not in columns:
                pairs.append((name, f"{prefix}.1", prefix))
    owned = {}
    for _, _, prefix in pairs:
        own = [c for c in (prefix, f"{prefix}_mean") if c in columns]
        if own:
            owned[prefix] = own[0]
    taken = {c for lower, upper, _ in pairs for c in (lower, upper)} | set(owned.values())
    return [(lower, upper, [owned[prefix]] if prefix in owned
             else [c for c in names if c not in taken])
            for lower, upper, prefix in pairs]


def json_records(node, path: str) -> dict[str, dict[str, float]]:
    """The numbers under a JSON node, grouped by the object that holds them.

    An object is one record: its numbers and the numbers of its lists (`ci`
    as `ci.0` and `ci.1`). An object nested in it, or in one of its lists, is
    a record of its own, so an interval cannot take its figure from one
    object and a bound from its neighbour. Objects stored as columns — sibling
    objects keyed alike, `{"rate": {"2013Q4": r}, "interval": {"2013Q4":
    [lo, hi]}}` — also make one record per shared key, `[2013Q4]`, joining
    the columns as a row.
    """
    out: dict[str, dict[str, float]] = {}

    def walk(value, owner: str, key: str) -> None:
        if isinstance(value, dict):
            here = f"{owner}.{key}" if owner and key else (key or owner)
            for child_key, child in value.items():
                if isinstance(child, (dict, list)):
                    walk(child, here, str(child_key))
                else:
                    put(here, str(child_key), child)
            columns = {str(k): v for k, v in value.items() if isinstance(v, dict)}
            shared: dict[str, int] = {}
            for column in columns.values():
                for row in column:
                    shared[row] = shared.get(row, 0) + 1
            for row, count in shared.items():
                if count < 2:
                    continue
                joined = f"{here}[{row}]"
                for name, column in columns.items():
                    cell = column.get(row)
                    if isinstance(cell, list):
                        for index, item in enumerate(cell):
                            put(joined, f"{name}.{index}", item)
                    else:
                        put(joined, name, cell)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                name = f"{key}.{index}" if key else str(index)
                if isinstance(child, (dict, list)):
                    walk(child, owner, name)
                else:
                    put(owner, name, child)
        else:
            put(owner, key or "value", value)

    def put(owner: str, key: str, value) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out.setdefault(owner, {})[key] = float(value)

    walk(node, path, "")
    return out


class Place:
    """One cited place an interval may come from whole: a CSV line or a JSON object."""

    def __init__(self, label: str, values: dict[str, float], reversed_: bool = False):
        self.label = label
        self.values = values
        self.pairs = bound_pairs(values)
        if reversed_:
            # B − A read as A − B: the lower bound of the text is the stored
            # upper bound negated. The values are already negated.
            self.pairs = [(upper, lower, own) for lower, upper, own in self.pairs]

    def produces(self, figure: str | None, lo: str, hi: str,
                 admits) -> str | None:
        """The columns that produce the interval, or None.

        `admits(written, value)` decides whether a written figure is a form of
        a stored value; the two gates differ only there.
        """
        if self.pairs:
            for lower, upper, own in self.pairs:
                if not (admits(lo, self.values[lower]) and admits(hi, self.values[upper])):
                    continue
                if figure is None:
                    return f"{lower}/{upper}"
                for column in own:
                    if admits(figure, self.values[column]):
                        return f"{column}/{lower}/{upper}"
            return None
        # No named bounds: each part from a column of its own in this one place.
        parts = ([figure] if figure is not None else []) + [lo, hi]
        candidates = [[c for c, v in self.values.items() if admits(written, v)]
                      for written in parts]
        for columns in itertools.product(*candidates):
            if len(set(columns)) == len(columns):
                return "/".join(columns) + " (no named bounds)"
        return None


@functools.cache
def plain_forms(value: float) -> frozenset[str]:
    return frozenset(form.replace(",", "") for form in forms(value))


def form_admits(written: str, value: float) -> bool:
    return written.replace(",", "") in plain_forms(value)


def forms(value: float) -> set[str]:
    """Every way a figure of this project may legitimately write a value.

    A value of zero or above is written bare or under `+`; a negative value
    only under its minus. Nearly every figure of this study is a signed
    difference, and a value taken from the row with the opposite sign is the
    error this checker exists for: a bare magnitude read as a negative value
    would let `[0.0054, +0.0786]` stand for a stored `[−0.0054, +0.0786]`,
    an interval that holds zero written as one that excludes it.
    """
    signs = ("+", "-") if value == 0 else ("-" if value < 0 else "+",)
    out: set[str] = set()
    for scaled in (abs(value), abs(value) * 100):
        written: set[str] = set()
        if abs(scaled - round(scaled)) < 1e-9:
            written.add(f"{round(scaled):,}")
            written.add(str(round(scaled)))
        for places in range(1, 7):
            written.add(f"{scaled:.{places}f}")
            written.add(f"{scaled:.{places}f}".rstrip("0").rstrip("."))
        if value >= 0:
            out |= written
        out |= {sign + form for sign in signs for form in written}
    return out


def scalars(node, out: set[float]) -> None:
    if isinstance(node, dict):
        for value in node.values():
            scalars(value, out)
    elif isinstance(node, list):
        for value in node:
            scalars(value, out)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        out.add(float(node))


def figures(statement: str) -> list[str]:
    text = DATE.sub(" ", COHORT.sub(" ", statement))
    found = []
    for match in FIGURE.finditer(text):
        token = match.group(0).rstrip("%").rstrip(",").replace(MINUS, "-")
        if YEAR.match(token.lstrip("+-")):
            continue
        if token == "10" and POWER_BASE.match(text[match.end():]):
            continue
        if ORDINAL.match(text[match.end() - 1:match.end() + 2]):
            continue
        if NAME_LEFT.search(text[:match.start()]) or NAME_RIGHT.match(text[match.end():]):
            continue
        found.append(token)
    return sorted(set(found), key=lambda s: (-len(s), s))


def line_numbers(spec: str) -> list[int]:
    out: list[int] = []
    for match in LINE_SPEC.finditer(spec):
        if match.group(3):
            out.append(int(match.group(3)))
            continue
        low, high = int(match.group(1)), int(match.group(2))
        out.extend(range(low, high + 1) if 0 < high - low <= MAX_RANGE else (low, high))
    return out


def resolve_path(summary, path: str):
    node = summary
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def load_derivations(draft: pathlib.Path):
    module_path = draft.parent / "derivations.py"
    if not module_path.exists():
        return None
    spec = importlib.util.spec_from_file_location("derivations", module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, "derive", None)


def find_file(evidence: pathlib.Path, name: str) -> pathlib.Path | None:
    for candidate in (evidence / name, pathlib.Path("experiments") / name,
                      pathlib.Path(name)):
        if candidate.exists():
            return candidate
    return None


def check_row(draft: pathlib.Path, text: str, row_id: str, derive,
              explain: bool = False) -> int:
    section = text.split(f"## {row_id} —", 1)[1].split("\n## ", 1)[0]
    statement = section.split("**Statement.**", 1)[1].split("**Setting.**", 1)[0]
    evidence_match = EVIDENCE.search(section)
    if not evidence_match:
        print(f"{row_id}: no Evidence pointer")
        return 1
    evidence = pathlib.Path(evidence_match.group(1))

    # Written form, without thousands separators -> the places that produce it.
    admissible: dict[str, list[str]] = {}

    def admit(value: float, source: str) -> None:
        for form in forms(value):
            admissible.setdefault(form.replace(",", ""), []).append(source)

    # Each cited place as a unit, for the intervals that must come from one.
    places: list[Place] = []
    cited_lines = 0
    whole_files: list[str] = []
    problems: list[str] = []
    summaries: dict[str, object] = {}

    rows = list(PROVENANCE.finditer(section))
    if not rows:
        # A table this parser cannot read would otherwise report every figure
        # as unbound, which reads like a finding and is a misconfiguration.
        print(f"{row_id}: no provenance table read — check the table's columns")
        return 1
    read = {row.group(0) for row in rows}
    for line in TABLE_ROW.findall(section):
        if line not in read:
            problems.append(f"  provenance row not read: {line[:100]}")
    for row in rows:
        name, where = row.group("file"), row.group("where")
        path = find_file(evidence, name)
        if path is None:
            problems.append(f"  cited file absent: {name}")
            continue
        if path.suffix == ".json":
            if name not in summaries:
                summaries[name] = json.loads(path.read_text(encoding="utf-8"))
            document = summaries[name]
            paths = KEY_PATH.findall(where)
            if not paths:
                whole_files.append(name)
                values: set[float] = set()
                scalars(document, values)
                for value in values:
                    admit(value, f"{name} (whole file)")
                for owner, record in json_records(document, "").items():
                    places.append(Place(f"{name} :: {owner or '(top)'} (whole file)", record))
                continue
            for key_path in paths:
                node = resolve_path(document, key_path)
                if node is None:
                    problems.append(f"  cited key path absent: {name} :: {key_path}")
                    continue
                values = set()
                scalars(node, values)
                for value in values:
                    admit(value, f"{name} :: {key_path}")
                for owner, record in json_records(node, key_path).items():
                    places.append(Place(f"{name} :: {owner}", record))
                if derive is not None:
                    derived: dict[str, float] = {}
                    for index, value in enumerate(
                            derive(lambda p, d=document: resolve_path(d, p), key_path)):
                        admit(float(value), f"{name} :: {key_path} (derived)")
                        derived[str(index)] = float(value)
                    places.append(Place(f"{name} :: {key_path} (derived)", derived))
            continue
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        if path.suffix != ".csv":
            whole_files.append(name)
            for number, line in enumerate(lines, start=1):
                found_here = re.findall(r"-?\d+\.\d+(?:[eE][-+]?\d+)?", line)
                for value in found_here:
                    admit(float(value), f"{name} (whole file)")
                if found_here:
                    places.append(Place(f"{name} l.{number} (whole file)",
                                        {str(i): float(v) for i, v in enumerate(found_here)}))
            continue
        header = next(csv.reader([lines[0]]))
        sign = -1.0 if REVERSED.search(where) else 1.0
        for number in line_numbers(where):
            if number > len(lines):
                problems.append(f"  cited line out of range: {name} l.{number}")
                continue
            cited_lines += 1
            record = dict(zip(header, next(csv.reader([lines[number - 1]]))))
            measures: dict[str, float] = {}
            for column, value in record.items():
                if column in KEY_COLUMNS or column in UNQUOTED_COLUMNS or not value:
                    continue
                try:
                    measure = float(value)
                except ValueError:
                    continue
                admit(sign * measure,
                      f"{name} l.{number} {column}" + (" negated" if sign < 0 else ""))
                measures[column] = sign * measure
            places.append(Place(f"{name} l.{number}" + (" reversed" if sign < 0 else ""),
                                measures, reversed_=sign < 0))

    found = figures(statement)
    missing = [f for f in found if f.replace(",", "") not in admissible]
    # An interval whose figures are each admitted must also come from one place.
    whole: list[tuple[str, list[str]]] = []
    split: list[str] = []
    for figure, lo, hi, written, _ in intervals(statement):
        if any(part.replace(",", "") not in admissible
               for part in (figure, lo, hi) if part is not None):
            continue
        producers = [f"{place.label} {columns}" for place in places
                     if (columns := place.produces(figure, lo, hi, form_admits))]
        if producers:
            whole.append((written, producers))
        else:
            split.append(written)
    print(f"{row_id}: {len(found)} figures, {cited_lines} CSV lines and "
          f"{len(whole_files)} whole files cited, {len(missing)} unbound, "
          f"{len(split)} of {len(whole) + len(split)} intervals not from one place")
    for problem in problems:
        print(problem)
    for figure in missing:
        sentences = [s.strip() for s in re.split(r"(?<=[.;]) ", " ".join(statement.split()))
                     if figure in s]
        print(f"  unbound: {figure}   ...{sentences[0][:110] if sentences else ''}")
    for written in split:
        print(f"  interval not from one place: {written}")
    if explain:
        for figure in found:
            sources = admissible.get(figure.replace(",", ""))
            if sources:
                shown = "; ".join(dict.fromkeys(sources))
                print(f"  bound: {figure}  <- {shown}")
        for written, producers in whole:
            print(f"  interval: {written}  <- {'; '.join(producers)}")
    return len(missing) + len(problems) + len(split)


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--explain"]
    explain = len(args) < len(sys.argv) - 1
    if not args:
        sys.exit(__doc__)
    draft = pathlib.Path(args[0])
    text = draft.read_text(encoding="utf-8")
    wanted = args[1:] or SECTION.findall(text)
    if not wanted:
        sys.exit(f"{draft}: no rows found")
    derive = load_derivations(draft)
    return sum(check_row(draft, text, row_id, derive, explain) for row_id in wanted)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(1 if main() else 0)
