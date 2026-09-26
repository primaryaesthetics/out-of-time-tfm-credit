"""The provenance table lists every version of every design document, follows
renames, and hashes the bytes each commit holds."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import design_provenance as dp


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def _commit(repo: Path, files: dict[str, str], message: str) -> str:
    for rel, text in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text.encode("utf-8"))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)
    return _git(repo, "rev-parse", "HEAD").strip()


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "record"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.name", "t")
    _git(repo, "config", "user.email", "t@example.org")
    _git(repo, "config", "core.autocrlf", "false")
    return repo


def test_selects_design_documents_only(tmp_path):
    repo = _repo(tmp_path)
    _commit(
        repo,
        {
            "docs/experiments/EXP-000-template.md": "t\n",
            "docs/experiments/EXP-001-a.md": "a\n",
            "docs/experiments/EXP-001-log.md": "log\n",
            "docs/protocol/gates.md": "g\n",
            "docs/decisions/ADR-0001-x.md": "x\n",
            "docs/ledger/CLAIMS.md": "c\n",
        },
        "one",
    )
    assert dp.design_documents(repo, "HEAD") == [
        "docs/decisions/ADR-0001-x.md",
        "docs/experiments/EXP-001-a.md",
        "docs/protocol/gates.md",
    ]


def test_every_version_hashed_and_rename_followed(tmp_path):
    repo = _repo(tmp_path)
    first = _commit(repo, {"docs/experiments/EXP-001-old.md": "design v1\n" * 20}, "one")
    second = _commit(repo, {"docs/experiments/EXP-001-old.md": "design v1\n" * 20 + "amendment\n"}, "two")
    _git(repo, "mv", "docs/experiments/EXP-001-old.md", "docs/experiments/EXP-001-new.md")
    _git(repo, "commit", "-q", "-m", "three")
    third = _git(repo, "rev-parse", "HEAD").strip()

    history = dp.versions(repo, "docs/experiments/EXP-001-new.md", "HEAD")
    assert [v.commit for v in history] == [first, second, third]
    assert [v.path_at_commit for v in history] == [
        "docs/experiments/EXP-001-old.md",
        "docs/experiments/EXP-001-old.md",
        "docs/experiments/EXP-001-new.md",
    ]
    assert history[0].sha256 == hashlib.sha256(("design v1\n" * 20).encode()).hexdigest()
    assert history[1].sha256 == history[2].sha256 != history[0].sha256

    text = dp.table(repo, "HEAD")
    assert f"| docs/experiments/EXP-001-new.md (as docs/experiments/EXP-001-old.md) | 1 | `{first}` |" in text
    rows = [line for line in text.splitlines() if line.startswith("| docs/")]
    assert len(rows) == 3
    assert rows[-1].endswith("| current |")
    assert not rows[0].endswith("| current |")


def test_table_at_an_earlier_revision_stops_there(tmp_path):
    repo = _repo(tmp_path)
    first = _commit(repo, {"docs/protocol/gates.md": "g1\n"}, "one")
    _commit(repo, {"docs/protocol/gates.md": "g2\n"}, "two")
    text = dp.table(repo, first)
    rows = [line for line in text.splitlines() if line.startswith("| docs/")]
    assert len(rows) == 1
    assert f"Record commit of this snapshot: `{first}`." in text
    assert rows[0].endswith("| current |")
