#!/usr/bin/env python3
"""Every figure in the paper's text must come from the source its marker names.

`check_figures.py` binds a ledger row's figures to the run the row cites. The
paper is one step further out: its sentences quote ledger rows, the
pre-registrations and the papers of the landscape, and a figure copied from
the wrong row, rounded, or given the other sign reaches the PDF with every
other gate green. This closes that for the LaTeX sources.

A sentence carrying a figure is preceded by a marker comment naming where its
figures come from:

    % FIG: C-023, C-028
    % FIG: EXP-002 §Setting (label window)
    % FIG: arXiv:2605.18147
    % FIG: vintage.CONTEXT_ROWS, EXP-004 §Setting
    % FIG: none (count words only)

A marker covers the lines after it up to the next marker or the next blank
line. Its references are the tokens below, anywhere in the marker; every
other word is a note to the reader and binds nothing.

| Token | Binds to |
| --- | --- |
| `C-NNN` | the Statement of that ledger row; a superseded row is refused |
| `EXP-NNN` | the pre-registration `docs/experiments/EXP-NNN-*.md` |
| `EXP-NNN-log` | the book's log `docs/experiments/EXP-NNN-log.md` |
| `§Heading` after a document | only that document's section whose heading contains the words; `§"…"` for a heading with a comma |
| `ADR-NNNN` | `docs/decisions/ADR-NNNN-*.md` |
| `arXiv:NNNN.NNNNN`, `SSRN NNNNNNN` | the lines of `docs/landscape/prior-art.md` naming that paper |
| `prior-art:Word` | the rows of `prior-art.md` whose first cell holds that word |
| `module.CONSTANT` | the assignment of that constant in `src/outoftime/module.py` |
| a `refs.bib` key | that bibliography entry |
| `none` | nothing: the lines must carry no figure |
| `experiments/<run>/<file>.csv` or `.json` | the values of that file of a recorded run, in any rounding |

The last is for a table printed from a run rather than quoted from the
ledger. A run file holds every value of its run, so a figure found there is
bound only loosely; the run must carry a manifest from a clean tree with exit
code zero, and the table's generator is what places each value in its cell.

A landscape row binds only when its status is verified; an abstract-only,
secondary or README-only row is refused, since an abstract is not a source.

A ledger row binds by its own text, not by the run behind it: the ledger is
the index every published number goes through, and the text quotes the row,
literally. Only the Statement binds: `check_figures.py` ties a Statement's
figures to the run and reads no Setting, so a figure found only in a Setting
has passed no gate. A design constant is cited from its pre-registration. A figure matches only as written there — the same digits, no
rounding — and under the same sign: a figure the source writes negative must
be written negative, and one written unsigned or positive in the source may
not be written negative. A document-wide reference (a document named without
`§`) is weaker than a row, and the summary line counts the figures that bound
only that way.

What a figure is, and what is a name or a date, is `check_figures.figures`,
applied after the LaTeX is reduced to the text it prints: `$`, `{,}`, `\\%`,
`--`, the argument of every referencing command and a table's structure (the
span of `\\multicolumn`, the columns of `\\cmidrule`, a `p{3.4cm}` width) are
removed, and a hyphen
before a digit inside math is read as a minus. A power of ten — 8.4 × 10⁻³,
`$8.4\\times10^{-3}$`, 1e-6 — is one figure, mantissa and exponent together.
Numbers spelled as words are not figures and are not checked.

A figure binds to its marker's sources as a set; an interval is held to more.
Every `v [lo, hi]` — `$-0.0412$ $[-0.0885, +0.0181]$`, or a table's value
cell and interval cell side by side, `$+0.0092$ & $[+0.0083, +0.0103]$` — and
every `[lo, hi]` written alone must be written whole by one place: one
interval of a source's text, figure with figure and bound with bound, or one
row of a run file (one object of a JSON one), its bounds a named pair of that
row (`auc_min` and `auc_max`, `ci_lo` and `ci_hi`) and its figure that pair's
own column (`auc_mean`). Each part is held to the same digits and sign as a lone
figure. A bound flipped onto a figure another interval of the row writes, or
taken from the next interval, passes the set and fails here. The lines under
a marker are read together for this, so an interval wrapped across two lines
is still one interval. An interval with a part that is unbound on its own is
reported once, as that part.

    python scripts/check_paper_figures.py sections/*.tex
    python scripts/check_paper_figures.py <file>.tex --explain   # what binds each figure

`--explain` also names, for every interval, the one place that writes it whole.

Exit code is non-zero when any figure or interval is unbound, any marker
names a source that does not resolve, or any figure stands under no marker or
under a marker that names no source. A marker naming no source over lines with no figure is
a note and passes.
"""
from __future__ import annotations

