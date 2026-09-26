#!/usr/bin/env python3
"""Scores one build's cohorts with a tabular foundation model, on a node.

This is the half of the study that runs on an accelerator, and it runs on a
machine that holds nothing but this file, a bundle from `export_context.py`
and the model weights. It reads no raw data, imports nothing from the
repository, and decides nothing: which rows form the context and which rows
are scored were settled where the book lives, and this script scores them.

For every model and every context seed in the bundle, the model is given the
context rows with their outcomes and asked for a probability on the same
context rows and on every scored cohort. The context scores are the reference
the stability index reads against; the cohort scores are the cells. Both come
out in the row format of `score_build.py`, so the node's two parquet files
append to the classical run's and the intervals script pairs every model on
the same rows.

Every cell is written to disk as soon as it exists, under `parts/`, and a
cell whose part is already there is not scored again. A runtime that dies,
as a free notebook's does on a schedule, costs the cell in flight and
nothing before it; starting the same command again continues.

Three things are checked and recorded rather than trusted. The bundle's files
are hashed and compared with the hashes the exporter wrote, so a copy that
was damaged in transfer is refused. A cohort cell whose rows are in the
context that would score it is refused before anything is fitted, because a
model scoring rows it was conditioned on measures nothing and says so
nowhere. And the first cell of every model is
scored twice from a fresh fit, and the largest disagreement between the two
passes is recorded, because an accelerator forward pass is not guaranteed to
be deterministic and the determinism gate asks for the disagreement, not for
an assurance.

    python score_context.py bundle --out-dir out --models tabpfn,tabicl --nearest 3

On Colab, upload the bundle directory and run the same line with the `!`
escape. TabPFN's licence token is read from the notebook's secret store under
TABPFN_TOKEN and is never written into a cell; a node that already holds the
checkpoint file needs no token at all.

Two settings can be moved off the library default, for the one question the
defaults cannot answer: whether a shortfall in the probabilities is the
model's or the softmax's. `--temperature` sets `softmax_temperature` on
either model (both ship 0.9), and `--balance` sets TabPFN's
`balance_probabilities`. A model scored off its defaults is written under a
name that says so, `tabpfn@t1`, `tabpfn@t1+bal`, `tabicl@t1`, so its
rows sit beside the default rows in the intervals table and never replace
them; its parts, its node record and its console lines carry the same name.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

import numpy as np
import pandas as pd

CONTEXT_FILE = "context.parquet"
SCORED_FILE = "scored.parquet"
DESCRIPTION_FILE = "bundle.json"
NODE_FILE = "node.json"
MODELS = ("tabpfn", "tabicl")

SCORE_COLUMNS = ["build_id", "arm", "as_of", "model", "context_seed", "cohort",
                 "age_quarters", "row", "outcome", "pd"]
REFERENCE_COLUMNS = ["build_id", "arm", "as_of", "model", "context_seed", "row", "outcome", "pd"]


# --- the machine ------------------------------------------------------------


def package(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def environment() -> dict:
    """What produced these numbers: interpreter, stack, and the accelerator."""
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "packages": {name: package(name)
                     for name in ("torch", "tabpfn", "tabicl", "numpy", "pandas", "scikit-learn")},
        "device": "cpu",
        "device_name": None,
    }
    try:
        import torch
    except ImportError:
        return info
    info["cuda"] = torch.version.cuda
    if torch.cuda.is_available():
        info["device"] = "cuda"
        info["device_name"] = torch.cuda.get_device_name(0)
        info["device_memory_gb"] = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2)
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        info["device"] = "mps"
        info["device_name"] = f"Apple Silicon GPU ({platform.machine()})"
        info["memory_is_unified"] = True
    return info


def peak_memory_gb() -> float | None:
    """Peak allocation on CUDA; on Metal the current allocation, which understates."""
    try:
        import torch
    except ImportError:
        return None
    if torch.cuda.is_available():
        return round(torch.cuda.max_memory_allocated() / 1e9, 3)
    mps = getattr(torch, "mps", None)
    if mps is not None and torch.backends.mps.is_available():
        for name in ("driver_allocated_memory", "current_allocated_memory"):
            reader = getattr(mps, name, None)
            if reader is not None:
                return round(reader() / 1e9, 3)
    return None


def reset_memory() -> None:
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        empty = getattr(getattr(torch, "mps", None), "empty_cache", None)
        if empty is not None:
            empty()


def synchronise() -> None:
    """A GPU launch is asynchronous, so an unsynchronised timer times nothing."""
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.synchronize()
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        sync = getattr(getattr(torch, "mps", None), "synchronize", None)
        if sync is not None:
            sync()


def load_colab_secret(name: str) -> bool:
    """Copies a Colab secret into the environment; false when there is none."""
    if os.environ.get(name):
        return True
    try:
        from google.colab import userdata
        value = userdata.get(name)
    except Exception:  # noqa: BLE001 - not on Colab, or access not granted
        return False
    if value:
        os.environ[name] = value
        return True
    return False


# --- the models -------------------------------------------------------------


def variant(name: str, settings: dict | None) -> str:
    """The name a model is written under: bare at the defaults, tagged off them."""
    tags = []
    if settings and settings.get("temperature") is not None:
        tags.append(f"t{settings['temperature']:g}")
    if settings and settings.get("balance"):
        tags.append("bal")
    return name if not tags else f"{name}@{'+'.join(tags)}"


def build(name: str, device: str, categorical: list[int], settings: dict | None = None):
    """A fresh estimator of the named model, at the library's defaults.

    Nothing is tuned, because the object under study is the model as shipped:
    a risk team that adopted one would adopt it at these settings. The one
    setting passed is the list of categorical columns, which the bundle
    declares and TabPFN would otherwise guess from cardinality. TabICL reads
    an object column as categorical on its own. `settings` holds the two
    knobs the command may move, and nothing else reaches the constructor.
    """
    settings = settings or {}
    temperature = settings.get("temperature")
    if name == "tabpfn":
        load_colab_secret("TABPFN_TOKEN")
        from tabpfn import TabPFNClassifier
        extra = {}
        if temperature is not None:
            extra["softmax_temperature"] = float(temperature)
        if settings.get("balance"):
            extra["balance_probabilities"] = True
        return TabPFNClassifier(device=device, categorical_features_indices=categorical or None,
                                ignore_pretraining_limits=True, **extra)
    if name == "tabicl":
        if settings.get("balance"):
            raise SystemExit("--balance is TabPFN's balance_probabilities; tabicl has no such "
                             "setting, so score it in a separate command")
        from tabicl import TabICLClassifier
        extra = {} if temperature is None else {"softmax_temperature": float(temperature)}
        return TabICLClassifier(device=None if device == "auto" else device, **extra)
    raise ValueError(f"unknown model {name!r}; one of {MODELS}")


def parameters(model) -> dict:
    try:
        return {k: v for k, v in sorted(model.get_params().items())}
    except Exception:  # noqa: BLE001 - a model without sklearn's protocol
        return {}


def checkpoint_hashes() -> dict[str, str]:
    """The weights this run read, by file hash, wherever the libraries keep them."""
    roots = [Path(p) for p in (os.environ.get("TABPFN_MODEL_CACHE_DIR"),
                                os.environ.get("HF_HOME"), os.environ.get("XDG_CACHE_HOME"))
             if p]
    roots += [Path.home() / ".cache", Path.home() / "Library" / "Caches" / "tabpfn"]
    found: dict[str, str] = {}
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*.ckpt"):
            found[path.name] = sha256(path)
    return found


# --- the bundle -------------------------------------------------------------


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_bundle(bundle: Path) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    description = json.loads((bundle / DESCRIPTION_FILE).read_text(encoding="utf-8"))
    for name, expected in description["files"].items():
        actual = sha256(bundle / name)
        if actual != expected:
            raise SystemExit(f"{name} does not hash to what the exporter wrote; "
                             f"the bundle was damaged in transfer")
    context = pd.read_parquet(bundle / CONTEXT_FILE)
    scored = pd.read_parquet(bundle / SCORED_FILE)
    for name in description["categorical"]:
        # Object with None for a missing value, whatever pandas read the
        # column back as, so that both models see one categorical dtype.
        for frame in (context, scored):
            frame[name] = frame[name].astype(object).where(frame[name].notna(), None)
    return description, context, scored


def select_cohorts(scored: pd.DataFrame, nearest: int | None) -> list[str]:
    """The cohorts to score: all of them, or the youngest N.

    Cohort names sort chronologically, and the youngest cohort of a build is
    the first one after the blind gap, so the nearest N are the first N.
    """
    order = sorted(scored["cohort"].unique())
    return order if nearest is None else order[:nearest]


def refuse_context_meeting_cells(context: pd.DataFrame, scored: pd.DataFrame,
                                 cohorts: list[str], seeds: list[int]) -> None:
    """Refuses a cohort cell whose rows are in the context that would score it.

    The reference cell is the context and is scored on it deliberately, which
    is what makes the in-sample level readable; every cohort cell is held out
    and must not meet it. A bundle that packs several folds of one pool into
    one file breaks that silently, because each fold's context is drawn from
    rows the other folds hold out, and the scores that come back look like
    every other scored cell. The check is a set intersection on `row` and
    costs nothing beside a fit.

    Only the cells that will be scored are checked, against only the draws
    that will score them: a cohort left out by `--nearest`, or a draw left out
    by `--seeds`, is not read. The question is whether a cell this run writes
    was conditioned on its own rows, not whether the bundle is clean.
    """
    for seed in seeds:
        context_rows = pd.Index(context.loc[context["context_seed"] == seed, "row"])
        for cohort in cohorts:
            cell = pd.Index(scored.loc[scored["cohort"] == cohort, "row"])
            met = int(cell.isin(context_rows).sum())
            if met:
                raise SystemExit(
                    f"context seed {seed}: {met:,} of the {len(cell):,} rows of {cohort} are in "
                    f"the context that would score it; nothing is scored")


# --- the run ----------------------------------------------------------------


def part_path(out: Path, model: str, seed: int, cell: str) -> Path:
    return out / "parts" / f"{model}-{seed}-{cell}.parquet"


def score(model, frame: pd.DataFrame, features: list[str], chunk: int) -> np.ndarray:
    """The probability of the positive class on every row, in the frame's order."""
    x = frame[features]
    if chunk <= 0 or len(x) <= chunk:
        return np.asarray(model.predict_proba(x))[:, 1].astype(float)
    pieces = [np.asarray(model.predict_proba(x.iloc[i:i + chunk]))[:, 1]
              for i in range(0, len(x), chunk)]
    return np.concatenate(pieces).astype(float)


