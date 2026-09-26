"""A paper figure is a recorded run's file, copied unchanged, or nothing is copied."""
import importlib.util
import json
import pathlib

import pytest
from PIL import Image

SPEC = importlib.util.spec_from_file_location(
    "paper_figures",
    pathlib.Path(__file__).resolve().parents[1] / "scripts" / "paper_figures.py")
paper_figures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(paper_figures)


def png(path, inches=(6.5, 4.0), dpi=300):
    size = (round(inches[0] * dpi), round(inches[1] * dpi)) if dpi else (650, 400)
    image = Image.new("RGB", size, "white")
    image.save(path, dpi=(dpi, dpi)) if dpi else image.save(path)


def run(root, name, *, dirty=False, exit_code=0, code_changed=False, inches=(6.5, 4.0), dpi=300):
    script = root / "scripts" / "draw.py"
    script.parent.mkdir(parents=True, exist_ok=True)
    if not script.exists():
        script.write_text("print('draw')\n", encoding="utf-8")
    digest = paper_figures.check_claims.file_hash(script)
    directory = root / "experiments" / name
    directory.mkdir(parents=True)
    png(directory / "plot.png", inches, dpi)
    manifest = {"command": ["python", "scripts/draw.py"], "git_dirty": dirty,
                "exit_code": exit_code, "git_sha": "abc123",
                "code_sha256": {"scripts/draw.py": "0" * 64 if code_changed else digest}}
    (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


def test_a_figure_is_copied_byte_for_byte_with_its_provenance(tmp_path):
    run(tmp_path, "good")
    out = tmp_path / "figures"
    record = paper_figures.copy_figures({"f1": ("good", "plot.png")}, out, root=tmp_path)
    assert (out / "f1.png").read_bytes() == (tmp_path / "experiments/good/plot.png").read_bytes()
    assert record["f1"]["run"] == "experiments/good" and record["f1"]["git_sha"] == "abc123"
    assert json.loads((out / "figures.json").read_text(encoding="utf-8")) == record


@pytest.mark.parametrize("flaw", [{"dirty": True}, {"exit_code": 1}, {"code_changed": True}])
def test_a_run_the_claim_gate_would_refuse_copies_nothing(tmp_path, flaw):
    run(tmp_path, "good")
    run(tmp_path, "bad", **flaw)
    out = tmp_path / "figures"
    with pytest.raises(SystemExit):
        paper_figures.copy_figures({"f1": ("good", "plot.png"), "f2": ("bad", "plot.png")},
                                   out, root=tmp_path)
    assert not out.exists()


def test_a_missing_file_is_refused(tmp_path):
    run(tmp_path, "good")
    with pytest.raises(SystemExit, match="does not exist"):
        paper_figures.copy_figures({"f1": ("good", "other.png")}, tmp_path / "f", root=tmp_path)


@pytest.mark.parametrize("inches", [(6.6, 4.0), (6.5, 8.6), (25.2, 4.0)])
def test_a_figure_larger_than_the_printed_page_is_refused(tmp_path, inches):
    run(tmp_path, "good")
    run(tmp_path, "wide", inches=inches, dpi=130)
    out = tmp_path / "figures"
    with pytest.raises(SystemExit, match="more than 6.5 x 8.5"):
        paper_figures.copy_figures({"f1": ("good", "plot.png"), "f2": ("wide", "plot.png")},
                                   out, root=tmp_path)
    assert not out.exists()


def test_a_figure_at_the_full_page_is_copied(tmp_path):
    run(tmp_path, "page", inches=(6.5, 8.5))
    record = paper_figures.copy_figures({"f1": ("page", "plot.png")}, tmp_path / "f", root=tmp_path)
    assert "f1" in record


def test_a_figure_that_states_no_dpi_is_refused(tmp_path):
    run(tmp_path, "nodpi", dpi=None)
    with pytest.raises(SystemExit, match="states no dpi"):
        paper_figures.copy_figures({"f1": ("nodpi", "plot.png")}, tmp_path / "f", root=tmp_path)
