#!/usr/bin/env python3
"""The paper's two tables, read from recorded runs and from the claim ledger.

T1 puts the published protocol beside this one on 2015H1-E, the build of the
Lending Club grid on which EXP-004's falsifying run was read, with every model
on the same rows under both protocols. Its rows are every metric EXP-004's
Setting registers and the protocol table holds, in time on a random fold and
out of time on the vintage cohorts. Its columns start with the three classical
models, which carry no temperature. The two foundation models follow at the
shipped temperature of 0.9 and again at 1.0. Each entry is the table's mean
over folds and context draws at four decimals. The least and the greatest
value follow in brackets only when either of them differs at four decimals
from the mean that precedes it. They are read from table.csv.

T2 has one line per kill criterion and model. Both books are read. A line
holds the criterion's reading, its interval and the verdict the ledger row
states; on Freddie Mac the nominal matrix's reading stands beside it.

No figure is typed in. Which recorded line is each criterion's reading is
data below: a run, a file, a selector that must match exactly one line, and
the line it must be. Every value and bound T2 prints, rounded as the ledger
writes it, must appear with its sign in that criterion's ledger row. The
verdict must be a quotation of the row and a whole phrase of it: it opens the
Statement, a clause after punctuation, or the words after "so", "and" or "is",
and it ends where the Statement ends or at a comma, semicolon, colon or full
stop. T2 prints each verdict in full, and the printed cell is checked against
it. Otherwise the script fails.

    python scripts/record_run.py paper-tables -- \\
        python scripts/paper_tables.py --out-dir experiments/<date>-paper-tables
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

# check_paper_figures loads check_figures by path; importing it by name as
# well puts it among the files record_run pins.
import check_figures  # noqa: F401
import check_paper_figures as cpf
import check_recorded_code as crc
from protocol_table import IN_TIME, OUT_OF_TIME, PUBLISHED, STUDY

ROOT = Path(__file__).resolve().parent.parent
PROTOCOLS = "experiments/2026-09-23-lc-2015h1e-protocols5-tfm"
T1_MODELS = ("scorecard", "gbm", "gbm-50k", "tabpfn", "tabicl", "tabpfn@t1", "tabicl@t1")
T1_HEAD = ("Scorecard", "GBM", "GBM-50k", "TabPFN", "TabICL", "TabPFN", "TabICL")
METRIC_NAMES = {
    "auc": "AUC", "gini": "Gini", "ks": "KS", "average_precision": "Average precision",
    "brier": "Brier score", "log_loss": "Log-loss", "accuracy": "Accuracy",
    "balanced_accuracy": "Balanced accuracy", "f1": "F1", "precision": "Precision",
    "recall": "Recall", "mcc": "MCC", "observed_over_expected": "Observed over expected",
    "abs_log_oe": r"$|\log \mathrm{O/E}|$", "cox_slope": "Cox slope",
    "brier_miscalibration": "Brier miscalibration", "psi": "PSI",
}
PROTOCOL_NAMES = {IN_TIME: "in time, random fold", OUT_OF_TIME: "out of time, vintage cohorts"}
MINUS = "−"
LEDGER = ROOT / "docs" / "ledger" / "CLAIMS.md"

# The criterion's control, and each hypothesis's comparator as the
# pre-registrations name it; H5 reads one model against itself.
CONTROL = "gbm-50k"
COMPARATOR = {"H1": "gbm-50k", "H2": "scorecard", "H3": "gbm-50k", "H4": "gbm-50k", "H5": None}
RATIO, NOMINAL = "ratio", "nominal"


@dataclass(frozen=True)
class Reading:
    """One recorded line: the run, the file, the column values that select it, its line."""
    run: str
    file: str
    select: tuple[tuple[str, str], ...]
    line: int


@dataclass(frozen=True)
class Criterion:
    """One T2 line: a criterion's reading for one model, and the nominal matrix's beside it."""
    book: str
    hypothesis: str
    claim: str
    model: str
    statistic: str
    decimals: int
    reading: Reading
    verdict: str
    nominal: Reading | None = None
    nominal_verdict: str | None = None
    scoped: tuple[Scoped, ...] = ()


@dataclass(frozen=True)
class Scoped:
    """A sub-line under a criterion's line: the same statistic on one scope of its cells.

    `nominal_interval` says whether the ledger row writes the nominal reading's
    interval; where it does not, only the value is printed.
    """
    scope: str
    reading: Reading
    nominal: Reading | None = None
    nominal_interval: bool = True


LC_ARM = "experiments/2026-09-22-lc-arm-e-intervals"
LC_BETWEEN = "experiments/2026-09-24-lc-between-arm-intervals"
FM_REFIT = "experiments/2026-09-21-fm-arm-e-intervals-refit-control"
FM_ARM = "experiments/2026-09-21-fm-arm-e-intervals"
FM_ARM_NOMINAL = "experiments/2026-09-23-fm-arm-e-intervals-upb-nominal"
FM_BETWEEN = "experiments/2026-09-22-fm-between-arm-intervals"
FM_BETWEEN_NOMINAL = "experiments/2026-09-23-fm-between-arm-intervals-upb-nominal"
FM_IN_SAMPLE = "experiments/2026-09-22-fm-grid-in-sample"
FM_IN_SAMPLE_NOMINAL = "experiments/2026-09-23-fm-grid-in-sample-upb-nominal"

AUC_SLOPE = "slope of AUC on age, one intercept per build, minus the control's"
COX = "mean absolute Cox-slope deviation minus the scorecard's"
PSI = "PSI against its own training reference minus the control's"
H4 = "expanding minus rolling Cox-slope deviation, minus the control's"
H5 = "O/E on the highest-rate rolling context minus the lowest"


def pick(**columns: str) -> tuple[tuple[str, str], ...]:
    return tuple(sorted(columns.items()))


def arm_line(run: str, metric: str, pair: str, line: int) -> Reading:
    """A pooled difference of an arm run: all cohorts held fixed, no draw held, the arm's scope."""
    return Reading(run, "paired.csv",
                   pick(scope="arm", cohorts="all", draw="", metric=metric, pair=pair), line)


