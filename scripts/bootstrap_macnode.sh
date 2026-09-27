#!/usr/bin/env bash
# Sets up an Apple Silicon machine as a compute node for this study.
#
# The machine this runs on is not a workstation and does not become one. It
# holds a Python environment, two scripts and whatever small data is sent to
# it, all inside one directory, and it goes away completely when that directory
# is deleted. Nothing is installed system-wide, no shell profile is touched, and
# no repository, credential store or editor configuration is copied across.
#
# The reason to want it: TabPFN needed 0.67 GB on a T4 at a 10,000-row context
# and about 1.6 GB extrapolated at 100,000, so a 16 GB Apple machine has room
# for the whole model comfortably. It is also unmetered and can work overnight,
# which a free hosted notebook cannot.
#
# Send this file and timing_probe.py across together, into one directory. A
# third file, tabpfn-v3-classifier-v3_default.ckpt, is optional but decisive:
# TabPFN verifies its licence token against a server before it downloads that
# checkpoint, and only then, so a machine that already has the file needs no
# token and never opens a connection to the licence server. Then:
#
#   bash bootstrap_macnode.sh
#
# It must be started with `bash`, because `sh` is a different shell on macOS.
#
# Caches are redirected into the node directory, because the tools involved
# default to the home directory: uv keeps its interpreter in ~/.local/share,
# Hugging Face keeps its downloads in ~/.cache, and TabPFN keeps its
# checkpoints in ~/Library/Caches/tabpfn. To remove every trace:
#
#   rm -rf ~/outoftime-node
#
# A machine bootstrapped before that redirection existed has those paths to
# clear by hand as well, plus ~/.cache/tabpfn/auth_token if a token was ever
# entered: TabPFN writes an accepted token there whatever the environment says.
#
# The three statements below run before `set` on purpose, and they carry a
# trailing comment on purpose. A copy of this file that has travelled through a
# Windows working tree arrives with CRLF line endings, and bash reads the
# carriage return as part of the last word on the line: `set -euo pipefail`
# becomes a request for an option named "pipefail<CR>" and the script dies on
# its first statement, several lines before it could say anything useful. A
# stray carriage return that lands inside a comment is harmless, so each line
# here ends in one, and none of them uses `if`, `case` or `[[`, whose closing
# keyword the same carriage return would hide. The result repairs a damaged
# copy in memory and re-runs it, so the file being wrong costs nothing.
OUTOFTIME_SRC="${OUTOFTIME_SRC:-$(cd -- "$(dirname -- "$0")" && pwd)}" # resolved while $0 is still a real path, and only on the first pass
export OUTOFTIME_SRC # so the repaired copy still knows which directory it came from
OUTOFTIME_CR="${OUTOFTIME_LF:-$(tr -dc '\r' < "$0" | wc -c | tr -dc '0-9')}" # counted with tr, which reads bytes rather than lines, and only on the first pass because the repaired copy arrives on a pipe that must not be read twice
test -z "${OUTOFTIME_LF:-}" && test "$OUTOFTIME_CR" != 0 && export OUTOFTIME_LF=1 && exec bash <(tr -d '\r' < "$0") "$@" # repair once, then run
set -euo pipefail

NODE_DIR="${OUTOFTIME_NODE_DIR:-$HOME/outoftime-node}"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

say "Checking the machine"

[ "$(uname -s)" = "Darwin" ] || fail "This bootstrap is for macOS. Found $(uname -s)."

# Checked here rather than at the end, because building the environment takes
# several minutes and downloads a gigabyte, and none of it is any use without
# the probe the two files were sent across to run.
[ -f "$OUTOFTIME_SRC/timing_probe.py" ] || fail \
"timing_probe.py is not in $OUTOFTIME_SRC, next to this script.
Both files travel together. Send timing_probe.py across and start again."

ARCH="$(uname -m)"
if [ "$ARCH" != "arm64" ]; then
    printf 'Architecture is %s, not arm64. There is no Apple GPU to use here,\n' "$ARCH"
    printf 'so the models would run on the CPU and slowly. Continue anyway? [y/N] '
    read -r reply
    [ "$reply" = "y" ] || exit 1
fi

# Total memory decides how far the context sweep is worth pushing. TabPFN
# peaked at 3.6 GB for a 50,000-row context on Metal, so that size is safe
# from 16 GB up. A 100,000-row context is not offered: on a 24 GB machine it
# failed inside a Metal kernel with an index out of range, with memory to
# spare, and the study never uses a context that large.
MEM_BYTES="$(sysctl -n hw.memsize)"
MEM_GB=$(( MEM_BYTES / 1000000000 ))
echo "  chip     : $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo "Apple Silicon")"
echo "  memory   : ${MEM_GB} GB, shared between CPU and GPU"
echo "  macOS    : $(sw_vers -productVersion)"
if [ "$MEM_GB" -ge 16 ]; then
    SWEEP_CONTEXTS="10000,50000"
