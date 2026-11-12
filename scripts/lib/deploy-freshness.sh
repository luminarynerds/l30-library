# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# assert_fresh <tree> [--allow-stale]
# Returns 0 if <tree> HEAD contains origin/main (or --allow-stale given),
# 1 if stale, 2 on usage/fetch error. Sourced, not executed.

assert_fresh() {
    tree="$1"
    allow_stale="${2:-}"
    if [ -z "$tree" ]; then
        echo "assert_fresh: missing <tree> argument" >&2
        return 2
    fi
    if ! git -C "$tree" fetch -q origin main; then
        echo "assert_fresh: 'git fetch origin main' failed in $tree" >&2
        return 2
    fi
    if git -C "$tree" merge-base --is-ancestor origin/main HEAD; then
        echo "freshness: OK ($tree contains origin/main)"
        return 0
    fi
    echo "freshness: STALE -- $tree is missing commits from origin/main:" >&2
    git -C "$tree" log --oneline HEAD..origin/main >&2
    if [ "$allow_stale" = "--allow-stale" ]; then
        echo "freshness: proceeding anyway (--allow-stale)" >&2
        return 0
    fi
    echo "Merge origin/main first (git -C $tree merge origin/main), or pass --allow-stale." >&2
    return 1
}
