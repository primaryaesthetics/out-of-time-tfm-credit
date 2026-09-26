"""A figure must come from the place its row cites, and not merely exist.

Every assertion here constructs the mistake the checker is for. The one that
matters most is `test_a_value_elsewhere_in_the_run_is_not_admitted`: a number
that appears in the run but not under any path the row names is exactly the
error the claim gate cannot see, because it opens no output file.
"""
import importlib.util
import json
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "check_figures",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "check_figures.py")
check_figures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_figures)

SUMMARY = {
    "loans": 1362500,
    "redated": {"count": 7095, "share": 0.00521},
    "windows": {"12": {"label": {"labelled": 1298994, "defaults": 6697},
                       "other": {"defaults": 4555}}},
}
ROWS = ("metric,seed,value,ci_lo,ci_hi,se\n"
        "gini,20260911,0.7431,,,\n"
        "gini,20260912,0.6822,,,\n"
        "slope,20260911,-0.001047,,,\n"
        "diff,20260905,-0.0162,-0.0398,0.0071,0.0115\n"
        "diff,20260906,0.0300,0.0100,0.0500,0.01624655\n")


def build(tmp_path, statement, table, derivations=None):
    run = tmp_path / "run"
    run.mkdir(exist_ok=True)
    (run / "summary.json").write_text(json.dumps(SUMMARY), encoding="utf-8")
    (run / "paired.csv").write_text(ROWS, encoding="utf-8")
    draft = tmp_path / "rows.md"
    draft.write_text(
        f"## C-001 — a row\n\n"
        f"**Evidence** `{run.as_posix()}` · **Status** `active`\n\n"
        f"**Statement.** {statement}\n\n"
        f"**Setting.** None.\n\n"
        f"| number | file | scope | line |\n| --- | --- | --- | --- |\n{table}\n",
        encoding="utf-8")
    if derivations:
        (tmp_path / "derivations.py").write_text(derivations, encoding="utf-8")
    return draft


def unbound(tmp_path, statement, table, derivations=None):
    draft = build(tmp_path, statement, table, derivations)
    text = draft.read_text(encoding="utf-8")
    return check_figures.check_row(
        draft, text, "C-001", check_figures.load_derivations(draft))


PATH_ROW = "| the count | `summary.json` | the book | `windows.12.label` |"


def test_a_figure_under_a_cited_key_path_is_bound(tmp_path):
    assert unbound(tmp_path, "It labels 1,298,994 loans with 6,697 defaults.",
                   PATH_ROW) == 0


def test_a_value_elsewhere_in_the_run_is_not_admitted(tmp_path):
    # 4,555 is in the summary, under a path this row does not cite.
    assert unbound(tmp_path, "It labels 1,298,994 loans with 4,555 defaults.",
                   PATH_ROW) == 1


def test_an_absent_key_path_is_reported(tmp_path):
    assert unbound(tmp_path, "It labels 1,298,994 loans.",
                   "| x | `summary.json` | s | `windows.12.missing` |") >= 1


def test_a_share_may_be_written_as_a_percentage(tmp_path):
    assert unbound(tmp_path, "The share is 0.521% of the book.",
                   "| the share | `summary.json` | the book | `redated` |") == 0


def test_a_csv_line_binds_only_its_own_row(tmp_path):
    table = "| the gini | `paired.csv` | the arm | 2 |"
    assert unbound(tmp_path, "Its Gini is 0.7431 there.", table) == 0
    assert unbound(tmp_path, "Its Gini is 0.6822 there.", table) == 1


def test_a_key_column_does_not_admit_a_figure(tmp_path):
    # 20260911 is a draw label in a key column, not a measurement.
    assert unbound(tmp_path, "It read 20260911 cells.",
                   "| the gini | `paired.csv` | the arm | 2 |") == 1


def test_a_derived_figure_needs_its_rule(tmp_path):
    statement = "The two readings differ by 2,142 defaults."
    table = "| the difference | `summary.json` | twelve months | `windows.12` |"
    assert unbound(tmp_path, statement, table) == 1
    rule = (
        "def derive(load, path):\n"
        "    if path == 'windows.12':\n"
        "        node = load(path)\n"
        "        return [node['label']['defaults'] - node['other']['defaults']]\n"
        "    return []\n")
    assert unbound(tmp_path, statement, table, derivations=rule) == 0