import csv
import functools
import importlib.util
import json
import math
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
LEDGER = ROOT / "docs" / "ledger" / "CLAIMS.md"
EXPERIMENTS = ROOT / "docs" / "experiments"
DECISIONS = ROOT / "docs" / "decisions"
PRIOR_ART = ROOT / "docs" / "landscape" / "prior-art.md"
PACKAGE = ROOT / "src" / "outoftime"

_SPEC = importlib.util.spec_from_file_location(
    "check_figures", ROOT / "scripts" / "check_figures.py")
check_figures = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_figures)
MINUS = check_figures.MINUS

MARKER = re.compile(r"^\s*%\s*FIG:\s*(?P<body>.*)$")
CLAIM = re.compile(r"\bC-\d{3}\b")
DOCUMENT = re.compile(r"\b(?P<doc>EXP-\d{3}(?:-log)?|ADR-\d{4})\b"
                      r"(?:\s+§(?:\"(?P<quoted>[^\"]+)\"|(?P<heading>[^,;()§]+)))?")
PAPER = re.compile(r"\barXiv:(\d{4}\.\d{4,5})\b|\bSSRN\s+(\d{6,8})\b")
# A landscape row with no arXiv or SSRN number, named by a word of its first cell.
ROW_NAME = re.compile(r"\bprior-art:([\w\-]+)")
# A landscape row read from its abstract, a README or a summary is not a
# source for a figure; only a row whose status opens with "verified" is.
VERIFIED = re.compile(r"^\**verified\b", re.IGNORECASE)
# The landscape writes context sizes as 1K and 50K; the text writes them out.
THOUSANDS = re.compile(r"\b(\d+)K\b")
CONSTANT = re.compile(r"\b([a-z_][a-z0-9_]*)\.([A-Z][A-Z0-9_]+)\b")
BIB_KEY = re.compile(r"\b[a-z]+\d{4}[a-z]+\b")
NONE = re.compile(r"^\s*none\b", re.IGNORECASE)
HEADING = re.compile(r"^(#+)\s+(.*)$")
RUN_FILE = re.compile(r"\bexperiments/[\w.\-]+/[\w.\-]+\.(?:csv|json)\b")
# A table's structure carries digits that print nothing a reader counts: the
# span of a merged cell, the columns a rule runs under, a column's width.
STRUCTURE = re.compile(
    r"\\(?:multicolumn|multirow)\{\d+\}"
    r"|\\(?:cmidrule|cline)(?:\([^)]*\))?\{[\d\-]+\}"
    r"|\\(?:hspace|vspace|setlength|rule|arraystretch)\*?(?:\{[^}]*\})+"
    r"|\b[pmb]\{[\d.]+(?:cm|mm|pt|em|ex|in)\}"
    r"|\\\\\[[^\]]*\]")

# Commands whose (first) argument is a key or a path, never printed text.
KEY_COMMANDS = re.compile(
    r"\\(?:label|ref|eqref|autoref|cref|Cref|pageref|cite|citep|citet|citealp|"
    r"citeauthor|citeyear|selfcitet|href|url|includegraphics|input|include|"
    r"bibliography|bibliographystyle|begin|end)\*?(?:\[[^\]]*\])?\{[^}]*\}")


