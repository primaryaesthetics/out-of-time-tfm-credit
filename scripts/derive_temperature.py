#!/usr/bin/env python3
"""Derives a foundation model's rows at one softmax temperature from its rows at another.

A softmax temperature divides the logit before the sigmoid, so for a model
that averages its ensemble on the logit scale the probability at one
temperature is an exact function of the probability at another:

    logit(p_to) = logit(p_from) * (from / to)

TabICL averages logits (``average_logits=True`` in its recorded parameters),
and its rows at 1.0 follow from its rows at the shipped 0.9 to the precision
of the stored probability. TabPFN averages after the softmax, and for it the
relation holds only approximately; by default its rows at another
temperature are scored, not derived. The script does not decide this by
model name: it refuses any model whose recorded parameters do not say the
ensemble is averaged on the logit scale, unless the approximation is asked
for by name, below.

The derivation is an identity about the library as installed, and a later
version that applies the temperature differently would break it silently.
So the derived rows are never written without a check against rows the
library actually scored at the target temperature: every checked cell has
to hold the same rows, and every row has to agree to a tolerance on the
probability, or nothing is written; a probability that is not a number, on
either side, refuses. The version of the library and the checkpoint it
loaded have to be the same in the source and the check. Every checked cell
is named by its build, context seed and cell in derive.json and in every
refusal.

    python scripts/derive_temperature.py \\
        experiments/<scored at 0.9> ... \\
        --check experiments/<scored at 1.0> \\
        --out-dir experiments/<derived>

Rows scored at the target temperature may exist on one build only, and the
derivation is wanted on every build. With ``--check-source`` the check is
made on that build and carried to the others by identity: the directory it
names holds the same model at the source temperature on the check's cells,
its rows are derived in memory by the same formula, and those rows are
compared with ``--check`` exactly as above — the same rows, the same
outcomes, every row within the tolerance, or nothing is written. Only the
sources' derived rows are written. The library version and the checkpoint
have to be identical across every source, the check source and the check;
every draw the check source holds has to be a draw the sources hold, scored
at the same temperature; and every source, the check source and the check
have to name one device, since what is carried to the sources is an identity
measured on that device. No derived row is then compared with a scored row,
and derive.json says so:
it names the build the checked cells belong to and the build the derived
rows belong to, and lists every derived cell as unchecked by row.

    python scripts/derive_temperature.py \\
        experiments/<build B scored at 0.9> \\
        --check-source experiments/<build A scored at 0.9> \\
        --check experiments/<build A scored at 1.0> \\
        --out-dir experiments/<build B derived>

``--approximate`` derives a model that averages after the softmax by the
same formula, as an approximation. It is refused for a model whose recorded
parameters say the ensemble is averaged on the logit scale
(``average_logits`` or ``average_before_softmax``), so an exact model never
takes this path. The check is then a measurement and not an identity: on
every checked cell, the largest and the mean absolute gap on the
probability and on the logit; the slope b of the scored logit on the
derived logit over the cell's rows; and the cell's mean probability,
observed over expected and Cox slope on the derived rows and on the scored
ones, with their differences. One quantity is bounded: |b − 1| per checked
cell. The derivation assumes the temperature is a scale on the logit, and b
is the scale that is missing from it; the level, which a scale on the logit
moves only through the mean of the logit, is reported and not bounded, and
a gap on the probability is not bounded because at a two-percent rate it
reads small whatever the scale error. The Lending Club figure, 8.4 × 10⁻⁴,
is the same measurement on that book's expanding-arm cells: derive.json
counts and names the checked cells above it, and nothing is refused there.
The derivation is refused only above the bound ``--max-cell-error`` gives,
which is required with ``--approximate``; EXP-005's note of 2026-09-14 sets
it at 8.4 × 10⁻³, ten times the Lending Club figure. The worst and the mean
derived-minus-scored gap in Cox slope and in observed over expected over the
checked cells are recorded beside the worst and mean |b − 1|, since a
statistic read from the rows is a Cox slope or a level more often than a
scale. The sources, the check source where one is named, and the check
have to name one device, since the approximation is a property of the
forward pass and not only of the library. derive.json marks the derivation
``approximate`` and carries every measured cell, so a pooling can put the
error beside a statistic read from the rows. The rows keep the scored
model's name
(``tabpfn@t1``): on the arm where nothing is scored at the target they
stand in for the scored rows, and the pooling scripts pair models across
arms by name.

    python scripts/derive_temperature.py \\
        experiments/<tabpfn scored at 0.9> \\
        --check experiments/<tabpfn scored at 1.0> \\
        --model tabpfn --approximate --max-cell-error <bound> \\
        --out-dir experiments/<derived>

``--measure-only`` makes the approximate check and writes derive.json alone,
marked ``measure_only``, with no rows: the record of the error on a build
whose rows at the target are scored, where derived rows beside the scored
ones would only be a hazard for a pooling. With it the bound is optional,
and given, it names the cells above it without refusing, since nothing is
derived. It measures the sources' own cells and is refused with
``--check-source``.

The output directory holds scores.parquet and reference.parquet in the shape
score_context.py writes, with the model named as that script names it off
the defaults (``tabicl@t1``), and derive.json: the sources and their hashes,
the temperatures, the library version and checkpoint, and the check cell by
cell. build_intervals.py reads the directory like any scored one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from score_context import NODE_FILE, REFERENCE_COLUMNS, SCORE_COLUMNS, variant

from outoftime import metrics as mt

SCORES_FILE = "scores.parquet"
REFERENCE_FILE = "reference.parquet"
DERIVE_FILE = "derive.json"
TOLERANCE = 1e-6
REFERENCE_CELL = "reference"
# |b - 1| as measured on the Lending Club grid's expanding-arm cells: counted
# against, never refused at.
LENDING_CLUB_FIGURE = 8.4e-4

SCORE_KEYS = ["build_id", "arm", "as_of", "context_seed", "cohort", "row"]
REFERENCE_KEYS = ["build_id", "arm", "as_of", "context_seed", "row"]


class Refused(SystemExit):
    """The derivation is not made; the reason is the message."""

    def __init__(self, reason: str):
        super().__init__(f"refused: {reason}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def logit(p: np.ndarray) -> np.ndarray:
    return np.log(p) - np.log1p(-p)


def sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def rescale(p: np.ndarray, from_temperature: float, to_temperature: float) -> np.ndarray:
    """The probability at ``to_temperature`` from the probability at ``from_temperature``."""
    p = np.asarray(p, dtype=float)
    if not np.all((p > 0.0) & (p < 1.0)):
        raise Refused("a probability of exactly 0 or 1 has no logit to rescale")
    return sigmoid(logit(p) * (from_temperature / to_temperature))


# --- what a scored directory says about itself ---------------------------------


def load_node(directory: Path) -> dict:
    path = directory / NODE_FILE
    if not path.is_file():
        raise Refused(f"{directory.as_posix()} holds no {NODE_FILE}; the library version, the "
                      "checkpoint and the temperature it scored at are unknown")
    return json.loads(path.read_text(encoding="utf-8"))


def library_of(node: dict, package: str) -> str:
    version = node.get("environment", {}).get("packages", {}).get(package)
    if not version:
        raise Refused(f"{NODE_FILE} records no {package} version")
    return version


def device_of(directory: Path) -> str:
    """The accelerator a directory's rows were scored on, as its node record names it."""
    name = load_node(directory).get("environment", {}).get("device_name")
    if not name:
        raise Refused(f"{directory.as_posix()}: {NODE_FILE} records no device_name")
    return str(name)


