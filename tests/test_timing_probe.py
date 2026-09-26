"""The probe has to survive being pasted into a notebook cell.

This is a regression test for a failure that happened rather than one that was
imagined. Pasted into Colab, the probe aborted before taking a single timing:
a notebook sets `__name__` to "__main__" exactly as a script does, so the entry
point fired, and `sys.argv` under a kernel carries Jupyter's own
`-f kernel-....json`, which argparse rejected.

The probe is a measuring instrument that runs on a machine nobody here can
reach, so an instrument that dies on arrival costs a round trip through a human
every time. These tests construct the kernel's argv and assert it is ignored.
"""

from __future__ import annotations

import json
import os
import runpy
import sys
import types
from pathlib import Path

import pytest

PROBE = Path(__file__).resolve().parent.parent / "scripts" / "timing_probe.py"

sys.path.insert(0, str(PROBE.parent))

import timing_probe as tp

# What Colab actually passed, from the failure being regressed.
KERNEL_ARGV = [
    "colab_kernel_launcher.py",
    "-f",
    "/root/.local/share/jupyter/runtime/kernel-06f086c3-e7df-4984-a9f9.json",
]


@pytest.fixture
def pretend_notebook(monkeypatch):
    """Puts the process in the state a Colab cell is in."""
    module = types.ModuleType("IPython")
    module.get_ipython = lambda: object()
    monkeypatch.setitem(sys.modules, "IPython", module)
    monkeypatch.setattr(sys, "argv", list(KERNEL_ARGV))


@pytest.fixture
def pretend_shell(monkeypatch):
    monkeypatch.setitem(sys.modules, "IPython", types.ModuleType("IPython"))
    sys.modules["IPython"].get_ipython = lambda: None
    monkeypatch.setattr(sys, "argv", ["timing_probe.py"])


def test_notebook_is_detected(pretend_notebook):
    assert tp.in_notebook() is True


def test_plain_shell_is_not_mistaken_for_a_notebook(pretend_shell):
    assert tp.in_notebook() is False


def test_kernel_argv_is_ignored_rather_than_parsed(pretend_notebook, tmp_path,
                                                   monkeypatch):
    """The failure being regressed: argparse saw -f kernel.json and exited 2."""
    monkeypatch.chdir(tmp_path)
    assert tp.main() == 0
    assert (tmp_path / "probe.json").exists()


def test_pasting_the_file_into_a_cell_does_not_raise(pretend_notebook, tmp_path,
                                                     monkeypatch):
    """Running the module top to bottom under a kernel must not SystemExit.

    Even a successful run raised one before, because the entry point called
    sys.exit() and a cell renders that as a traceback.
    """
    monkeypatch.chdir(tmp_path)
    runpy.run_path(str(PROBE), run_name="__main__")