def test_an_ordinal_is_not_a_figure(tmp_path):
    assert unbound(tmp_path, "Its 95th percentile is 1,298,994 loans.",
                   PATH_ROW) == 0


SLOPE_ROW = "| the slope | `paired.csv` | the arm | 4 |"


def test_a_negative_figure_binds_to_the_line_that_produces_it(tmp_path):
    assert unbound(tmp_path, "The slope is −0.001047 on the arm.", SLOPE_ROW) == 0


def test_a_figure_written_with_the_opposite_sign_is_not_admitted(tmp_path):
    """The cited line holds the magnitude; the row claims it under the other sign."""
    assert unbound(tmp_path, "The slope is +0.001047 on the arm.", SLOPE_ROW) == 1


def test_an_unsigned_figure_does_not_bind_a_negative_value(tmp_path):
    """A bare magnitude reads as positive; the stored value is negative."""
    assert unbound(tmp_path, "The slope is 0.001047 on the arm.", SLOPE_ROW) == 1


def test_a_hyphen_inside_a_model_name_is_not_a_sign(tmp_path):
    """GBM-50k must not be read as the figure -50, which no cited line produces."""
    assert unbound(tmp_path, "GBM-50k reads a Gini of 0.7431.",
                   "| the gini | `paired.csv` | the arm | 2 |") == 0


def test_a_figure_opening_a_wrapped_line_is_still_checked(tmp_path):
    """A line break is not the inside of a name.

    The statement wraps after a word, so the character before the figure is a
    newline preceded by a letter. Read with `$` rather than `\\Z` that looks
    like `GBM-` and the figure is skipped: the checker then reports one figure
    fewer than the statement holds and calls an unbound number bound.
    """
    assert unbound(tmp_path, "The slope of the arm\n0.6822 is not the gini.",
                   SLOPE_ROW) == 1
    assert check_figures.figures("the arm\n0.6822 is") == ["0.6822"]


PAIR_ROW = "| the difference | `paired.csv` | the arm | 5 |"


def test_a_signed_interval_binds_and_its_flip_does_not(tmp_path):
    """The figure this project writes most: a signed difference with its interval."""
    assert unbound(tmp_path, "It reads −0.0162 [−0.0398, +0.0071] on the arm.",
                   PAIR_ROW) == 0
    assert unbound(tmp_path, "It reads +0.0162 [−0.0398, +0.0071] on the arm.",
                   PAIR_ROW) == 1


def test_a_standard_error_does_not_admit_a_figure(tmp_path):
    assert unbound(tmp_path, "Its standard error is 0.0115.", PAIR_ROW) == 1


def test_a_flipped_figure_is_not_rescued_by_another_lines_standard_error(tmp_path):
    """Line 6's se of 0.01624655 once admitted the flip +0.0162 of line 5's value."""
    assert unbound(tmp_path, "It reads +0.0162 on the arm.",
                   "| the difference | `paired.csv` | the arm | 5-6 |") == 1


def test_a_reversed_pair_binds_only_negated(tmp_path):
    table = "| the difference, stored B − A | `paired.csv` | the arm | 5 (reversed) |"
    assert unbound(tmp_path, "A − B reads +0.0162 [−0.0071, +0.0398].", table) == 0
    assert unbound(tmp_path, "A − B reads −0.0162 on the arm.", table) == 1


def test_a_date_is_not_a_figure():
    assert check_figures.figures("the note of 2026-09-12 and 2013-06 to 2017-06") == []


def test_the_base_of_a_power_of_ten_is_not_a_figure():
    assert check_figures.figures("within 1.36 × 10⁻⁷ of it") == ["1.36"]


def test_explain_names_the_place_that_binds(tmp_path, capsys):
    draft = build(tmp_path, "It reads −0.0162 on the arm.", PAIR_ROW)
    check_figures.check_row(draft, draft.read_text(encoding="utf-8"), "C-001",
                            None, explain=True)
    assert "paired.csv l.5 value" in capsys.readouterr().out


def test_a_provenance_row_the_parser_cannot_read_is_reported(tmp_path):
    """Two files in one cell dropped the row silently, and its figures bound elsewhere or not at all."""
    table = ("| the gini | `paired.csv` | the arm | 2 |\n"
             "| the slope | `paired.csv`, `summary.json` | the arm | 4 |")
    assert unbound(tmp_path, "Its Gini is 0.7431 there.", table) == 1