def model_settings(node: dict, model: str) -> dict[int, dict]:
    """The recorded parameters of every context draw of one model."""
    found = {}
    for key, entry in node.get("models", {}).items():
        name, _, seed = key.partition("/")
        if name == model:
            found[int(seed)] = entry.get("parameters", {})
    if not found:
        raise Refused(f"{NODE_FILE} records no parameters for {model}")
    return found


def temperature_of(parameters: dict, model: str, seed: int) -> float:
    temperature = parameters.get("softmax_temperature")
    if temperature is None:
        raise Refused(f"{model}/{seed} records no softmax_temperature")
    return float(temperature)


def checkpoint_of(node: dict, parameters: dict, model: str, seed: int) -> dict[str, str]:
    """The checkpoint one draw loaded, as name and hash; a scorer may hash several models'.

    A model that names its checkpoint (``checkpoint_version``) is read by
    that name. A model that loads the library's default weights records
    ``model_path='auto'`` and no name; the scorer hashes every checkpoint in
    the node's caches, and the one it read is taken to be the single hashed
    checkpoint named for its library. Two such checkpoints, or none, and the
    one it read is not on record, so the derivation is refused.
    """
    name = parameters.get("checkpoint_version")
    if not name:
        path = parameters.get("model_path")
        if path == "auto":
            base = model.split("@", 1)[0]
            candidates = sorted(n for n in node.get("checkpoints", {}) if n.startswith(f"{base}-"))
            if len(candidates) != 1:
                raise Refused(f"{model}/{seed} loaded the library's default weights and "
                              f"{NODE_FILE} hashed {len(candidates)} {base} checkpoints; which "
                              "one it read is not on record")
            name = candidates[0]
        elif path:
            name = Path(str(path)).name
        else:
            raise Refused(f"{model}/{seed} records no checkpoint_version")
    digest = node.get("checkpoints", {}).get(name)
    if not digest:
        raise Refused(f"{model}/{seed} loaded {name}, which {NODE_FILE} did not hash")
    return {name: digest}


