"""The run recorder, tested on the two ways a manifest can pin the wrong thing.

A hash of a text file's working-tree bytes pins a run to one platform's line
endings rather than to the file: the same commit checked out on Windows and on
Linux would disagree, and nothing could tell that from tampering. And a commit
read after the command has run pins the run to whatever the tree became while
it ran, not to what it started from.
"""

from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_recorder():
    spec = importlib.util.spec_from_file_location("record_run", ROOT / "scripts" / "record_run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["record_run"] = module
    spec.loader.exec_module(module)
    return module


def test_a_text_file_hashes_the_same_whatever_its_line_endings(tmp_path):
    recorder = load_recorder()
    lf = tmp_path / "lf.py"
    crlf = tmp_path / "crlf.py"
    lf.write_bytes(b"import sys\nprint(sys.argv)\n")
    crlf.write_bytes(b"import sys\r\nprint(sys.argv)\r\n")

    assert recorder.file_hash(lf) == recorder.file_hash(crlf)
    assert recorder.file_hash(lf) == hashlib.sha256(lf.read_bytes()).hexdigest()


def test_a_binary_file_hashes_its_bytes_as_they_are(tmp_path):
    recorder = load_recorder()
    binary = tmp_path / "blob.gz"
    payload = b"\x1f\x8b\x00\r\n\x00\r\nend"
    binary.write_bytes(payload)

    assert not recorder.is_text(binary)
    assert recorder.file_hash(binary) == hashlib.sha256(payload).hexdigest()


def test_the_commit_and_the_inputs_are_sampled_before_the_command_runs():
    source = (ROOT / "scripts" / "record_run.py").read_text(encoding="utf-8")
    body = source[source.index("def main("):]
    run = body.index("subprocess.run(")
    assert body.index('git("rev-parse", "HEAD")') < run
    assert body.index("input_hashes(command)") < run


def _tree(root: Path, files: dict[str, str]) -> None:
    for rel, text in files.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")


def test_the_code_a_command_executes_is_its_local_import_closure(tmp_path):
    recorder = load_recorder()
    _tree(
        tmp_path,
        {
            "scripts/run.py": "import numpy\nimport helper\nfrom lib import tools\n",
            "scripts/helper.py": "import os\n",
            "scripts/unused.py": "",
            "src/lib/__init__.py": "",
            "src/lib/tools.py": "from . import core\n",
            "src/lib/core.py": "",
            "src/lib/other.py": "",
            "packages/pkg/src/pkg/__init__.py": "from .inner import f\n",
            "packages/pkg/src/pkg/inner.py": "",
            "scripts/second.py": "import pkg\n",
        },
    )

    def names(command):
        return [p.relative_to(tmp_path).as_posix() for p in recorder.local_code(command, tmp_path)]

    assert names(["python", "scripts/run.py", "--out", "x"]) == [
        "scripts/helper.py",
        "scripts/run.py",
        "src/lib/__init__.py",
        "src/lib/core.py",
        "src/lib/tools.py",
    ]
    assert names([str(tmp_path / "python.exe"), str(tmp_path / "scripts" / "second.py")]) == [
        "packages/pkg/src/pkg/__init__.py",
        "packages/pkg/src/pkg/inner.py",
        "scripts/second.py",
    ]
    assert names(["python", "-m", "lib.tools"]) == [
        "src/lib/__init__.py",
        "src/lib/core.py",
        "src/lib/tools.py",
    ]
