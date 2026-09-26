"""A figure in the paper must be the one its marker's source writes, with its sign.

The typical figure of this paper is a signed difference with its interval,
quoted from a ledger row; most assertions here build that figure and then the
mistakes that keep every other gate green — the sign flipped, the digits
rounded, the row next to the cited one, a superseded row.
"""
import importlib.util
import pathlib

import pytest

SPEC = importlib.util.spec_from_file_location(
    "check_paper_figures",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_paper_figures.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

LEDGER = """| ID | Statement | Setting | Evidence | Status |
| --- | --- | --- | --- | --- |
| C-001 | TabPFN − GBM-50k on the stability index +0.0092 [+0.0083, +0.0103]; the ratio matrix reads −0.0052 [−0.0110, +0.0007]; the other seed reads −0.0103 [−0.0200, −0.0010]; 2,260,668 loans, 23.2% pinned. | A setting of 12,345 rows. | experiments/x | active |
| C-002 | TabICL − GBM-50k on the slope −0.00049. | Lending Club. | experiments/y | active |
| C-003 | An older reading, +0.0312. | Freddie Mac. | experiments/z | superseded by C-004 |
| C-004 | The corrected reading, +0.0311. | Freddie Mac. | experiments/z | active |
"""
PREREG = """# EXP-901 — a design

## Setting

The label window is twelve months; each quarter holds 20,000 loans, seed 20260902.
A cell above 8.4 × 10⁻³ refuses the build; rows are checked to 1e-6.

## Kill criteria

Fires at 0.05 of the rows.
"""
PRIOR_ART = ("| arXiv:2605.99999 — Someone, \"A paper\" | 43 datasets, 5 folds "
             "| **verified** 2026-09-01, full text |\n"
             "| arXiv:2605.88888 — Other, \"An abstract\" | 12 datasets | abstract-only |\n")
# An identifier the synthetic ledger does not define, built so the claim gate
# does not read it as a citation.
UNKNOWN = "C-" + "999"
MODULE = "CONTEXT_ROWS = 50_000\nCONTEXT_SEEDS = (20260911, 20260912)\n"


@pytest.fixture
def sources(tmp_path, monkeypatch):
    ledger = tmp_path / "CLAIMS.md"
    ledger.write_text(LEDGER, encoding="utf-8")
    experiments = tmp_path / "experiments"
    experiments.mkdir()
    (experiments / "EXP-901-design.md").write_text(PREREG, encoding="utf-8")
    prior = tmp_path / "prior-art.md"
    prior.write_text(PRIOR_ART, encoding="utf-8")
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "vintage.py").write_text(MODULE, encoding="utf-8")
    monkeypatch.setattr(gate, "LEDGER", ledger)
    monkeypatch.setattr(gate, "EXPERIMENTS", experiments)
    monkeypatch.setattr(gate, "PRIOR_ART", prior)
    monkeypatch.setattr(gate, "PACKAGE", package)
    return gate.Sources()


def unbound(tmp_path, sources, tex):
    path = tmp_path / "section.tex"
    path.write_text(tex, encoding="utf-8")
    _, count, _, report = gate.check(path, sources)
    return count, report


def test_the_typical_figure_binds(tmp_path, sources):
    tex = ("% FIG: C-001\n"
           "The difference is $+0.0092$ [$+0.0083$, $+0.0103$] on the nominal matrix.\n")
    assert unbound(tmp_path, sources, tex)[0] == 0


def test_the_typical_figure_with_its_sign_flipped_is_unbound(tmp_path, sources):
    tex = "% FIG: C-001\nThe difference is $-0.0092$ [$+0.0083$, $+0.0103$].\n"
    assert unbound(tmp_path, sources, tex)[0] == 1