def h4_line(run: str, model: str, line: int, scope: str = "arm") -> Reading:
    return Reading(run, "paired.csv", pick(scope=scope, cohorts="all", draw="", kind="h4",
                                           metric="cox_slope_deviation", model=model), line)


def h5_line(run: str, model: str, line: int) -> Reading:
    return Reading(run, "h5.csv", pick(arm="R", ranking="pool", criterion="True", metric="h5",
                                       model=model), line)


LC_H1_VERDICT = "H1's kill does not fire, and its second branch does not fire either"
LC_H4_VERDICT = "killed inside the interval for both models at both settings"
LENDING_CLUB = [
    Criterion("Lending Club", "H1", "C-021", "tabpfn", AUC_SLOPE, 5,
              arm_line(LC_ARM, "auc_slope_build", "tabpfn - gbm-50k", 188),
              LC_H1_VERDICT),
    Criterion("Lending Club", "H1", "C-021", "tabicl", AUC_SLOPE, 5,
              arm_line(LC_ARM, "auc_slope_build", "tabicl - gbm-50k", 189),
              LC_H1_VERDICT),
    Criterion("Lending Club", "H2", "C-007", "tabpfn", COX, 4,
              arm_line(LC_ARM, "cox_slope_deviation", "tabpfn - scorecard", 67),
              "no kill fires for TabPFN"),
    Criterion("Lending Club", "H2", "C-007", "tabicl", COX, 4,
              arm_line(LC_ARM, "cox_slope_deviation", "tabicl - scorecard", 68),
              "H2's kill fires for TabICL at 0.9"),
    Criterion("Lending Club", "H3", "C-038", "tabpfn", PSI, 4,
              arm_line(LC_ARM, "psi", "tabpfn - gbm-50k", 132),
              "no kill fires for TabPFN"),
    Criterion("Lending Club", "H3", "C-038", "tabicl", PSI, 4,
              arm_line(LC_ARM, "psi", "tabicl - gbm-50k", 133),
              "H3's kill fires for TabICL"),
    Criterion("Lending Club", "H4", "C-034", "tabpfn", H4, 4,
              h4_line(LC_BETWEEN, "tabpfn", 25), LC_H4_VERDICT),
    Criterion("Lending Club", "H4", "C-034", "tabicl", H4, 4,
              h4_line(LC_BETWEEN, "tabicl", 26), LC_H4_VERDICT),
]