def printed(line: str) -> str:
    """The text a LaTeX line prints, as far as its figures are concerned."""
    line = re.sub(r"(?<!\\)%.*$", "", line)
    line = KEY_COMMANDS.sub(" ", line)
    line = STRUCTURE.sub(" ", line)
    line = line.replace("{,}", ",").replace("\\%", "%")
    line = re.sub(r"(?<=\d)\\,(?=\d)", "", line)
    line = line.replace("\\,", " ").replace("~", " ")
    line = line.replace("\\textminus", MINUS).replace("\\textpm", "±")
    line = line.replace("---", "—").replace("--", "–")

    def math(match: re.Match) -> str:
        body = match.group(1)
        body = re.sub(r"10\^\{?([-−]?\d+)\}?",
                      lambda m: "10" + m.group(1).translate(SUPERSCRIPT), body)
        body = re.sub(r"\\(?:times|cdot)", "×", body)
        body = re.sub(r"(?<![\w)\]}])-(?=\s*\d)", MINUS, body)
        body = re.sub(r"\\(?:,|;|!|quad|qquad)", " ", body)
        return " " + body + " "

    line = re.sub(r"\$([^$]*)\$", math, line)
    return line


SUPERSCRIPT = str.maketrans("-−0123456789", "⁻⁻⁰¹²³⁴⁵⁶⁷⁸⁹")
PLAIN = str.maketrans("⁻⁰¹²³⁴⁵⁶⁷⁸⁹", "-0123456789")
# A power of ten, written as 8.4 × 10⁻³, 10⁻⁶ or 1e-6. Its mantissa and its
# exponent are one figure: read apart, the mantissa of 8.4 × 10⁻⁴ would bind
# to a source that holds only 8.4 × 10⁻³.
POWER = re.compile(r"(?:(?P<mantissa>\d+(?:\.\d+)?)\s*×\s*)?10(?P<exponent>[⁻]?[⁰¹²³⁴⁵⁶⁷⁸⁹]+)"
                   r"|(?<![\w.])(?P<m2>\d+(?:\.\d+)?)e(?P<e2>[-+]?\d+)\b")


def powers(text: str) -> tuple[list[str], str]:
    """The powers of ten in a text, as `mantissa e exponent`, and the text without them."""
    found: list[str] = []

    def take(match: re.Match) -> str:
        if match.group("exponent"):
            mantissa = match.group("mantissa") or "1"
            exponent = int(match.group("exponent").translate(PLAIN))
        else:
            mantissa, exponent = match.group("m2"), int(match.group("e2"))
        found.append(f"{mantissa}e{exponent}")
        return " "

    return found, POWER.sub(take, text)


def split_sign(token: str) -> tuple[str, str]:
    if token[:1] in "+-":
        return token[0], token[1:]
    return "", token


