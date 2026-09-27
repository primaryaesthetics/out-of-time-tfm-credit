#!/usr/bin/env python3
"""Records a run as evidence.

Creates experiments/<date>-<slug>/ containing manifest.json and the raw output
of the command. A number that did not come through here is not evidence and
cannot be cited from the claim ledger.

    python scripts/record_run.py lc-oot-baseline -- \
        python -m outoftime.run --config configs/lc_oot.toml

The manifest pins what makes a run in this project reproducible: the git sha,
the exact versions of every installed package (an ML result is a claim about a
library stack as much as about a method), the host, a hash of every input
file named on the command line, and a hash of every file of this repository the
command executes: its script and each local module that script imports.
"""

from __future__ import annotations

import ast
import datetime as dt
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Versions of these decide the number. Recorded even when absent, since "absent"
# is itself part of the environment that produced the result.
PINNED = [
    "numpy", "scipy", "pandas", "polars", "pyarrow", "scikit-learn",
    "lightgbm", "xgboost", "catboost", "torch", "tabpfn", "tabicl",
    "optbinning", "statsmodels", "matplotlib", "shap",
]


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], capture_output=True, text=True, cwd=ROOT, check=True
    ).stdout.strip()


def package_versions() -> dict[str, str | None]:
    from importlib.metadata import PackageNotFoundError, version

    out: dict[str, str | None] = {}
    for name in PINNED:
        try:
            out[name] = version(name)
        except PackageNotFoundError:
            out[name] = None
    return out


def cpu_model() -> str:
    system = platform.system()
    try:
        if system == "Linux":
            for line in Path("/proc/cpuinfo").read_text().splitlines():
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
        elif system == "Darwin":
            return subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        elif system == "Windows":
            return subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "(Get-CimInstance Win32_Processor).Name"],
                capture_output=True, text=True, check=True,
            ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        pass
    return platform.processor() or "unknown"


def gpu_model() -> str | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        return out or None
    except (OSError, subprocess.CalledProcessError):
        return None


def working_tree_is_dirty() -> bool:
    """Whether the tree that produced this run differs from its commit.

    Runs recorded earlier the same day sit in experiments/ untracked, and they
    are output rather than input: they say nothing about whether this run can be
    reproduced. A tracked file under experiments/ that has been *modified* is a
    different matter, since a recorded run is never edited, and it counts.
    """
    for line in git("status", "--porcelain").splitlines():
        status, path = line[:2], line[3:].strip().strip('"')
        if status == "??" and path.startswith("experiments/"):
            continue
        return True
    return False


def is_text(path: Path) -> bool:
    """Whether a file is text, by the absence of a NUL byte in its first 8 KiB."""
    with path.open("rb") as handle:
        return b"\0" not in handle.read(8192)


def file_hash(path: Path) -> str:
    """SHA-256 of a file, with a text file's line endings normalised to LF.

    Git stores every text file of this repository with LF endings and checks
    it out with the platform's, so the bytes on a Windows disk are not the
    bytes in the commit. Hashing the working-tree bytes pins a run to one
    platform's checkout; hashing after normalisation pins it to the file, and
    the same value verifies on any checkout. Binary inputs are hashed as they
    are. Manifests written before this convention hold the raw hash.
    """
    digest = hashlib.sha256()
    text = is_text(path)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block.replace(b"\r\n", b"\n") if text else block)
    return digest.hexdigest()


def input_hashes(command: list[str]) -> dict[str, str]:
    """Hashes any argument that names an existing file, so the input is pinned."""
    return {
        Path(argument).as_posix(): file_hash(Path(argument))
        for argument in command
        if Path(argument).is_file()
    }


def module_bases(root: Path) -> list[Path]:
    """Where this repository's own modules are imported from: the scripts,
    which import one another by putting their directory on the path, the
    library, and the source of every package kept under `packages/`."""
    return [root / "scripts", root / "src", *sorted((root / "packages").glob("*/src"))]


def module_file(name: str, root: Path) -> Path | None:
    for base in module_bases(root):
        stem = base.joinpath(*name.split("."))
        if stem.with_suffix(".py").is_file():
            return stem.with_suffix(".py")
        if (stem / "__init__.py").is_file():
            return stem / "__init__.py"
    return None


def module_name(path: Path, root: Path) -> str:
    for base in module_bases(root):
        if path.is_relative_to(base):
            parts = list(path.relative_to(base).with_suffix("").parts)
            return ".".join(parts[:-1] if parts[-1] == "__init__" else parts)
    return path.stem


