#!/usr/bin/env bash
# Runs the scoring jobs of an archive on a Linux machine with an NVIDIA GPU,
# and packs the result for the trip back.
#
#   tar xzf outoftime-run-<name>.tar.gz
#   cd outoftime-run-<name>
#   tmux new -s outoftime        # or screen; see below
#   bash run.sh
#
# The machine is usually rented and reached over SSH, and a dropped
# connection takes a foreground process with it. Inside tmux or screen the
# jobs outlive the connection; `tmux attach -t outoftime` returns to them.
# A second start continues in any case: finished jobs are skipped by their
# tally, and the job in flight continues from the cells already scored.
#
# The archive carries this file, the scorer, the bundles to score, the runner
# that walks the job list, and jobs.json. On the first start the environment
# is built inside one directory (~/outoftime-node): uv, Python 3.12, torch
# with CUDA, and the two model packages at the versions every earlier node
# ran. Nothing is installed system-wide and no shell profile is touched; the
# caches the libraries would put in the home directory are sent there too.
#
# TabPFN downloads its checkpoint behind a licence check. A copy of the
# checkpoint placed beside this file, tabpfn-v3-classifier-v3_default.ckpt,
# is hashed against the one every earlier node ran and copied into the cache,
# and then no token and no licence server are involved. Without it the jobs
# that name TabPFN need TABPFN_TOKEN in the environment, and the runner
# refuses to start rather than let the library prompt for the key, because a
# key typed at that prompt lands in the log.
#
# When the last job finishes, or one fails, every scored directory, the
# tally, the log and the GPU's description are packed into one file in the
# home directory, and the last lines say where.
#
# The three statements below run before `set` on purpose and carry a trailing
# comment on purpose: a copy of this file that travelled through a Windows
# working tree arrives with CRLF endings, and bash would read the carriage
# return as part of the last word of every line. See bootstrap_macnode.sh.
OUTOFTIME_SRC="${OUTOFTIME_SRC:-$(cd -- "$(dirname -- "$0")" && pwd)}" # resolved while $0 is a real path, first pass only
export OUTOFTIME_SRC # so the repaired copy still knows where the archive was unpacked
OUTOFTIME_CR="${OUTOFTIME_LF:-$(tr -dc '\r' < "$0" | wc -c | tr -dc '0-9')}" # counted in bytes, first pass only
test -z "${OUTOFTIME_LF:-}" && test "$OUTOFTIME_CR" != 0 && export OUTOFTIME_LF=1 && exec bash <(tr -d '\r' < "$0") "$@" # repair once, then run
set -euo pipefail

NODE_DIR="${OUTOFTIME_NODE_DIR:-$HOME/outoftime-node}"
RESULT_DIR="${OUTOFTIME_RESULT_DIR:-$HOME}"
DRY="${OUTOFTIME_DRY:-}"

# The checkpoint the M4 and T4 runs recorded in their node.json.
TABPFN_CKPT="tabpfn-v3-classifier-v3_default.ckpt"
TABPFN_CKPT_SHA256="d0d865d54dfbc524f5703104be90620182dca7e5fb2c16de72e9959ea18f3988"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

for name in jobs.json node_jobs.py score_context.py; do
    [ -f "$OUTOFTIME_SRC/$name" ] || fail "$name is missing next to run.sh; the archive is incomplete."
done
PYTHON="${OUTOFTIME_PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || fail "No $PYTHON on this machine; the runner needs one to read jobs.json."
CLEAN="$(mktemp -d)"
JOBS_PY="$CLEAN/node_jobs.py"
tr -d '\r' < "$OUTOFTIME_SRC/node_jobs.py" > "$JOBS_PY"
JOBS_JSON="$CLEAN/jobs.json"
tr -d '\r' < "$OUTOFTIME_SRC/jobs.json" > "$JOBS_JSON"
NAME="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$JOBS_JSON" | tr -d '\r')"
BUNDLES="$("$PYTHON" "$JOBS_PY" "$JOBS_JSON" --list bundles | tr -d '\r')"
OUTPUTS="$("$PYTHON" "$JOBS_PY" "$JOBS_JSON" --list outputs | tr -d '\r')"
[ -n "$NAME" ] || fail "jobs.json names no archive."
[ -n "$BUNDLES" ] || fail "jobs.json names no bundle."
for bundle in $BUNDLES; do
    [ -d "$OUTOFTIME_SRC/$bundle" ] || fail "The bundle directory $bundle is not in the archive."
