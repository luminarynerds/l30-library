#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -euo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
TARGET="${1:-all}"

usage() {
    echo "Usage: scripts/lint-clean.sh [all|frontend|backend]"
}

case "$TARGET" in
    all|frontend|backend) ;;
    -h|--help)
        usage
        exit 0
        ;;
    *)
        usage >&2
        exit 2
        ;;
esac

if ! command -v docker >/dev/null 2>&1; then
    echo "lint-clean: Docker is required" >&2
    exit 1
fi

lint_frontend() {
    echo "lint-clean: frontend (Node 20, clean npm install)"
    docker run --rm --pull=missing \
        -v "$ROOT_DIR:/repo:ro" \
        node:20-bookworm-slim \
        bash -euo pipefail -c '
            mkdir -p /tmp/l30/frontend /tmp/l30/scripts
            tar -C /repo/frontend \
                --exclude=node_modules \
                --exclude=dist \
                --exclude=coverage \
                -cf - . | tar -C /tmp/l30/frontend -xf -
            cp /repo/scripts/validate-translations.js /tmp/l30/scripts/
            cd /tmp/l30/frontend
            npm ci --legacy-peer-deps
            npm run lint
            npm run typecheck
            npm run lint:i18n
            node ../scripts/validate-translations.js
        '
}

lint_backend() {
    echo "lint-clean: backend (Python 3.12, clean Ruff install)"
    docker run --rm --pull=missing \
        -v "$ROOT_DIR:/repo:ro" \
        -w /repo/backend \
        python:3.12-slim \
        sh -eu -c '
            python -m pip install --disable-pip-version-check --quiet ruff
            ruff check --no-cache app
        '
}

if [[ "$TARGET" == all || "$TARGET" == frontend ]]; then
    lint_frontend
fi

if [[ "$TARGET" == all || "$TARGET" == backend ]]; then
    lint_backend
fi

echo "lint-clean: passed ($TARGET)"