else
    SWEEP_CONTEXTS="10000,20000"
    echo "  note     : under 16 GB. TabPFN should fit; TabICL probably will not."
fi

say "Creating $NODE_DIR"
mkdir -p "$NODE_DIR"
cd "$NODE_DIR"

# Copied rather than left to be moved by hand, and stripped of carriage returns
# on the way in for the same reason the guard at the top of this file exists.
tr -d '\r' < "$OUTOFTIME_SRC/timing_probe.py" > "$NODE_DIR/timing_probe.py"
echo "  timing_probe.py copied in from $OUTOFTIME_SRC"

# The scorer travels the same way when it is sent. The probe alone measures
# a machine; the scorer is what the study's runs need, and a bundle from
# export_context.py is what it reads.
if [ -f "$OUTOFTIME_SRC/score_context.py" ]; then
    tr -d '\r' < "$OUTOFTIME_SRC/score_context.py" > "$NODE_DIR/score_context.py"
    echo "  score_context.py copied in from $OUTOFTIME_SRC"
fi

# Everything below writes into the node directory instead of the home directory.
# Without this the toolchain scatters: uv puts its managed interpreter in
# ~/.local/share/uv, Hugging Face puts 213 MB of model weights in ~/.cache, and
# TabPFN writes the accepted licence key into ~/.config, where it outlives the
# study on a machine that is not ours. The promise below is that deleting one
# directory removes everything, and these five variables are what make it true.
export UV_PYTHON_INSTALL_DIR="$NODE_DIR/uv-python"
export HF_HOME="$NODE_DIR/cache/huggingface"
export XDG_CACHE_HOME="$NODE_DIR/cache"
export XDG_CONFIG_HOME="$NODE_DIR/config"
export TABPFN_MODEL_CACHE_DIR="$NODE_DIR/cache/tabpfn"
mkdir -p "$HF_HOME" "$XDG_CACHE_HOME" "$XDG_CONFIG_HOME" "$TABPFN_MODEL_CACHE_DIR"

# TabPFN looks for its checkpoint in that cache directory and downloads it only
# when the file is absent. The licence check happens inside that download and
# nowhere else, so a checkpoint sent across with the scripts removes both the
# token and the licence server from this machine's concerns.
TABPFN_CKPT="tabpfn-v3-classifier-v3_default.ckpt"
if [ -f "$OUTOFTIME_SRC/$TABPFN_CKPT" ]; then
    cp "$OUTOFTIME_SRC/$TABPFN_CKPT" "$TABPFN_MODEL_CACHE_DIR/$TABPFN_CKPT"
    TABPFN_READY=yes
    echo "  $TABPFN_CKPT copied in; no licence token is needed"
else
    TABPFN_READY=no
    echo "  $TABPFN_CKPT was not sent across; TabPFN will need a token and the licence server"
fi

# uv is installed into the node directory rather than onto the machine, so that
# deleting the directory really does remove everything.
if command -v uv >/dev/null 2>&1; then
    echo "  uv already present: $(command -v uv)"
    UV=uv
elif [ -x "$NODE_DIR/bin/uv" ]; then
    UV="$NODE_DIR/bin/uv"
else
    say "Installing uv into the node directory"
    export UV_INSTALL_DIR="$NODE_DIR/bin"
    export UV_NO_MODIFY_PATH=1
    curl -LsSf https://astral.sh/uv/install.sh | sh
    UV="$NODE_DIR/bin/uv"
fi

say "Building the environment"
"$UV" venv --python 3.12 "$NODE_DIR/.venv"
# torch on Apple Silicon ships Metal support in the default wheel; there is no
# separate index to point at, unlike CUDA. The two model packages are pinned to
# the versions the T4 probes recorded, so that timings compare across machines
# and not across releases.
"$UV" pip install --python "$NODE_DIR/.venv" \
    torch numpy pandas pyarrow scikit-learn tabpfn==8.5.0 tabicl==2.1.1

say "Checking that the GPU is visible to torch"
"$NODE_DIR/.venv/bin/python" - <<'PY'
import torch
available = torch.backends.mps.is_available()
built = torch.backends.mps.is_built()
print(f"  torch            : {torch.__version__}")
print(f"  metal built in   : {built}")
print(f"  metal available  : {available}")
if available:
    x = torch.randn(2048, 2048, device="mps")
    torch.mps.synchronize()
    print(f"  a matmul on the GPU: {(x @ x).sum().item():.2f}")
    print("\n  The GPU works. Run the probe next.")
else:
    print("\n  No Metal device. Everything will run on the CPU, which is slower")
    print("  but still produces the same predictions.")
