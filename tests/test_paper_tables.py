"""The paper's tables: T1 as the protocol table writes it, T2 bound to its ledger rows.

The typical T2 figure is a signed difference with its interval quoted from a
ledger row, so the checks below build that figure and then the mistakes that
keep every other gate green: the sign flipped, a superseded row, a run whose
control is not the criterion's, a selector landing on the next line.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")
pytest.importorskip("matplotlib")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import paper_tables as pt

ROOT = Path(__file__).resolve().parent.parent
TABLE = ROOT / pt.PROTOCOLS

HEADER = ("arm,cohorts,draw,scope,metric,pair,is_difference,value,ci_lo,ci_hi,se,alpha,"
          "resamples,seed,excludes_zero,reads_derived\n")
ROWS = ("E,all,,arm,psi,tabpfn - gbm-50k,True,0.00921,0.00834,0.01031,0.0005,0.05,200,"
        "20260905,True,False\n"
        "E,all,,arm,psi,tabicl - gbm-50k,True,-0.00712,-0.01161,-0.00451,0.0017,0.05,200,"
        "20260905,True,False\n")
STATEMENT = ("TabPFN − GBM-50k on the stability index is +0.0092 [+0.0083, +0.0103], so H3's "
             "kill fires for TabPFN.")
FLIPPED = STATEMENT.replace("+0.0092", "−0.0092")


def ledger(tmp: Path, statement: str, status: str = "active",
           evidence: str = "experiments/run-a") -> Path:
    path = tmp / "CLAIMS.md"
    path.write_text("| ID | Statement | Setting | Evidence | Status |\n| --- | --- | --- | --- | "
                    f"--- |\n| C-001 | {statement} | Synthetic, ratio matrix. | {evidence} | "
                    f"{status} |\n", encoding="utf-8")
    return path


def run(tmp: Path, name: str = "run-a", control: str | None = None,
        sources: str = "experiments/x-scores") -> str:
    directory = tmp / "experiments" / name
    directory.mkdir(parents=True)
    (directory / "paired.csv").write_text(HEADER + ROWS, encoding="utf-8")
    summary = {"sources": [sources]}
    if control is not None:
        summary["control"] = control
    (directory / "summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return f"experiments/{name}"


def criterion(run_name: str, line: int = 2) -> pt.Criterion:
    return pt.Criterion("Freddie Mac", "H3", "C-001", "tabpfn", pt.PSI, 4,
                        pt.arm_line(run_name, "psi", "tabpfn - gbm-50k", line),
                        "H3's kill fires for TabPFN")


def lines(tmp: Path, crit: pt.Criterion, ledger_path: Path) -> list[dict]:
    return pt.t2_lines(tmp, [crit], pt.load_sources(ledger_path),
                       pt.ledger_evidence(ledger_path))


def table_md_cells() -> dict[tuple[str, str, str], str]:
    cells, metric, models = {}, None, []
    for text in (TABLE / "table.md").read_text(encoding="utf-8").splitlines():
        parts = [p.strip() for p in text.strip().strip("|").split("|")]
        if not text.startswith("|") or parts[0].startswith("---"):
            continue
        if parts[0] in (*pt.PUBLISHED, *pt.STUDY, "predicted_positive_share", "threshold"):
            metric, models = parts[0], parts[1:]
            continue
        for model, value in zip(models, parts[1:]):
            cells[(metric, parts[0], model)] = value
    return cells


@pytest.mark.skipif(not (TABLE / "table.md").exists(), reason="the recorded table is not here")
def test_t1_reproduces_the_recorded_table():
    """Every cell equals table.md where the two bracket rules agree.

    table.md brackets a spread wider than 5e-5; T1 brackets one whose bounds
    differ from the mean at four decimals. On this table they part on five
    cells: two brackets table.md prints read as the mean (Brier miscalibration,
    GBM in time and TabPFN at 1.0 out of time), and three spreads under 5e-5
    cross a fourth-decimal boundary. There only the mean is compared.
    """
    written = table_md_cells()
    produced = pt.t1_cells(TABLE)
    assert len(produced) == 17 * 2 * 7
    parted = []
    for cell in produced:
        recorded = written[(cell["metric"], cell["protocol"], cell["model"])]
        wide = cell["max"] - cell["min"] > 5e-5
        if wide == ("[" in cell["text"]):
            assert cell["text"] == recorded, cell
        else:
            assert cell["text"].split(" ")[0] == recorded.split(" ")[0], cell
            parted.append((cell["metric"], cell["model"]))
    assert len(parted) == 5
    assert ("brier_miscalibration", "gbm") in parted


def test_t1_spread_rule():
    assert pt.cell_text(0.70021, 0.70020, 0.70024) == "0.7002"
    assert pt.cell_text(0.000287, 0.000261, 0.000324) == "0.0003"
    assert pt.cell_text(0.70021, 0.70010, 0.70024) == "0.7002 [0.7001, 0.7002]"


def test_t2_line_is_read_and_bound(tmp_path):
    name = run(tmp_path, control="gbm-50k")
    [entry] = lines(tmp_path, criterion(name), ledger(tmp_path, STATEMENT))
    assert entry["ratio"]["value"] == "+0.0092"
    assert entry["ratio"]["interval"] == ["+0.0083", "+0.0103"]
    assert entry["ratio"]["source"]["line"] == 2


def test_t2_sign_flipped_in_the_ledger_fails(tmp_path):
    name = run(tmp_path)
    with pytest.raises(SystemExit, match=r"\+0\.0092 is not written in C-001"):
        lines(tmp_path, criterion(name), ledger(tmp_path, FLIPPED))


def test_t2_negative_figure_needs_its_minus(tmp_path):
    name = run(tmp_path)
    crit = pt.Criterion("Freddie Mac", "H3", "C-001", "tabicl", pt.PSI, 4,
                        pt.arm_line(name, "psi", "tabicl - gbm-50k", 3), "H3's kill fires")
    unsigned = "TabICL is 0.0071 [0.0116, 0.0045] and H3's kill fires."
    with pytest.raises(SystemExit, match="is not written in C-001"):
        lines(tmp_path, crit, ledger(tmp_path, unsigned))
    signed = "TabICL is −0.0071 [−0.0116, −0.0045] and H3's kill fires."
    assert lines(tmp_path, crit, ledger(tmp_path, signed))[0]["ratio"]["value"] == "−0.0071"


def test_t2_superseded_row_is_refused(tmp_path):
    name = run(tmp_path)
    with pytest.raises(SystemExit, match="superseded by C-002"):
        lines(tmp_path, criterion(name), ledger(tmp_path, STATEMENT, "superseded by C-002"))


def test_t2_run_with_another_control_is_refused(tmp_path):
    name = run(tmp_path, control="gbm-50k@share")
    with pytest.raises(SystemExit, match="control is gbm-50k@share"):
        lines(tmp_path, criterion(name), ledger(tmp_path, STATEMENT))


def test_t2_selector_on_another_line_is_refused(tmp_path):
    name = run(tmp_path)
    with pytest.raises(SystemExit, match="the mapping cites 3"):
        lines(tmp_path, criterion(name, line=3), ledger(tmp_path, STATEMENT))


def test_t2_verdict_must_be_a_quotation(tmp_path):
    name = run(tmp_path)
    crit = pt.Criterion("Freddie Mac", "H3", "C-001", "tabpfn", pt.PSI, 4,
                        pt.arm_line(name, "psi", "tabpfn - gbm-50k", 2), "H3's kill does not fire")
    with pytest.raises(SystemExit, match="not a quotation"):
        lines(tmp_path, crit, ledger(tmp_path, STATEMENT))


def test_t2_evidence_and_matrix_must_be_the_rows(tmp_path):
    name = run(tmp_path)
    with pytest.raises(SystemExit, match="evidence is experiments/other"):
        lines(tmp_path, criterion(name), ledger(tmp_path, STATEMENT, evidence="experiments/other"))
    nominal = run(tmp_path, "run-n", sources="experiments/x-scores-upb-nominal")
    with pytest.raises(SystemExit, match="reads the nominal matrix, not the ratio"):
        lines(tmp_path, criterion(nominal), ledger(tmp_path, STATEMENT,
                                                   evidence="experiments/run-n"))


H4_HEADER = ("cohorts,draw,scope,metric,kind,model,arm,pair,is_difference,value,ci_lo,ci_hi,se,"
             "alpha,resamples,seed,excludes_zero,reads_derived\n")
H4_ROWS = "".join(f"all,,{scope},cox_slope_deviation,h4,tabpfn,,tabpfn - gbm-50k: E - R,True,"
                  f"{v},{lo},{hi},0.02,0.05,200,20260905,False,False\n"
                  for scope, v, lo, hi in (("arm", -0.01621, -0.04461, 0.01752),
                                           ("pre-flag", 0.02273, -0.02591, 0.07411),
                                           ("flagged", -0.02378, -0.04781, 0.00991)))
H4_STATEMENT = ("H4 is undetermined: −0.0162 [−0.0446, +0.0175], pre-flag +0.0227 [−0.0259, "
                "+0.0741], flagged −0.0238 [−0.0478, +0.0099].")


def h4_criterion(name: str, pre_flag_line: int) -> pt.Criterion:
    return pt.Criterion("Freddie Mac", "H4", "C-001", "tabpfn", pt.H4, 4,
                        pt.h4_line(name, "tabpfn", 2), "H4 is undetermined",
                        scoped=(pt.Scoped("pre-flag", pt.h4_line(name, "tabpfn", pre_flag_line,
                                                                 "pre-flag")),
                                pt.Scoped("flagged", pt.h4_line(name, "tabpfn", 4, "flagged"))))


def test_t2_scoped_sub_lines_read_and_bound(tmp_path):
    name = run(tmp_path, control="gbm-50k")
    (tmp_path / name / "paired.csv").write_text(H4_HEADER + H4_ROWS, encoding="utf-8")
    [entry] = lines(tmp_path, h4_criterion(name, 3), ledger(tmp_path, H4_STATEMENT))
    assert [s["ratio"]["value"] for s in entry["scoped"]] == ["+0.0227", "−0.0238"]


def test_t2_scoped_sub_line_off_its_cited_line_is_refused(tmp_path):
    name = run(tmp_path, control="gbm-50k")
    (tmp_path / name / "paired.csv").write_text(H4_HEADER + H4_ROWS, encoding="utf-8")
    with pytest.raises(SystemExit, match="the selector reads line 3, the mapping cites 4"):
        lines(tmp_path, h4_criterion(name, 4), ledger(tmp_path, H4_STATEMENT))


def test_t2_equal_weight_line_is_refused_though_the_row_writes_it(tmp_path):
    name = run(tmp_path, control="gbm-50k")
    builds = ("E,all,,builds,psi,tabpfn - gbm-50k,True,-0.00121,-0.00362,0.00041,0.001,0.05,"
              "200,20260905,False,False\n")
    (tmp_path / name / "paired.csv").write_text(HEADER + ROWS + builds, encoding="utf-8")
    both = STATEMENT + " With every build weighted alike −0.0012 [−0.0036, +0.0004]."
    wrong = pt.Criterion("Freddie Mac", "H3", "C-001", "tabpfn", pt.PSI, 4,
                         pt.Reading(name, "paired.csv",
                                    pt.pick(scope="builds", cohorts="all", draw="", metric="psi",
                                            pair="tabpfn - gbm-50k"), 4),
                         "H3's kill fires for TabPFN")
    with pytest.raises(SystemExit, match="the line reads scope 'builds'"):
        lines(tmp_path, wrong, ledger(tmp_path, both))
    assert lines(tmp_path, criterion(name), ledger(tmp_path, both))[0]["ratio"]["value"] \
        == "+0.0092"


def test_mapping_names_one_line_per_criterion_and_model():
    keys = [(c.claim, c.model) for c in pt.CRITERIA]
    assert len(keys) == len(set(keys)) == 18
    assert {c.claim for c in pt.CRITERIA} == {"C-021", "C-007", "C-038", "C-034", "C-025",
                                              "C-027", "C-042", "C-041", "C-028"}
    assert all((c.nominal is None) == (c.book == "Lending Club") for c in pt.CRITERIA)


LC_H4 = ROOT / pt.LC_BETWEEN / "paired.csv"


def test_lending_club_h4_lines_mirror_freddie_mac_h4():
    """C-034's two lines pin what C-041's pin: kind h4 on the Cox-slope deviation, the arm
    scope, the cohorts held fixed and no draw held, at the shipped temperature."""
    by_key = {(c.claim, c.model): c for c in pt.CRITERIA}
    for model, line in (("tabpfn", 25), ("tabicl", 26)):
        lc, fm = by_key[("C-034", model)], by_key[("C-041", model)]
        assert (lc.book, lc.hypothesis, lc.statistic, lc.decimals) == \
            ("Lending Club", "H4", pt.H4, fm.decimals)
        assert lc.reading == pt.h4_line(pt.LC_BETWEEN, model, line)
        assert dict(lc.reading.select) == dict(fm.reading.select)
        assert lc.nominal is None and lc.scoped == ()


@pytest.mark.skipif(not LC_H4.exists(), reason="the recorded run is not here")
def test_lending_club_h4_lines_read_their_ledger_row():
    criteria = [c for c in pt.CRITERIA if c.claim == "C-034"]
    got = pt.t2_lines(ROOT, criteria, pt.load_sources(pt.LEDGER), pt.ledger_evidence(pt.LEDGER))
    assert [(e["model"], e["ratio"]["source"]["line"], e["ratio"]["value"],
             e["ratio"]["interval"]) for e in got] == [
        ("tabpfn", 25, "−0.0412", ["−0.0885", "+0.0181"]),
        ("tabicl", 26, "−0.0447", ["−0.0916", "+0.0167"])]


@pytest.mark.skipif(not LC_H4.exists(), reason="the recorded run is not here")
def test_lending_club_h4_at_temperature_one_is_not_a_criterion_line():
    """The run reads the rows at 1.0 beside the criterion, not as it; a line citing one is
    refused though the ledger row writes its figures."""
    beside = pt.Criterion("Lending Club", "H4", "C-034", "tabpfn@t1", pt.H4, 4,
                          pt.h4_line(pt.LC_BETWEEN, "tabpfn@t1", 28), pt.LC_H4_VERDICT)
    with pytest.raises(SystemExit, match="does not read tabpfn@t1 as a criterion row"):
        pt.t2_lines(ROOT, [beside], pt.load_sources(pt.LEDGER), pt.ledger_evidence(pt.LEDGER))


@pytest.mark.parametrize("cut", ["H3's kill fires", "kill fires for TabPFN"])
def test_t2_truncated_verdict_is_refused(tmp_path, cut):
    """A verdict cut at either end is still a substring of the row; it is refused."""
    name = run(tmp_path)
    crit = pt.Criterion("Freddie Mac", "H3", "C-001", "tabpfn", pt.PSI, 4,
                        pt.arm_line(name, "psi", "tabpfn - gbm-50k", 2), cut)
    with pytest.raises(SystemExit, match="not a whole phrase"):
        lines(tmp_path, crit, ledger(tmp_path, STATEMENT))


def test_whole_phrase_boundaries():
    row = ("H4, that the window helps, is killed inside the interval for both models at both "
           "settings, as registered; no kill fires for TabPFN.")
    assert pt.whole_phrase("killed inside the interval for both models at both settings", row)
    assert not pt.whole_phrase("killed inside the interval for both models", row)
    assert pt.whole_phrase("no kill fires for TabPFN", row)
    assert not pt.whole_phrase("kill fires for TabPFN", row)
    assert not pt.whole_phrase("fires for TabPFN", row)


def test_every_mapped_verdict_is_a_whole_phrase_of_its_row():
    sources = pt.load_sources(pt.LEDGER)
    for c in pt.CRITERIA:
        for verdict in filter(None, (c.verdict, c.nominal_verdict)):
            assert pt.whole_phrase(verdict, sources.rows[c.claim]), (c.claim, verdict)


def test_t2_printed_verdict_cut_short_is_refused(tmp_path):
    name = run(tmp_path, control="gbm-50k")
    got = lines(tmp_path, criterion(name), ledger(tmp_path, STATEMENT))
    latex = pt.t2_latex(got)
    pt.check_printed_verdicts(latex, got)
    cut = latex.replace("H3's kill fires for TabPFN", "H3's kill fires")
    with pytest.raises(SystemExit, match="prints the verdict \"H3's kill fires\""):
        pt.check_printed_verdicts(cut, got)
