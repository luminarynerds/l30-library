#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Chunked pytest runner for the deploy-backend.sh gate. A single
# whole-suite pytest invocation was confirmed (2026-07-09 re-baseline) to
# wedge the host indefinitely on certain hang-prone tests; chunking bounds
# any single hang to CHUNK_TIMEOUT seconds instead of the whole gate.
# Must be run with cwd already at <tree>/backend and DATABASE_URL/REDIS_URL/
# PYTHONPATH/PII_ENCRYPTION_ENABLED already exported by the caller.
set -eu

CHUNK_SIZE=5
CHUNK_TIMEOUT=${CHUNK_TIMEOUT:-1800}
# Files heavy enough (many parametrized DB+Redis+bcrypt cases) to blow the
# per-chunk timeout even alone if bundled with CHUNK_SIZE-1 other files --
# confirmed 2026-07-09 (test_off_button_matrix.py alone took ~617s). Each
# gets its own single-file chunk with a longer ceiling.
HEAVY_FILES="tests/contract/test_off_button_matrix.py"
HEAVY_TIMEOUT=1800
PYTEST=/opt/l30/backend/.venv/bin/pytest
RESULTS_DIR=$(mktemp -d /tmp/l30-deploy-pytest.XXXXXX)
FAILED=0

run_group() {
    group_name="$1"
    filelist="$2"
    n=$(wc -l < "$filelist" | tr -d ' ')
    if [ "$n" -eq 0 ]; then
        echo "run-pytest-chunked: no files for group $group_name, skipping"
        return 0
    fi
    split -l "$CHUNK_SIZE" -d -a 3 "$filelist" "$RESULTS_DIR/chunk_${group_name}_"
    total=$(ls "$RESULTS_DIR"/chunk_${group_name}_* | wc -l | tr -d ' ')
    i=0
    for chunkfile in "$RESULTS_DIR"/chunk_${group_name}_*; do
        i=$((i + 1))
        chunkname=$(basename "$chunkfile")
        echo "run-pytest-chunked: [$i/$total] $group_name chunk $chunkname"
        # shellcheck disable=SC2046
        if ! timeout "$CHUNK_TIMEOUT" "$PYTEST" $(cat "$chunkfile") \
            --timeout=120 -q -p no:warnings --tb=line \
            --junitxml="$RESULTS_DIR/${chunkname}.xml"; then
            echo "run-pytest-chunked: FAILED $group_name chunk $chunkname (see above)" >&2
            FAILED=1
        fi
    done
}

run_heavy() {
    i=0
    for f in $HEAVY_FILES; do
        [ -f "$f" ] || continue
        i=$((i + 1))
        safe=$(echo "$f" | tr '/' '_')
        echo "run-pytest-chunked: [heavy $i] $f"
        if ! timeout "$HEAVY_TIMEOUT" "$PYTEST" "$f" \
            --timeout=120 -q -p no:warnings --tb=line \
            --junitxml="$RESULTS_DIR/heavy_${safe}.xml"; then
            echo "run-pytest-chunked: FAILED heavy $f (see above)" >&2
            FAILED=1
        fi
    done
}

find tests -name 'test_*.py' -not -path 'tests/api/*' -not -path 'tests/quarantine/*' > "$RESULTS_DIR/root_files_all.txt"
for hf in $HEAVY_FILES; do
    grep -vF "$hf" "$RESULTS_DIR/root_files_all.txt" > "$RESULTS_DIR/root_files_all.txt.tmp" || true
    mv "$RESULTS_DIR/root_files_all.txt.tmp" "$RESULTS_DIR/root_files_all.txt"
done
sort "$RESULTS_DIR/root_files_all.txt" > "$RESULTS_DIR/root_files.txt"
find tests/api -name 'test_*.py' | sort > "$RESULTS_DIR/api_files.txt"
# pyproject testpaths is ["app/tests", "tests"]; until 2026-08-14 this gate
# only enumerated tests/, silently skipping the ~30 files under app/tests
# (~350 test functions). Probed same-env 2026-08-14: ~11 min of chunks.
find app/tests -name 'test_*.py' | sort > "$RESULTS_DIR/app_files.txt"

run_heavy
run_group root "$RESULTS_DIR/root_files.txt"
run_group api "$RESULTS_DIR/api_files.txt"
run_group app "$RESULTS_DIR/app_files.txt"

echo "run-pytest-chunked: results/junitxml in $RESULTS_DIR"
if [ "$FAILED" -ne 0 ]; then
    echo "run-pytest-chunked: one or more chunks failed" >&2
    exit 1
fi
echo "run-pytest-chunked: all chunks green"