class Sources:
    """Resolves marker references to the text they bind."""

    def __init__(self, bib: pathlib.Path | None = None):
        self.rows, self.settings, self.status = self._ledger()
        self.bib = bib
        self._bib_entries: dict[str, str] | None = None

    @staticmethod
    def _ledger() -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """Statement (what binds a figure), Setting (read, never bound) and status."""
        rows: dict[str, str] = {}
        settings: dict[str, str] = {}
        status: dict[str, str] = {}
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) >= 5 and re.fullmatch(r"C-\d{3}", cells[0]):
                rows[cells[0]] = cells[1]
                settings[cells[0]] = cells[2]
                status[cells[0]] = cells[4]
        return rows, settings, status

    def bib_entries(self) -> dict[str, str]:
        if self._bib_entries is None:
            self._bib_entries = {}
            if self.bib and self.bib.exists():
                text = self.bib.read_text(encoding="utf-8")
                for match in re.finditer(r"@\w+\{([^,]+),(.*?)(?=^@|\Z)", text, re.DOTALL | re.MULTILINE):
                    self._bib_entries[match.group(1).strip()] = match.group(2)
        return self._bib_entries

    def document(self, doc: str, heading: str | None) -> tuple[str | None, str]:
        if doc.startswith("ADR-"):
            found = sorted(DECISIONS.glob(f"{doc}-*.md"))
        elif doc.endswith("-log"):
            found = [EXPERIMENTS / f"{doc}.md"]
        else:
            found = [p for p in sorted(EXPERIMENTS.glob(f"{doc}-*.md"))
                     if not p.name.endswith("-log.md")]
        found = [p for p in found if p.exists()]
        if not found:
            return None, f"{doc}: no such document"
        text = found[0].read_text(encoding="utf-8")
        if heading is None:
            return text, ""
        wanted = heading.strip().lower()
        lines = text.splitlines()
        for start, line in enumerate(lines):
            head = HEADING.match(line)
            if head and wanted in head.group(2).lower():
                level = len(head.group(1))
                end = len(lines)
                for later in range(start + 1, len(lines)):
                    other = HEADING.match(lines[later])
                    if other and len(other.group(1)) <= level:
                        end = later
                        break
                return "\n".join(lines[start:end]), ""
        return None, f"{doc} §{heading.strip()}: no such heading"

    def paper(self, ident: str, first_cell: bool = False) -> tuple[str | None, str]:
        lines = [line for line in PRIOR_ART.read_text(encoding="utf-8").splitlines()
                 if line.startswith("|") and ident in
                 (line.strip("|").split("|")[0] if first_cell else line)]
        if not lines:
            return None, f"{ident}: not in prior-art.md"
        verified = [line for line in lines if VERIFIED.match(
            line.strip().strip("|").split("|")[-1].strip())]
        if not verified:
            status = lines[0].strip().strip("|").split("|")[-1].strip()
            return None, f"{ident}: the row is not verified ({status[:40]})"
        text = "\n".join(verified)
        return THOUSANDS.sub(lambda m: f"{int(m.group(1)) * 1000:,}", text), ""

    def constant(self, module: str, name: str) -> tuple[str | None, str]:
        path = PACKAGE / f"{module}.py"
        if not path.exists():
            return None, f"{module}.{name}: no module src/outoftime/{module}.py"
        for line in path.read_text(encoding="utf-8").splitlines():
            if re.match(rf"^{name}\s*(?::[^=]+)?=", line):
                return line.replace("_", ","), ""
        return None, f"{module}.{name}: no such constant"

    def resolve(self, body: str) -> tuple[list[tuple[str, str, bool]], list[str], bool]:
        """(label, text, document-wide) per reference; errors; whether `none`."""
        refs: list[tuple[str, str, bool]] = []
        errors: list[str] = []
        if NONE.match(body):
            return refs, errors, True
        for claim in CLAIM.findall(body):
            if claim not in self.rows:
                errors.append(f"{claim}: not in the ledger")
            elif self.status[claim] != "active":
                errors.append(f"{claim}: {self.status[claim]}; cite the successor")
            else:
                refs.append((claim, self.rows[claim], False))
        for match in DOCUMENT.finditer(body):
            doc, heading = match.group("doc"), match.group("heading")
            if heading:
                heading = re.split(r"\s+(?:and|with)\s+", heading)[0].strip()
            if match.group("quoted"):
                heading = match.group("quoted")
            text, error = self.document(doc, heading)
            if text is None:
                errors.append(error)
            else:
                label = doc + (f" §{heading.strip()}" if heading else "")
                refs.append((label, text, heading is None))
        for match in PAPER.finditer(body):
            ident = f"arXiv:{match.group(1)}" if match.group(1) else f"SSRN {match.group(2)}"
            text, error = self.paper(ident)
            if text is None:
                errors.append(error)
            else:
                refs.append((ident, text, False))
        for word in ROW_NAME.findall(body):
            text, error = self.paper(word, first_cell=True)
            if text is None:
                errors.append(error)
            else:
                refs.append((f"prior-art:{word}", text, False))
        for module, name in CONSTANT.findall(body):
            text, error = self.constant(module, name)
            if text is None:
                errors.append(error)
            else:
                refs.append((f"{module}.{name}", text, False))
        entries = self.bib_entries()
        for key in BIB_KEY.findall(body):
            if key in entries:
                refs.append((key, entries[key], False))
        for name in RUN_FILE.findall(body):
            text, error = run_file(ROOT / name)
            if text is None:
                errors.append(error)
            else:
                refs.append((name, text, True))
        return refs, errors, False


