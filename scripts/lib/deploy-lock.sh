# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# Deploy mutex via flock. Sourced, not executed.
#   acquire_deploy_lock [timeout_seconds]
#   release_deploy_lock
# Lock is held for the life of the calling shell (fd 9) until release/exit.

: "${L30_DEPLOY_LOCK:=/var/lock/l30-deploy.lock}"

acquire_deploy_lock() {
    timeout="${1:-180}"
    if ! exec 9>"$L30_DEPLOY_LOCK"; then
        echo "lock: cannot open $L30_DEPLOY_LOCK" >&2
        return 2
    fi
    if ! flock -w "$timeout" 9; then
        echo "lock: another deploy is in progress -- held by:" >&2
        cat "${L30_DEPLOY_LOCK}.holder" 2>/dev/null >&2 || echo "  (holder unknown)" >&2
        exec 9>&- 2>/dev/null || true
        return 1
    fi
    printf 'user=%s time=%s pid=%s tree=%s\n' \
        "${USER:-root}" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$$" "${DEPLOY_TREE:-?}" \
        > "${L30_DEPLOY_LOCK}.holder"
    echo "lock: acquired ($L30_DEPLOY_LOCK)"
}

release_deploy_lock() {
    rm -f "${L30_DEPLOY_LOCK}.holder" 2>/dev/null || true
    exec 9>&- 2>/dev/null || true
    echo "lock: released"
}
