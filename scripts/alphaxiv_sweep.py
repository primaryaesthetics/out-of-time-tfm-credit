#!/usr/bin/env python3
"""Literature search over alphaXiv's public discovery API (no login, no key).

A second channel beside the arXiv listings and web search for the standing
sweep in ``scripts/check_sweep.py``. Two strategies:

  embedding  semantic search over title and abstract; best for "what has
             appeared lately" on a topic.
  keyword    BM25 over title, abstract and full text, returning the page
             snippet that matched; it finds a paper whose abstract omits the
             term but whose body uses it (a temporal split mentioned only in
             the experimental section, for instance).

The endpoints are undocumented, so a failed call means the API moved, never
that no literature exists; every failure is printed and the other queries
still run.

    python scripts/alphaxiv_sweep.py sweep --after 2026-09-12
    python scripts/alphaxiv_sweep.py embedding "tabular foundation model credit default" --after 2026-09-01
    python scripts/alphaxiv_sweep.py keyword "TabPFN vintage" --after 2026-08-01 --recency
    python scripts/alphaxiv_sweep.py paper 2609.16102

Candidates found here are abstract-only until the full text is read.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request

API = "https://api.alphaxiv.org"
USER_AGENT = "outoftime-literature-sweep"
HITS_PER_QUERY = 10

STANDING = [
    ("embedding", "tabular foundation model credit risk probability of default"),
    ("embedding", "TabPFN TabICL out-of-time temporal split distribution shift evaluation"),
    ("embedding", "calibration of tabular foundation models reliability proper scoring"),
    ("embedding", "vintage analysis credit scoring model degradation over origination cohorts"),
    ("embedding", "population stability index critical values hypothesis test"),
    ("embedding", "in-context learning tabular context selection time-ordered data"),
    ("keyword", "TabPFN credit"),
    ("keyword", "TabICL credit"),
    ("keyword", "TabPFN out-of-time"),
    ("keyword", "population stability index Yurdakul"),
    ("keyword", "Lending Club TabPFN"),
    ("keyword", "Freddie Mac TabPFN"),
]


def get(path: str, params: dict | None = None):
    url = API + path + ("?" + urllib.parse.urlencode(params) if params else "")
    request = urllib.request.Request(url, headers={"user-agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def discover(strategy: str, query: str, after=None, before=None, prioritize="default"):
    params = {"q": query, "prioritize": prioritize}
    if after:
        params["publishedAfter"] = after
    if before:
        params["publishedBefore"] = before
    return get(f"/search/v2/paper/discover/{strategy}", params)


def show(hits, seen: set | None = None) -> None:
    for hit in hits:
        paper_id = hit["paperId"]
        if seen is not None:
            if paper_id in seen:
                continue
            seen.add(paper_id)
        print(f"{paper_id}  {hit.get('publicationDate', '')[:10]}  {hit['title']}")
        for snippet in (hit.get("snippets") or [])[:1]:
            text = snippet["snippet"][:200].replace("\n", " ")
            print(f"    p{snippet.get('pageNumber')}> {text}")


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("mode", choices=["keyword", "embedding", "paper", "sweep"])
    parser.add_argument("query", nargs="?")
    parser.add_argument("--after", help="YYYY-MM-DD, publication date lower bound")
    parser.add_argument("--before", help="YYYY-MM-DD, publication date upper bound")
    parser.add_argument("--recency", action="store_true", help="rank newer papers first")
    args = parser.parse_args(argv)
    prioritize = "recency" if args.recency else "default"

    if args.mode == "paper":
        paper = get("/papers/v3/" + re.sub(r"v\d+$", "", args.query))
        print(paper["title"], "|", paper.get("sourceUrl"))
        print(paper.get("abstract", ""))
        print(paper.get("citationBibtex", ""))
        return 0

    if args.mode == "sweep":
        seen: set = set()
        failed = 0
        for strategy, query in STANDING:
            print(f"\n## {strategy}: {query}")
            try:
                show(discover(strategy, query, args.after, args.before)[:HITS_PER_QUERY], seen)
            except (OSError, ValueError, KeyError) as error:  # URLError, HTTPError, bad JSON
                failed += 1
                print("   FAILED:", error)
        print(f"\n{len(seen)} distinct papers over {len(STANDING)} queries, {failed} failed")
        return 1 if failed == len(STANDING) else 0

    if not args.query:
        parser.error(f"{args.mode} needs a query")
    show(discover(args.mode, args.query, args.after, args.before, prioritize))
    return 0


if __name__ == "__main__":
    sys.exit(main())
