"""The bootstrap runs on machines that are not ours, and arrives by hand.

Two files are copied to a borrowed Apple machine and started by someone who is
not going to debug them. A copy that has passed through a Windows working tree
arrives with CRLF line endings, and bash reads the carriage return as part of
the last word on the line, so `set -euo pipefail` becomes a request for an
option named "pipefail<CR>" and the script dies on its first statement. The
guard at the top of the script repairs such a copy in memory and re-runs it.

That guard cannot be exercised by hand on a Windows checkout: the tools there
translate line endings on the way in, so `grep` reports a file as clean while
`od` shows the carriage returns, and a damaged script appears to run correctly
for the wrong reason. These tests build the damage explicitly and read the
result, so the guard is checked where line endings are not translated.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

BOOTSTRAP = Path(__file__).resolve().parents[1] / "scripts" / "bootstrap_macnode.sh"

# The last line of the region that has to survive a damaged copy.
GUARD_MARK = "repair once, then run"

# The first line that a carriage return is known to break.
FIRST_FRAGILE = "set -euo pipefail"

BASH = shutil.which("bash")

pytestmark = pytest.mark.skipif(BASH is None, reason="bash is not installed")


def _lines() -> list[str]:
    return BOOTSTRAP.read_text(encoding="utf-8").splitlines()


def _guard_region() -> list[str]:
    lines = _lines()
    end = next(i for i, line in enumerate(lines) if GUARD_MARK in line)
    return lines[: end + 1]


def test_the_script_parses() -> None:
    result = subprocess.run(
        [BASH, "-n", str(BOOTSTRAP)], capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


def test_the_guard_comes_before_the_first_fragile_line() -> None:
    lines = _lines()
    guard = next(i for i, line in enumerate(lines) if GUARD_MARK in line)
    fragile = next(i for i, line in enumerate(lines) if line.startswith(FIRST_FRAGILE))
    assert guard < fragile


def test_every_statement_in_the_guard_carries_a_trailing_comment() -> None:
    """A stray carriage return is harmless only where a comment absorbs it."""
    for line in _guard_region():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        assert " #" in line, f"no trailing comment to absorb a carriage return: {line}"


def test_the_guard_uses_no_keyword_that_needs_closing() -> None:
    """`if`, `case` and `[[` end in a keyword a carriage return would hide."""
    for line in _guard_region():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        statement = line.split(" #")[0]
        for keyword in ("if ", "case ", "[[ ", "while ", "for "):
            assert keyword not in statement, f"{keyword.strip()} in {statement}"


def _run_guard(tmp_path: Path, *, crlf: bool, argv: tuple[str, ...] = ()) -> str:
    """Run the guard region alone, damaged or not, and report what it saw."""
    body = "\n".join(_guard_region()) + "\n" + (
        'echo "fired=${OUTOFTIME_LF:-no} src=${OUTOFTIME_SRC} args=$*"\n'
    )
    raw = body.encode("utf-8")
    if crlf:
        raw = raw.replace(b"\n", b"\r\n")

    home = tmp_path / "node"
    home.mkdir()
    script = home / "guard.sh"
    script.write_bytes(raw)

    result = subprocess.run(
        [BASH, str(script), *argv],
        check=False,
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_a_damaged_copy_repairs_itself_and_runs(tmp_path: Path) -> None:
    out = _run_guard(tmp_path, crlf=True, argv=("alpha", "beta"))
    assert "fired=1" in out, out


def test_a_clean_copy_is_not_re_executed(tmp_path: Path) -> None:
    out = _run_guard(tmp_path, crlf=False)
    assert "fired=no" in out, out


@pytest.mark.parametrize("crlf", [True, False])
def test_the_source_directory_survives_the_repair(tmp_path: Path, crlf: bool) -> None:
    """The repaired copy is read from a pipe, so `$0` no longer locates it.

    Without this the script would look for timing_probe.py beside a file
    descriptor rather than beside itself.
    """
    out = _run_guard(tmp_path, crlf=crlf)
    source = out.split("src=")[1].split(" args=")[0]
    assert not source.startswith("/dev/fd"), out
    assert source.endswith("/node"), out


@pytest.mark.parametrize("crlf", [True, False])
def test_arguments_survive_the_repair(tmp_path: Path, crlf: bool) -> None:
    out = _run_guard(tmp_path, crlf=crlf, argv=("alpha", "beta"))
    assert "args=alpha beta" in out, out
