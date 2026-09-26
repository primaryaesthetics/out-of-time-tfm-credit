"""The archive a node receives, on what would make it incomplete or wrong.

An archive is opened on a machine that holds nothing else, by someone who
will not debug it. So every file the runner reads has to be inside, every
line ending has to be LF whatever tree the archive was built in, and the job
list has to say the same thing the packing command said. Bundles are stood
in for by three named files; the runner's dry run is exercised through bash
where one is installed.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

import pack_node_run as pk

BASH = shutil.which("bash")


def bundle(root: Path, name: str) -> Path:
    path = root / name
    path.mkdir(parents=True)
    (path / "bundle.json").write_bytes(b'{"build": {"build_id": "%s"}}\r\n' % name.encode())
    (path / "context.parquet").write_bytes(b"PAR1\r\n\x00")
    (path / "scored.parquet").write_bytes(b"PAR1\x00\r\n")
    return path


def tar_members(target: Path) -> dict[str, tuple[bytes, int]]:
    with tarfile.open(target, "r:gz") as archive:
        return {m.name: (archive.extractfile(m).read(), m.mode) for m in archive.getmembers()}


def test_one_bundle_with_options_is_the_older_shape(tmp_path: Path) -> None:
    b = bundle(tmp_path, "2026-09-05-lc-2015h1e-bundle")
    target = pk.pack([b], name=None, jobs=[], args="--nearest 3 --seeds 20260911", fmt="tar",
                     out_dir=tmp_path / "out")
    assert target.name == "outoftime-run-2026-09-05-lc-2015h1e-bundle.tar.gz"
    files = tar_members(target)
    top = "outoftime-run-2026-09-05-lc-2015h1e-bundle"
    listing = json.loads(files[f"{top}/jobs.json"][0])
    assert listing["command"] == ["./run-score.sh"]
    assert listing["jobs"] == [{
        "name": b.name, "bundle": b.name, "out": f"{b.name}-scored",
        "args": ["--nearest", "3", "--seeds", "20260911"]}]
    digest = (tmp_path / "out" / f"{target.name}.sha256").read_text().split()
    assert digest == [pk.sha256(target.read_bytes()), target.name]


def test_named_jobs_run_on_every_bundle_and_one_on_one(tmp_path: Path) -> None:
    b1, b2 = bundle(tmp_path, "b1"), bundle(tmp_path, "b2")
    target = pk.pack([b1, b2], name="grid", fmt="tar", args=None, out_dir=tmp_path / "out",
                     jobs=["tabpfn=--models tabpfn",
                           "tabpfn-t1=--models tabpfn --temperature 1.0",
                           "check@b2=--models tabicl --temperature 1.0 --nearest 1"])
    listing = json.loads(tar_members(target)["outoftime-run-grid/jobs.json"][0])
    assert listing["bundles"] == ["b1", "b2"]
    assert [(j["name"], j["out"]) for j in listing["jobs"]] == [
        ("tabpfn@b1", "b1-scored-tabpfn"), ("tabpfn-t1@b1", "b1-scored-tabpfn-t1"),
        ("tabpfn@b2", "b2-scored-tabpfn"), ("tabpfn-t1@b2", "b2-scored-tabpfn-t1"),
        ("check@b2", "b2-scored-check")]
    assert listing["jobs"][1]["args"] == ["--models", "tabpfn", "--temperature", "1.0"]
    assert (tmp_path / "out" / "outoftime-run-grid.tar.gz.jobs.json").read_text() == \
        json.dumps(listing, indent=2) + "\n"


def test_everything_the_runner_reads_is_inside_with_lf_endings(tmp_path: Path) -> None:
    b = bundle(tmp_path, "b1")
    target = pk.pack([b], name=None, jobs=["j=--models tabicl"], args=None, fmt="tar",
                     out_dir=tmp_path / "out")
    files = tar_members(target)
    top = "outoftime-run-b1"
    for name in ("run.sh", "jobs.json", "README.txt", *pk.NODE_SCRIPTS, "b1/bundle.json",
                 "b1/context.parquet", "b1/scored.parquet"):
        assert f"{top}/{name}" in files, name
    for name in ("run.sh", "jobs.json", "node_jobs.py", "score_context.py", "b1/bundle.json"):
        assert b"\r" not in files[f"{top}/{name}"][0], name
    assert files[f"{top}/b1/context.parquet"][0] == b"PAR1\r\n\x00"
    assert files[f"{top}/run.sh"][1] & 0o111
    assert files[f"{top}/bootstrap_macnode.sh"][1] & 0o111
    assert not files[f"{top}/node_jobs.py"][1] & 0o111


def test_the_zip_holds_the_same_files_and_starts_the_scorer_directly(tmp_path: Path) -> None:
    b = bundle(tmp_path, "b1")
    tar = pk.pack([b], name=None, jobs=["j=--models tabicl"], args=None, fmt="tar",
                  out_dir=tmp_path / "out")
    zipped = pk.pack([b], name=None, jobs=["j=--models tabicl"], args=None, fmt="zip",
                     out_dir=tmp_path / "out")
    assert zipped.name == "outoftime-run-b1.zip"
    sidecars = sorted(p.name for p in (tmp_path / "out").iterdir() if p.suffix != ".gz"
                      and p.suffix != ".zip")
    assert sidecars == ["outoftime-run-b1.tar.gz.jobs.json", "outoftime-run-b1.tar.gz.sha256",
                        "outoftime-run-b1.zip.jobs.json", "outoftime-run-b1.zip.sha256"]
    assert (tmp_path / "out" / "outoftime-run-b1.tar.gz.sha256").read_text().split()[0] == \
        pk.sha256(tar.read_bytes())
    with zipfile.ZipFile(zipped) as archive:
        names = {info.filename: archive.read(info) for info in archive.infolist()}
    tarred = tar_members(tar)
    assert set(names) == set(tarred)
    listing = json.loads(names["outoftime-run-b1/jobs.json"])
    assert listing["command"] == ["python", "score_context.py"]
    for name, content in names.items():
        if not name.endswith("jobs.json"):
            assert content == tarred[name][0], name


@pytest.mark.parametrize("spec", ["nojob", "=--models x", "a b=--models x"])
def test_a_job_that_is_not_name_equals_options_is_refused(spec: str) -> None:
    with pytest.raises(SystemExit):
        pk.parse_job(spec)


def test_what_cannot_be_packed_is_refused(tmp_path: Path) -> None:
    b1 = bundle(tmp_path / "x", "same")
    b2 = bundle(tmp_path / "y", "same")
    with pytest.raises(SystemExit, match="share a directory name"):
        pk.pack([b1, b2], name="n", jobs=[], args="", fmt="tar", out_dir=tmp_path / "out")
    b3 = bundle(tmp_path, "b3")
    with pytest.raises(SystemExit, match="--name is needed"):
        pk.pack([b1, b3], name=None, jobs=[], args="", fmt="tar", out_dir=tmp_path / "out")
    with pytest.raises(SystemExit, match="not packed"):
        pk.pack([b3], name=None, jobs=["j@b9=--models x"], args=None, fmt="tar",
                out_dir=tmp_path / "out")
    with pytest.raises(SystemExit, match="do not mix"):
        pk.pack([b3], name=None, jobs=["j=--models x"], args="--nearest 1", fmt="tar",
                out_dir=tmp_path / "out")
    (b3 / "scored.parquet").unlink()
    with pytest.raises(SystemExit, match="not a bundle"):
        pk.pack([b3], name=None, jobs=[], args="", fmt="tar", out_dir=tmp_path / "out")


@pytest.mark.skipif(BASH is None, reason="bash is not installed")
def test_the_runner_reads_the_archive_it_is_given(tmp_path: Path) -> None:
    b1, b2 = bundle(tmp_path, "b1"), bundle(tmp_path, "b2")
    target = pk.pack([b1, b2], name="grid", fmt="tar", args=None, out_dir=tmp_path / "out",
                     jobs=["tabpfn=--models tabpfn", "tabpfn-t1=--models tabpfn --temperature 1.0"])
    with tarfile.open(target, "r:gz") as archive:
        archive.extractall(tmp_path / "node", filter="data")
    unpacked = tmp_path / "node" / "outoftime-run-grid"
    env = {**os.environ, "OUTOFTIME_DRY": "1", "OUTOFTIME_PYTHON": sys.executable,
           "HOME": str(tmp_path)}
    result = subprocess.run([BASH, "run.sh"], cwd=unpacked, env=env, capture_output=True,
                            text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "archive  : grid" in result.stdout
    assert "bundles  : 2" in result.stdout
    assert "./run-score.sh b1 --out-dir b1-scored-tabpfn --models tabpfn" in result.stdout
    assert "./run-score.sh b2 --out-dir b2-scored-tabpfn-t1 --models tabpfn --temperature 1.0" \
        in result.stdout
    assert "Dry run" in result.stdout
    assert not (tmp_path / "outoftime-node").exists()


def test_the_cuda_archive_carries_its_own_runner(tmp_path: Path) -> None:
    b = bundle(tmp_path, "b1")
    tar = pk.pack([b], name="apple", jobs=["j=--models tabicl"], args=None, fmt="tar",
                  out_dir=tmp_path / "out")
    cuda = pk.pack([b], name="rented", jobs=["j=--models tabicl"], args=None, fmt="cuda",
                   out_dir=tmp_path / "out")
    assert cuda.name == "outoftime-run-rented.tar.gz"
    files = tar_members(cuda)
    assert files["outoftime-run-rented/run.sh"][0] == pk.text_bytes(pk.SCRIPTS / "node_run_cuda.sh")
    assert files["outoftime-run-rented/run.sh"][1] & 0o111
    listing = json.loads(files["outoftime-run-rented/jobs.json"][0])
    assert listing["command"] == ["python", "score_context.py"]
    apple = {n.split("/", 1)[1] for n in tar_members(tar)}
    assert {n.split("/", 1)[1] for n in files} == apple


def test_a_checkpoint_travels_beside_the_runner_under_its_own_name(tmp_path: Path) -> None:
    b = bundle(tmp_path, "b1")
    ckpt = tmp_path / pk.TABPFN_CKPT
    ckpt.write_bytes(b"\x00weights\r\n")
    target = pk.pack([b], name=None, jobs=["j=--models tabpfn"], args=None, fmt="cuda",
                     out_dir=tmp_path / "out", checkpoint=ckpt)
    files = tar_members(target)
    assert files[f"outoftime-run-b1/{pk.TABPFN_CKPT}"][0] == b"\x00weights\r\n"
    other = tmp_path / "renamed.ckpt"
    other.write_bytes(b"x")
    with pytest.raises(SystemExit, match="travels as"):
        pk.pack([b], name=None, jobs=["j=--models tabpfn"], args=None, fmt="cuda",
                out_dir=tmp_path / "out", checkpoint=other)


@pytest.mark.skipif(BASH is None, reason="bash is not installed")
def test_the_cuda_runner_parses_and_reads_the_archive_it_is_given(tmp_path: Path) -> None:
    parsed = subprocess.run([BASH, "-n", str(pk.SCRIPTS / "node_run_cuda.sh")],
                            capture_output=True, text=True, check=False)
    assert parsed.returncode == 0, parsed.stderr
    b1 = bundle(tmp_path, "b1")
    target = pk.pack([b1], name="probe", fmt="cuda", args=None, out_dir=tmp_path / "out",
                     jobs=["tabpfn=--models tabpfn --chunk 20000",
                           "tabicl-t1=--models tabicl --temperature 1.0"])
    with tarfile.open(target, "r:gz") as archive:
        archive.extractall(tmp_path / "node", filter="data")
    unpacked = tmp_path / "node" / "outoftime-run-probe"
    env = {**os.environ, "OUTOFTIME_DRY": "1", "OUTOFTIME_PYTHON": sys.executable,
           "HOME": str(tmp_path)}
    result = subprocess.run([BASH, "run.sh"], cwd=unpacked, env=env, capture_output=True,
                            text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "archive  : probe" in result.stdout
    assert "outoftime-result-probe.tar.gz" in result.stdout
    assert "python score_context.py b1 --out-dir b1-scored-tabpfn --models tabpfn --chunk 20000" \
        in result.stdout
    assert "python score_context.py b1 --out-dir b1-scored-tabicl-t1 --models tabicl " \
        "--temperature 1.0" in result.stdout
    assert "Dry run" in result.stdout
    assert not (tmp_path / "outoftime-node").exists()


@pytest.mark.skipif(BASH is None, reason="bash is not installed")
def test_the_runner_refuses_an_incomplete_archive(tmp_path: Path) -> None:
    b = bundle(tmp_path, "b1")
    target = pk.pack([b], name=None, jobs=["j=--models tabicl"], args=None, fmt="tar",
                     out_dir=tmp_path / "out")
    with tarfile.open(target, "r:gz") as archive:
        archive.extractall(tmp_path / "node", filter="data")
    unpacked = tmp_path / "node" / "outoftime-run-b1"
    shutil.rmtree(unpacked / "b1")
    env = {**os.environ, "OUTOFTIME_DRY": "1", "OUTOFTIME_PYTHON": sys.executable}
    result = subprocess.run([BASH, "run.sh"], cwd=unpacked, env=env, capture_output=True,
                            text=True, check=False)
    assert result.returncode == 1
    assert "b1 is not in the archive" in result.stderr
