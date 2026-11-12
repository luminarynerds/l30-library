# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# guard_build_load [max_load] [max_wait_s] [min_free_mb]
# Block until the shared VPS can absorb a build: 1-min load average at/under
# max_load AND at least min_free_mb of available memory. Stops concurrent builds
# across the per-session worktrees from piling up and pinning the box (the
# 2026-06-22 build-storm that maxed CPU/RAM). Sourced, not executed.
# Defaults: max_load = CPU count, max_wait = 900s, min_free_mb = 2048.
# Never hard-fails a deploy: after max_wait it logs a warning and proceeds.

guard_build_load() {
    _lg_cores=$(nproc 2>/dev/null || echo 2)
    _lg_max="${1:-$_lg_cores}"
    _lg_wait="${2:-900}"
    _lg_minmb="${3:-2048}"
    _lg_elapsed=0
    while :; do
        _lg_load=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)
        _lg_free=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 999999)
        # proceed when load1 is NOT above max AND free memory is sufficient
        if ! awk -v a="$_lg_load" -v b="$_lg_max" 'BEGIN{exit !(a>b)}' && [ "$_lg_free" -ge "$_lg_minmb" ]; then
            if [ "$_lg_elapsed" -gt 0 ]; then
                echo "load-guard: capacity clear (load1=$_lg_load, freeMB=$_lg_free) -- building" >&2
            fi
            return 0
        fi
        if [ "$_lg_elapsed" -ge "$_lg_wait" ]; then
            echo "load-guard: still busy after ${_lg_wait}s (load1=$_lg_load vs max=$_lg_max, freeMB=$_lg_free vs min=$_lg_minmb) -- proceeding anyway" >&2
            return 0
        fi
        echo "load-guard: waiting for capacity (load1=$_lg_load max=$_lg_max, freeMB=$_lg_free min=$_lg_minmb); ${_lg_elapsed}/${_lg_wait}s" >&2
        sleep 15
        _lg_elapsed=$((_lg_elapsed + 15))
    done
}
