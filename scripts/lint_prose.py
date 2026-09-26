"""Prose linter: counts the statistical tells of stock, templated prose in markdown (RU/EN).

Not a detector and not a score — a set of raw metrics plus flagged lines,
so a rewrite can be checked against the same numbers. Deterministic, no deps.

Usage: python lint_prose.py [--check] FILE [FILE...]

With --check the exit code is non-zero when a file breaches a threshold, so a
public text cannot be committed reading like dictation. Without it the metrics
are printed and nothing fails, which is the mode for a draft in progress.
"""
import re
import statistics
import sys

STOCK_EN = [
    "delve", "leverage", "robust", "seamless", "unlock", "game-chang",
    "revolutionar", "it's worth noting", "furthermore", "moreover",
    "in conclusion", "in today's", "let's dive", "dive into", "empower",
    "it is important to note", "notably,",
]
STOCK_RU = [
    "стоит отметить", "важно отметить", "в заключение", "погрузимся",
    "давайте разберемся", "давайте разберёмся", "в современном мире",
    "не секрет, что", "как известно",
]
# contrast frames: the "not X; it's Y" / "didn't fall; it was" cadence
CONTRAST_EN = [
    r"\bisn't\b[^.;]{0,60};", r";\s*it'?s\b", r"\bnot\b[^.,;]{1,40},?\s+but\b",
    r"\bdidn'?t\b[^.;]{0,60};\s*it\b", r"\bno\b[^.;]{1,30}—\s*just\b",
]
CONTRAST_RU = [
    r"не\s+[^.;,]{1,40}—\s*(?:а|это)\b", r";\s*это\b",
]
# The rule of three is a cadence over words. A claim row writes "11, 23 and 21
# cohorts" and "[+0.00003, +0.00109], 20260907) and holds zero" by the dozen,
# and the same pattern matches those: the commas there belong to the figures,
# not to the cadence. A match carrying a digit is therefore read as a list of
# figures and not as a triad, at the price of missing a rule of three built on
# numbers, which is rare and is the cheaper of the two errors here.
TRIAD = (r"[\w’']+[^,.;:\n]{0,25},\s+[\w’']+[^,.;:\n]{0,25},?"
         r"\s+(?:and|или|и)\s+[\w’']+")
HAS_DIGIT = re.compile(r"\d")


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+", text)
    return [p for p in (s.strip() for s in parts) if len(p) > 1]


def words(s):
    return re.findall(r"[A-Za-zА-Яа-яЁё0-9'’\-]+", s)


def is_prose_par(par):
    p = par.strip()
    if not p or p.startswith(("#", "|", "```", "<", "[IMAGE", "---")):
        return False
    if re.match(r"^\*[^*]+\*$", p):  # caption-only paragraph: still prose
        return True
    return True


