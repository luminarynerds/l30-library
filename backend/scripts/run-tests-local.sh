#!/usr/bin/env bash
# Local backend test runner — ephemeral Postgres (pgvector) + Redis via standalone
# docker (NOT docker compose), replicating .github/workflows/backend-tests.yml
# with non-conflicting ports for this machine. Idempotent: reuses containers if
# they already exist, creates them if not.
#
# Usage: backend/scripts/run-tests-local.sh [pytest args...]
# Example: backend/scripts/run-tests-local.sh -k test_attendance -v

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

PG_CONTAINER="l30-test-pg-fable"
REDIS_CONTAINER="l30-test-redis-fable"
PG_PORT="5435"
REDIS_PORT="6380"

export DATABASE_URL="postgresql+asyncpg://lsc:test_password@127.0.0.1:${PG_PORT}/lsc_test"
export REDIS_URL="redis://127.0.0.1:${REDIS_PORT}/0"
export SECRET_KEY="test-secret-key-do-not-use"
export PII_ENCRYPTION_ENABLED="false"

ensure_container_running() {
    local name="$1"
    shift
    if docker ps --format '{{.Names}}' | grep -qx "$name"; then
        echo "-- $name already running"
    elif docker ps -a --format '{{.Names}}' | grep -qx "$name"; then
        echo "-- starting existing container $name"
        docker start "$name" >/dev/null
    else
        echo "-- creating container $name"
        "$@"
    fi
}

ensure_container_running "$PG_CONTAINER" \
    docker run -d --name "$PG_CONTAINER" \
        -e POSTGRES_USER=lsc \
        -e POSTGRES_PASSWORD=test_password \
        -e POSTGRES_DB=lsc_test \
        -p "${PG_PORT}:5432" \
        pgvector/pgvector:pg16

ensure_container_running "$REDIS_CONTAINER" \
    docker run -d --name "$REDIS_CONTAINER" \
        -p "${REDIS_PORT}:6379" \
        redis:7-alpine

echo "-- waiting for postgres..."
for _ in $(seq 1 30); do
    if docker exec "$PG_CONTAINER" pg_isready -U lsc -d lsc_test >/dev/null 2>&1; then
        break
    fi
    sleep 1
done
docker exec "$PG_CONTAINER" pg_isready -U lsc -d lsc_test

# tests/conftest.py hardcodes the pytest-session database name to "l30_test"
# (it swaps the last path segment of DATABASE_URL regardless of what's given),
# so the lsc_test db created above is only used by init_db.py — pytest itself
# needs a separate "l30_test" db to exist or it silently falls back to SQLite.
if ! docker exec "$PG_CONTAINER" psql -U lsc -d lsc_test -tc \
        "SELECT 1 FROM pg_database WHERE datname = 'l30_test'" | grep -q 1; then
    echo "-- creating l30_test database (used by pytest via conftest.py db-name swap)"
    docker exec "$PG_CONTAINER" psql -U lsc -d lsc_test -c "CREATE DATABASE l30_test;"
fi

# pgvector's docker-entrypoint-initdb.d only creates the "vector" extension in
# the POSTGRES_DB-created database (lsc_test), not in l30_test (created above
# after container init) — models with a VECTOR column fail with
# `type "vector" does not exist` unless we create it explicitly in both.
docker exec "$PG_CONTAINER" psql -U lsc -d lsc_test -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null
docker exec "$PG_CONTAINER" psql -U lsc -d l30_test -c "CREATE EXTENSION IF NOT EXISTS vector;" >/dev/null

cd "$BACKEND_DIR"

if [[ ! -d .venv ]]; then
    echo "-- no .venv found; create one first: python3.12 -m venv .venv && source .venv/bin/activate && pip install -e . && pip install pytest pytest-asyncio pytest-cov aiosqlite jsonschema faker greenlet" >&2
    exit 1
fi
# shellcheck disable=SC1091
source .venv/bin/activate

# Schema is idempotent (init_db.py syncs from models); safe to re-run.
python scripts/init_db.py

python -m pytest tests/ --cov=app --cov-report=term-missing -q -p no:warnings \
    --continue-on-collection-errors "$@"