# The typical figure of an H4 row, as `paired.csv` of an arm pooling stores it:
# the contrast of each model with the control, and a model's own E − R whose
# lower bound is the negation of the first line's upper bound.
PAIRED = (
    "arm,cohorts,draw,scope,metric,pair,is_difference,value,ci_lo,ci_hi,se,"
    "alpha,resamples,seed,excludes_zero,reads_derived\n"
    "between,fixed,all,arm,auc,tabpfn - gbm-50k,True,-0.041183,-0.088512,0.018143,"
    "0.0271,0.05,200,20260905,False,False\n"
    "between,fixed,all,arm,auc,tabicl - gbm-50k,True,-0.044702,-0.091577,0.016711,"
    "0.0277,0.05,200,20260905,False,False\n"
    "between,fixed,all,arm,auc,tabpfn E - R,True,-0.001104,-0.018092,0.015847,"
    "0.0088,0.05,200,20260905,False,False\n")
H4_ROWS = "| the H4 rows | `paired.csv` | the arm | 2-4 |"


def h4(tmp_path, statement, table=H4_ROWS):
    draft = build(tmp_path, statement, table)
    (tmp_path / "run" / "paired.csv").write_text(PAIRED, encoding="utf-8")
    return check_figures.check_row(draft, draft.read_text(encoding="utf-8"), "C-001", None)


def test_the_typical_interval_binds_to_its_line(tmp_path):
    assert h4(tmp_path, "TabPFN − GBM-50k is −0.0412 [−0.0885, +0.0181] and TabICL "
                        "−0.0447 [−0.0916, +0.0167]; TabPFN's own E − R is −0.0011 "
                        "[−0.0181, +0.0158].") == 0


def test_a_bound_flipped_onto_another_lines_value_is_caught(tmp_path, capsys):
    """+0.0181 → −0.0181: each figure is admitted, line 4 holding −0.0181 as its ci_lo."""
    statement = ("TabPFN − GBM-50k is −0.0412 [−0.0885, −0.0181]; TabPFN's own E − R "
                 "is −0.0011 [−0.0181, +0.0158].")
    assert h4(tmp_path, statement) == 1
    out = capsys.readouterr().out
    assert "0 unbound" in out
    assert "interval not from one place: −0.0412 [−0.0885, −0.0181]" in out


def test_a_bound_taken_from_another_line_is_caught(tmp_path):
    # +0.0167 is line 3's upper bound, quoted as line 2's.
    assert h4(tmp_path, "TabPFN − GBM-50k is −0.0412 [−0.0885, +0.0167] and TabICL "
                        "−0.0447 [−0.0916, +0.0167].") == 1


def test_bounds_written_alone_must_be_one_lines_pair(tmp_path):
    assert h4(tmp_path, "Resampled, it holds zero ([−0.0916, +0.0167]).") == 0
    assert h4(tmp_path, "Resampled, it holds zero ([−0.0916, +0.0181]).") == 1


def test_a_figure_beside_the_wrong_lines_interval_is_caught(tmp_path):
    assert h4(tmp_path, "TabICL − GBM-50k is −0.0412 [−0.0916, +0.0167].") == 1


def test_an_interval_wrapped_across_lines_is_still_one_interval(tmp_path):
    assert h4(tmp_path, "TabPFN − GBM-50k is −0.0412\n[−0.0885, +0.0181] on the arm.") == 0
    # Line 2's figure before line 3's pair: each binds on its own, so the
    # wrong pairing is seen only if the break is read through.
    assert h4(tmp_path, "TabICL − GBM-50k is −0.0412\n[−0.0916, +0.0167] on the arm.") == 1


def test_an_unsigned_bound_does_not_bind_a_negative_one(tmp_path):
    """[0.0885, +0.0181] for a stored [−0.0885, +0.0181] reads a pair that holds zero as one that excludes it."""
    assert h4(tmp_path, "TabPFN − GBM-50k is −0.0412 [0.0885, +0.0181].") == 1
    assert h4(tmp_path, "TabPFN − GBM-50k is 0.0412 [−0.0885, +0.0181].") == 1
    assert h4(tmp_path, "TabPFN − GBM-50k is −0.0412 [−0.0885, 0.0181].") == 0


def test_a_reversed_line_turns_its_interval_over(tmp_path):
    table = "| GBM-50k − TabPFN, stored the other way | `paired.csv` | the arm | 2 (reversed) |"
    assert h4(tmp_path, "GBM-50k − TabPFN is +0.0412 [−0.0181, +0.0885].", table) == 0
    # Each figure is admitted negated, but the bounds are not turned over.
    assert h4(tmp_path, "GBM-50k − TabPFN is +0.0412 [+0.0885, −0.0181].", table) == 1


