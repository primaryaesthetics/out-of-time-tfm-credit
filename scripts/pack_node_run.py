#!/usr/bin/env python3
"""Packs scoring jobs for a node into a single archive.

A node holds nothing but a Python environment and what is sent to it, so what
is sent has to be complete: the scorer, the bundles from `export_context.py`,
the list of jobs, the runner that walks the list, and the bootstrap for a
machine that has never run. This writes all of that into one archive, with
every text file's line endings normalised to LF and the scripts marked
executable, so the archive behaves the same whether it was built on Windows
or not.

One bundle and one set of options is the smallest job:

    python scripts/pack_node_run.py experiments/2026-09-05-lc-2015h1e-bundle \\
        --args "--nearest 3 --seeds 20260911" --out-dir data/derived/node

The grid is every bundle of an arm and, for the model whose temperature
cannot be rescaled after the fact, two passes over each. A named job is one
pass with its options; every named job is run on every bundle, in bundle
order, and a job named `<job>@<bundle>` is run on that bundle alone:

    python scripts/pack_node_run.py experiments/*-lc-*e-bundle --name grid-e-tabpfn \\
        --job "tabpfn=--models tabpfn" \\
        --job "tabpfn-t1=--models tabpfn --temperature 1.0"

The scores of a job go to `<bundle>-scored-<job>` beside the bundle, one
directory per pass, so that each carries its own node record; with `--args`
alone they go to `<bundle>-scored`, the shape the single-bundle runs used.
`jobs.json` in the archive lists every job in order with the command the
scorer is started with, and `node_jobs.py` walks it, skipping what a previous
start finished.

The archive is a `.tar.gz` for the Apple Silicon node, whose `run.sh` does the
whole procedure, a `.tar.gz` for a Linux machine with an NVIDIA GPU
(`--format cuda`), whose `run.sh` builds its own environment and does the
same, or a `.zip` for a hosted notebook, where the same list is run by hand
with `python node_jobs.py jobs.json`. A TabPFN checkpoint given with
`--checkpoint` travels beside `run.sh`, so a node without the licence
server's blessing can still run TabPFN. The archive's name and
top-level directory are `outoftime-run-<name>`, the name defaulting to the
bundle's when there is one. The archive's hash is printed and written beside
it, so the copy that arrives on the node can be checked against the one that
left.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import shlex
import sys
import tarfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

BUNDLE_FILES = ("bundle.json", "context.parquet", "scored.parquet")
NODE_SCRIPTS = ("score_context.py", "node_jobs.py", "bootstrap_macnode.sh", "timing_probe.py")
TEXT_SUFFIXES = {".sh", ".py", ".txt", ".conf", ".json"}
EXECUTABLE = {"run.sh", "bootstrap_macnode.sh"}
NODE_COMMAND = {"tar": ["./run-score.sh"], "zip": ["python", "score_context.py"],
                "cuda": ["python", "score_context.py"]}
RUNNER = {"tar": "node_run.sh", "zip": "node_run.sh", "cuda": "node_run_cuda.sh"}
TABPFN_CKPT = "tabpfn-v3-classifier-v3_default.ckpt"

README = """\
outoftime — scoring jobs for a node

On an Apple Silicon machine:

  bash run.sh

That is the whole procedure. It uses ~/outoftime-node if it is there, builds it
if it is not, runs every job in jobs.json that is not finished yet, and leaves
one file on the Desktop to send back: outoftime-result-<name>.tar.gz.

On a Linux machine with an NVIDIA GPU, when the archive was packed for one
(its run.sh then says so in its first lines):

  tmux new -s outoftime
  bash run.sh

It builds ~/outoftime-node, runs every job, and leaves
~/outoftime-result-<name>.tar.gz to send back.

On a hosted notebook or any Linux machine with the libraries installed:

  python node_jobs.py jobs.json

and send back every directory jobs.json names under "out", with the console
output.

Files here:
  run.sh                 the runner; start it with bash, not sh
  jobs.json              the jobs, in order, and what starts the scorer
  node_jobs.py           walks jobs.json; a second start skips finished jobs
  score_context.py       the scorer
  <bundle>/              the rows to score and their description, one per build
  bootstrap_macnode.sh   builds the node directory on a machine that has none
  timing_probe.py        the bootstrap needs it beside itself

