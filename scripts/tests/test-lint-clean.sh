#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin"
cat > "$TMP_DIR/bin/docker" <<'EOF'
#!/usr/bin/env bash
printf '%q ' "$@" >> "$DOCKER_LOG"
printf '\n' >> "$DOCKER_LOG"
EOF
chmod +x "$TMP_DIR/bin/docker"

export DOCKER_LOG="$TMP_DIR/docker.log"
export PATH="$TMP_DIR/bin:$PATH"

: > "$DOCKER_LOG"
"$ROOT_DIR/scripts/lint-clean.sh" frontend
[[ "$(wc -l < "$DOCKER_LOG")" -eq 1 ]]
grep -q 'node:20-bookworm-slim' "$DOCKER_LOG"
! grep -q 'python:3.12-slim' "$DOCKER_LOG"

: > "$DOCKER_LOG"
"$ROOT_DIR/scripts/lint-clean.sh" backend
[[ "$(wc -l < "$DOCKER_LOG")" -eq 1 ]]
grep -q 'python:3.12-slim' "$DOCKER_LOG"
grep -q -- '--no-cache' "$DOCKER_LOG"
! grep -q 'node:20-bookworm-slim' "$DOCKER_LOG"

: > "$DOCKER_LOG"
"$ROOT_DIR/scripts/lint-clean.sh"
[[ "$(wc -l < "$DOCKER_LOG")" -eq 2 ]]

: > "$DOCKER_LOG"
if "$ROOT_DIR/scripts/lint-clean.sh" unknown >/dev/null 2>&1; then
    echo "invalid target unexpectedly succeeded" >&2
    exit 1
fi
[[ ! -s "$DOCKER_LOG" ]]

echo "lint-clean orchestration: ok"