FM_H1_VERDICT = "H1's kill does not fire, and its uninformative branch does not fire"
FM_H1_NOMINAL = "neither the kill nor the uninformative branch fires"
FM_H2_VERDICT = "H2's kill fires for both at 0.9 as the criterion reads it on the ratio matrix"
FREDDIE_MAC_H1_H2 = [
    Criterion("Freddie Mac", "H1", "C-025", "tabpfn", AUC_SLOPE, 6,
              arm_line(FM_REFIT, "auc_slope_build", "tabpfn - gbm-50k", 239), FM_H1_VERDICT,
              arm_line(FM_ARM_NOMINAL, "auc_slope_build", "tabpfn - gbm-50k", 188),
              FM_H1_NOMINAL),
    Criterion("Freddie Mac", "H1", "C-025", "tabicl", AUC_SLOPE, 6,
              arm_line(FM_REFIT, "auc_slope_build", "tabicl - gbm-50k", 240), FM_H1_VERDICT,
              arm_line(FM_ARM_NOMINAL, "auc_slope_build", "tabicl - gbm-50k", 189),
              FM_H1_NOMINAL + ", and TabICL's row loses its star"),
    Criterion("Freddie Mac", "H2", "C-027", "tabpfn", COX, 4,
              arm_line(FM_ARM, "cox_slope_deviation", "tabpfn - scorecard", 67),
              FM_H2_VERDICT,
              arm_line(FM_ARM_NOMINAL, "cox_slope_deviation", "tabpfn - scorecard", 67),
              "it fires at 0.9 as well"),
    Criterion("Freddie Mac", "H2", "C-027", "tabicl", COX, 4,
              arm_line(FM_ARM, "cox_slope_deviation", "tabicl - scorecard", 68),
              FM_H2_VERDICT,
              arm_line(FM_ARM_NOMINAL, "cox_slope_deviation", "tabicl - scorecard", 68),
              "it fires at 0.9 as well"),
]

FM_H3_VERDICT = ("H3's kill does not fire for either model as the criterion reads it on the "
                 "ratio matrix")
FM_H4_VERDICT = "H4 is undetermined on this book for both foundation models"
FM_H4_NOMINAL = "both rows reading killed inside the interval"
def h4_scopes(model: str, pre_flag: int, flagged: int) -> tuple[Scoped, ...]:
    """H4's verdict is the sign of the pre-flag row against the flagged row; the ledger
    writes the nominal matrix's scoped values without their intervals."""
    return tuple(Scoped(scope, h4_line(FM_BETWEEN, model, line, scope),
                        h4_line(FM_BETWEEN_NOMINAL, model, line, scope), nominal_interval=False)
                 for scope, line in (("pre-flag", pre_flag), ("flagged", flagged)))


FM_H5_VERDICT = ("H5's kill fires on the rolling arm at 0.9 as the criterion reads it on the "
                 "ratio matrix")
FM_H5_NOMINAL = "the kill fires there too and the nominal reading changes nothing"
FREDDIE_MAC_H3_H5 = [
    Criterion("Freddie Mac", "H3", "C-042", "tabpfn", PSI, 4,
              arm_line(FM_REFIT, "psi", "tabpfn - gbm-50k", 167), FM_H3_VERDICT,
              arm_line(FM_ARM_NOMINAL, "psi", "tabpfn - gbm-50k", 132),
              "H3's kill fires for TabPFN on the nominal matrix"),
    Criterion("Freddie Mac", "H3", "C-042", "tabicl", PSI, 4,
              arm_line(FM_REFIT, "psi", "tabicl - gbm-50k", 168), FM_H3_VERDICT,
              arm_line(FM_ARM_NOMINAL, "psi", "tabicl - gbm-50k", 133),
              "for TabICL it does not fire on either matrix"),
    Criterion("Freddie Mac", "H4", "C-041", "tabpfn", H4, 4,
              h4_line(FM_BETWEEN, "tabpfn", 25), FM_H4_VERDICT,
              h4_line(FM_BETWEEN_NOMINAL, "tabpfn", 25), FM_H4_NOMINAL,
              h4_scopes("tabpfn", 268, 295)),
    Criterion("Freddie Mac", "H4", "C-041", "tabicl", H4, 4,
              h4_line(FM_BETWEEN, "tabicl", 26), FM_H4_VERDICT,
              h4_line(FM_BETWEEN_NOMINAL, "tabicl", 26), FM_H4_NOMINAL,
              h4_scopes("tabicl", 269, 296)),
    Criterion("Freddie Mac", "H5", "C-028", "tabpfn", H5, 3,
              h5_line(FM_IN_SAMPLE, "tabpfn", 22), FM_H5_VERDICT,
              h5_line(FM_IN_SAMPLE_NOMINAL, "tabpfn", 22), FM_H5_NOMINAL),
    Criterion("Freddie Mac", "H5", "C-028", "tabicl", H5, 3,
              h5_line(FM_IN_SAMPLE, "tabicl", 28), FM_H5_VERDICT,
              h5_line(FM_IN_SAMPLE_NOMINAL, "tabicl", 28), FM_H5_NOMINAL),
]

