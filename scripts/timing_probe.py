#!/usr/bin/env python3
"""Measures what a tabular-foundation-model forward pass costs, on this machine.

The compute budget in ADR-0004 rests on arXiv:2512.00888, a paper whose
architecture descriptions are wrong in checkable ways. Its timings are cited
for orders of magnitude and nothing else, and no experiment design may stand on
them. This replaces the estimate with a measurement.

The probe carries no data. Forward-pass cost is set by the shape of the input
rather than its values, so a synthetic frame of the intended shape times the
same work as the real book, and nothing has to be moved to the accelerator to
find out. What this does not capture is preprocessing on real columns, and that
limit is stated wherever these numbers get used.

Every configuration is timed twice. Accelerator forward passes are
nondeterministic, and the determinism gate requires the disagreement to be
recorded rather than averaged away.

On Colab, paste this file into a cell and run it. It detects the kernel and
takes its defaults, because under a kernel `sys.argv` belongs to Jupyter rather
than to us. For anything other than the defaults, call `run` from the next cell:

    run(models="tabpfn", context_sizes="1000,5000,10000")

From a shell, including Colab's `!` escape, the flags work as flags:

    python timing_probe.py --models tabpfn --out probe.json

Both `--context-sizes` and `--test-rows` take a comma-separated list and
are swept against each other, because a context row and a scored row draw
on the same buffer and a sweep over one of them alone cannot say which is
paying.

Locally it takes whatever accelerator is present: CUDA, Apple Metal, or the
CPU. On the CPU path keep the sizes small with --context-sizes 500,1000, which
checks that the script works and measures nothing the study is budgeted on.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from importlib.metadata import PackageNotFoundError, version

import numpy as np


def package(name: str) -> str | None:
    try:
        return version(name)
    except PackageNotFoundError:
        return None


def environment() -> dict:
    """Everything needed to reconstruct what produced these numbers.

    A timing is a claim about a machine and a library stack as much as about a
    model, so the manifest assembled from this run needs all of it.
    """
    info = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "processor": platform.processor() or "unknown",
        "packages": {
            name: package(name)
            for name in ("torch", "tabpfn", "tabicl", "numpy", "scikit-learn")
        },
        "device": "cpu",
        "device_name": None,
        "cuda": None,
    }
    try:
        import torch
    except ImportError:
        return info

    info["cuda"] = torch.version.cuda
    if torch.cuda.is_available():
        info["device"] = "cuda"
        info["device_name"] = torch.cuda.get_device_name(0)
        properties = torch.cuda.get_device_properties(0)
        info["device_memory_gb"] = round(properties.total_memory / 1e9, 2)
    elif getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        # Apple Silicon. The GPU shares one pool with the system, so the figure
        # below is total machine memory and not a budget the model may spend.
        info["device"] = "mps"
        info["device_name"] = f"Apple Silicon GPU ({platform.machine()})"
        try:
            import subprocess
            total = subprocess.run(["sysctl", "-n", "hw.memsize"],
                                   capture_output=True, text=True,
                                   check=False).stdout.strip()
            info["device_memory_gb"] = round(int(total) / 1e9, 2)
            info["memory_is_unified"] = True
        except Exception:  # noqa: BLE001
            info["device_memory_gb"] = None
    return info


def synthetic(rows: int, features: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    """A frame shaped like a credit book, with a signal weak enough to be real.

    The values do not affect timing, but a degenerate target can make a model
    take a shortcut, so the target is a noisy linear function of a few columns
    at a base rate near what a consumer book shows.
    """
    rng = np.random.default_rng(seed)
    x = rng.standard_normal((rows, features)).astype(np.float32)
    weights = rng.standard_normal(features) / np.sqrt(features)
    logit = x @ weights + rng.standard_normal(rows) * 0.5 - 1.9
    y = (rng.random(rows) < 1 / (1 + np.exp(-logit))).astype(np.int64)
    return x, y


def peak_memory_gb() -> float | None:
    """Peak allocation, on whichever accelerator is present.

    Metal reports what is currently allocated rather than a high-water mark, so
    the MPS figure is a reading taken after the pass rather than a true peak. It
    understates, and it is not comparable with a CUDA number.
    """
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


def time_once(model, x_train, y_train, x_test) -> float:
    reset_memory()
    synchronise()
    start = time.perf_counter()
    model.fit(x_train, y_train)
    model.predict_proba(x_test)
    synchronise()
    return time.perf_counter() - start


def load_colab_secret(name: str) -> bool:
    """Copies a Colab secret into the environment, if it is not already there.

    TabPFN reads its licence token from TABPFN_TOKEN. Setting that with an
    assignment in a cell writes the token into the notebook, where it survives
    saving and sharing. Colab's secret store keeps it against the account
    instead, so the token is fetched from there and never appears in the file.

    Returns whether the variable is set afterwards. Absent Colab, absent
    permission for this notebook, or an absent secret all mean the same thing to
    the caller: use whatever the environment already had.
    """
    import os

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


def build(name: str, device: str):
    if name == "tabpfn":
        load_colab_secret("TABPFN_TOKEN")
        from tabpfn import TabPFNClassifier
        return TabPFNClassifier(device=device)
    if name == "tabicl":
        from tabicl import TabICLClassifier
        return TabICLClassifier(device=device)
    raise ValueError(f"unknown model {name!r}")


def warm_up(name: str, device: str, features: int, seed: int) -> str:
    """One discarded pass, so the first measured one is not the slowest.

    A cold first call pays for weight download, CUDA context creation and
    kernel autotuning, and charges all of it to whichever configuration happens
    to run first. In the run of 2026-08-30 that inflated the smallest context to
    a 19.75% spread and a 13.7 GB peak while every later row sat under 0.7% and
    9.5 GB. Discarding a small pass first costs seconds and removes the
    artefact.
    """
    try:
        x, y = synthetic(256, features, seed)
        model = build(name, device)
        model.fit(x, y)
        model.predict_proba(x[:64])
        synchronise()
        return "ok"
    except Exception as error:  # noqa: BLE001 - reported, not raised
        return f"{type(error).__name__}: {error}"[:2000]


def probe(models, context_sizes, test_sizes, features, seed, repeats,
          out: str | None = None) -> list[dict]:
    """Sweeps the configurations, writing the file after every one of them.

    The climb toward the ceiling ends by design in a failure, and on 2026-08-30
    that failure killed the Colab kernel outright rather than raising anything
    catchable. Results written only at the end die with it. Every row is
    therefore flushed to disk as soon as it exists, so a killed kernel costs
    the row being measured and nothing before it.

    Both the context and the scoring batch are swept, because on 2026-08-30 the
    T4 measurements showed a context row and a scored row costing the same 73 KB
    in one shared attention buffer. A sweep that varies only the context cannot
    separate what each of them costs, and every timing taken so far scored 5,000
    rows where a real cohort runs past 100,000.
    """
    env = environment()
    device = env["device"]
    results = []
    # Ascending, because the stopping rule below reads a failure at the smallest
    # batch as a failure of the context rather than of the batch.
    test_sizes = sorted(test_sizes)

    def flush() -> None:
        if out is None:
            return
        with open(out, "w", encoding="utf-8") as handle:
            json.dump({"environment": env, "results": results}, handle, indent=2)

    scored = {rows: synthetic(rows, features, seed + 1000)[0] for rows in test_sizes}

    for name in models:
        status = warm_up(name, device, features, seed)
        print(json.dumps({"model": name, "warm_up": status}), flush=True)

        for context in context_sizes:
            x_train, y_train = synthetic(context, features, seed)
            context_itself_failed = False

            for test in test_sizes:
                record = {
                    "model": name,
                    "context_rows": context,
                    "test_rows": test,
                    "features": features,
                    "seconds": [],
                    "peak_gpu_gb": None,
                    "status": "ok",
                }
                try:
                    for _ in range(repeats):
                        model = build(name, device)
                        record["seconds"].append(round(time_once(
                            model, x_train, y_train, scored[test]), 3))
                    record["peak_gpu_gb"] = peak_memory_gb()
                except Exception as error:  # noqa: BLE001 - the failure is the datum
                    # An out-of-memory at some size is a result, not a bug: it is
                    # exactly the ceiling the study has to design around.
                    # Kept long: a library's failure message is often the only
                    # instruction for fixing it, and truncating it throws that away.
                    record["status"] = f"{type(error).__name__}: {error}"[:2000]
                    reset_memory()

                if len(record["seconds"]) > 1:
                    low, high = min(record["seconds"]), max(record["seconds"])
                    record["spread_seconds"] = round(high - low, 3)
                    record["spread_fraction"] = (
                        round((high - low) / high, 4) if high else 0.0)

                results.append(record)
                flush()
                print(json.dumps(record), flush=True)

                if record["status"] != "ok":
                    # Bigger batches at this context fail the same way, so stop
                    # widening the batch. Whether to stop climbing the context
                    # depends on which batch died: the two share one row budget,
                    # so a context that fails even at the narrowest batch has
                    # nothing left to give, while one that failed only at a wide
                    # batch may still hold a larger context scored in chunks.
                    context_itself_failed = test == test_sizes[0]
                    print(f"  {name}: {context} rows of context failed at "
                          f"{test} scored", flush=True)
                    break

            if context_itself_failed:
                print(f"  {name}: stopping the context climb at {context} rows",
                      flush=True)
                break
    return results


def caption(device: str) -> str:
    """What the run about to be taken is, so its numbers are not miscaptioned.

    An earlier version tested `device != "cuda"` and so told an Apple machine
    it was timing the CPU path while the model sat on Metal. A caption that
    misdescribes the run is worse than none, because it is what gets pasted
    beside the numbers.
    """
    if device == "cuda":
        return "Timing on CUDA."
    if device == "mps":
        return ("Timing on Apple Metal. These are accelerator timings. The "
                "memory reading is the driver's allocated pool rather than a "
                "high-water mark, so it is not comparable with a CUDA figure.")
    return ("No accelerator. These timings measure the CPU path and are not "
            "the numbers the study is budgeted against.")


def in_notebook() -> bool:
    """True when this module is executing inside an IPython kernel.

    A notebook sets `__name__` to "__main__" exactly as a script does, so the
    entry point below fires when the file is pasted into a cell. What differs is
    `sys.argv`, which belongs to the kernel and carries its own `-f
    kernel-....json`. Parsing that as our arguments aborts the process before a
    single timing is taken, and that is how this probe first failed on Colab.
    """
    try:
        get_ipython  # type: ignore[name-defined]  # noqa: B018
    except NameError:
        try:
            from IPython import get_ipython as _get
        except ImportError:
            return False
        return _get() is not None
    return True


def run(**overrides):
    """Entry point for a notebook cell, where there is no command line.

    Call with the same names the flags use, in their underscore form:

        run(models="tabpfn", context_sizes="1000,5000,10000")
    """
    argv = []
    for key, value in overrides.items():
        argv += [f"--{key.replace('_', '-')}", str(value)]
    return main(argv)


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        # Under a kernel, sys.argv is the kernel's and must not be parsed.
        argv = [] if in_notebook() else sys.argv[1:]

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--models", default="tabpfn",
                        help="comma-separated: tabpfn,tabicl")
    parser.add_argument("--context-sizes", default="1000,5000,10000,20000,50000",
                        help="training-context row counts to sweep")
    parser.add_argument("--test-rows", default="20000",
                        help="comma-separated scoring batch sizes to sweep")
    parser.add_argument("--features", type=int, default=30,
                        help="feature count after selection")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--repeats", type=int, default=2,
                        help="times each configuration is run (minimum 2)")
    parser.add_argument("--out", default="probe.json")
    args = parser.parse_args(argv)

    env = environment()
    print(json.dumps(env, indent=2), flush=True)
    print("", caption(env["device"]), "", sep=chr(10), flush=True)

    results = probe(
        models=[m.strip() for m in args.models.split(",") if m.strip()],
        context_sizes=[int(s) for s in args.context_sizes.split(",")],
        test_sizes=[int(s) for s in args.test_rows.split(",")],
        features=args.features,
        seed=args.seed,
        repeats=max(2, args.repeats),
        out=args.out,
    )
    print(f"\nwrote {args.out}")

    print("\nmodel     context    test   median s   spread   peak GB   status")
    for r in results:
        seconds = r["seconds"]
        median = f"{sorted(seconds)[len(seconds) // 2]:8.2f}" if seconds else "       -"
        spread = f"{r.get('spread_fraction', 0):6.1%}" if seconds else "     -"
        peak = f"{r['peak_gpu_gb']:7.2f}" if r["peak_gpu_gb"] else "      -"
        status = "ok" if r["status"] == "ok" else r["status"][:40]
        print(f"{r['model']:<9} {r['context_rows']:>7} {r['test_rows']:>7} "
              f"{median} {spread} {peak}   {status}")
    return 0


if __name__ == "__main__":
    # No sys.exit() under a kernel: it raises SystemExit and shows a traceback
    # in the cell even when the run succeeded.
    if in_notebook():
        main()
    else:
        sys.exit(main())