done
RESULT="$RESULT_DIR/outoftime-result-$NAME.tar.gz"

say "The job"
echo "  archive  : $NAME"
echo "  bundles  : $(echo "$BUNDLES" | wc -l | tr -dc '0-9')"
echo "  node     : $NODE_DIR"
echo "  result   : $RESULT"
"$PYTHON" "$JOBS_PY" "$JOBS_JSON" --dry-run --command "python score_context.py" | sed 's/^/  /'

if [ -n "$DRY" ]; then
    say "Dry run: nothing is copied, installed or scored."
    exit 0
fi

say "Checking the machine"
[ "$(uname -s)" = "Linux" ] || fail "This runner is for Linux with an NVIDIA GPU. Found $(uname -s)."
command -v nvidia-smi >/dev/null 2>&1 || fail \
"No nvidia-smi on this machine, so no NVIDIA driver. Rent an instance with a GPU and its driver."
GPU="$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader)"
echo "  gpu      : $GPU"
echo "  cpus     : $(nproc)"
echo "  disk     : $(df -h "$HOME" | awk 'NR==2 {print $4}') free in $HOME"
if [ -z "${TMUX:-}${STY:-}" ]; then
    echo "  note     : not inside tmux or screen; a dropped SSH connection stops the jobs."
    echo "             A second start continues where they stopped."
fi

mkdir -p "$NODE_DIR"
echo "$GPU" > "$NODE_DIR/gpu.txt"

# Everything below writes into the node directory instead of the home
# directory, so that deleting one directory removes everything.
export UV_PYTHON_INSTALL_DIR="$NODE_DIR/uv-python"
export UV_CACHE_DIR="$NODE_DIR/cache/uv"
export HF_HOME="$NODE_DIR/cache/huggingface"
export XDG_CACHE_HOME="$NODE_DIR/cache"
export XDG_CONFIG_HOME="$NODE_DIR/config"
export TABPFN_MODEL_CACHE_DIR="$NODE_DIR/cache/tabpfn"
mkdir -p "$UV_CACHE_DIR" "$HF_HOME" "$XDG_CONFIG_HOME" "$TABPFN_MODEL_CACHE_DIR"

if grep -q '"tabpfn' "$JOBS_JSON"; then
    if [ -f "$OUTOFTIME_SRC/$TABPFN_CKPT" ]; then
        ACTUAL="$(sha256sum "$OUTOFTIME_SRC/$TABPFN_CKPT" | cut -d' ' -f1)"
        [ "$ACTUAL" = "$TABPFN_CKPT_SHA256" ] || fail \
"$TABPFN_CKPT beside run.sh hashes to $ACTUAL,
not to the checkpoint every earlier node ran ($TABPFN_CKPT_SHA256).
A truncated upload is the usual cause; send the file again."
        cp "$OUTOFTIME_SRC/$TABPFN_CKPT" "$TABPFN_MODEL_CACHE_DIR/$TABPFN_CKPT"
        echo "  $TABPFN_CKPT checked and copied in; no licence token is needed"
    elif [ -f "$TABPFN_MODEL_CACHE_DIR/$TABPFN_CKPT" ]; then
        echo "  $TABPFN_CKPT is already in the node's cache"
    elif [ -n "${TABPFN_TOKEN:-}" ]; then
        echo "  no checkpoint sent; TabPFN downloads it with the token in TABPFN_TOKEN"
    else
        fail "The jobs name TabPFN, and there is neither $TABPFN_CKPT beside run.sh
nor TABPFN_TOKEN in the environment. Upload the checkpoint next to run.sh
and start again."
    fi
fi