CRITERIA = LENDING_CLUB + FREDDIE_MAC_H1_H2 + FREDDIE_MAC_H3_H5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cell_text(mean: float, lo: float, hi: float) -> str:
    """One entry: the mean at four decimals, and the least and greatest value in brackets
    when either differs from the mean at those decimals."""
    text, low, high = f"{mean:.4f}", f"{lo:.4f}", f"{hi:.4f}"
    if low != text or high != text:
        text += f" [{low}, {high}]"
    return text


def derived_models(run: Path) -> dict[str, list[str]]:
    """Per model label, the score directories the table read that were derived, not scored."""
    described = json.loads((run / "protocols.json").read_text(encoding="utf-8"))
    found: dict[str, list[str]] = {}
    for name in [*described["in_time_tfm"], *described["out_of_time"]]:
        derive = ROOT / name / "derive.json"
        if derive.exists():
            label = json.loads(derive.read_text(encoding="utf-8"))["derived_as"]
            found.setdefault(label, []).append(name)
    return found


def t1_cells(run: Path) -> list[dict]:
    """Every T1 entry with the line of table.csv it was read from."""
    table = pd.read_csv(run / "table.csv")
    cells = []
    for metric in (*PUBLISHED, *STUDY):
        for protocol in (IN_TIME, OUT_OF_TIME):
            for model in T1_MODELS:
                hit = table[(table["protocol"] == protocol) & (table["model"] == model)]
                if len(hit) != 1:
                    raise SystemExit(f"T1: {len(hit)} lines of table.csv for {protocol}/{model}")
                row = hit.iloc[0]
                mean, lo, hi = (float(row[f"{metric}_{s}"]) for s in ("mean", "min", "max"))
                cells.append({"metric": metric, "protocol": protocol, "model": model,
                              "text": cell_text(mean, lo, hi), "mean": mean, "min": lo,
                              "max": hi, "source": {"run": run.relative_to(ROOT).as_posix(),
                                                    "file": "table.csv",
                                                    "line": int(hit.index[0]) + 2,
                                                    "columns": [f"{metric}_mean", f"{metric}_min",
                                                                f"{metric}_max"]}})
    return cells