def test_run_translates_keywords_into_flags(pretend_notebook, tmp_path,
                                            monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert tp.run(models="tabpfn", context_sizes="300", test_rows="50",
                  features=4, out="custom.json") == 0
    assert (tmp_path / "custom.json").exists()


def test_a_missing_model_is_recorded_not_raised():
    """An absent library is a status on a row, not a crash.

    The same handling carries the case the probe exists to find: an
    out-of-memory at some context size is the ceiling the study designs around.
    """
    results = tp.probe(models=["tabpfn"], context_sizes=[100], test_sizes=[50],
                       features=4, seed=0, repeats=2)
    assert len(results) == 1
    assert results[0]["status"].startswith("ModuleNotFoundError")
    assert results[0]["seconds"] == []


def test_the_climb_stops_after_the_first_failure():
    """Larger contexts fail the same way; spending quota on them is waste."""
    results = tp.probe(models=["tabpfn"], context_sizes=[100, 200, 400],
                       test_sizes=[50], features=4, seed=0, repeats=2)
    assert len(results) == 1


def test_synthetic_target_is_neither_constant_nor_balanced():
    """A degenerate target lets a model take a shortcut and mistimes the pass."""
    _, y = tp.synthetic(4000, 20, seed=0)
    rate = y.mean()
    assert 0.02 < rate < 0.40


def test_a_warm_up_runs_before_the_first_measurement(monkeypatch, tmp_path):
    """The first timed configuration must not be the one paying for start-up.

    Regressing the artefact seen on 2026-08-30: cold-start cost landed on the
    smallest context and inflated its spread to 19.75% against under 0.7%
    everywhere below it.
    """
    monkeypatch.chdir(tmp_path)
    calls = []
    monkeypatch.setattr(tp, "warm_up",
                        lambda *a, **k: calls.append("warm") or "ok")
    tp.probe(models=["tabpfn"], context_sizes=[100], test_sizes=[50],
             features=4, seed=0, repeats=2)
    assert calls == ["warm"], "warm_up must run exactly once per model"


def test_a_failing_warm_up_is_reported_not_raised():
    """An absent library must not abort before the results table is written."""
    assert tp.warm_up("tabpfn", "cpu", 4, 0).startswith("ModuleNotFoundError")


def test_each_row_is_on_disk_before_the_next_one_is_measured(tmp_path,
                                                             monkeypatch):
    """A killed kernel must cost the row in flight and nothing before it.

    Regressing 2026-08-30, where the Colab kernel was killed outright during
    the 100,000-row configuration and took every earlier result with it,
    because the file was written only after the sweep finished.
    """
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "incremental.json"
    seen = []

    real = tp.time_once

    def spy(model, x_train, y_train, x_test):
        # Whatever is on disk when a measurement starts is what a kill preserves.
        seen.append(json.loads(out.read_text())["results"] if out.exists() else [])
        return real(model, x_train, y_train, x_test)

    monkeypatch.setattr(tp, "time_once", spy)
    monkeypatch.setattr(tp, "build", lambda name, device: _Stub())
    tp.probe(models=["tabpfn"], context_sizes=[100, 200], test_sizes=[50],
             features=4, seed=0, repeats=2, out=str(out))

    assert len(seen[-1]) == 1, "the second configuration began with the first saved"
    assert len(json.loads(out.read_text())["results"]) == 2


class _Stub:
    def fit(self, x, y): return self
    def predict_proba(self, x): return x[:, :1]


def test_an_existing_token_is_never_overwritten(monkeypatch):
    monkeypatch.setenv("TABPFN_TOKEN", "already-set")
    assert tp.load_colab_secret("TABPFN_TOKEN") is True
    assert os.environ["TABPFN_TOKEN"] == "already-set"


def test_absent_colab_is_not_an_error(monkeypatch):
    """Off Colab the probe must fall through to the environment, not raise."""
    monkeypatch.delenv("TABPFN_TOKEN", raising=False)
    monkeypatch.setitem(sys.modules, "google.colab", None)
    assert tp.load_colab_secret("TABPFN_TOKEN") is False


def test_a_secret_is_copied_into_the_environment(monkeypatch):
    monkeypatch.delenv("TABPFN_TOKEN", raising=False)
    colab = types.ModuleType("google.colab")
    colab.userdata = types.SimpleNamespace(get=lambda n: "from-the-vault")
    monkeypatch.setitem(sys.modules, "google.colab", colab)
    assert tp.load_colab_secret("TABPFN_TOKEN") is True
    assert os.environ["TABPFN_TOKEN"] == "from-the-vault"


def test_the_token_is_not_written_into_the_recorded_environment():
    """A manifest is committed. A credential must never reach one."""
    os.environ["TABPFN_TOKEN"] = "secret-value-that-must-not-leak"
    try:
        assert "secret-value-that-must-not-leak" not in json.dumps(tp.environment())
    finally:
        os.environ.pop("TABPFN_TOKEN", None)


def _fake_torch(*, cuda=False, mps=False):
    torch = types.ModuleType("torch")
    torch.version = types.SimpleNamespace(cuda="12.8" if cuda else None)
    torch.cuda = types.SimpleNamespace(
        is_available=lambda: cuda,
        get_device_name=lambda i: "Tesla T4",
        get_device_properties=lambda i: types.SimpleNamespace(total_memory=15_640_000_000),
        max_memory_allocated=lambda: 9_489_000_000,
        empty_cache=lambda: None, reset_peak_memory_stats=lambda: None,
        synchronize=lambda: None)
    torch.backends = types.SimpleNamespace(
        mps=types.SimpleNamespace(is_available=lambda: mps))
    torch.mps = types.SimpleNamespace(
        current_allocated_memory=lambda: 1_234_000_000,
        empty_cache=lambda: None, synchronize=lambda: None)
    return torch


def test_apple_silicon_is_detected_when_there_is_no_cuda(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch(mps=True))
    env = tp.environment()
    assert env["device"] == "mps"
    assert "Apple Silicon" in env["device_name"]


def test_cuda_still_wins_when_both_are_present(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch(cuda=True, mps=True))
    assert tp.environment()["device"] == "cuda"


def test_the_mps_memory_reading_is_taken_from_the_metal_allocator(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch(mps=True))
    assert tp.peak_memory_gb() == pytest.approx(1.234)


def test_synchronise_and_reset_do_not_raise_on_apple_silicon(monkeypatch):
    monkeypatch.setitem(sys.modules, "torch", _fake_torch(mps=True))
    tp.synchronise()
    tp.reset_memory()


def test_metal_is_not_captioned_as_the_cpu_path():
    """The run of 2026-09-02 was printed as a CPU run while it sat on Metal.

    The guard tested `device != "cuda"`, so an Apple machine was told its GPU
    timings were CPU timings. The caption is what gets pasted beside the numbers
    into a manifest, so a wrong one mislabels evidence rather than a console.
    """
    assert "CPU path" not in tp.caption("mps")
    assert "Metal" in tp.caption("mps")
    assert "CPU path" in tp.caption("cpu")
    assert "CUDA" in tp.caption("cuda")


def _sweep_that_dies_above(limit, monkeypatch):
    """A probe whose only failure mode is a scoring batch wider than `limit`."""
    monkeypatch.setattr(tp, "warm_up", lambda *a, **k: "ok")
    monkeypatch.setattr(tp, "build", lambda name, device: _Stub())

    def time_once(model, x_train, y_train, x_test):
        if len(x_test) > limit:
            raise RuntimeError("CUDA out of memory")
        return 0.1

    monkeypatch.setattr(tp, "time_once", time_once)


def test_the_scoring_batch_is_swept_against_the_context(monkeypatch):
    """Every timing before 2026-09-02 scored one batch size, so nothing measured
    what a scored row costs. Two contexts by two batches is four rows."""
    _sweep_that_dies_above(10_000, monkeypatch)
    results = tp.probe(models=["tabpfn"], context_sizes=[100, 200],
                       test_sizes=[50, 100], features=4, seed=0, repeats=2)
    assert [(r["context_rows"], r["test_rows"]) for r in results] == [
        (100, 50), (100, 100), (200, 50), (200, 100)]
    assert all(r["status"] == "ok" for r in results)


def test_a_batch_that_is_too_wide_does_not_condemn_the_context(monkeypatch):
    """The two draw on one row budget, so a context that died only at the wide
    batch may still hold a larger context scored in chunks. Climbing continues."""
    _sweep_that_dies_above(50, monkeypatch)
    results = tp.probe(models=["tabpfn"], context_sizes=[100, 200],
                       test_sizes=[50, 100], features=4, seed=0, repeats=2)
    assert [(r["context_rows"], r["test_rows"]) for r in results] == [
        (100, 50), (100, 100), (200, 50), (200, 100)]
    assert [r["status"] == "ok" for r in results] == [True, False, True, False]


def test_a_failure_at_the_narrowest_batch_stops_the_context_climb(monkeypatch):
    """Nothing is left to give at this context, so larger ones are quota waste."""
    _sweep_that_dies_above(10, monkeypatch)
    results = tp.probe(models=["tabpfn"], context_sizes=[100, 200],
                       test_sizes=[50, 100], features=4, seed=0, repeats=2)
    assert [(r["context_rows"], r["test_rows"]) for r in results] == [(100, 50)]
