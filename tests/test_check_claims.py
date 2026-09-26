"""An active claim reruns from the checkout: a clean run whose manifest pins
every local file its command executes, each unchanged since."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_claims
from record_run import code_hashes

COMMAND = ["python", "scripts/run.py", "--out-dir", "experiments/x"]


def _record(root: Path, **overrides) -> str:
    _code(root)
    manifest = {"command": COMMAND, "git_dirty": False, "code_sha256": code_hashes(COMMAND, root)}
    manifest.update(overrides)
    (root / "experiments/x").mkdir(parents=True, exist_ok=True)
    (root / "experiments/x/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return "experiments/x"


def _code(root: Path) -> None:
    (root / "scripts").mkdir(parents=True, exist_ok=True)
    (root / "packages/pkg/src/pkg").mkdir(parents=True, exist_ok=True)
    (root / "scripts/run.py").write_text("import pkg\n", encoding="utf-8")
    (root / "packages/pkg/src/pkg/__init__.py").write_text("X = 1\n", encoding="utf-8")


def test_unchanged_clean_run_passes(tmp_path):
    assert check_claims.check_code("C-001", _record(tmp_path), tmp_path) == []


def test_a_changed_module_fails(tmp_path):
    evidence = _record(tmp_path)
    (tmp_path / "packages/pkg/src/pkg/__init__.py").write_text("X = 2\n", encoding="utf-8")
    errors = check_claims.check_code("C-001", evidence, tmp_path)
    assert len(errors) == 1 and "has changed since its run" in errors[0]


def test_an_unpinned_module_and_a_dirty_run_fail(tmp_path):
    _code(tmp_path)
    evidence = _record(
        tmp_path,
        git_dirty=True,
        code_sha256={},
        input_sha256={"scripts/run.py": code_hashes(COMMAND, tmp_path)["scripts/run.py"]},
    )
    errors = check_claims.check_code("C-001", evidence, tmp_path)
    assert any("dirty tree" in error for error in errors)
    assert any("does not pin it" in error and "pkg/__init__.py" in error for error in errors)
    assert not any("scripts/run.py" in error for error in errors)