def entry_files(command: list[str], root: Path) -> list[Path]:
    """The Python files a command runs: a `.py` argument, or the module after `-m`."""
    found = []
    for index, argument in enumerate(command):
        if argument.endswith(".py"):
            parts = Path(argument).parts
            for start in range(len(parts)):
                candidate = root.joinpath(*parts[start:])
                if candidate.is_file() and candidate.resolve().is_relative_to(root.resolve()):
                    found.append(candidate)
                    break
        elif argument == "-m" and index + 1 < len(command):
            path = module_file(command[index + 1], root)
            if path is not None:
                found.append(path)
    return found


def local_code(command: list[str], root: Path = ROOT) -> list[Path]:
    """Every file of this repository a command executes: its entry file and,
    transitively, each local module imported, with the packages above it.
    Third-party and standard-library imports resolve nowhere here and are
    pinned by the package versions instead."""
    seen: set[Path] = set()
    queue = entry_files(command, root)
    while queue:
        path = queue.pop()
        if path in seen:
            continue
        seen.add(path)
        package = module_name(path, root).split(".")
        if path.name != "__init__.py":
            package = package[:-1]
        names: list[str] = []
        for node in ast.walk(ast.parse(path.read_bytes(), filename=str(path))):
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    anchor = package[: len(package) - (node.level - 1)]
                    base = ".".join([*anchor, *([node.module] if node.module else [])])
                else:
                    base = node.module or ""
                names.append(base)
                names.extend(f"{base}.{alias.name}" for alias in node.names)
        for name in names:
            parts = name.split(".")
            for depth in range(1, len(parts) + 1):
                found = module_file(".".join(parts[:depth]), root)
                if found is not None and found not in seen:
                    queue.append(found)
    return sorted(seen)


def code_hashes(command: list[str], root: Path = ROOT) -> dict[str, str]:
    return {path.relative_to(root).as_posix(): file_hash(path) for path in local_code(command, root)}


def main(argv: list[str]) -> int:
    if "--" not in argv:
        print(__doc__, file=sys.stderr)
        return 2
    split = argv.index("--")
    slug, command = argv[0], argv[split + 1:]
    if not slug or not command:
        print(__doc__, file=sys.stderr)
        return 2

    # Sampled before the run directory exists, since creating it would itself
    # make the tree dirty and every run would then disown its own evidence —
    # and before the command runs, since the commit and the inputs a run is
    # pinned to are the ones it started from, not the ones there at its end.
    dirty = working_tree_is_dirty()
    sha = git("rev-parse", "HEAD")
    inputs = input_hashes(command)
    code = code_hashes(command)
    # The command names a script and a data file; the split, the label, the
    # matrix and the models live in the library, which the command never
    # names. Hashed here so that the manifest pins what ran and not only
    # what was typed.
    library = {
        path.relative_to(ROOT).as_posix(): file_hash(path)
        for path in sorted((ROOT / "src" / "outoftime").glob("*.py"))
    }

    date = dt.datetime.now().astimezone().date().isoformat()
    directory = ROOT / "experiments" / f"{date}-{slug}"
    if directory.exists():
        print(f"{directory} exists; a recorded run is never overwritten", file=sys.stderr)
        return 1
    directory.mkdir(parents=True)

    started = dt.datetime.now(dt.UTC)
    completed = subprocess.run(
        command, capture_output=True, text=True, cwd=ROOT, check=False
    )
    finished = dt.datetime.now(dt.UTC)

    (directory / "stdout.txt").write_text(completed.stdout, encoding="utf-8")
    (directory / "stderr.txt").write_text(completed.stderr, encoding="utf-8")

    manifest = {
        "slug": slug,
        "command": command,
        "exit_code": completed.returncode,
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "wall_seconds": round((finished - started).total_seconds(), 3),
        "git_sha": sha,
        "git_dirty": dirty,
        "host": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu_model(),
        "gpu": gpu_model(),
        "python": platform.python_version(),
        "packages": package_versions(),
        "input_sha256": inputs,
        "library_sha256": library,
        "code_sha256": code,
    }
    (directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )

    print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    print(f"\nrecorded: {directory.relative_to(ROOT).as_posix()}")
    if manifest["git_dirty"]:
        print("warning: working tree was dirty; this run is not reproducible", file=sys.stderr)
    return completed.returncode


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