PY

cat > "$NODE_DIR/run-probe.sh" <<EOF
#!/usr/bin/env bash
# Measures what a forward pass costs on this machine.
#
# The licence token is read from the environment:
#   export TABPFN_TOKEN=...
# TabPFN caches an accepted key of its own accord. The config directory below
# sends that cache inside the node directory, so it goes away with everything
# else rather than sitting in the home directory afterwards.
set -euo pipefail
export HF_HOME="$NODE_DIR/cache/huggingface"
export XDG_CACHE_HOME="$NODE_DIR/cache"
export XDG_CONFIG_HOME="$NODE_DIR/config"
export TABPFN_MODEL_CACHE_DIR="$NODE_DIR/cache/tabpfn"
cd "$NODE_DIR"

# Called with no arguments, this runs the sweep this machine was added to the
# study to run: TabPFN over context ascending, then scoring batch ascending,
# so a failure at one size still leaves every smaller one measured. TabICL is
# left out on purpose. On Metal it ran out of a 24 GB machine's memory at a
# 10,000-row context and 5,000 scored rows, the smallest shape probed, where a
# T4 holds five times that context in 11.3 GB, so it stays on CUDA. The
# context sizes were chosen from the ${MEM_GB} GB this machine reported when
# it was bootstrapped. Any argument given is passed to the probe instead.
if [ "\$#" -eq 0 ]; then
    set -- --models tabpfn \\
           --context-sizes $SWEEP_CONTEXTS \\
           --test-rows 5000,20000 \\
           --out probe.json
fi

# Kept as a pipeline rather than exec so that the console output is also on
# disk afterwards; pipefail above means the probe's own exit status survives.
"$NODE_DIR/.venv/bin/python" timing_probe.py "\$@" 2>&1 | tee -a "$NODE_DIR/probe.log"
EOF
chmod +x "$NODE_DIR/run-probe.sh"

cat > "$NODE_DIR/run-score.sh" <<EOF
#!/usr/bin/env bash
# Scores a bundle from export_context.py with a foundation model.
#
#   ./run-score.sh <bundle-dir> [--nearest 3] [--seeds 20260911] [--models tabpfn]
#
# The bundle directory holds context.parquet, scored.parquet and bundle.json.
# Scores go to <bundle-dir>-scored beside it, one part per cell as each is
# finished, and a second start continues from the parts already there. The
# model defaults to TabPFN, the one that runs on Metal; any option given
# after the bundle is passed to the scorer and a later --models wins.
set -euo pipefail
export HF_HOME="$NODE_DIR/cache/huggingface"
export XDG_CACHE_HOME="$NODE_DIR/cache"
export XDG_CONFIG_HOME="$NODE_DIR/config"
export TABPFN_MODEL_CACHE_DIR="$NODE_DIR/cache/tabpfn"
cd "$NODE_DIR"
if [ "\$#" -lt 1 ]; then
    echo "usage: ./run-score.sh <bundle-dir> [options for score_context.py]" >&2
    exit 2
fi
BUNDLE="\${1%/}"
shift
"$NODE_DIR/.venv/bin/python" score_context.py "\$BUNDLE" --out-dir "\$BUNDLE-scored" \\
    --models tabpfn "\$@" 2>&1 | tee -a "$NODE_DIR/score.log"
EOF
chmod +x "$NODE_DIR/run-score.sh"

if [ "$TABPFN_READY" = yes ]; then
    TOKEN_LINE=""
    TOKEN_NOTE="  The checkpoint is in place, so no token is needed and nothing is verified
  over the network."
else
    TOKEN_LINE="    export TABPFN_TOKEN=
"
    TOKEN_NOTE="  The token arrives separately; paste it after the =. It is checked against
  a licence server that is not reachable from every network. If that check
  times out, the way past it is the checkpoint named at the top of this
  script, placed next to the scripts before bootstrapping again."
fi

say "Done"
cat <<EOF
  Everything lives in $NODE_DIR, caches included, and no shell profile or
  system location was written to.
  Remove it all with:  rm -rf $NODE_DIR

  Commands remaining:

    cd $NODE_DIR
${TOKEN_LINE}    ./run-probe.sh
    ./run-score.sh <bundle-dir> --nearest 3 --seeds 20260911   # once a bundle is sent

$TOKEN_NOTE

  The sweep this machine will run, chosen from its ${MEM_GB} GB:
  TabPFN over contexts $SWEEP_CONTEXTS, scoring batches 5000 and 20000.
  Every row is written as it is measured, so interrupting with Ctrl-C is safe
  and keeps everything measured up to that point.

  Send back probe.json and probe.log from $NODE_DIR. They decide whether this
  machine can carry TabICL, which is what decides whether any GPU has to be
  rented at all.
EOF