def test_explain_names_the_line_that_writes_the_interval(tmp_path, capsys):
    draft = build(tmp_path, "TabPFN − GBM-50k is −0.0412 [−0.0885, +0.0181].", H4_ROWS)
    (tmp_path / "run" / "paired.csv").write_text(PAIRED, encoding="utf-8")
    check_figures.check_row(draft, draft.read_text(encoding="utf-8"), "C-001",
                            None, explain=True)
    assert ("interval: −0.0412 [−0.0885, +0.0181]  <- paired.csv l.2 value/ci_lo/ci_hi"
            in capsys.readouterr().out)


CELLS = ("build_id,model,rows,observed_over_expected,bootstrap_lo,bootstrap_hi,"
         "cox_slope,cox_slope_lo,cox_slope_hi\n"
         "2015H1-E,scorecard,20000,0.9571,0.9102,1.0133,0.8682,0.8457,0.8969\n")


def test_a_named_pair_takes_its_own_columns_figure(tmp_path):
    draft = build(tmp_path, "The scorecard's Cox slope is 0.8682 [0.8457, 0.8969].",
                  "| the slope | `cells.csv` | the build | 2 |")
    (tmp_path / "run" / "cells.csv").write_text(CELLS, encoding="utf-8")
    text = draft.read_text(encoding="utf-8")
    assert check_figures.check_row(draft, text, "C-001", None) == 0
    # O/E of the same line beside the slope's bounds: one line, the wrong pair.
    wrong = text.replace("0.8682 [", "0.9571 [")
    assert check_figures.check_row(draft, wrong, "C-001", None) == 1


def test_digits_of_a_name_are_not_an_intervals_figure():
    assert check_figures.intervals("on 2014H1 [−0.0885, +0.0181]")[0][0] is None
    assert check_figures.intervals("GBM-50 [−0.0885, +0.0181]")[0][0] is None
    assert check_figures.intervals("1.919% [1.795, 2.052]")[0][:3] == ("1.919", "1.795", "2.052")


CRITERIA = {"criterion_1": {"starred_pairs": [
    {"pair": "tabpfn - gbm", "out_of_time": 0.0197, "ci": [0.0139, 0.0251]},
    {"pair": "tabicl - gbm", "out_of_time": 0.0233, "ci": [0.0168, 0.0317]},
]}}


def test_a_json_interval_comes_from_one_object(tmp_path):
    """A key path over several objects is not one place: each object is."""
    table = "| the starred pairs | `criteria.json` | the run | `criterion_1` |"
    draft = build(tmp_path, "TabPFN − GBM reads +0.0197 [+0.0139, +0.0251].", table)
    (tmp_path / "run" / "criteria.json").write_text(json.dumps(CRITERIA), encoding="utf-8")
    text = draft.read_text(encoding="utf-8")
    assert check_figures.check_row(draft, text, "C-001", None) == 0
    # The upper bound of the next object, and a bound read as the figure.
    assert check_figures.check_row(
        draft, text.replace("+0.0251]", "+0.0317]"), "C-001", None) == 1
    assert check_figures.check_row(
        draft, text.replace("+0.0197 [", "+0.0139 ["), "C-001", None) == 1


TRAJECTORY = {"windows": {"12": {
    "cohort_default_rate": {"2013Q4": 0.01919, "2016Q2": 0.03444},
    "cohort_interval": {"2013Q4": [0.01795, 0.02052], "2016Q2": [0.03331, 0.03560]}}}}


def test_columns_keyed_alike_join_into_one_row(tmp_path):
    """A rate and its interval stored as two columns keyed by cohort are one row per cohort."""
    table = "| the twelve-month rates | `trajectory.json` | the book | `windows.12` |"
    draft = build(tmp_path, "The rate runs from 1.919% [1.795, 2.052] at 2013Q4.", table)
    (tmp_path / "run" / "trajectory.json").write_text(json.dumps(TRAJECTORY), encoding="utf-8")
    text = draft.read_text(encoding="utf-8")
    assert check_figures.check_row(draft, text, "C-001", None) == 0
    # 2016Q2's rate beside 2013Q4's interval.
    assert check_figures.check_row(
        draft, text.replace("1.919% [", "3.444% ["), "C-001", None) == 1