def require_logit_averaging(parameters: dict, model: str, seed: int) -> None:
    if parameters.get("average_logits") is not True:
        raise Refused(f"{model}/{seed} does not record average_logits=True; the temperature "
                      "is not an exact scale on its probability and its rows are scored, "
                      "not derived")


def require_approximable(parameters: dict, model: str, seed: int) -> None:
    """Refuses an exact model on the approximate path: it is derived exactly or not at all."""
    if parameters.get("average_logits") is True or parameters.get("average_before_softmax") is True:
        raise Refused(f"{model}/{seed} records that its ensemble is averaged on the logit scale; "
                      "the temperature is an exact scale on its probability, and it is derived "
                      "exactly, not approximately")


def require_one_device(devices: dict) -> None:
    """Refuses a derivation whose sources were scored on another device than its check."""
    for directory, name in devices["sources"].items():
        if name != devices["check"]:
            raise Refused(f"{directory} was scored on {name} and the check on {devices['check']}; "
                          "the derivation is checked on one device and holds on that one")


# The one quantity an approximate derivation is bounded on, as derive.json names it.
CELL_ERROR = ("|b - 1| on each checked cell, b the least-squares slope of the scored logit on "
              "the derived logit over the cell's rows; a derivation that is the scale the "
              "library applies reads b = 1")


def measure_cell(derived: pd.DataFrame, scored: pd.DataFrame) -> dict:
    """What an approximate derivation misses on one cell, against the rows the library scored.

    A Cox fit that is refused on the cell (one outcome class) or does not
    converge is recorded as failed, by which rows, with its slope as NaN; the
    Cox slope is reported and not bounded, so the cell's measurement stands
    without it.
    """
    y = derived["outcome"].to_numpy()
    p_derived = derived["pd"].to_numpy(dtype=float)
    p_scored = scored["pd"].to_numpy(dtype=float)
    if not np.all((p_scored > 0.0) & (p_scored < 1.0)):
        raise Refused("the check holds a probability of exactly 0 or 1, whose logit gap is "
                      "undefined")
    l_derived, l_scored = logit(p_derived), logit(p_scored)
    gap_pd = np.abs(p_derived - p_scored)
    gap_logit = np.abs(l_derived - l_scored)
    centred = l_derived - l_derived.mean()
    slope = float(np.dot(centred, l_scored - l_scored.mean()) / np.dot(centred, centred))
    observed = float(y.mean())
    oe_derived = observed / float(p_derived.mean())
    oe_scored = observed / float(p_scored.mean())
    cox_slopes = {"derived": float("nan"), "scored": float("nan")}
    cox_failed = []
    for which, p in (("derived", p_derived), ("scored", p_scored)):
        try:
            fit = mt.cox(y, p)
        except mt.MetricError:
            cox_failed.append(which)
            continue
        if fit.converged:
            cox_slopes[which] = float(fit.slope)
        else:
            cox_failed.append(which)
    cox_derived, cox_scored = cox_slopes["derived"], cox_slopes["scored"]
    return {
        "rows": int(y.size),
        "max_abs_pd_gap": float(gap_pd.max()), "mean_abs_pd_gap": float(gap_pd.mean()),
        "max_abs_logit_gap": float(gap_logit.max()), "mean_abs_logit_gap": float(gap_logit.mean()),
        "logit_slope": slope, "logit_slope_gap": abs(slope - 1.0),
        "mean_pd_derived": float(p_derived.mean()), "mean_pd_scored": float(p_scored.mean()),
        "mean_pd_gap": float(p_derived.mean() - p_scored.mean()),
        "oe_derived": oe_derived, "oe_scored": oe_scored, "oe_gap": oe_derived - oe_scored,
        "cox_slope_derived": float(cox_derived), "cox_slope_scored": float(cox_scored),
        "cox_slope_gap": float(cox_derived - cox_scored),
        "cox_fit_failed": cox_failed,
    }


