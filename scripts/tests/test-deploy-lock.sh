#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -eu
LOCKDIR=$(mktemp -d); trap 'rm -rf "$LOCKDIR"' EXIT
export L30_DEPLOY_LOCK="$LOCKDIR/test.lock"
. "$(dirname "$0")/../lib/deploy-lock.sh"

# Case 1: acquire when free (subshell so fd 9 closes on exit, releasing)
if ( acquire_deploy_lock 2 >/dev/null 2>&1 ); then echo "PASS: acquire when free"; else echo "FAIL: should acquire"; exit 1; fi

# Case 2: contention -> second acquire times out
flock -x "$L30_DEPLOY_LOCK" -c 'sleep 3' &
HOLDER=$!
sleep 1
if acquire_deploy_lock 1 >/dev/null 2>&1; then echo "FAIL: should time out under contention"; kill "$HOLDER" 2>/dev/null; exit 1; else echo "PASS: contention times out"; fi
wait "$HOLDER" 2>/dev/null || true

echo "ALL LOCK TESTS PASSED"