def run_file(path: pathlib.Path) -> tuple[str | None, str]:
    """Every way a figure may write a value of a recorded run's file, as text.

    A table printed from a run rounds what the run stores, so the value is
    admitted in each of its roundings (`check_figures.forms`), under its own
    sign; a column that names a row rather than measuring it is not read. The
    run must be recorded: a manifest, a clean tree, exit code zero.
    """
    if not path.exists():
        return None, f"{path.relative_to(ROOT).as_posix()}: no such file"
    manifest = path.parent / "manifest.json"
    if not manifest.exists():
        return None, f"{path.parent.name}: not a recorded run (no manifest)"
    recorded = json.loads(manifest.read_text(encoding="utf-8"))
    if recorded.get("git_dirty") or recorded.get("exit_code") != 0:
        return None, f"{path.parent.name}: recorded from a dirty tree or a failed run"
    values: set[float] = set()
    if path.suffix == ".json":
        check_figures.scalars(json.loads(path.read_text(encoding="utf-8")), values)
    else:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                for column, cell in row.items():
                    if column in check_figures.KEY_COLUMNS or column in check_figures.UNQUOTED_COLUMNS:
                        continue
                    try:
                        values.add(float(cell))
                    except (TypeError, ValueError):
                        continue
    forms: set[str] = set()
    for value in values:
        if math.isnan(value) or abs(value) == float("inf"):
            continue
        written = check_figures.forms(value)
        # A negative value is admitted only written negative, as a ledger
        # figure is; its bare magnitude would let `+x` and `x` bind to `-x`.
        forms |= {form for form in written if form.startswith("-")} if value < 0 else written
    return " ; ".join(sorted(form.replace("-", MINUS) for form in forms)), ""


def admits(token: str, source: list[str]) -> bool:
    """Whether a figure of the text is written, with its sign, in the source."""
    sign, magnitude = split_sign(token)
    for other in source:
        other_sign, other_magnitude = split_sign(other)
        if other_magnitude != magnitude:
            continue
        if sign == "-" and other_sign == "-":
            return True
        if sign in ("", "+") and other_sign in ("", "+"):
            return True
    return False


@functools.cache
def source_figures(text: str) -> tuple[str, ...]:
    found, rest = powers(text)
    return tuple(found) + tuple(check_figures.figures(rest))


@functools.cache
def source_intervals(text: str) -> tuple[tuple[str | None, str, str, str], ...]:
    return tuple((figure, lo, hi, written)
                 for figure, lo, hi, written, _ in check_figures.intervals(text))


@functools.cache
def run_value_forms(value: float) -> tuple[str, ...]:
    """The written forms of a run's value, negative ones only under their sign."""
    written = check_figures.forms(value)
    if value < 0:
        written = {form for form in written if form.startswith("-")}
    return tuple(written)


def run_admits(written: str, value: float) -> bool:
    return admits(written, list(run_value_forms(value)))


@functools.cache
def run_places(path: pathlib.Path) -> tuple[check_figures.Place, ...]:
    """A run file's rows, each a place an interval may come from whole."""
    if path.suffix == ".json":
        records = check_figures.json_records(json.loads(path.read_text(encoding="utf-8")), "")
        return tuple(check_figures.Place(f"{path.name} {owner or '(top)'}", record)
                     for owner, record in records.items())
    places = []
    with path.open(encoding="utf-8", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle), start=2):
            values: dict[str, float] = {}
            for column, cell in row.items():
                if column in check_figures.KEY_COLUMNS or column in check_figures.UNQUOTED_COLUMNS:
                    continue
                try:
                    value = float(cell)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(value):
                    values[column] = value
            places.append(check_figures.Place(f"{path.name} l.{number}", values))
    return tuple(places)


def interval_source(figure: str | None, lo: str, hi: str,
                    refs: list[tuple[str, str, bool]]) -> str | None:
    """The one place of the marker's sources that writes the interval whole.

    A text source binds an interval only through an interval it writes itself,
    figure with figure, lower bound with lower and upper with upper. Bounds
    the paper writes alone may be taken from an interval the source writes
    with its figure; a figure the paper writes before the bounds must be the
    one the source writes before them. A run file binds it through one of its
    rows.
    """
    for label, text, _ in refs:
        if RUN_FILE.fullmatch(label):
            for place in run_places(ROOT / label):
                columns = place.produces(figure, lo, hi, run_admits)
                if columns:
                    return f"{label} {place.label.split(' ', 1)[1]} {columns}"
            continue
        for other_figure, other_lo, other_hi, written in source_intervals(text):
            if not (admits(lo, [other_lo]) and admits(hi, [other_hi])):
                continue
            if figure is None or (other_figure is not None and admits(figure, [other_figure])):
                return f"{label} “{written}”"
    return None


