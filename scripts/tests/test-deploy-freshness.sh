#!/bin/sh
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -eu
. "$(dirname "$0")/../lib/deploy-freshness.sh"

TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
git init -q -b main --bare "$TMP/origin.git"
git clone -q "$TMP/origin.git" "$TMP/work"
( cd "$TMP/work" && git config user.email t@t && git config user.name t   && echo a > a && git add a && git commit -qm a && git branch -M main && git push -q origin main )

# Case 1: up to date -> fresh
if assert_fresh "$TMP/work" >/dev/null 2>&1; then echo "PASS: fresh when up-to-date"; else echo "FAIL: should be fresh"; exit 1; fi

# advance origin/main from a second clone
git clone -q "$TMP/origin.git" "$TMP/work2"
( cd "$TMP/work2" && git checkout -q main && git config user.email t@t && git config user.name t   && echo b > b && git add b && git commit -qm b && git push -q origin main )

# Case 2: behind origin/main -> stale (return 1)
if assert_fresh "$TMP/work" >/dev/null 2>&1; then echo "FAIL: should be stale"; exit 1; else echo "PASS: stale when behind"; fi

# Case 3: stale + --allow-stale -> return 0
if assert_fresh "$TMP/work" --allow-stale >/dev/null 2>&1; then echo "PASS: allow-stale overrides"; else echo "FAIL: allow-stale should pass"; exit 1; fi

echo "ALL FRESHNESS TESTS PASSED"