if [ ! -x "$NODE_DIR/.venv/bin/python" ]; then
    say "Building the environment in $NODE_DIR"
    if command -v uv >/dev/null 2>&1; then
        UV=uv
    elif [ -x "$NODE_DIR/bin/uv" ]; then
        UV="$NODE_DIR/bin/uv"
    else
        export UV_INSTALL_DIR="$NODE_DIR/bin"
        export UV_NO_MODIFY_PATH=1
        curl -LsSf https://astral.sh/uv/install.sh | sh
        UV="$NODE_DIR/bin/uv"
    fi
    "$UV" venv --python 3.12 "$NODE_DIR/.venv"
    # The default Linux wheel of torch carries CUDA. A machine whose driver is
    # older than that wheel's CUDA takes a wheel from the index named here,
    # e.g. https://download.pytorch.org/whl/cu126.
    if [ -n "${OUTOFTIME_TORCH_INDEX:-}" ]; then
        "$UV" pip install --python "$NODE_DIR/.venv" torch --index-url "$OUTOFTIME_TORCH_INDEX"
    fi
    # Pinned to the versions of every earlier node, so that a difference between
    # machines is a difference between machines and not between releases.
    "$UV" pip install --python "$NODE_DIR/.venv" \
        torch numpy pandas pyarrow scikit-learn tabpfn==8.5.0 tabicl==2.1.1
fi

say "Checking that torch sees the GPU"
"$NODE_DIR/.venv/bin/python" - <<'PY' || fail "torch does not see the GPU. If the driver is older than the wheel's CUDA, delete ~/outoftime-node/.venv and start again with OUTOFTIME_TORCH_INDEX set."
import sys

import torch

print(f"  torch    : {torch.__version__} (CUDA {torch.version.cuda})")
if not torch.cuda.is_available():
    sys.exit(1)
x = torch.randn(4096, 4096, device="cuda")
torch.cuda.synchronize()
print(f"  device   : {torch.cuda.get_device_name(0)}, a matmul gives {(x @ x).sum().item():.1f}")
PY

say "Placing the scorer, the runner and the bundles in $NODE_DIR"
tr -d '\r' < "$OUTOFTIME_SRC/score_context.py" > "$NODE_DIR/score_context.py"
cp "$JOBS_PY" "$NODE_DIR/node_jobs.py"
if [ -f "$NODE_DIR/jobs.json" ] && ! cmp -s "$JOBS_JSON" "$NODE_DIR/jobs.json"; then
    echo "  a different jobs.json is already there; its tally is kept under jobs-done.json"
fi
cp "$JOBS_JSON" "$NODE_DIR/jobs.json"
for bundle in $BUNDLES; do
    if [ -d "$NODE_DIR/$bundle" ]; then
        echo "  $bundle is already there; kept, the scorer checks its hashes"
    else
        cp -R "$OUTOFTIME_SRC/$bundle" "$NODE_DIR/$bundle"
        echo "  $bundle copied in"
    fi
done

say "Scoring"
echo "  Started $(date '+%Y-%m-%d %H:%M %Z')."
STARTED=$(date +%s)
set +e
( cd "$NODE_DIR" && "$NODE_DIR/.venv/bin/python" node_jobs.py jobs.json \
      --command "$NODE_DIR/.venv/bin/python score_context.py" --log "$NODE_DIR/score.log" )
CODE=$?
set -e
ELAPSED=$(( $(date +%s) - STARTED ))

say "Packing the result"
PACKED="jobs.json gpu.txt"
for name in jobs-done.json score.log $OUTPUTS; do
    [ -e "$NODE_DIR/$name" ] && PACKED="$PACKED $name"
done
# shellcheck disable=SC2086
( cd "$NODE_DIR" && tar czf "$RESULT" $PACKED )
echo "  $RESULT"
echo "  $(du -h "$RESULT" | cut -f1), sha256 $(sha256sum "$RESULT" | cut -d' ' -f1)"
echo "  $ELAPSED s of scoring"

if [ "$CODE" != 0 ]; then
    fail "A job failed (exit $CODE); the result holds everything scored up to it and the log.
Send it back as it is. Starting run.sh again continues from the same place."
fi

say "Done"
cat <<EOF
  Send this one file back:

    $RESULT

  Everything the study put on this machine lives in $NODE_DIR and is
  removed with:

    rm -rf $NODE_DIR

  On a rented machine, download the result first, then destroy the instance.
EOF