def fit(name: str, device: str, context: pd.DataFrame, features: list[str],
        categorical: list[int], settings: dict | None = None):
    model = build(name, device, categorical, settings)
    model.fit(context[features], context["outcome"].to_numpy())
    return model


def run(bundle: Path, out: Path, models: list[str], *, nearest: int | None, seeds: list[int] | None,
        device: str, chunk: int, repeat: bool, settings: dict | None = None) -> dict:
    settings = {k: v for k, v in (settings or {}).items() if v}
    started = time.time()
    description, context, scored = load_bundle(bundle)
    features = list(description["features"])
    categorical = [features.index(name) for name in description["categorical"]]
    cohorts = select_cohorts(scored, nearest)
    context_seeds = [int(s) for s in description["context"]["seeds"]]
    if seeds:
        unknown = set(seeds) - set(context_seeds)
        if unknown:
            raise SystemExit(f"the bundle holds no context for seeds {sorted(unknown)}")
        context_seeds = [s for s in context_seeds if s in seeds]
    refuse_context_meeting_cells(context, scored, cohorts, context_seeds)
    out.mkdir(parents=True, exist_ok=True)
    (out / "parts").mkdir(exist_ok=True)
    stamp = {k: scored[k].iloc[0] for k in ("build_id", "arm", "as_of")}

    node_path = out / NODE_FILE
    node = json.loads(node_path.read_text(encoding="utf-8")) if node_path.exists() else {
        "bundle": {"path": bundle.as_posix(), "files": description["files"],
                   "build": description["build"], "features": features,
                   "categorical": description["categorical"]},
        "environment": environment(),
        "cohorts": cohorts, "context_seeds": context_seeds,
        "models": {}, "cells": [], "repeats": [],
    }
    node["environment"] = environment()
    node["command"] = {"models": models, "nearest": nearest, "device": device, "chunk": chunk,
                       "repeat": repeat, "settings": settings}
    node["tuning_budget"] = ("none: zero trials, no validation split, every parameter at the "
                             "library default except those the command names; the classical "
                             "models this is paired with were tuned on their own pool and the "
                             "asymmetry runs both ways, since the 50,000-row control inherits "
                             "the point chosen on the full pool")

    def flush() -> None:
        node["wall_seconds"] = round(time.time() - started, 1)
        node_path.write_text(json.dumps(node, indent=2, default=str), encoding="utf-8")

    for name in models:
        if name not in MODELS:
            raise SystemExit(f"unknown model {name!r}; one of {MODELS}")
        label = variant(name, settings)
        for seed in context_seeds:
            wanted = [("reference", None)] + [(cohort, cohort) for cohort in cohorts]
            missing = [(cell, cohort) for cell, cohort in wanted
                       if not part_path(out, label,seed, cell).exists()]
            if not missing:
                print(f"{label}/{seed}: every part present, skipped", flush=True)
                continue
            rows = context[context["context_seed"] == seed].reset_index(drop=True)
            reset_memory()
            synchronise()
            fit_started = time.perf_counter()
            model = fit(name, device, rows, features, categorical, settings)
            synchronise()
            fit_seconds = time.perf_counter() - fit_started
            node["models"][f"{label}/{seed}"] = {
                "context_rows": len(rows), "fit_seconds": round(fit_seconds, 3),
                "parameters": parameters(model),
            }
            print(f"{label}/{seed}: context {len(rows):,} rows read in {fit_seconds:.1f}s",
                  flush=True)

            for cell, cohort in missing:
                frame = rows if cohort is None else (
                    scored[scored["cohort"] == cohort].reset_index(drop=True))
                reset_memory()
                synchronise()
                cell_started = time.perf_counter()
                predicted = score(model, frame, features, chunk)
                synchronise()
                seconds = time.perf_counter() - cell_started
                if not np.isfinite(predicted).all():
                    raise SystemExit(f"{label}/{seed}/{cell}: a non-finite probability")
                if cohort is None:
                    part = pd.DataFrame({**stamp, "model": label, "context_seed": seed,
                                         "row": frame["row"].to_numpy(dtype=np.int64),
                                         "outcome": frame["outcome"].to_numpy(dtype=np.int64),
                                         "pd": predicted})[REFERENCE_COLUMNS]
                else:
                    part = pd.DataFrame({**stamp, "model": label, "context_seed": seed,
                                         "cohort": cohort,
                                         "age_quarters": int(frame["age_quarters"].iloc[0]),
                                         "row": frame["row"].to_numpy(dtype=np.int64),
                                         "outcome": frame["outcome"].to_numpy(dtype=np.int64),
                                         "pd": predicted})[SCORE_COLUMNS]
                part.to_parquet(part_path(out, label,seed, cell), index=False)
                node["cells"].append({
                    "model": label, "context_seed": seed, "cell": cell, "rows": len(frame),
                    "seconds": round(seconds, 3), "peak_gpu_gb": peak_memory_gb(),
                    "mean_pd": round(float(predicted.mean()), 6),
                })
                flush()
                print(f"  {cell:<10} {len(frame):>7,} rows  {seconds:>7.1f}s  "
                      f"mean pd {predicted.mean():.4f}", flush=True)

            if repeat and cohorts and not any(r["model"] == label and r["context_seed"] == seed
                                              for r in node["repeats"]):
                # The same cell again from a fresh fit, for the disagreement.
                cohort = cohorts[0]
                frame = scored[scored["cohort"] == cohort].reset_index(drop=True)
                first = pd.read_parquet(part_path(out, label,seed, cohort))["pd"].to_numpy()
                again = score(fit(name, device, rows, features, categorical, settings), frame, features,
                              chunk)
                gap = np.abs(again - first)
                node["repeats"].append({
                    "model": label, "context_seed": seed, "cell": cohort,
                    "max_abs_difference": float(gap.max()),
                    "mean_abs_difference": float(gap.mean()),
                    "rows_differing": int((gap > 0).sum()),
                })
                flush()
                print(f"  repeat {cohort}: largest disagreement {gap.max():.2e}, "
                      f"{int((gap > 0).sum()):,} rows differ", flush=True)
            del model

    node["checkpoints"] = checkpoint_hashes()
    scores = sorted((out / "parts").glob("*.parquet"))
    references = [p for p in scores if p.stem.endswith("-reference")]
    cells = [p for p in scores if p not in references]
    if cells:
        pd.concat([pd.read_parquet(p) for p in cells], ignore_index=True).astype(
            {"context_seed": "Int64"}).to_parquet(out / "scores.parquet", index=False)
    if references:
        pd.concat([pd.read_parquet(p) for p in references], ignore_index=True).astype(
            {"context_seed": "Int64"}).to_parquet(out / "reference.parquet", index=False)
    node["scored_rows"] = int(sum(len(pd.read_parquet(p)) for p in cells))
    node["reference_rows"] = int(sum(len(pd.read_parquet(p)) for p in references))
    flush()
    print(f"\nscored rows           : {node['scored_rows']:,}")
    print(f"reference rows        : {node['reference_rows']:,}")
    print(f"wall                  : {time.time() - started:.0f}s")
    return node


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("bundle", type=Path, help="a directory written by export_context.py")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--nearest", type=int, default=None,
                        help="score only the N youngest cohorts; default every cohort")
    parser.add_argument("--seeds", default="",
                        help="context seeds to score, comma-separated; default every seed "
                             "in the bundle")
    parser.add_argument("--device", default="auto")
    parser.add_argument("--chunk", type=int, default=0,
                        help="rows per predict call; 0 scores a cohort in one call")
    parser.add_argument("--no-repeat", action="store_true",
                        help="skip the second pass on the first cell of every model")
    parser.add_argument("--temperature", type=float, default=None,
                        help="softmax_temperature for every model named; default the "
                             "library's, 0.9 on both")
    parser.add_argument("--balance", action="store_true",
                        help="TabPFN's balance_probabilities; refused for tabicl")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run(args.bundle, args.out_dir, [m.strip() for m in args.models.split(",") if m.strip()],
        nearest=args.nearest, seeds=[int(s) for s in args.seeds.split(",") if s.strip()],
        device=args.device, chunk=args.chunk, repeat=not args.no_repeat,
        settings={"temperature": args.temperature, "balance": args.balance})
    return 0


if __name__ == "__main__":
    sys.exit(main())
