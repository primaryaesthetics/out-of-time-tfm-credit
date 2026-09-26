#!/usr/bin/env python3
"""Copy the paper's figures out of the recorded runs that drew them.

A figure in the paper is a file a recorded run wrote, copied byte for byte and
never edited. Each entry of `FIGURES` names the run and the file; the copy is
refused when the run is not one `check_claims.check_code` accepts — recorded
from a clean tree, its code pinned by the manifest and unchanged since — or
when its exit code is not zero. `figures.json` beside the copies gives, per
figure, the run, the file, its sha256 and the commit the run was recorded at,
so a reader can go from the PDF back to the run.

Every figure is printed at the text width, so a PNG wider than 6.5 in or
taller than 8.5 in at its own dpi, or one that states no dpi, is refused:
scaled down to fit, its type would print below the size it was drawn at.

    python scripts/paper_figures.py --out-dir <paper>/figures
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
_SPEC = importlib.util.spec_from_file_location("check_claims", ROOT / "scripts" / "check_claims.py")
check_claims = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_claims)

# Name in the paper -> (run, file in the run).
FIGURES = {
    "lc-protocols-reliability": ("2026-09-26-lc-2015h1e-reliability-print", "reliability-protocols.png"),
    "lc-auc-age": ("2026-09-26-lc-arm-e-auc-age-print", "auc-age.png"),
    "fm-auc-age": ("2026-09-25-fm-arm-e-auc-age-floors", "auc-age.png"),
    "fm-build-rows": ("2026-09-26-fm-arm-e-build-rows-print", "build-rows.png"),
    "fm-between-arm-rows": ("2026-09-26-fm-between-arm-rows-print", "build-rows.png"),
}

# The printed page: text width and the height of a full page with its caption.
MAX_WIDTH_IN = 6.5
MAX_HEIGHT_IN = 8.5


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def print_size_error(name: str, path: Path) -> str | None:
    """Why a figure would not print at the size it was drawn, or None."""
    if path.suffix.lower() != ".png":
        return None
    with Image.open(path) as image:
        dpi = image.info.get("dpi")
        width, height = image.size
    if not dpi:
        return f"{name}: {path.name} states no dpi"
    width_in, height_in = width / dpi[0], height / dpi[1]
    if width_in > MAX_WIDTH_IN + 0.01 or height_in > MAX_HEIGHT_IN + 0.01:
        return (f"{name}: {path.name} is {width_in:.2f} x {height_in:.2f} in, "
                f"more than {MAX_WIDTH_IN} x {MAX_HEIGHT_IN}")
    return None


def copy_figures(figures: dict[str, tuple[str, str]], out_dir: Path,
                 root: Path = ROOT) -> dict[str, dict]:
    """Copy every figure, or none: every run is checked before the first copy."""
    errors: list[str] = []
    for name, (run, file) in figures.items():
        evidence = f"experiments/{run}"
        manifest_path = root / evidence / "manifest.json"
        if not (root / evidence / file).exists():
            errors.append(f"{name}: {evidence}/{file} does not exist")
            continue
        if not manifest_path.exists():
            errors.append(f"{name}: {evidence} is not a recorded run")
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("exit_code") != 0:
            errors.append(f"{name}: {evidence} exited {manifest.get('exit_code')}")
        errors += check_claims.check_code(name, evidence, root)
        size_error = print_size_error(name, root / evidence / file)
        if size_error:
            errors.append(size_error)
    if errors:
        raise SystemExit("\n".join(errors))
    out_dir.mkdir(parents=True, exist_ok=True)
    record: dict[str, dict] = {}
    for name, (run, file) in figures.items():
        source = root / "experiments" / run / file
        target = out_dir / f"{name}{source.suffix}"
        shutil.copyfile(source, target)
        manifest = json.loads((source.parent / "manifest.json").read_text(encoding="utf-8"))
        record[name] = {"run": f"experiments/{run}", "file": file, "sha256": sha256(target),
                        "git_sha": manifest.get("git_sha")}
    (out_dir / "figures.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    record = copy_figures(FIGURES, args.out_dir)
    for name, entry in record.items():
        print(f"{name:32s} {entry['run']}/{entry['file']}  {entry['sha256'][:12]}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
