"""The triad count must survive a text made of figures.

Every assertion here constructs the mistake: a claim row reports counts and
intervals by the dozen, and the pattern that catches the rule of three reads
each of them as one unless a list of figures is set aside first. The last case is the one
that matters: setting figure lists aside must not buy the reduction by hiding a
real triad that happens to sit in the same sentence as a count.
"""
import importlib.util
import pathlib

SPEC = importlib.util.spec_from_file_location(
    "lint_prose", pathlib.Path(__file__).resolve().parents[1] / "scripts" / "lint_prose.py")
lint_prose = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lint_prose)


def triads(tmp_path, text):
    path = tmp_path / "text.md"
    path.write_text(text, encoding="utf-8")
    return lint_prose.lint(path)["triads"]


def test_a_rule_of_three_is_counted(tmp_path):
    assert triads(tmp_path, "The split, the seed and the metric are fixed here.") == 1


def test_a_run_of_counts_is_not_a_triad(tmp_path):
    assert triads(tmp_path, "The twelve-month window clears 11, 23 and 21 cohorts.") == 0


def test_thousands_separators_do_not_read_as_a_run(tmp_path):
    text = "It labels 1,298,994 loans with 6,697 defaults, dropping 54,931 and 1,470."
    assert triads(tmp_path, text) == 0


def test_a_bracketed_interval_before_and_is_not_a_triad(tmp_path):
    text = "The difference is +0.00041 [+0.00003, +0.00109] and holds zero there."
    assert triads(tmp_path, text) == 0


def test_masking_does_not_hide_a_triad_beside_the_figures(tmp_path):
    text = ("It clears 11, 23 and 21 cohorts, and the split, the seed and the "
            "metric are fixed.")
    assert triads(tmp_path, text) == 1
