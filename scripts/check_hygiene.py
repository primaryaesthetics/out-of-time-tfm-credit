#!/usr/bin/env python3
"""Hygiene gate.

Scans tracked files for what must never reach the public repository:
attribution of authorship to a tool, commentary about the process that
produced a file rather than about the file, the working context or tool role
named as the one who did the work, and citations of private documents.
Every pattern is also matched across line breaks, so a phrase wrapped over
two lines is caught.

Run from the repository root. Exits non-zero on any finding.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TEXT_SUFFIXES = {
    ".md", ".py", ".toml", ".yml", ".yaml", ".sh", ".ipynb", ".cfg",
    ".cff", ".txt", ".json", ".html", ".css", ".js",
}

SELF_EXEMPT = {"scripts/check_hygiene.py"}

ATTRIBUTION = [
    (r"\bco-authored-by\b", "authorship trailer"),
    (r"\b(?:generated|written|authored|created)\s+(?:with|by)\s+\w*\s*(?:ai|llm|claude|gpt|copilot|cursor|gemini)\b",
     "tool attribution"),
    (r"\b(?:ai|llm)[- ]?(?:generated|assisted|written|authored)\b", "tool attribution"),
    (r"\bclaude(?:\.ai)?\b", "tool name"),
    (r"\banthropic\b", "tool name"),
    (r"\bchatgpt\b|\bopenai\b|\bcopilot\b", "tool name"),
    (r"🤖", "tool marker"),
]

META = [
    (r"\bin this (?:session|conversation|chat)\b", "process commentary"),
    (r"\b(?:this|the previous|the last) (?:session|pass|audit|iteration)\b", "process commentary"),
    (r"\bas (?:discussed|requested|we agreed)\b", "process commentary"),
    (r"\b(?:I|we) (?:then )?(?:tried|attempted|decided to try)\b", "process commentary"),
    (r"\blet(?:'s| us) (?:now )?(?:try|see|check)\b", "process commentary"),
    (r"\bhere(?:'s| is) (?:the|your) (?:updated|revised|new) \w+\b", "process commentary"),
]

# Who did the work, named as a working context or a tool role rather than as an
# audit or a person's decision: "audited by a session", "the X agent". A
# notebook, Colab or GPU session is a compute term and stays allowed.
ACTOR = [
    ((r"\b(?:a|an|the|each|every|another|this|that|separate|later|fresh|working|second|third)\s+"
      r"(?!notebook\b|colab\b|runtime\b|gpu\b|t4\b|browser\b|ssh\b|login\b|conference\b|poster\b)"
      r"(?:\w+\s+)?sessions?\b(?!\s+and\s+talk)"), "working session as actor"),
    (r"\b(?:cost|spent|wasted|lost)\s+(?:\w+\s+)?sessions?\b", "working session as actor"),
    (r"(?<!user-)(?<!user_)\b(?:sub-?)?agents?\b(?!\s*(?:string|header))", "agent as actor"),
    (r"\b(?:cold-auditor|ledger-auditor|senior-review|run-checker|sweep-runner|outoftime-lab)\b",
     "private tool role"),
]

# Documents that never become public, cited from files that do.
PRIVATE = [
    (r"\bPLAN(?:\.md)?\s*§|\bPLAN\.md\b", "private plan cited"),
    (r"\bCLAUDE\.md\b|\bTODO\.md\b", "private file cited"),
    (r"(?<![\w/.-])notes/", "private directory cited"),
]

# Recorded runs describe the machines they ran on; "session" there is a
# notebook or remote-shell session, so the actor pattern skips them.
ACTOR_EXEMPT_PREFIXES = ("experiments/",)

PATTERNS = [(re.compile(p, re.IGNORECASE), why, kind)
            for group, kind in ((ATTRIBUTION, "attribution"), (META, "meta"),
                                (ACTOR, "actor"), (PRIVATE, "private"))
            for p, why in group]


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z"], capture_output=True, text=True, check=True
    ).stdout
    return [Path(name) for name in out.split("\0") if name]


def main() -> int:
    findings = []
    for path in tracked_files():
        if path.suffix not in TEXT_SUFFIXES:
            continue
        if path.as_posix() in SELF_EXEMPT:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        lines = text.splitlines()
        # Newlines (and a comment or quote marker after them) become single
        # spaces, and each offset of the joined text maps back to its line.
        joined, line_of = [], []
        for number, line in enumerate(lines, start=1):
            piece = re.sub(r"^\s*(?:#|//|>|\*)?\s*", "", line) if joined else line
            joined.append(piece + " ")
            line_of.extend([number] * (len(piece) + 1))
        flat = "".join(joined)
        seen = set()
        for pattern, why, kind in PATTERNS:
            if kind == "actor" and path.as_posix().startswith(ACTOR_EXEMPT_PREFIXES):
                continue
            for match in pattern.finditer(flat):
                number = line_of[match.start()]
                if (number, why) in seen:
                    continue
                seen.add((number, why))
                findings.append((path.as_posix(), number, kind, why, lines[number - 1].strip()))

    if not findings:
        print("hygiene: clean")
        return 0

    for path, number, kind, why, line in findings:
        print(f"{path}:{number}: {kind} ({why}): {line}", file=sys.stderr)
    print(f"\nhygiene: {len(findings)} finding(s)", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