def lint(path):
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    # strip code blocks and front matter
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    body_pars = [p for p in re.split(r"\n\s*\n", text) if is_prose_par(p)]
    prose = "\n\n".join(p for p in body_pars if not p.strip().startswith("#"))
    plain = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", prose)   # unlink
    plain = plain.replace("**", "").replace("`", "")

    sents = split_sentences(re.sub(r"\s+", " ", plain))
    slens = [len(words(s)) for s in sents]
    n_words = sum(slens)
    pars = [p for p in re.split(r"\n\s*\n", plain) if p.strip() and not p.strip().startswith("#")]
    plens = [len(split_sentences(re.sub(r"\s+", " ", p))) for p in pars]

    low = plain.lower()
    # En-dashes joining surnames (Duan–Mao–Mao–Shu–Yin) or bounding a numeric
    # range (10⁶–10⁷, 2020–2024) are scientific typography, not a tell, and
    # counting them with the rest inflates the metric on exactly the texts this
    # is used on. Split out rather than dropped, so the number stays checkable.
    citation_dash = len(re.findall(r"(?<=[A-Za-zА-Яа-яЁё])–(?=[A-ZА-Я])", plain))
    citation_dash += len(re.findall(r"(?<=[\d⁰¹²³⁴⁵⁶⁷⁸⁹])\s?–\s?(?=[\d⁰¹²³⁴⁵⁶⁷⁸⁹])", plain))
    em_dash = plain.count("—")
    en_dash = plain.count("–")
    dash = em_dash + max(0, en_dash - citation_dash)
    # Split out rather than dropped, so the number stays checkable: what the
    # pattern matched, and how much of it was a list of figures.
    matched = re.findall(TRIAD, plain)
    figure_lists = [m for m in matched if HAS_DIGIT.search(m)]
    triads = len(matched) - len(figure_lists)
    stock_hits = [w for w in STOCK_EN + STOCK_RU if w in low]
    contrast = 0
    contrast_lines = []
    for pat in CONTRAST_EN + CONTRAST_RU:
        for m in re.finditer(pat, plain, flags=re.IGNORECASE):
            contrast += 1
            ln = plain[: m.start()].count("\n") + 1
            contrast_lines.append((ln, plain[max(0, m.start() - 30): m.end() + 20].replace("\n", " ")))
    rhet_q = sum(1 for s in sents if s.endswith("?"))
    starters = [words(s)[0].lower() for s in sents if words(s)]
    top_starter, top_n = ("", 0)
    if starters:
        from collections import Counter
        top_starter, top_n = Counter(starters).most_common(1)[0]
    bold_runs = text.count("**") // 2

    def cv(xs):
        return (statistics.pstdev(xs) / statistics.mean(xs)) if xs and statistics.mean(xs) else 0.0

    print(f"\n=== {path} ===")
    print(f"words {n_words} | sentences {len(sents)} | paragraphs {len(pars)}")
    print(f"dashes per 1000 words       : {dash * 1000 / max(1, n_words):.1f}   (target < 6)")
    print(f"  of which em / en / cited  : {em_dash} / {en_dash - citation_dash} / {citation_dash} excluded")
    print(f"sentence len mean/cv        : {statistics.mean(slens):.1f} / {cv(slens):.2f}   (cv target > 0.55)")
    print(f"short sents <8w             : {sum(1 for x in slens if x < 8) * 100 // max(1, len(slens))}%   (target > 12%)")
    print(f"paragraph sents mean/cv     : {statistics.mean(plens):.1f} / {cv(plens):.2f}   (cv target > 0.45)")
    print(f"triad constructions         : {triads}   (target <= 3)")
    print(f"  of which lists of figures : {len(figure_lists)} set aside")
    print(f"contrast frames (not/;it's) : {contrast}   (target <= 3)")
    print(f"rhetorical questions        : {rhet_q}")
    print(f"bold runs                   : {bold_runs}   (target <= 8)")
    print(f"top sentence starter        : '{top_starter}' x{top_n} ({top_n * 100 // max(1, len(sents))}%)")
    print(f"stock phrases               : {stock_hits if stock_hits else 'none'}")
    if contrast_lines:
        print("contrast-frame spots:")
        for ln, frag in contrast_lines[:8]:
            print(f"  ~line {ln}: …{frag}…")

    return {
        "dash_per_1000": dash * 1000 / max(1, n_words),
        "sent_cv": cv(slens),
        "triads": triads,
        "contrast": contrast,
        "stock": stock_hits,
    }


def breaches(path):
    """Thresholds that hold for any public text here. Deliberately few: the
    ones below are counts of a specific habit, not a style score."""
    out = []
    m = lint(path)
    if m["dash_per_1000"] >= 6:
        out.append(f"dashes per 1000 words {m['dash_per_1000']:.1f}, limit 6")
    if m["sent_cv"] <= 0.55:
        out.append(f"sentence length cv {m['sent_cv']:.2f}, floor 0.55")
    if m["triads"] > 3:
        out.append(f"triad constructions {m['triads']}, limit 3")
    if m["contrast"] > 3:
        out.append(f"contrast frames {m['contrast']}, limit 3")
    if m["stock"]:
        out.append(f"stock phrases {m['stock']}")
    return out


if __name__ == "__main__":
    args = sys.argv[1:]
    check = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        sys.exit(__doc__)
    sys.stdout.reconfigure(encoding="utf-8")
    failed = 0
    for f in files:
        if check:
            problems = breaches(f)
            if problems:
                failed += 1
                for problem in problems:
                    print(f"{f}: {problem}", file=sys.stderr)
        else:
            lint(f)
    if check:
        if failed:
            print(f"prose: {failed} file(s) over threshold", file=sys.stderr)
        else:
            print("prose: clean")
    sys.exit(1 if failed else 0)
