"""The export of the record carries no account name in a home path and no host
name that names a person or a business, and the record itself is never
rewritten."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import redact_snapshot as rs

# The fixtures' home paths are assembled at run time, so this file carries no
# home path of its own and the redaction it tests leaves it unchanged.
LENDER = "lender"
SLASH = "/"
BACKSLASH = "\\"


def home(name: str, rest: str, root: str = "Users", sep: str = SLASH, drive: str = "") -> str:
    return drive + sep + root + sep + name + sep + rest


PYTHON = home(LENDER, "outoftime-pool/.venv/bin/python")

MANIFEST = {
    "command": [PYTHON, "scripts/arm_intervals.py"],
    "input_sha256": {PYTHON: "2d96eb82", "experiments/cells.csv": "abc123"},
}


def _export(tmp_path: Path) -> Path:
    export = tmp_path / "export" / "experiments" / "run"
    export.mkdir(parents=True)
    (export / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    (export / "stderr.txt").write_text(
        home(LENDER, "outoftime-pool/outoftime/scripts/arm_intervals.py:542: ")
        + "RuntimeWarning: Mean of empty slice\n",
        encoding="utf-8",
    )
    return tmp_path / "export"


def test_survey_counts_files_and_occurrences(tmp_path):
    export = _export(tmp_path)
    assert rs.survey(export, set()) == {LENDER: (2, 3)}


def test_an_allowed_name_is_not_a_finding(tmp_path):
    export = _export(tmp_path)
    assert rs.survey(export, {LENDER}) == {}


def test_write_replaces_the_account_and_nothing_else(tmp_path):
    assert rs.PLACEHOLDER == "node"
    export = _export(tmp_path)
    assert rs.main(["--write", str(export)]) == 0

    manifest = json.loads((export / "experiments" / "run" / "manifest.json").read_text(encoding="utf-8"))
    redacted = home(rs.PLACEHOLDER, "outoftime-pool/.venv/bin/python")
    assert manifest["command"] == [redacted, "scripts/arm_intervals.py"]
    assert manifest["input_sha256"] == {redacted: "2d96eb82", "experiments/cells.csv": "abc123"}
    assert "arm_intervals.py:542" in (export / "experiments" / "run" / "stderr.txt").read_text(encoding="utf-8")
    assert rs.survey(export, set()) == {}


def test_check_reports_without_rewriting(tmp_path):
    export = _export(tmp_path)
    before = (export / "experiments" / "run" / "manifest.json").read_bytes()
    assert rs.main(["--check", str(export)]) == 1
    assert (export / "experiments" / "run" / "manifest.json").read_bytes() == before


def test_windows_and_linux_homes_are_found_too():
    text = (
        home("owner", "Documents\\x.py", sep=BACKSLASH, drive="C:")
        + " and "
        + home("owner", "Documents/y.py", drive="C:")
        + " and "
        + home("ci", "z.py", root="home")
    )
    assert rs.names_in(text) == {"owner": 2, "ci": 1}
    assert home(rs.PLACEHOLDER, "Documents/y.py") in rs.redact(text, set())
    assert home(rs.PLACEHOLDER, "z.py", root="home") in rs.redact(text, set())


def test_a_bare_path_without_an_account_is_untouched():
    for text in ("/Users", "/Users/", "/home/", "no path here"):
        assert rs.names_in(text) == {}
        assert rs.redact(text, set()) == text


def test_line_endings_survive_a_rewrite(tmp_path):
    export = tmp_path / "export"
    export.mkdir()
    target = export / "stderr.txt"
    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(home("someone", "a.py") + "\r\nsecond line\r\n")
    rs.write(export, set())
    with target.open(encoding="utf-8", newline="") as handle:
        assert handle.read() == home(rs.PLACEHOLDER, "a.py") + "\r\nsecond line\r\n"


def test_write_refuses_to_touch_the_record(capsys):
    assert rs.main(["--write", str(rs.ROOT)]) == 2
    assert "never" in capsys.readouterr().err

    assert rs.main(["--write", str(rs.ROOT / "experiments")]) == 2


# Host names are assembled at run time for the same reason: this file holds no
# host name that the redaction would rewrite. The domain is a reserved name.
OWNER = "Lender"
DOMAIN = "provider.example"
GPU = "1x NVIDIA GeForce RTX 4090 (24564 MiB), Ubuntu 24.04"

LEGIT_HOSTS = (
    "Google Colab free tier",
    "Google Colab, free tier, Linux x86_64, Python 3.13.15",
    "Apple M4 Pro laptop, 24 GB unified memory, macOS 26.6.2",
    "Apple M3 laptop, 17.18 GB unified memory, macOS 14.6.1",
    "Apple M4 Pro node, macOS 26.6.2 arm64, Python 3.12.14",
    "WIN-612LDG3827A",
    "Rented host, Linux-7.0.0-31-generic-x86_64-with-glibc2.43, Python 3.12.14",
    "Rented instance, " + GPU,
    "MacBook-Pro.local",
    "MacBook-Pro-2.local",
    "MacBook-Pro-node.local",
    "MacBook-Pro",
    "MacBook-Pro-",
    "Mac-mini",
    "Spot rented instance, " + GPU,
)


def mac_host(name: str, model: str = "MacBook-Pro") -> str:
    return model + "-" + name + ".local"


def host_line(value: str) -> str:
    return json.dumps({"host": value})


def _host_export(tmp_path: Path) -> Path:
    export = tmp_path / "export"
    for run, value in (
        ("mac", mac_host(OWNER)),
        ("rented", DOMAIN + " rented instance, " + GPU),
        ("colab", LEGIT_HOSTS[1]),
    ):
        (export / "experiments" / run).mkdir(parents=True)
        (export / "experiments" / run / "manifest.json").write_text(
            json.dumps({"host": value, "exit_code": 0}, indent=2), encoding="utf-8"
        )
    (export / "experiments" / "mac" / "stdout.log").write_text(
        "running on " + mac_host(OWNER) + "\n", encoding="utf-8"
    )
    return export


def _host(export: Path, run: str) -> str:
    manifest = export / "experiments" / run / "manifest.json"
    return json.loads(manifest.read_text(encoding="utf-8"))["host"]


def test_a_macos_host_name_loses_its_owner():
    assert rs.redact(mac_host(OWNER), set()) == "MacBook-Pro-node.local"
    assert rs.redact(mac_host(OWNER, "iMac"), set()) == "iMac-node.local"
    owner_first = OWNER + "s-" + "MacBook-Air.local"
    assert rs.redact(owner_first, set()) == "node-MacBook-Air.local"
    assert rs.hosts_in(mac_host(OWNER) + " " + owner_first) == {mac_host(OWNER): 1, owner_first: 1}
    # The number macOS appends on a name clash is not the owner's name.
    numbered = OWNER + "s-" + "MacBook-Pro-2.local"
    assert rs.redact(numbered, set()) == "node-MacBook-Pro-2.local"
    assert rs.hosts_in(numbered) == {numbered: 1}


def test_a_macos_host_name_is_read_in_any_case_and_bare_when_quoted():
    lower = mac_host(OWNER.lower(), "macbook-pro")
    assert rs.redact(lower, set()) == "macbook-pro-node.local"
    assert rs.hosts_in(lower) == {lower: 1}
    bare = "MacBook-Pro-" + OWNER
    assert rs.hosts_in(host_line(bare)) == {bare: 1}
    assert rs.redact(host_line(bare), set()) == host_line("MacBook-Pro-node")
    assert rs.redact(host_line(OWNER + "s" + "-Mac-mini"), set()) == host_line("node-Mac-mini")
    # Without ".local" and outside a host value, a model joined to a word is
    # running text or some other string, not a host name: this is the rule's
    # limit.
    for text in (
        "ran on the MacBook-Pro-" + OWNER + " machine",
        json.dumps({"book": "freddie-mac"}),
        json.dumps({"machine": bare}),
    ):
        assert rs.hosts_in(text) == {}, text
        assert rs.redact(text, set()) == text, text


def test_a_macos_host_name_counts_only_where_a_host_name_starts():
    for text in ("foo." + OWNER + "s" + "-MacBook-Pro.local", "x" + mac_host(OWNER)):
        assert rs.hosts_in(text) == {}, text
        assert rs.redact(text, set()) == text, text


def test_a_rented_host_loses_the_domain_of_its_provider():
    before = host_line(DOMAIN + " rented instance, " + GPU)
    assert rs.hosts_in(before) == {DOMAIN: 1}
    assert rs.redact(before, set()) == host_line("Rented instance, " + GPU)
    capital = host_line(DOMAIN + " Rented instance, " + GPU)
    assert rs.redact(capital, set()) == host_line("Rented instance, " + GPU)


def test_the_domain_rule_stops_where_it_should():
    for line in (
        # a domain not followed by "rented"
        host_line(DOMAIN + " instance, " + GPU),
        # "rented" after a word that is not a domain
        host_line("Spot rented instance, " + GPU),
        # a field other than "host"
        json.dumps({"provider": DOMAIN + " rented instance"}),
    ):
        assert rs.hosts_in(line) == {}, line
        assert rs.redact(line, set()) == line, line


def test_legitimate_hosts_are_untouched():
    for value in LEGIT_HOSTS:
        line = host_line(value)
        assert rs.hosts_in(line) == {}, value
        assert rs.redact(line, set()) == line, value


def test_check_reports_hosts_until_the_export_is_rewritten(tmp_path, capsys):
    export = _host_export(tmp_path)
    assert rs.main(["--check", str(export)]) == 1
    err = capsys.readouterr().err
    assert "host " + mac_host(OWNER) + ": 2 occurrence(s) in 2 file(s)" in err
    assert "host " + DOMAIN + ": 1 occurrence(s) in 1 file(s)" in err
    assert "Google" not in err

    assert rs.main(["--write", str(export)]) == 0
    assert _host(export, "mac") == "MacBook-Pro-node.local"
    assert _host(export, "rented") == "Rented instance, " + GPU
    assert _host(export, "colab") == LEGIT_HOSTS[1]
    assert rs.main(["--check", str(export)]) == 0


def test_an_allowed_host_name_is_not_a_finding(tmp_path):
    export = _host_export(tmp_path)
    assert rs.main(["--check", str(export), "--allow", OWNER, "--allow", DOMAIN]) == 0


def test_a_rewrite_is_idempotent(tmp_path):
    export = _host_export(tmp_path)
    (export / "experiments" / "run").mkdir()
    (export / "experiments" / "run" / "manifest.json").write_text(
        json.dumps(MANIFEST, indent=2), encoding="utf-8"
    )
    assert rs.write(export, set())
    after = {path: path.read_bytes() for path in rs.text_files(export)}
    assert rs.write(export, set()) == []
    assert {path: path.read_bytes() for path in rs.text_files(export)} == after


def test_this_file_and_the_script_survive_their_own_redaction():
    for path in (Path(__file__), rs.ROOT / "scripts" / "redact_snapshot.py"):
        text = rs.read(path)
        assert rs.redact(text, set()) == text, path.name
        assert rs.hosts_in(text) == {}, path.name
