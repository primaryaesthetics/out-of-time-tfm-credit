#!/usr/bin/env bash
# Runs the scoring jobs of an archive on an Apple Silicon node, and packs the
# result for the trip back.
#
#   tar xzf outoftime-run-<name>.tar.gz
#   cd outoftime-run-<name>
#   bash run.sh
#
# The archive carries this file, the scorer, the bundles to score, the runner
# that walks the job list, and jobs.json, which names every job in order. If
# the node directory (~/outoftime-node) is not there yet, the bootstrap that
# travels in the same archive builds it first; on a machine that has run
# before, nothing is installed and nothing is downloaded. A second start
# continues: finished jobs are skipped by their tally, and the job in flight
# continues from the cells already scored. When the last job finishes, every
# scored directory, the tally and the log are packed into one file on the
# Desktop, and the last lines say where.
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
DRY="${OUTOFTIME_DRY:-}"

say() { printf '\n\033[1m%s\033[0m\n' "$1"; }
fail() { printf '\n\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

# jobs.json names the archive, the bundles and every job. Written by
# pack_node_run.py; read here through the runner, which is the one parser of
# it, so that what the shell copies is what the runner will score.
for name in jobs.json node_jobs.py score_context.py; do
    [ -f "$OUTOFTIME_SRC/$name" ] || fail "$name is missing next to run.sh; the archive is incomplete."
done
PYTHON="${OUTOFTIME_PYTHON:-python3}"
command -v "$PYTHON" >/dev/null 2>&1 || fail "No $PYTHON on this machine; the runner needs one."
CLEAN="$(mktemp -d)"
JOBS_PY="$CLEAN/node_jobs.py"
tr -d '\r' < "$OUTOFTIME_SRC/node_jobs.py" > "$JOBS_PY"
JOBS_JSON="$CLEAN/jobs.json"
tr -d '\r' < "$OUTOFTIME_SRC/jobs.json" > "$JOBS_JSON"
# The carriage returns are stripped again here: a Python on Windows, where the
# dry run of this file is tested, ends every printed line with one.
NAME="$("$PYTHON" -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$JOBS_JSON" | tr -d '\r')"
BUNDLES="$("$PYTHON" "$JOBS_PY" "$JOBS_JSON" --list bundles | tr -d '\r')"
OUTPUTS="$("$PYTHON" "$JOBS_PY" "$JOBS_JSON" --list outputs | tr -d '\r')"
[ -n "$NAME" ] || fail "jobs.json names no archive."
[ -n "$BUNDLES" ] || fail "jobs.json names no bundle."
for bundle in $BUNDLES; do
    [ -d "$OUTOFTIME_SRC/$bundle" ] || fail "The bundle directory $bundle is not in the archive."
done

say "The job"
echo "  archive  : $NAME"
echo "  bundles  : $(echo "$BUNDLES" | wc -l | tr -dc '0-9')"
echo "  node     : $NODE_DIR"
echo "  result   : $HOME/Desktop/outoftime-result-$NAME.tar.gz"
"$PYTHON" "$JOBS_PY" "$JOBS_JSON" --dry-run --command ./run-score.sh | sed 's/^/  /'

if [ -n "$DRY" ]; then
    say "Dry run: nothing is copied, installed or scored."
    exit 0
fi

[ "$(uname -s)" = "Darwin" ] || fail "This runner is for macOS. Found $(uname -s)."

# A machine that has never run needs the environment first. The bootstrap
# travels in the archive for that case and is not touched otherwise.
if [ ! -x "$NODE_DIR/run-score.sh" ]; then
    say "No node directory yet; building it"
    [ -f "$OUTOFTIME_SRC/bootstrap_macnode.sh" ] || fail \
"$NODE_DIR does not exist and bootstrap_macnode.sh is not in the archive."
    ( cd "$OUTOFTIME_SRC" && OUTOFTIME_NODE_DIR="$NODE_DIR" bash bootstrap_macnode.sh )
    [ -x "$NODE_DIR/run-score.sh" ] || fail "The bootstrap did not produce $NODE_DIR/run-score.sh."
fi

say "Placing the scorer, the runner and the bundles in $NODE_DIR"
tr -d '\r' < "$OUTOFTIME_SRC/score_context.py" > "$NODE_DIR/score_context.py"
echo "  score_context.py copied in"
cp "$JOBS_PY" "$NODE_DIR/node_jobs.py"
echo "  node_jobs.py copied in"
if [ -f "$NODE_DIR/jobs.json" ] && ! cmp -s "$JOBS_JSON" "$NODE_DIR/jobs.json"; then
    echo "  a different jobs.json is already there; its tally is kept under jobs-done.json"
fi
cp "$JOBS_JSON" "$NODE_DIR/jobs.json"
echo "  jobs.json copied in"
for bundle in $BUNDLES; do
    if [ -d "$NODE_DIR/$bundle" ]; then
        echo "  $bundle is already there; kept, the scorer checks its hashes"
    else
        cp -R "$OUTOFTIME_SRC/$bundle" "$NODE_DIR/$bundle"
        echo "  $bundle copied in"
    fi
done

say "Scoring"
echo "  Started $(date '+%Y-%m-%d %H:%M'). The laptop is kept awake while this runs."
echo "  Interrupting with Ctrl-C is safe: a second start skips the finished jobs and"
echo "  continues the one in flight from the cells already scored."
STARTED=$(date +%s)
# run-score.sh wraps the scorer in the node's environment and appends its
# console to score.log; the runner walks the list through it.
( cd "$NODE_DIR" && caffeinate -i "$NODE_DIR/.venv/bin/python" node_jobs.py jobs.json --command ./run-score.sh )
ELAPSED=$(( $(date +%s) - STARTED ))

say "Packing the result"
RESULT="$HOME/Desktop/outoftime-result-$NAME.tar.gz"
# shellcheck disable=SC2086
( cd "$NODE_DIR" && tar czf "$RESULT" $OUTPUTS jobs.json jobs-done.json score.log )
echo "  $RESULT"
echo "  $(du -h "$RESULT" | cut -f1) — $ELAPSED s of scoring"

say "Done"
cat <<EOF
  Send this one file back:

    $RESULT

  Nothing else on this machine was written to. Everything the study put here
  lives in $NODE_DIR and is removed with:

    rm -rf $NODE_DIR
EOF
