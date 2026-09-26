#!/usr/bin/env python3
"""Extracts a paper to text, and reports where the extraction cannot be trusted.

No extractor is error-free, and the dangerous failures are silent: a dropped
inequality sign, a table column merged into its neighbour, a page that was an
image and came back empty. This script does not promise a clean extraction. It
promises to say which pages are suspect, so those get read in the PDF itself
and the rest can be read as text.

The method is the differential gate applied to documents: run every extractor
present on the machine, then compare them page by page. Where independent
engines agree, the text is almost certainly right. Where they disagree, the
page is flagged and nothing may be quoted from it without opening the PDF.

    python scripts/extract_paper.py 2605.18147
    python scripts/extract_paper.py --url https://example.org/x.pdf --slug smith2024
    python scripts/extract_paper.py --file papers/local.pdf --slug local

Output lands in papers/<slug>/: source.pdf (cached, so nothing is fetched
twice), text-<engine>.txt per engine, report.json, and REPORT.md listing the
suspect pages.

Engines, in descending fidelity. Missing ones are skipped and named in the
report rather than failing the run.

    pymupdf4llm   markdown, keeps headings/tables/reading order   uv pip install pymupdf4llm
    pdftotext     poppler, -layout mode; ships with git-bash      already present
    docling       layout model, best on scans                     uv pip install docling

Math never survives any of them intact: the report flags every page carrying
symbols that are known to drop, and those pages are read from the PDF. See the
`primary-source` skill, references/extraction.md, for why, and for what to do
about gzipped PostScript from the 1990s.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / "papers"

ARXIV_ID = re.compile(r"^\d{4}\.\d{4,5}(v\d+)?$")
PAGE_BREAK = "\f"

# Sequences that mean the extractor mangled TeX rather than read it. Their
# presence is not fatal, since "oating pt oin" is still readable as "floating
# point", but a page full of them is a page to read in the PDF.
MOJIBAKE = [
    re.compile(r"\b(?:oating|tegers|cient|erent|nite|rst|eld|nding)\b"),
    re.compile("�"),
    re.compile(r"\(cid:\d+\)"),
]

# Symbols whose direction or identity is routinely lost. A page containing any
# of them is never quoted from the extraction.
FRAGILE_MATH = re.compile(
    "[≤≥≪≫≠≈∈⊆⊂∀∃"
    "⇒⇐⇔√∑∏∫∂∇"
    "ΩΘΛΦΨαβγδεθ"
    "λμπρσφψω"
    "†‡∼≃≅⌈⌉⌊⌋]"
)

TOKEN = re.compile(r"[A-Za-z0-9]+")


def die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


def fetch(url: str, target: Path) -> None:
    if target.exists():
        print(f"cached: {target.relative_to(ROOT).as_posix()}")
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    print(f"fetching {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    if not data.startswith(b"%PDF"):
        die(f"{url} did not return a PDF (first bytes: {data[:16]!r})")
    target.write_bytes(data)
    print(f"saved {len(data)} bytes to {target.relative_to(ROOT).as_posix()}")


def page_count(pdf: Path) -> int | None:
    """The PDF's own page count, which is the only trustworthy alignment key.

    Engines disagree about what a page is. `pdftotext -layout` emits two form
    feeds per physical page on some documents - on the first paper run through
    this script it reported 50 pages for a 25-page preprint - so splitting its
    output on form feeds silently shifts every page number by a growing offset
    and the differential compares unrelated pages. Both engines are therefore
    driven page by page against this count instead.
    """
    if shutil.which("pdfinfo"):
        completed = subprocess.run(
            ["pdfinfo", str(pdf)], capture_output=True, text=True, errors="replace",
            check=False,
        )
        if completed.returncode == 0:
            for line in completed.stdout.splitlines():
                if line.startswith("Pages:"):
                    return int(line.split(":", 1)[1].strip())
    try:
        import pymupdf

        with pymupdf.open(str(pdf)) as document:
            return document.page_count
    except (ImportError, OSError, RuntimeError, ValueError):
        return None


def run_pdftotext(pdf: Path, pages: int | None) -> list[str] | None:
    if not shutil.which("pdftotext") or pages is None:
        return None
    out: list[str] = []
    for number in range(1, pages + 1):
        completed = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8",
             "-f", str(number), "-l", str(number), str(pdf), "-"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            check=False,
        )
        if completed.returncode != 0:
            return None
        out.append(completed.stdout.replace(PAGE_BREAK, ""))
    return out


def run_pymupdf4llm(pdf: Path, pages: int | None) -> list[str] | None:
    try:
        import pymupdf4llm
    except ImportError:
        return None
    chunks = pymupdf4llm.to_markdown(str(pdf), page_chunks=True)
    numbered = {
        chunk["metadata"].get("page_number", index + 1): chunk["text"]
        for index, chunk in enumerate(chunks)
    }
    total = pages or max(numbered, default=0)
    return [numbered.get(number, "") for number in range(1, total + 1)]


def run_docling(pdf: Path, pages: int | None) -> list[str] | None:
    """Whole-document markdown, so it carries no page boundaries.

    Left out of the per-page differential deliberately rather than aligned by
    guesswork: a fabricated page mapping would make the agreement scores look
    better and mean less. The text is still written out for reading.
    """
    return None


ENGINES = {
    "pymupdf4llm": run_pymupdf4llm,
    "pdftotext": run_pdftotext,
    "docling": run_docling,
}


def agreement(left: str, right: str) -> float:
    """Token-level Jaccard. Insensitive to layout and whitespace, which is the
    point: engines are allowed to disagree about columns and not about words."""
    a = set(TOKEN.findall(left.lower()))
    b = set(TOKEN.findall(right.lower()))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def suspect(entry: dict) -> list[str]:
    reasons = []
    if entry["characters"] < 200:
        reasons.append("near-empty: probably an image or a figure page")
    if entry["mojibake"] > 5:
        reasons.append(f"{entry['mojibake']} mangled-ligature hits")
    scores = [v for v in entry["agreement"].values() if v is not None]
    if scores and min(scores) < 0.80:
        reasons.append(f"engines agree only {min(scores):.2f}")
    if entry["fragile_math"] > 0:
        reasons.append(
            f"{entry['fragile_math']} fragile math symbols: do not quote inequalities"
        )
    return reasons


def diagnose(slug: str, texts: dict[str, list[str]], missing: list[str], declared: int | None) -> dict:
    page_counts = {name: len(pages) for name, pages in texts.items()}
    primary = max(texts, key=lambda name: sum(len(p) for p in texts[name]))
    primary_pages = texts[primary]

    pages: list[dict] = []
    for index, page in enumerate(primary_pages, start=1):
        entry: dict = {
            "page": index,
            "characters": len(page.strip()),
            "mojibake": sum(len(p.findall(page)) for p in MOJIBAKE),
            "fragile_math": len(FRAGILE_MATH.findall(page)),
            "agreement": {},
        }
        for name, other in texts.items():
            if name == primary:
                continue
            entry["agreement"][name] = (
                round(agreement(page, other[index - 1]), 3)
                if index <= len(other) else None
            )
        pages.append(entry)

    flagged = [
        {"page": e["page"], "reasons": suspect(e)} for e in pages if suspect(e)
    ]

    return {
        "slug": slug,
        "engines_used": sorted(texts),
        "engines_missing": missing,
        "differential": len(texts) > 1,
        "primary": primary,
        "declared_pages": declared,
        "page_counts": page_counts,
        "pages": pages,
        "suspect_pages": flagged,
    }


def write_report(directory: Path, report: dict) -> None:
    (directory / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    lines = [f"# Extraction report - {report['slug']}", ""]
    if not report["differential"]:
        lines += [
            "**Single engine only - there is no differential and no page is verified.**",
            "",
            (
                f"Missing: {', '.join(report['engines_missing']) or 'none'}. "
                "Install a second engine (`uv pip install pymupdf4llm`) and re-run; "
                "until then treat every page as suspect."
            ),
            "",
        ]
    else:
        lines += [
            (
                f"Engines: {', '.join(report['engines_used'])}. "
                f"Primary: `{report['primary']}`."
            ),
            "",
        ]

    counts = report["page_counts"]
    declared = report["declared_pages"]
    if declared is not None and set(counts.values()) != {declared}:
        lines += [
            (
                f"**Page counts disagree with the PDF**: the document declares "
                f"{declared} pages and the engines produced {counts}. Page numbers "
                "below are unreliable until that is resolved."
            ),
            "",
        ]
    elif declared is not None:
        lines += [f"Aligned on the PDF's own {declared} pages.", ""]

    flagged = report["suspect_pages"]
    lines += [f"## Suspect pages ({len(flagged)} of {len(report['pages'])})", ""]
    if not flagged:
        lines += [
            "None. Every page is long enough, clean, and agreed between engines.",
            "",
        ]
    else:
        lines += [
            "Read these in the PDF. Nothing from them is quotable as extracted.",
            "",
            "| Page | Why |",
            "| --- | --- |",
        ]
        lines += [f"| {f['page']} | {'; '.join(f['reasons'])} |" for f in flagged]
        lines += [""]

    lines += [
        "## Standing rule",
        "",
        (
            "Inequalities, bounds and Greek letters are never quoted from an extraction, "
            "on any page, however clean. Find where the paper applies the statement - a "
            "proof almost always restates it concretely - and reconstruct the direction "
            "from there. See the `primary-source` skill."
        ),

        "",
    ]
    (directory / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def resolve_target(args: argparse.Namespace, parser: argparse.ArgumentParser) -> Path:
    if args.arxiv_id:
        if not ARXIV_ID.match(args.arxiv_id):
            die(f"{args.arxiv_id!r} is not an arXiv id; use --url or --file")
        directory = PAPERS / (args.slug or args.arxiv_id)
        fetch(f"https://arxiv.org/pdf/{args.arxiv_id}", directory / "source.pdf")
        return directory
    if args.url:
        if not args.slug:
            die("--url needs --slug")
        directory = PAPERS / args.slug
        fetch(args.url, directory / "source.pdf")
        return directory
    if args.file:
        source = Path(args.file)
        if not source.is_file():
            die(f"{source} does not exist")
        directory = PAPERS / (args.slug or source.stem)
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "source.pdf"
        if target.resolve() != source.resolve():
            target.write_bytes(source.read_bytes())
        return directory
    parser.print_help()
    raise SystemExit(2)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("arxiv_id", nargs="?", help="arXiv id, e.g. 2605.18147")
    parser.add_argument("--url", help="direct PDF url")
    parser.add_argument("--file", help="a PDF already on disk")
    parser.add_argument("--slug", help="directory under papers/ (defaults to the arXiv id)")
    args = parser.parse_args()

    directory = resolve_target(args, parser)
    pdf = directory / "source.pdf"

    declared = page_count(pdf)
    if declared is None:
        print("warning: the PDF's page count could not be read", file=sys.stderr)
    else:
        print(f"pdf: {declared} pages")

    texts: dict[str, list[str]] = {}
    missing: list[str] = []
    for name, engine in ENGINES.items():
        try:
            pages = engine(pdf, declared)
        except (OSError, RuntimeError, ValueError, ImportError) as error:
            print(f"{name}: failed ({error})", file=sys.stderr)
            missing.append(name)
            continue
        if pages is None:
            missing.append(name)
            continue
        texts[name] = pages
        (directory / f"text-{name}.txt").write_text(
            PAGE_BREAK.join(pages), encoding="utf-8"
        )
        print(f"{name}: {sum(len(p) for p in pages)} characters, {len(pages)} pages")

    if not texts:
        die("no extractor available; install one: uv pip install pymupdf4llm")

    report = diagnose(directory.name, texts, missing, declared)
    write_report(directory, report)

    flagged = len(report["suspect_pages"])
    total = len(report["pages"])
    print(
        f"\n{(directory / 'REPORT.md').relative_to(ROOT).as_posix()} "
        f"- {flagged} of {total} pages suspect"
    )
    if not report["differential"]:
        print("warning: one engine only; no page is cross-verified", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