def check(path: pathlib.Path, sources: Sources, explain: bool = False) -> tuple[int, int, int, list[str]]:
    """Returns (figures, unbound, document-wide only, report lines)."""
    report: list[str] = []
    total = unbound = weak = 0
    refs: list[tuple[str, str, bool]] | None = None
    is_none = False
    marker_line = 0
    # The printed lines under the current marker, read together for the
    # intervals: one may wrap from a line to the next.
    block: list[tuple[int, str]] = []

    def flush() -> None:
        nonlocal unbound
        if refs and block:
            joined, starts, offset = "", [], 0
            for number, text in block:
                starts.append((offset, number))
                joined += text + " "
                offset = len(joined)
            for figure, lo, hi, written, at in check_figures.intervals(joined):
                number = max(n for start, n in starts if start <= at)
                parts = [p for p in (figure, lo, hi) if p is not None]
                if not all(any(admits(p, source_figures(text)) for _, text, _ in refs)
                           for p in parts):
                    continue
                shown = written.replace("-", MINUS)
                bound_by = interval_source(figure, lo, hi, refs)
                if bound_by is None:
                    unbound += 1
                    report.append(f"{path}:{number}: interval {shown} is not written whole "
                                  f"by any one place of the marker's sources (marker l. {marker_line})")
                elif explain:
                    report.append(f"{path}:{number}: interval {shown} <- {bound_by}")
        block.clear()

    lines = path.read_text(encoding="utf-8").splitlines()
    for number, raw in enumerate(lines, start=1):
        marker = MARKER.match(raw)
        if marker:
            flush()
            refs, errors, is_none = sources.resolve(marker.group("body"))
            marker_line = number
            for error in errors:
                report.append(f"{path}:{number}: marker: {error}")
                unbound += 1
            continue
        if not raw.strip():
            flush()
            refs, is_none = None, False
            continue
        if raw.lstrip().startswith("%"):
            continue
        block.append((number, printed(raw)))
        found = source_figures(printed(raw))
        for token in found:
            total += 1
            shown = token.replace("-", MINUS)
            if refs is None and not is_none:
                unbound += 1
                report.append(f"{path}:{number}: {shown} stands under no marker")
                continue
            if is_none:
                unbound += 1
                report.append(f"{path}:{number}: {shown} under a `none` marker (l. {marker_line})")
                continue
            if not refs:
                unbound += 1
                report.append(f"{path}:{number}: {shown} under a marker naming no source (l. {marker_line})")
                continue
            binding = [(label, wide) for label, text, wide in refs
                       if admits(token, source_figures(text))]
            if not binding:
                unbound += 1
                names = ", ".join(label for label, _, _ in refs) or "nothing"
                report.append(f"{path}:{number}: {shown} not in {names} (marker l. {marker_line})")
                continue
            if all(wide for _, wide in binding):
                weak += 1
            if explain:
                labels = ", ".join(label + (" (weak)" if wide else "")
                                   for label, wide in binding)
                report.append(f"{path}:{number}: {shown} <- {labels}")
    flush()
    return total, unbound, weak, report


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    explain = "--explain" in argv
    paths = [pathlib.Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        print(__doc__.split("\n\n")[0])
        return 2
    bib = paths[0].resolve().parent.parent / "refs.bib"
    sources = Sources(bib if bib.exists() else None)
    failed = False
    for path in paths:
        total, unbound, weak, report = check(path, sources, explain)
        for line in report:
            print(line)
        print(f"{path}: {total} figures, {unbound} unbound, "
              f"{weak} bound only by a whole document or a run file")
        failed |= unbound > 0
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