def t1_latex(cells: list[dict], derived: dict[str, list[str]]) -> str:
    heads = [h + (r"$^{\dagger}$" if m in derived else "") for m, h in zip(T1_MODELS, T1_HEAD)]
    lines = [r"\begin{tabular}{ll" + "r" * len(T1_MODELS) + "}",
             f"% FIG: {PROTOCOLS}/table.csv", r"\toprule",
             (r" & & & & & \multicolumn{2}{c}{shipped temperature} "
              r"& \multicolumn{2}{c}{temperature one} \\"),
             r"\cmidrule(lr){6-7}\cmidrule(lr){8-9}",
             "Metric & Protocol & " + " & ".join(heads) + r" \\", r"\midrule"]
    by_key = {(c["metric"], c["protocol"], c["model"]): c["text"] for c in cells}
    for index, metric in enumerate((*PUBLISHED, *STUDY)):
        if index:
            lines.append(r"\addlinespace")
        for protocol in (IN_TIME, OUT_OF_TIME):
            first = METRIC_NAMES[metric] if protocol == IN_TIME else ""
            row = [first, PROTOCOL_NAMES[protocol]]
            row += [by_key[(metric, protocol, m)] for m in T1_MODELS]
            lines.append(" & ".join(row) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(lines)


def read_line(root: Path, reading: Reading) -> dict:
    """The one line the selector names, refused unless it is the line the mapping cites."""
    frame = pd.read_csv(root / reading.run / reading.file, dtype=str, keep_default_na=False)
    mask = pd.Series(True, index=frame.index)
    for column, value in reading.select:
        if column not in frame.columns:
            raise SystemExit(f"{reading.run}/{reading.file}: no column {column}")
        mask &= frame[column] == value
    hits = frame[mask]
    where = f"{reading.run}/{reading.file} {dict(reading.select)}"
    if len(hits) != 1:
        raise SystemExit(f"{where}: {len(hits)} lines match, one is required")
    line = int(hits.index[0]) + 2
    if line != reading.line:
        raise SystemExit(f"{where}: the selector reads line {line}, the mapping cites "
                         f"{reading.line}")
    row = hits.iloc[0]
    return {"value": float(row["value"]), "lo": float(row["ci_lo"]), "hi": float(row["ci_hi"]),
            "line": line, "row": row.to_dict()}


def matrix_of(run: Path) -> str:
    """Which feature matrix a run read: its summary's ablation, else the names of its sources."""
    summary = run / "summary.json"
    record = json.loads(summary.read_text(encoding="utf-8")) if summary.exists() else {}
    if "matrix" in record:
        ablation = (record["matrix"] or {}).get("ablation")
        return NOMINAL if ablation == "upb_nominal" else RATIO
    intervals = run / "intervals.json"
    if not record.get("sources") and intervals.exists():
        record = json.loads(intervals.read_text(encoding="utf-8"))
    sources = record.get("sources") or []
    nominal = {"upb-nominal" in s for s in sources}
    if len(nominal) != 1:
        raise SystemExit(f"{run.name}: its sources name no single matrix")
    return NOMINAL if nominal.pop() else RATIO


METRIC = {"H1": "auc_slope_build", "H2": "cox_slope_deviation", "H3": "psi",
          "H4": "cox_slope_deviation", "H5": "h5"}
SUB_SCOPES = ("pre-flag", "flagged")


def check_setting(name: str, hypothesis: str, row: dict, scope: str) -> None:
    """The line is the criterion's reading and not one reported beside it: its statistic,
    its scope, the cohorts held fixed and no context draw held."""
    expect = {"metric": METRIC[hypothesis]}
    if hypothesis == "H5":
        expect.update(arm="R", ranking="pool", criterion="True")
    else:
        expect.update(scope=scope, cohorts="all", draw="")
    if hypothesis == "H4":
        expect["kind"] = "h4"
    for column, value in expect.items():
        if row.get(column) != value:
            raise SystemExit(f"{name}: the line reads {column} {row.get(column)!r}, the "
                             f"criterion's is {value!r}")


def check_identity(root: Path, criterion: Criterion, reading: Reading, row: dict,
                   matrix: str, scope: str = "arm") -> None:
    """The run measures what the criterion reads: its control, its matrix, its comparison."""
    run = root / reading.run
    name = f"{criterion.claim} {criterion.model} ({reading.run})"
    check_setting(name, criterion.hypothesis, row, scope)
    summary = run / "summary.json"
    if summary.exists():
        record = json.loads(summary.read_text(encoding="utf-8"))
        if "control" in record and record["control"] != CONTROL:
            raise SystemExit(f"{name}: the run's control is {record['control']}, the "
                             f"criterion's is {CONTROL}")
        reading_of = (record.get("criterion") or {}).get("reading", {}).get(criterion.model)
        if reading_of is not None and reading_of.get("criterion") is not True:
            raise SystemExit(f"{name}: the run does not read {criterion.model} as a criterion row")
    if matrix_of(run) != matrix:
        raise SystemExit(f"{name}: the run reads the {matrix_of(run)} matrix, not the {matrix}")
    comparator = COMPARATOR[criterion.hypothesis]
    if "pair" in row and comparator is not None:
        left, _, right = row["pair"].split(":")[0].partition(" - ")
        if (left.strip(), right.strip()) != (criterion.model, comparator):
            raise SystemExit(f"{name}: the line reads {row['pair']}, the criterion "
                             f"{criterion.model} - {comparator}")
    elif row.get("model") != criterion.model:
        raise SystemExit(f"{name}: the line reads {row.get('model')}")


def code_not_identical(root: Path, runs: list[str]) -> dict[str, list[str]]:
    """Per run, the code files whose class under check_recorded_code is not identical or crlf."""
    record = crc.Record(root)
    found: dict[str, list[str]] = {}
    for run in runs:
        manifest = json.loads((root / run / "manifest.json").read_text(encoding="utf-8"))
        for path, recorded in sorted(crc.code_hashes(manifest).items()):
            status = crc.classify(record, manifest, path, recorded)
            if status not in ("identical", "crlf"):
                found.setdefault(run, []).append(f"{path} ({status})")
    return found


def ledger_evidence(path: Path) -> dict[str, str]:
    evidence = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 5 and re.fullmatch(r"C-\d{3}", cells[0]):
            evidence[cells[0]] = cells[3]
    return evidence


def load_sources(path: Path) -> cpf.Sources:
    saved = cpf.LEDGER
    cpf.LEDGER = path
    try:
        return cpf.Sources()
    finally:
        cpf.LEDGER = saved


def signed(x: float, decimals: int) -> str:
    """A figure as the ledger writes it: its sign always, a typographic minus."""
    return f"{x:+.{decimals}f}".replace("-", MINUS)


def self_check(criterion: Criterion, sources: cpf.Sources, evidence: dict[str, str],
               figures: list[str], verdicts: list[str], nominal_run: str | None) -> None:
    """Every printed figure, with its sign, and every verdict quoted must be in the row."""
    claim = criterion.claim
    name = f"T2 {criterion.book} {criterion.hypothesis} {criterion.model} ({claim})"
    if claim not in sources.rows:
        raise SystemExit(f"{name}: {claim} is not in the ledger")
    if sources.status[claim] != "active":
        raise SystemExit(f"{name}: {claim} is {sources.status[claim]}")
    if evidence.get(claim) != criterion.reading.run:
        raise SystemExit(f"{name}: the row's evidence is {evidence.get(claim)}, the mapping "
                         f"reads {criterion.reading.run}")
    text = sources.rows[claim]
    if nominal_run is not None and nominal_run not in text + sources.settings[claim]:
        raise SystemExit(f"{name}: the row does not name {nominal_run}")
    written = cpf.source_figures(text)
    for figure in figures:
        token = figure.replace(MINUS, "-")
        if not cpf.admits(token, written):
            raise SystemExit(f"{name}: {figure} is not written in {claim}")
    for verdict in verdicts:
        if verdict not in text:
            raise SystemExit(f"{name}: the verdict \"{verdict}\" is not a quotation of {claim}")
        if not whole_phrase(verdict, text):
            raise SystemExit(f"{name}: the verdict \"{verdict}\" is a quotation of {claim} but "
                             "not a whole phrase of it")


# Where a verdict may open: the Statement's start, after clause punctuation or
# a dash, or after "so", "and" or "is". Where it may end: the Statement's end
# or clause punctuation. "kill fires for TabPFN" cut from "no kill fires for
# TabPFN", or "killed inside the interval for both models" cut from "... for
# both models at both settings", is refused.
PHRASE_OPENS = re.compile(r"(?:\A|[.;:,—]\s+|\b(?:so|and|is)\s+)\Z")
PHRASE_ENDS = re.compile(r"(?:[.;:,]|\Z)")


def whole_phrase(verdict: str, text: str) -> bool:
    """Whether the verdict occurs in the text with a phrase boundary on both sides."""
    return any(PHRASE_OPENS.search(text[:m.start()]) and PHRASE_ENDS.match(text, m.end())
               for m in re.finditer(re.escape(verdict), text))


def check_printed_verdicts(latex: str, lines: list[dict]) -> None:
    """Every T2 line prints its verdicts whole, each in its own cell."""
    rows = latex.splitlines()
    marked = [i + 1 for i, text in enumerate(rows) if text.startswith("% FIG:")]
    if len(marked) != len(lines):
        raise SystemExit(f"T2 prints {len(marked)} marked lines for {len(lines)} criteria")
    for index, entry in zip(marked, lines):
        cells = [c.strip() for c in rows[index].removesuffix(r"\\").split(" & ")]
        name = f"T2 {entry['book']} {entry['hypothesis']} {entry['model']} ({entry['claim']})"
        if cells[6] != entry["verdict"]:
            raise SystemExit(f"{name}: prints the verdict \"{cells[6]}\", the mapping's is "
                             f"\"{entry['verdict']}\"")
        if cells[9] != entry.get("nominal_verdict", ""):
            raise SystemExit(f"{name}: prints the nominal reading \"{cells[9]}\", the mapping's "
                             f"is \"{entry.get('nominal_verdict', '')}\"")


MODEL_NAMES = {"tabpfn": "TabPFN", "tabicl": "TabICL"}


def shown_reading(root: Path, criterion: Criterion, reading: Reading, matrix: str,
                  interval: bool, figures: list[str], scope: str = "arm") -> dict:
    """One reading as T2 prints it; the figures printed are added to `figures`.

    Without `interval` only the value is printed, and the bounds are neither
    shown nor checked: T2 prints no figure its ledger row does not write.
    """
    got = read_line(root, reading)
    check_identity(root, criterion, reading, got["row"], matrix, scope)
    keys = ("value", "lo", "hi") if interval else ("value",)
    shown = [signed(got[k], criterion.decimals) for k in keys]
    figures += shown
    return {"value": shown[0], "interval": shown[1:] if interval else None,
            "raw": [got[k] for k in keys],
            "source": {"run": reading.run, "file": reading.file, "line": got["line"],
                       "select": dict(reading.select)}}


def t2_lines(root: Path, criteria: list[Criterion], sources: cpf.Sources,
             evidence: dict[str, str]) -> list[dict]:
    """Every T2 line, each value read from its cited line and checked against its ledger row."""
    lines = []
    for criterion in criteria:
        entry = {"book": criterion.book, "hypothesis": criterion.hypothesis,
                 "claim": criterion.claim, "model": criterion.model,
                 "statistic": criterion.statistic, "verdict": criterion.verdict}
        figures, verdicts = [], [criterion.verdict]
        for key, reading, matrix in (("ratio", criterion.reading, RATIO),
                                     ("nominal", criterion.nominal, NOMINAL)):
            if reading is None:
                continue
            entry[key] = shown_reading(root, criterion, reading, matrix, True, figures)
        entry["scoped"] = []
        for sub in criterion.scoped:
            if sub.scope not in SUB_SCOPES:
                raise SystemExit(f"{criterion.claim} {criterion.model}: a sub-line on scope "
                                 f"{sub.scope}; T2's sub-lines are {', '.join(SUB_SCOPES)}")
            part = {"scope": sub.scope,
                    "ratio": shown_reading(root, criterion, sub.reading, RATIO, True, figures,
                                           sub.scope)}
            if sub.nominal is not None:
                part["nominal"] = shown_reading(root, criterion, sub.nominal, NOMINAL,
                                                sub.nominal_interval, figures, sub.scope)
            entry["scoped"].append(part)
        if criterion.nominal_verdict is not None:
            entry["nominal_verdict"] = criterion.nominal_verdict
            verdicts.append(criterion.nominal_verdict)
        self_check(criterion, sources, evidence, figures, verdicts,
                   criterion.nominal.run if criterion.nominal else None)
        entry["ledger_check"] = "every figure and verdict written in " + criterion.claim
        lines.append(entry)
    return lines


def math(figure: str) -> str:
    return "$" + figure.replace(MINUS, "-") + "$"


def shown_cells(part: dict | None) -> list[str]:
    """Value and interval cells; a dash where the ledger writes no interval."""
    if part is None:
        return ["", ""]
    if part["interval"] is None:
        return [math(part["value"]), "--"]
    return [math(part["value"]),
            "$[" + ", ".join(math(b)[1:-1] for b in part["interval"]) + "]$"]


def t2_latex(lines: list[dict]) -> str:
    """The T2 body; a figure marker before each line binds it to its ledger row."""
    out = [r"\begin{tabular}{lllp{3.4cm}rlp{3.4cm}rlp{3.4cm}}", r"\toprule",
           r" & & & & \multicolumn{3}{c}{criterion's matrix} & \multicolumn{3}{c}{nominal matrix} \\",
           r"\cmidrule(lr){5-7}\cmidrule(lr){8-10}",
           (r"Book & Hypothesis & Model & Statistic & Value & Interval & Verdict "
            r"& Value & Interval & Reading \\"), r"\midrule"]
    for entry in lines:
        cells = [entry["book"], f"{entry['hypothesis']} ({entry['claim']})",
                 MODEL_NAMES[entry["model"]], entry["statistic"]]
        for key, verdict in (("ratio", "verdict"), ("nominal", "nominal_verdict")):
            cells += [*shown_cells(entry.get(key)), entry.get(verdict, "")]
        out.append(f"% FIG: {entry['claim']}")
        out.append(" & ".join(cells) + r" \\")
        for sub in entry["scoped"]:
            cells = ["", "", "", rf"\quad {sub['scope']} scope"]
            for key in ("ratio", "nominal"):
                cells += [*shown_cells(sub.get(key)), ""]
            out.append(" & ".join(cells) + r" \\")
    out += [r"\bottomrule", r"\end{tabular}", ""]
    return "\n".join(out)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=LEDGER,
                        help="the claim ledger T2 is checked against")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    runs = sorted({PROTOCOLS} | {r.run for c in CRITERIA for r in (c.reading, c.nominal) if r})
    changed = code_not_identical(ROOT, runs)
    if changed:
        raise SystemExit("recorded code changed since these runs: " + "; ".join(
            f"{run}: {', '.join(files)}" for run, files in changed.items()))
    print(f"recorded code: {len(runs)} runs, every code file identical to what ran")

    run = ROOT / PROTOCOLS
    derived = derived_models(run)
    cells = t1_cells(run)
    (args.out_dir / "t1.tex").write_text(t1_latex(cells, derived), encoding="utf-8")
    print(f"T1: {len(cells)} entries from {PROTOCOLS}/table.csv; derived: {sorted(derived)}")

    sources = load_sources(args.ledger)
    lines = t2_lines(ROOT, CRITERIA, sources, ledger_evidence(args.ledger))
    t2_path = args.out_dir / "t2.tex"
    t2_body = t2_latex(lines)
    check_printed_verdicts(t2_body, lines)
    t2_path.write_text(t2_body, encoding="utf-8")
    # The gate reads the arguments of \multicolumn, \cmidrule and p{} as
    # figures, so it is applied to the marked lines, which carry every figure.
    with tempfile.TemporaryDirectory() as scratch:
        body = Path(scratch) / "t2-rows.tex"
        marked = t2_path.read_text(encoding="utf-8").splitlines()
        first = next(i for i, text in enumerate(marked) if text.startswith("% FIG:"))
        last = next(i for i, text in enumerate(marked) if text.startswith(r"\bottomrule"))
        body.write_text("\n".join(marked[first:last]) + "\n", encoding="utf-8")
        total, unbound, _, report = cpf.check(body, sources)
    if unbound:
        raise SystemExit("T2 under the paper's figure gate: " + "; ".join(report))
    print(f"T2: {len(lines)} lines; {total} figures, each written with its sign in its "
          "ledger row; every verdict a quotation of it")
    for entry in lines:
        nominal = entry.get("nominal")
        print(f"  {entry['book']:<12} {entry['hypothesis']} {entry['claim']} "
              f"{entry['model']:<6} {entry['ratio']['value']} "
              f"[{', '.join(entry['ratio']['interval'])}]"
              + ("" if not nominal else f"  nominal {nominal['value']} "
                 f"[{', '.join(nominal['interval'])}]"))
        for sub in entry["scoped"]:
            ratio, nominal = sub["ratio"], sub.get("nominal")
            print(f"    {sub['scope']:<8} {ratio['value']} [{', '.join(ratio['interval'])}]"
                  + ("" if not nominal else f"  nominal {nominal['value']}"
                     + (f" [{', '.join(nominal['interval'])}]" if nominal["interval"] else "")))

    files = [run / "table.csv", run / "protocols.json", args.ledger]
    files += sorted({ROOT / r.run / r.file for c in CRITERIA for r in (c.reading, c.nominal) if r})
    echo = {"t1": {"run": PROTOCOLS, "derived": derived, "cells": cells},
            "t2": {"ledger": args.ledger.resolve().relative_to(ROOT).as_posix()
                   if args.ledger.resolve().is_relative_to(ROOT) else args.ledger.as_posix(),
                   "lines": lines},
            "recorded_code": {"runs": runs, "not_identical": changed},
            "inputs": {f.resolve().relative_to(ROOT).as_posix(): sha256(f) for f in files}}
    (args.out_dir / "tables.json").write_text(json.dumps(echo, indent=2, ensure_ascii=False),
                                              encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