def read_rows(directory: Path, model: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = pd.read_parquet(directory / SCORES_FILE)
    reference = pd.read_parquet(directory / REFERENCE_FILE)
    scores = scores[scores["model"] == model].reset_index(drop=True)
    reference = reference[reference["model"] == model].reset_index(drop=True)
    if scores.empty and reference.empty:
        raise Refused(f"{directory.as_posix()} holds no rows of {model}")
    return scores, reference


# --- the derivation --------------------------------------------------------------


def derive(sources: list[Path], model: str, to_temperature: float, package: str,
           approximate: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """The derived rows of ``model`` at ``to_temperature`` and an account of where they came from.

    Exact unless ``approximate``, which admits only a model that does not
    average its ensemble on the logit scale.
    """
    target = variant(model, {"temperature": to_temperature})
    version: str | None = None
    checkpoints: dict | None = None
    scores_out, reference_out, account = [], [], []
    for directory in sources:
        node = load_node(directory)
        this_version = library_of(node, package)
        if version is None:
            version = this_version
        elif this_version != version:
            raise Refused(f"{directory.as_posix()} was scored by {package} {this_version}, an "
                          f"earlier source by {version}; one derivation, one library")
        scores, reference = read_rows(directory, model)
        if ((pd.read_parquet(directory / SCORES_FILE)["model"] == target).any()):
            raise Refused(f"{directory.as_posix()} already holds {target}; it is scored, not a source")
        settings = model_settings(node, model)
        seeds = sorted({int(s) for s in pd.concat([scores["context_seed"], reference["context_seed"]]).dropna().unique()})
        temperatures = {}
        for seed in seeds:
            if seed not in settings:
                raise Refused(f"{model}/{seed} has rows but no recorded parameters")
            if approximate:
                require_approximable(settings[seed], model, seed)
            else:
                require_logit_averaging(settings[seed], model, seed)
            temperatures[seed] = temperature_of(settings[seed], model, seed)
            loaded = checkpoint_of(node, settings[seed], model, seed)
            if checkpoints is None:
                checkpoints = loaded
            elif loaded != checkpoints:
                raise Refused(f"{model}/{seed} loaded {loaded}, an earlier draw {checkpoints}; "
                              "one derivation, one checkpoint")
        for frame, sink in ((scores, scores_out), (reference, reference_out)):
            if frame.empty:
                continue
            frame = frame.copy()
            from_t = frame["context_seed"].astype(int).map(temperatures).to_numpy(dtype=float)
            frame["pd"] = rescale(frame["pd"].to_numpy(), from_t, to_temperature)
            frame["model"] = target
            sink.append(frame)
        account.append({
            "directory": directory.as_posix(),
            "sha256": {name: sha256(directory / name)
                       for name in (SCORES_FILE, REFERENCE_FILE, NODE_FILE)},
            "context_seeds": seeds,
            "from_temperature": {str(seed): temperatures[seed] for seed in seeds},
            "scored_rows": len(scores),
            "reference_rows": len(reference),
        })
    scores_df = pd.concat(scores_out, ignore_index=True)[SCORE_COLUMNS] if scores_out else pd.DataFrame(columns=SCORE_COLUMNS)
    reference_df = pd.concat(reference_out, ignore_index=True)[REFERENCE_COLUMNS] if reference_out else pd.DataFrame(columns=REFERENCE_COLUMNS)
    for frame, keys in ((scores_df, SCORE_KEYS), (reference_df, REFERENCE_KEYS)):
        if not frame.empty and frame.duplicated(keys).any():
            raise Refused("two sources hold the same cell; a cell is derived from one scoring")
    provenance = {
        "model": model, "derived_as": target, "to_temperature": to_temperature,
        "formula": "logit(pd_to) = logit(pd_from) * (from_temperature / to_temperature)",
        "library": {package: version}, "checkpoints": checkpoints,
        "sources": account,
    }
    if approximate:
        provenance["approximate"] = True
    return scores_df, reference_df, provenance


# --- the check -------------------------------------------------------------------


def cells_of(scores: pd.DataFrame, reference: pd.DataFrame
             ) -> dict[tuple[str, int, str], pd.DataFrame]:
    """Every (build, context seed, cell) of the rows, keyed to compare one cell against another.

    The build is part of the key: the reference cell of one build and the
    reference cell of another share a seed and a name and are not one cell.
    """
    cells: dict[tuple[str, int, str], pd.DataFrame] = {}
    for (build, seed, cohort), frame in scores.groupby(["build_id", "context_seed", "cohort"],
                                                       sort=True):
        cells[(str(build), int(seed), str(cohort))] = (
            frame.set_index("row")[["outcome", "pd"]].sort_index())
    for (build, seed), frame in reference.groupby(["build_id", "context_seed"], sort=True):
        cells[(str(build), int(seed), REFERENCE_CELL)] = (
            frame.set_index("row")[["outcome", "pd"]].sort_index())
    return cells


def check(derived: tuple[pd.DataFrame, pd.DataFrame], probe: Path, model: str,
          to_temperature: float, package: str, version: str, checkpoints: dict | None,
          tolerance: float, bound: float | None = None, refuse_above: bool = True) -> dict:
    """The derived rows against rows the library scored at the target temperature.

    Refuses unless the probe was scored by the same library and checkpoint at
    the target temperature, at least one cell is shared, every shared cell
    holds exactly the same rows with the same outcomes and a number on every
    row, and every row agrees to the tolerance on the probability. Returns
    the comparison cell by cell, each cell named by build, seed and cell.

    With a ``bound`` the derivation is approximate: every shared cell is
    measured by `measure_cell` instead, the cells above the bound (infinite
    for none) and above the Lending Club figure are counted, and the refusal
    is on |b − 1| above the bound on any cell, unless ``refuse_above`` is
    False, for a measurement that writes no rows.
    """
    target = variant(model, {"temperature": to_temperature})
    node = load_node(probe)
    probe_version = library_of(node, package)
    if probe_version != version:
        raise Refused(f"the check was scored by {package} {probe_version}, the sources by {version}; "
                      "the derivation is an identity about one installed library")
    for seed, parameters in model_settings(node, target).items():
        if temperature_of(parameters, target, seed) != to_temperature:
            raise Refused(f"{target}/{seed} in the check was scored at "
                          f"{parameters['softmax_temperature']}, not {to_temperature}")
        if bound is None:
            require_logit_averaging(parameters, target, seed)
        else:
            require_approximable(parameters, target, seed)
        loaded = checkpoint_of(node, parameters, target, seed)
        if loaded != checkpoints:
            raise Refused(f"the check loaded {loaded}, the sources {checkpoints}; the derivation "
                          "is an identity about one checkpoint")
    scored, reference = read_rows(probe, target)
    probe_cells = cells_of(scored, reference)
    derived_cells = cells_of(*derived)
    shared = sorted(set(probe_cells) & set(derived_cells))
    if not shared:
        raise Refused("the check shares no cell with the derived rows; nothing was checked")
    report = []
    worst_pd = worst_logit = 0.0
    for key in shared:
        a, b = derived_cells[key], probe_cells[key]
        build, seed, cell = key
        name = f"{build} {seed}/{cell}"
        if not a.index.equals(b.index):
            raise Refused(f"cell {name}: the check holds {len(b):,} rows and the "
                          f"derivation {len(a):,}, or not the same ones")
        if not np.array_equal(a["outcome"].to_numpy(), b["outcome"].to_numpy()):
            raise Refused(f"cell {name}: an outcome differs between the check and the source")
        if not (np.isfinite(a["pd"].to_numpy()).all() and np.isfinite(b["pd"].to_numpy()).all()):
            raise Refused(f"cell {name}: a probability that is not a number; the row cannot be "
                          "compared")
        if bound is not None:
            report.append({"build_id": build, "context_seed": seed, "cell": cell,
                           **measure_cell(a, b)})
            continue
        gap_pd = float(np.max(np.abs(a["pd"].to_numpy() - b["pd"].to_numpy())))
        gap_logit = float(np.max(np.abs(logit(a["pd"].to_numpy()) - logit(b["pd"].to_numpy()))))
        report.append({"build_id": build, "context_seed": seed, "cell": cell, "rows": len(a),
                       "max_abs_pd_gap": gap_pd, "max_abs_logit_gap": gap_logit})
        worst_pd, worst_logit = max(worst_pd, gap_pd), max(worst_logit, gap_logit)
    if bound is not None:
        worst = max(c["logit_slope_gap"] for c in report)
        above = [c for c in report if c["logit_slope_gap"] > bound]
        if above and refuse_above:
            raise Refused(f"{len(above)} of {len(report)} checked cells exceed the bound {bound:g} "
                          f"on |b - 1|, b the slope of the scored logit on the derived logit (worst "
                          f"{worst:.3g}, at {cell_name(max(report, key=lambda c: c['logit_slope_gap']))}"
                          "); the approximation is not as close as the bound requires")
        above_figure = [c for c in report if c["logit_slope_gap"] > LENDING_CLUB_FIGURE]
        unchecked = sorted(set(derived_cells) - set(probe_cells))
        return {
            "directory": probe.as_posix(),
            "sha256": {name: sha256(probe / name) for name in (SCORES_FILE, REFERENCE_FILE, NODE_FILE)},
            "approximate": True,
            "max_cell_error": bound if np.isfinite(bound) else None,
            "refused_above_bound": refuse_above,
            "cells_above_bound": [cell_name(c) for c in above],
            "lending_club_figure": LENDING_CLUB_FIGURE,
            "cells_above_lending_club_figure": len(above_figure),
            "cells_above_lending_club_figure_named": [cell_name(c) for c in above_figure],
            "cell_error": CELL_ERROR,
            "cells": report,
            "rows_checked": int(sum(c["rows"] for c in report)),
            "worst_cell_error": worst,
            "mean_cell_error": float(np.mean([c["logit_slope_gap"] for c in report])),
            "cox_slope_gap": gap_summary(report, "cox_slope_gap"),
            "oe_gap": gap_summary(report, "oe_gap"),
            "cox_fit_failed_cells": [cell_name(c) for c in report if c["cox_fit_failed"]],
            "max_abs_pd_gap": max(c["max_abs_pd_gap"] for c in report),
            "max_abs_logit_gap": max(c["max_abs_logit_gap"] for c in report),
            "unchecked_cells": [{"build_id": b, "context_seed": s, "cell": c}
                                for b, s, c in unchecked],
        }
    if worst_pd > tolerance:
        failing = [c for c in report if c["max_abs_pd_gap"] > tolerance]
        raise Refused(f"{len(failing)} of {len(report)} checked cells exceed the tolerance "
                      f"{tolerance:g} on the probability (worst {worst_pd:.3g}); the temperature "
                      f"is not the scale the derivation assumes for this library")
    unchecked = sorted(set(derived_cells) - set(probe_cells))
    return {
        "directory": probe.as_posix(),
        "sha256": {name: sha256(probe / name) for name in (SCORES_FILE, REFERENCE_FILE, NODE_FILE)},
        "tolerance_on_pd": tolerance,
        "cells": report,
        "rows_checked": int(sum(c["rows"] for c in report)),
        "max_abs_pd_gap": worst_pd,
        "max_abs_logit_gap": worst_logit,
        "unchecked_cells": [{"build_id": b, "context_seed": s, "cell": c}
                            for b, s, c in unchecked],
    }


def cell_name(cell: dict) -> str:
    return f"{cell['build_id']} {cell['context_seed']}/{cell['cell']}"


def gap_summary(report: list[dict], key: str) -> dict:
    """The worst (largest in size, with its sign) and the mean of a derived-minus-scored gap."""
    values = np.array([c[key] for c in report], dtype=float)
    finite = values[np.isfinite(values)]
    if finite.size == 0:
        return {"worst": None, "mean": None, "mean_abs": None, "cells": 0}
    return {"worst": float(finite[np.argmax(np.abs(finite))]), "mean": float(finite.mean()),
            "mean_abs": float(np.abs(finite).mean()), "cells": int(finite.size)}


def builds_of(scores: pd.DataFrame, reference: pd.DataFrame) -> list[str]:
    return sorted({str(b) for b in pd.concat([scores["build_id"], reference["build_id"]]).dropna()})


def check_through(derived: tuple[pd.DataFrame, pd.DataFrame], provenance: dict,
                  check_source: Path, probe: Path, model: str, to_temperature: float,
                  package: str, tolerance: float, bound: float | None = None,
                  refuse_above: bool = True) -> dict:
    """The check made on another build's cells and carried to the derived rows by identity.

    The check source's rows are derived in memory by the same formula and
    compared with the probe by `check`. Refuses unless the check source was
    scored by the sources' library and checkpoint at the sources' temperature
    on every draw, and on the device the probe was scored on. Returns the
    comparison, with every derived cell listed as unchecked by row. With a
    ``bound`` the comparison is the approximate one, and the sources have to
    name the probe's device as well.
    """
    version = provenance["library"][package]
    proxy_scores, proxy_reference, proxy = derive([check_source], model, to_temperature, package,
                                                  approximate=bound is not None)
    if proxy["library"] != provenance["library"]:
        raise Refused(f"the check source was scored by {package} {proxy['library'][package]}, the "
                      f"sources by {version}; the identity is carried only within one library")
    if proxy["checkpoints"] != provenance["checkpoints"]:
        raise Refused(f"the check source loaded {proxy['checkpoints']}, the sources "
                      f"{provenance['checkpoints']}; the identity is carried only within one "
                      "checkpoint")
    source_temperature: dict[str, float] = {}
    for source in provenance["sources"]:
        source_temperature.update(source["from_temperature"])
    proxy_temperature = proxy["sources"][0]["from_temperature"]
    for seed, temperature in proxy_temperature.items():
        wanted = source_temperature.get(seed)
        if wanted is None:
            raise Refused(f"{model}/{seed} in the check source is a draw the sources do not hold; "
                          "the check source has to hold the sources' temperature draw for draw")
        if temperature != wanted:
            raise Refused(f"{model}/{seed} in the check source was scored at {temperature}, the "
                          f"sources at {wanted}; the check source has to hold the sources' "
                          "temperature draw for draw")
    devices = {
        "sources": {s["directory"]: device_of(Path(s["directory"])) for s in provenance["sources"]},
        "check_source": device_of(check_source),
        "check": device_of(probe),
    }
    if devices["check_source"] != devices["check"]:
        raise Refused(f"the check source was scored on {devices['check_source']} and the check on "
                      f"{devices['check']}; the comparison is of one library on one device")
    require_one_device(devices)
    verified = check((proxy_scores, proxy_reference), probe, model, to_temperature, package,
                     version, provenance["checkpoints"], tolerance, bound=bound,
                     refuse_above=refuse_above)
    checked_build = builds_of(proxy_scores, proxy_reference)
    derived_build = builds_of(*derived)
    verified["check_source_unchecked_cells"] = verified.pop("unchecked_cells")
    verified["unchecked_cells"] = [{"build_id": b, "context_seed": s, "cell": c}
                                   for b, s, c in sorted(cells_of(*derived))]
    verified["checked_build"] = checked_build
    verified["derived_build"] = derived_build
    verified["scope"] = (
        f"the rows compared are the check source's, on build {', '.join(checked_build)}, derived "
        f"by the formula and compared with rows the library scored at {to_temperature:g}; no "
        f"derived row of build {', '.join(derived_build)} is compared with a scored row. The "
        "check carries to them by the identity of the library version, the checkpoint and the "
        "source temperature, which are the same across every source, the check source and the "
        "check")
    if bound is not None:
        verified["scope"] += (
            ". The derivation is approximate: what carries is the error measured on the check "
            "source's cells, under the same library, checkpoint, source temperature and device, "
            "and not a verification of the derived rows")
    check_source_record = {
        **proxy["sources"][0],
        "build_id": checked_build,
        "device": devices["check_source"],
    }
    return {"check": verified, "check_source": check_source_record, "devices": devices}


# --- the command -----------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", type=Path, nargs="+",
                        help="directories written by score_context.py holding the model at "
                             "the temperature it was scored at")
    parser.add_argument("--check", type=Path, required=True,
                        help="a directory written by score_context.py holding the same model "
                             "scored at the target temperature; the derivation is refused "
                             "unless every shared cell agrees")
    parser.add_argument("--check-source", type=Path, default=None,
                        help="a directory holding the same model at the sources' temperature on "
                             "the check's cells, usually of another build; its rows are derived "
                             "in memory and compared with --check, and only the sources' rows "
                             "are written")
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--model", default="tabicl")
    parser.add_argument("--package", default=None,
                        help="the installed library whose version pins the derivation; "
                             "defaults to the model name")
    parser.add_argument("--to", type=float, default=1.0, dest="to_temperature",
                        help="the softmax temperature to derive rows at (default 1.0)")
    parser.add_argument("--tolerance", type=float, default=TOLERANCE,
                        help="the largest absolute gap on the probability the check accepts "
                             f"on any row (default {TOLERANCE:g})")
    parser.add_argument("--approximate", action="store_true",
                        help="derive a model that averages after the softmax, as an "
                             "approximation measured against the check; refused for a model "
                             "that averages on the logit scale")
    parser.add_argument("--max-cell-error", type=float, default=None,
                        help="with --approximate, the largest |b - 1| accepted on any checked "
                             "cell, b the slope of the scored logit on the derived logit; "
                             "required with --approximate unless --measure-only, where it only "
                             "names the cells above it")
    parser.add_argument("--measure-only", action="store_true",
                        help="with --approximate, record the check in derive.json and write no "
                             "rows")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    package = args.package or args.model
    if args.out_dir.exists() and any(args.out_dir.iterdir()) and (
            (args.out_dir / SCORES_FILE).exists() or (args.out_dir / DERIVE_FILE).exists()):
        raise Refused(f"{args.out_dir.as_posix()} already holds a derivation; not overwritten")
    if args.measure_only and not args.approximate:
        raise Refused("--measure-only records an approximate derivation's error; an exact "
                      "derivation's check is written with its rows")
    if args.measure_only and args.check_source is not None:
        raise Refused("--measure-only measures the sources' own cells against the check; "
                      "--check-source would measure another build's")
    if args.approximate and args.max_cell_error is None and not args.measure_only:
        raise Refused("--approximate needs --max-cell-error: an approximate derivation is written "
                      "only under a bound stated on the command line")
    if args.max_cell_error is not None and not args.approximate:
        raise Refused("--max-cell-error bounds an approximate derivation and --approximate is not "
                      "given; an exact derivation is checked to --tolerance")
    bound: float | None = None
    if args.approximate:
        bound = args.max_cell_error if args.max_cell_error is not None else float("inf")
    refuse_above = not args.measure_only
    scores, reference, provenance = derive(args.sources, args.model, args.to_temperature, package,
                                           approximate=args.approximate)
    through: dict | None = None
    devices: dict | None = None
    if args.check_source is None:
        if bound is not None:
            devices = {"sources": {s["directory"]: device_of(Path(s["directory"]))
                                   for s in provenance["sources"]},
                       "check": device_of(args.check)}
            require_one_device(devices)
        verified = check((scores, reference), args.check, args.model, args.to_temperature, package,
                         provenance["library"][package], provenance["checkpoints"], args.tolerance,
                         bound=bound, refuse_above=refuse_above)
    else:
        through = check_through((scores, reference), provenance, args.check_source, args.check,
                                args.model, args.to_temperature, package, args.tolerance,
                                bound=bound, refuse_above=refuse_above)
        verified = through["check"]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    if args.measure_only:
        provenance["measure_only"] = True
    else:
        scores.to_parquet(args.out_dir / SCORES_FILE, index=False)
        reference.to_parquet(args.out_dir / REFERENCE_FILE, index=False)
    if devices is not None:
        provenance["devices"] = devices
    if through is not None:
        provenance["check_source"] = through["check_source"]
        provenance["devices"] = through["devices"]
        provenance["derived_build"] = verified["derived_build"]
        provenance["checked_build"] = verified["checked_build"]
    provenance["check"] = verified
    provenance["scored_rows"] = len(scores)
    provenance["reference_rows"] = len(reference)
    (args.out_dir / DERIVE_FILE).write_text(json.dumps(provenance, indent=2) + "\n",
                                            encoding="utf-8")

    target = provenance["derived_as"]
    print(f"{'measured' if args.measure_only else 'derived'} {target} at "
          f"{args.to_temperature:g} from "
          f"{', '.join(s['directory'] for s in provenance['sources'])}")
    print(f"library               : {package} {provenance['library'][package]}")
    for source in provenance["sources"]:
        print(f"  {source['directory']}: seeds {source['context_seeds']}, "
              f"from {sorted(set(source['from_temperature'].values()))}, "
              f"{source['scored_rows']:,} scored + {source['reference_rows']:,} reference rows")
    if through is not None:
        source = through["check_source"]
        print(f"check source          : {source['directory']} (build "
              f"{', '.join(source['build_id'])}, seeds {source['context_seeds']}, "
              f"{source['device']})")
    print(f"check                 : {verified['directory']}")
    for cell in verified["cells"]:
        line = (f"  {cell_name(cell):<30} {cell['rows']:>7,} rows  "
                f"max |d pd| {cell['max_abs_pd_gap']:.2e}  max |d logit| {cell['max_abs_logit_gap']:.2e}")
        if bound is not None:
            line += f"  |b - 1| {cell['logit_slope_gap']:.2e}"
        print(line)
    if bound is None:
        within = f"worst |d pd| {verified['max_abs_pd_gap']:.2e} within {args.tolerance:g}"
    else:
        if not np.isfinite(bound):
            limit = "no bound given"
        elif refuse_above:
            limit = f"within {bound:g}"
        else:
            limit = f"{len(verified['cells_above_bound'])} above {bound:g}, not refused"
        within = (f"worst |b - 1| {verified['worst_cell_error']:.2e}, mean "
                  f"{verified['mean_cell_error']:.2e}, {verified['cells_above_lending_club_figure']} "
                  f"of {len(verified['cells'])} cells above the Lending Club figure "
                  f"{LENDING_CLUB_FIGURE:g}, {limit}, approximate")

        def number(value):
            return "n/a" if value is None else f"{value:+.2e}"

        cox, level = verified["cox_slope_gap"], verified["oe_gap"]
        print(f"derived - scored      : Cox slope worst {number(cox['worst'])}, mean "
              f"{number(cox['mean'])}; O/E worst {number(level['worst'])}, mean "
              f"{number(level['mean'])}; {len(verified['cox_fit_failed_cells'])} cells with a "
              "Cox fit that did not finish")
    if through is not None:
        source = through["check_source"]
        print(f"rows checked          : {verified['rows_checked']:,} of the check source's "
              f"{source['scored_rows'] + source['reference_rows']:,}, on build "
              f"{', '.join(verified['checked_build'])}, {within}")
        carried = ("the identity of" if bound is None
                   else "the error measured on the check source under")
        print(f"derived rows checked  : none by row; {len(verified['unchecked_cells'])} cells of "
              f"build {', '.join(verified['derived_build'])} carried by {carried} "
              f"{package} {provenance['library'][package]}, the checkpoint and the source "
              f"temperature")
        print(f"written               : {args.out_dir.as_posix()}")
        return 0
    print(f"rows checked          : {verified['rows_checked']:,} of "
          f"{provenance['scored_rows'] + provenance['reference_rows']:,}, {within}")
    if verified["unchecked_cells"]:
        names = ", ".join(cell_name(c) for c in verified["unchecked_cells"])
        print(f"unchecked cells       : {names} (derived under the same library and checkpoint)")
    if args.measure_only:
        print(f"written               : {(args.out_dir / DERIVE_FILE).as_posix()} only; no rows")
    else:
        print(f"written               : {args.out_dir.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