Everything the study puts on an Apple machine lives in ~/outoftime-node and is
removed with: rm -rf ~/outoftime-node
"""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def text_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n")


def parse_job(spec: str) -> tuple[str, str | None, list[str]]:
    """`name=options` for every bundle, `name@bundle=options` for one."""
    if "=" not in spec:
        raise SystemExit(f"a job is written name=options, not {spec!r}")
    head, options = spec.split("=", 1)
    name, _, only = head.partition("@")
    if not name or any(c in name for c in " /\\"):
        raise SystemExit(f"{head!r} is not a job name")
    return name, only or None, shlex.split(options)


def jobs_for(bundles: list[Path], specs: list[str], args: str | None) -> list[dict]:
    if specs and args is not None:
        raise SystemExit("--args and --job do not mix; --args is one unnamed job")
    if not specs:
        return [{"name": b.name, "bundle": b.name, "out": f"{b.name}-scored",
                 "args": shlex.split(args or "")} for b in bundles]
    parsed = [parse_job(spec) for spec in specs]
    names = {b.name for b in bundles}
    for name, only, _ in parsed:
        if only is not None and only not in names:
            raise SystemExit(f"job {name} names the bundle {only}, which is not packed")
    jobs = []
    for bundle in bundles:
        for name, only, options in parsed:
            if only is not None and only != bundle.name:
                continue
            jobs.append({"name": f"{name}@{bundle.name}", "bundle": bundle.name,
                         "out": f"{bundle.name}-scored-{name}", "args": options})
    if len({job["name"] for job in jobs}) != len(jobs):
        raise SystemExit("two jobs share a name")
    return jobs


def check_inputs(bundles: list[Path]) -> None:
    if not bundles:
        raise SystemExit("no bundle given")
    if len({b.name for b in bundles}) != len(bundles):
        raise SystemExit("two bundles share a directory name; the node tells them apart by it")
    for bundle in bundles:
        for name in BUNDLE_FILES:
            if not (bundle / name).exists():
                raise SystemExit(f"{bundle} has no {name}; not a bundle from export_context.py")
    for name in (*sorted(set(RUNNER.values())), *NODE_SCRIPTS):
        if not (SCRIPTS / name).exists():
            raise SystemExit(f"scripts/{name} is missing")


def members(top: str, bundles: list[Path], listing: dict, *, runner: str = "node_run.sh",
            checkpoint: Path | None = None) -> list[tuple[str, bytes, bool]]:
    """Every file of the archive as (path, bytes, executable), in a fixed order."""
    files: list[tuple[str, bytes, bool]] = [
        (f"{top}/run.sh", text_bytes(SCRIPTS / runner), True),
        (f"{top}/jobs.json", (json.dumps(listing, indent=2) + "\n").encode(), False),
        (f"{top}/README.txt", README.encode(), False),
    ]
    for name in NODE_SCRIPTS:
        files.append((f"{top}/{name}", text_bytes(SCRIPTS / name), name in EXECUTABLE))
    for bundle in bundles:
        for name in BUNDLE_FILES:
            path = bundle / name
            data = text_bytes(path) if path.suffix in TEXT_SUFFIXES else path.read_bytes()
            files.append((f"{top}/{bundle.name}/{name}", data, False))
    if checkpoint is not None:
        files.append((f"{top}/{checkpoint.name}", checkpoint.read_bytes(), False))
    return files


def write_tar(target: Path, files: list[tuple[str, bytes, bool]]) -> None:
    with tarfile.open(target, "w:gz") as archive:
        for name, data, executable in files:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mtime = int(time.time())
            info.mode = 0o755 if executable else 0o644
            archive.addfile(info, io.BytesIO(data))


def write_zip(target: Path, files: list[tuple[str, bytes, bool]]) -> None:
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data, executable in files:
            info = zipfile.ZipInfo(name, date_time=time.localtime()[:6])
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if executable else 0o644) << 16
            archive.writestr(info, data)


def pack(bundles: list[Path], *, name: str | None, jobs: list[str], args: str | None,
         fmt: str, out_dir: Path, checkpoint: Path | None = None) -> Path:
    check_inputs(bundles)
    if checkpoint is not None:
        # The runners look for the checkpoint by this name and no other.
        if checkpoint.name != TABPFN_CKPT:
            raise SystemExit(f"the checkpoint travels as {TABPFN_CKPT}, not {checkpoint.name}")
        if not checkpoint.is_file():
            raise SystemExit(f"{checkpoint} is not a file")
    if name is None:
        if len(bundles) > 1:
            raise SystemExit("--name is needed when more than one bundle is packed")
        name = bundles[0].name
    top = f"outoftime-run-{name}"
    listing = {"name": name, "command": NODE_COMMAND[fmt],
               "bundles": [b.name for b in bundles], "jobs": jobs_for(bundles, jobs, args)}
    out_dir.mkdir(parents=True, exist_ok=True)
    tarred = fmt in ("tar", "cuda")
    target = out_dir / (f"{top}.tar.gz" if tarred else f"{top}.zip")
    files = members(top, bundles, listing, runner=RUNNER[fmt], checkpoint=checkpoint)
    (write_tar if tarred else write_zip)(target, files)
    # The sidecars are named after the archive file, not the archive's name:
    # the same jobs packed as a tar and as a zip sit beside each other.
    digest = sha256(target.read_bytes())
    (out_dir / f"{target.name}.sha256").write_text(f"{digest}  {target.name}\n",
                                                   encoding="utf-8")
    (out_dir / f"{target.name}.jobs.json").write_text(json.dumps(listing, indent=2) + "\n",
                                                      encoding="utf-8")
    return target


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundles", type=Path, nargs="+",
                        help="directories written by export_context.py")
    parser.add_argument("--name", default=None,
                        help="the archive's name after outoftime-run-; the bundle's when one")
    parser.add_argument("--args", default=None,
                        help="options passed to the scorer after the bundle, one job per "
                             "bundle into <bundle>-scored; the older shape")
    parser.add_argument("--job", action="append", default=[],
                        help="a named pass, name=options, run on every bundle into "
                             "<bundle>-scored-<name>; name@bundle=options for one bundle; "
                             "repeatable")
    parser.add_argument("--format", choices=("tar", "cuda", "zip"), default="tar",
                        help="tar for the Apple node's run.sh, cuda for a Linux machine with an "
                             "NVIDIA GPU, zip for a hosted notebook")
    parser.add_argument("--checkpoint", type=Path, default=None,
                        help=f"a {TABPFN_CKPT} to travel beside run.sh")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "data" / "derived" / "node")
    parsed = parser.parse_args(argv)
    if not parsed.job and parsed.args is None:
        parsed.args = "--nearest 3 --seeds 20260911"

    target = pack(parsed.bundles, name=parsed.name, jobs=parsed.job, args=parsed.args,
                  fmt=parsed.format, out_dir=parsed.out_dir, checkpoint=parsed.checkpoint)
    top = target.name.removesuffix(".tar.gz").removesuffix(".zip")
    listing = json.loads((parsed.out_dir / f"{target.name}.jobs.json").read_text(encoding="utf-8"))
    digest = (parsed.out_dir / f"{target.name}.sha256").read_text().split()[0]
    print(f"archive : {target}")
    print(f"size    : {target.stat().st_size / 1e6:.1f} MB")
    print(f"sha256  : {digest}")
    print(f"bundles : {len(listing['bundles'])}")
    print(f"jobs    : {len(listing['jobs'])}")
    for job in listing["jobs"]:
        print(f"  {job['name']:<48} -> {job['out']}  {shlex.join(job['args'])}")
    if parsed.format == "tar":
        print(f"unpack  : tar xzf {target.name} && cd {top} && bash run.sh")
    elif parsed.format == "cuda":
        print(f"unpack  : tar xzf {target.name} && cd {top} && tmux new -s outoftime "
              f"&& bash run.sh")
    else:
        print(f"unpack  : unzip -q {target.name} && cd {top} && python node_jobs.py jobs.json")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