def test_a_negative_figure_written_unsigned_is_unbound(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: C-002\nThe slope is 0.00049.\n")[0] == 1
    assert unbound(tmp_path, sources, "% FIG: C-002\nThe slope is $-0.00049$.\n")[0] == 0


def test_a_rounded_figure_is_unbound(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: C-001\nIt is $+0.009$.\n")[0] == 1


def test_a_figure_of_a_row_the_marker_does_not_name_is_unbound(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: C-001\nThe slope is $-0.00049$.\n")[0] == 1


def test_a_superseded_row_is_refused(tmp_path, sources):
    count, report = unbound(tmp_path, sources, "% FIG: C-003\nIt reads $+0.0312$.\n")
    assert count >= 1 and any("C-004" in line for line in report)
    assert unbound(tmp_path, sources, "% FIG: C-004\nIt reads $+0.0311$.\n")[0] == 0


def test_an_unknown_row_is_reported(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: " + UNKNOWN + "\nIt reads 0.5.\n")[0] >= 1


def test_a_figure_under_no_marker_is_unbound(tmp_path, sources):
    assert unbound(tmp_path, sources, "It reads $+0.0092$.\n")[0] == 1


def test_a_blank_line_ends_the_marker(tmp_path, sources):
    tex = "% FIG: C-001\nIt reads $+0.0092$.\n\nAnd again $+0.0092$.\n"
    assert unbound(tmp_path, sources, tex)[0] == 1


def test_a_none_marker_admits_names_and_no_figure(tmp_path, sources):
    assert unbound(tmp_path, sources,
                   "% FIG: none\nGBM-50k and H3 on 2015H1-E, ADR-0006.\n")[0] == 0
    assert unbound(tmp_path, sources, "% FIG: none\nIt reads 0.5.\n")[0] == 1


def test_latex_thousands_and_percent_bind(tmp_path, sources):
    tex = "% FIG: C-001\nOf 2{,}260{,}668 loans, 23.2\\% are pinned.\n"
    assert unbound(tmp_path, sources, tex)[0] == 0


def test_keys_and_labels_are_not_figures(tmp_path, sources):
    tex = ("% FIG: none\nAs \\citet{baesens2026foundation} note in "
           "Section~\\ref{sec:h2025} and Figure~\\ref{fig:f3}.\n")
    assert unbound(tmp_path, sources, tex)[0] == 0


def test_a_power_of_ten_binds_with_its_exponent(tmp_path, sources):
    ok = "% FIG: EXP-901 §Setting\nA cell above $8.4\\times10^{-3}$ refuses; checked to $10^{-6}$.\n"
    assert unbound(tmp_path, sources, ok)[0] == 0
    wrong = "% FIG: EXP-901 §Setting\nA cell above $8.4\\times10^{-4}$ refuses.\n"
    assert unbound(tmp_path, sources, wrong)[0] == 1


def test_a_heading_narrows_the_document(tmp_path, sources):
    tex = "% FIG: EXP-901 §Setting (label)\nIt fires at 0.05.\n"
    assert unbound(tmp_path, sources, tex)[0] == 1
    tex = "% FIG: EXP-901\nIt fires at 0.05.\n"
    path = tmp_path / "section.tex"
    path.write_text(tex, encoding="utf-8")
    _, count, weak, _ = gate.check(path, sources)
    assert count == 0 and weak == 1


def test_an_unknown_heading_is_reported(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: EXP-901 §Nowhere\nIt holds 20,000.\n")[0] >= 1


def test_a_prior_art_row_and_a_constant_bind(tmp_path, sources):
    tex = ("% FIG: arXiv:2605.99999\nIt uses 43 datasets and 5 folds.\n"
           "% FIG: vintage.CONTEXT_ROWS, vintage.CONTEXT_SEEDS\n"
           "Contexts of 50,000 rows under seeds 20260911 and 20260912.\n")
    assert unbound(tmp_path, sources, tex)[0] == 0
    tex = "% FIG: arXiv:2605.99999\nIt uses 44 datasets.\n"
    assert unbound(tmp_path, sources, tex)[0] == 1


def test_a_marker_naming_nothing_is_reported(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: design constant (context size)\nIt is 50,000.\n")[0] >= 1


def test_a_marker_naming_nothing_over_no_figure_passes(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: model name only\nTabICLv2 reads it.\n")[0] == 0


def test_a_landscape_row_is_named_by_its_first_cell(tmp_path, sources, monkeypatch):
    prior = tmp_path / "prior-art-named.md"
    prior.write_text("| Yurdakul, thesis, 2018 | the 0.10/0.25 rule, 1K to 50K rows "
                     "| verified from source |\n"
                     "| Other, 2020 | 0.30 | **verified** 2026-09-01 |\n", encoding="utf-8")
    monkeypatch.setattr(gate, "PRIOR_ART", prior)
    tex = "% FIG: prior-art:Yurdakul\nThresholds of 0.10 and 0.25, from 1,000 to 50,000 rows.\n"
    assert unbound(tmp_path, sources, tex)[0] == 0
    assert unbound(tmp_path, sources, "% FIG: prior-art:Yurdakul\nA threshold of 0.30.\n")[0] == 1


def test_an_unverified_landscape_row_is_refused(tmp_path, sources):
    count, report = unbound(tmp_path, sources, "% FIG: arXiv:2605.88888\nIt uses 12 datasets.\n")
    assert count >= 1 and any("not verified" in line for line in report)


def test_table_structure_is_not_a_figure(tmp_path, sources):
    tex = ("% FIG: none\n"
           "\\begin{tabular}{lllp{3.4cm}r}\n"
           "Model & \\multicolumn{3}{c}{Ratio matrix} \\\\\n"
           "\\cmidrule(lr){5-7} \\cmidrule{8-10}\n")
    assert unbound(tmp_path, sources, tex)[0] == 0


def recorded_run(tmp_path, monkeypatch, dirty=False):
    run = tmp_path / "experiments" / "2026-01-01-run"
    run.mkdir(parents=True)
    (run / "table.csv").write_text("model,seed,auc_mean,gap\n"
                                   "gbm,20260911,0.70064218,-0.00731\n", encoding="utf-8")
    (run / "manifest.json").write_text(
        '{"git_dirty": %s, "exit_code": 0}' % ("true" if dirty else "false"), encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    return "% FIG: experiments/2026-01-01-run/table.csv\n"


def test_a_run_file_binds_a_rounded_value_under_its_sign(tmp_path, sources, monkeypatch):
    marker = recorded_run(tmp_path, monkeypatch)
    assert unbound(tmp_path, sources, marker + "AUC 0.7006 & $-0.0073$ \\\n")[0] == 0
    assert unbound(tmp_path, sources, marker + "A gap of $+0.0073$.\n")[0] == 1
    assert unbound(tmp_path, sources, marker + "AUC 0.7007.\n")[0] == 1


def test_a_run_file_does_not_admit_a_key_column(tmp_path, sources, monkeypatch):
    marker = recorded_run(tmp_path, monkeypatch)
    assert unbound(tmp_path, sources, marker + "Under seed 20260911.\n")[0] == 1


def test_a_run_file_from_a_dirty_tree_is_refused(tmp_path, sources, monkeypatch):
    marker = recorded_run(tmp_path, monkeypatch, dirty=True)
    count, report = unbound(tmp_path, sources, marker + "AUC 0.7006.\n")
    assert count >= 1 and any("dirty" in line for line in report)


def test_a_figure_only_in_a_rows_setting_is_unbound(tmp_path, sources):
    # The Setting's figures are not tied to the run by check_figures.py.
    assert unbound(tmp_path, sources, "% FIG: C-001\nOn 12,345 rows.\n")[0] == 1


def test_a_quoted_heading_may_hold_a_comma(tmp_path, sources, monkeypatch):
    doc = sources.document("EXP-901", None)[0] + (
        "\n### Amendment of 2026-01-01\n\nA floor of 0.20.\n"
        "\n### Amendment of 2026-01-01, late\n\nA floor of 0.30.\n")
    (tmp_path / "experiments" / "EXP-901-design.md").write_text(doc, encoding="utf-8")
    tex = '% FIG: EXP-901 §"Amendment of 2026-01-01, late"\nA floor of 0.30.\n'
    assert unbound(tmp_path, sources, tex)[0] == 0
    tex = '% FIG: EXP-901 §"Amendment of 2026-01-01, late"\nA floor of 0.20.\n'
    assert unbound(tmp_path, sources, tex)[0] == 1


def test_an_interval_binds_to_one_interval_of_the_row(tmp_path, sources, capsys):
    tex = ("% FIG: C-001\n"
           "The difference is $+0.0092$ $[+0.0083, +0.0103]$; the ratio matrix "
           "reads $-0.0052$ $[-0.0110, +0.0007]$.\n")
    path = tmp_path / "section.tex"
    path.write_text(tex, encoding="utf-8")
    _, count, _, report = gate.check(path, sources, explain=True)
    assert count == 0
    assert any("interval +0.0092 [+0.0083, +0.0103] <- C-001" in line for line in report)


def test_a_bound_flipped_onto_another_intervals_figure_is_unbound(tmp_path, sources):
    """+0.0103 → −0.0103: the row writes −0.0103, as another interval's figure."""
    tex = "% FIG: C-001\nThe difference is $+0.0092$ $[+0.0083, -0.0103]$.\n"
    count, report = unbound(tmp_path, sources, tex)
    assert count == 1 and "not written whole" in report[0]


def test_a_bound_taken_from_another_interval_is_unbound(tmp_path, sources):
    # +0.0007 is the upper bound of the ratio matrix's interval, not of this one.
    tex = "% FIG: C-001\nThe difference is $+0.0092$ $[+0.0083, +0.0007]$.\n"
    assert unbound(tmp_path, sources, tex)[0] == 1


def test_bounds_written_alone_bind_to_one_intervals_pair(tmp_path, sources):
    assert unbound(tmp_path, sources, "% FIG: C-001\nIt holds zero, $[-0.0110, +0.0007]$.\n")[0] == 0
    assert unbound(tmp_path, sources, "% FIG: C-001\nIt holds zero, $[-0.0200, +0.0007]$.\n")[0] == 1


def test_an_interval_in_a_table_row_and_across_lines(tmp_path, sources):
    row = "% FIG: C-001\nH3 & TabPFN & $+0.0092$ & $[+0.0083, +0.0103]$ & fires \\\\\n"
    assert unbound(tmp_path, sources, row)[0] == 0
    assert unbound(tmp_path, sources, row.replace("+0.0103]", "+0.0007]"))[0] == 1
    wrapped = "% FIG: C-001\nThe difference is $+0.0092$\n$[+0.0083, +0.0103]$ there.\n"
    assert unbound(tmp_path, sources, wrapped)[0] == 0
    # The ratio matrix's figure before the stability index's pair: each binds
    # on its own, so the wrong pairing is seen only if the lines are joined.
    crossed = "% FIG: C-001\nThe difference is $-0.0052$\n$[+0.0083, +0.0103]$ there.\n"
    assert unbound(tmp_path, sources, crossed)[0] == 1


def test_a_run_file_binds_an_interval_through_one_row(tmp_path, sources, monkeypatch):
    run = tmp_path / "experiments" / "2026-01-01-run"
    run.mkdir(parents=True)
    (run / "table.csv").write_text(
        "protocol,model,auc_mean,auc_min,auc_max,gini_mean,gini_min,gini_max\n"
        "in time,gbm,0.70064,0.69408,0.71060,0.40128,0.38817,0.42121\n"
        "in time,scorecard,0.68534,0.67210,0.69254,0.37067,0.34420,0.38509\n",
        encoding="utf-8")
    (run / "manifest.json").write_text('{"git_dirty": false, "exit_code": 0}', encoding="utf-8")
    monkeypatch.setattr(gate, "ROOT", tmp_path)
    marker = "% FIG: experiments/2026-01-01-run/table.csv\n"
    assert unbound(tmp_path, sources, marker + "AUC & 0.7006 [0.6941, 0.7106] \\\\\n")[0] == 0
    # The scorecard's upper bound in the GBM's cell: every figure is in the run.
    assert unbound(tmp_path, sources, marker + "AUC & 0.7006 [0.6941, 0.6925] \\\\\n")[0] == 1
    # The GBM's Gini bounds under its AUC mean: one row, the wrong pair.
    assert unbound(tmp_path, sources, marker + "AUC & 0.7006 [0.3882, 0.4212] \\\\\n")[0] == 1
