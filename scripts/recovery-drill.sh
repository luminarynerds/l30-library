#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# L30 Library System - Backup recovery drill
#
# Run quarterly. Decrypts an age-encrypted backup with the operator's secret
# identity, restores it into an EPHEMERAL throwaway Postgres container, runs
# sanity queries, and reports PASS/FAIL. Tears the container down on exit.
#
# DO NOT run this on the prod host. The whole point of off-host backup
# encryption is that the secret identity does not live on prod. Run this on
# an operator workstation or a dedicated recovery box that has:
#   - docker
#   - age
#   - the secret identity file (l30-backup.key) loaded from the password manager
#   - optionally aws CLI (for --s3-bucket)
#
# Usage:
#   ./recovery-drill.sh --identity ~/l30-backup.key --archive /path/to/l30_backup_*.sql.gz.age
#   ./recovery-drill.sh --identity ~/l30-backup.key --s3-bucket l30-backups
#
# Exit codes:
#   0 - drill passed
#   1 - drill failed (decrypt, restore, or sanity check failed)
#   2 - bad arguments / missing tools

set -euo pipefail

IDENTITY=""
ARCHIVE=""
S3_BUCKET=""
PG_IMAGE="pgvector/pgvector:pg16"
MIN_TABLES=50         # L30 has ~220 models; <50 means restore was incomplete
KEEP_ON_FAIL=0        # set 1 to keep the container running on failure for inspection

while [ $# -gt 0 ]; do
    case "$1" in
        --identity)    IDENTITY="$2"; shift 2 ;;
        --archive)     ARCHIVE="$2"; shift 2 ;;
        --s3-bucket)   S3_BUCKET="$2"; shift 2 ;;
        --keep-on-fail) KEEP_ON_FAIL=1; shift ;;
        -h|--help)     sed -n '2,30p' "$0"; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; exit 2 ;;
    esac
done

die() { echo "ERROR: $*" >&2; exit "${2:-1}"; }

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------
[ -n "$IDENTITY" ]   || die "--identity is required" 2
[ -f "$IDENTITY" ]   || die "Identity file not found: $IDENTITY" 2
for bin in docker age; do
    command -v "$bin" >/dev/null 2>&1 || die "Required tool missing: $bin" 2
done
if [ -z "$ARCHIVE" ] && [ -z "$S3_BUCKET" ]; then
    die "Provide either --archive PATH or --s3-bucket NAME" 2
fi
if [ -n "$ARCHIVE" ] && [ -n "$S3_BUCKET" ]; then
    die "--archive and --s3-bucket are mutually exclusive" 2
fi

WORKDIR=$(mktemp -d -t l30-recovery-drill.XXXXXX)
CONTAINER_NAME="l30-recovery-drill-$(date +%s)-$$"
PG_PORT=""        # filled in after container starts
SUMMARY_FILE="$WORKDIR/summary.txt"
PASS=1            # flips to 0 on any failure
declare -a CHECKS

cleanup() {
    local exit_code=$?
    if [ "$KEEP_ON_FAIL" = "1" ] && [ "$exit_code" -ne 0 ]; then
        echo
        echo "==> --keep-on-fail set; leaving container $CONTAINER_NAME running for inspection"
        echo "    Connect: docker exec -it $CONTAINER_NAME psql -U drill drill"
        echo "    Stop:    docker rm -f $CONTAINER_NAME"
    else
        if docker ps -aq -f "name=^${CONTAINER_NAME}$" | grep -q .; then
            docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
        fi
    fi
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

record() {
    # record <pass|fail> <description>
    local status="$1" msg="$2"
    if [ "$status" = "fail" ]; then PASS=0; fi
    CHECKS+=("[$status] $msg")
}

# ---------------------------------------------------------------------------
# Resolve archive (pull from S3 if needed)
# ---------------------------------------------------------------------------
if [ -n "$S3_BUCKET" ]; then
    command -v aws >/dev/null 2>&1 || die "aws CLI required for --s3-bucket" 2
    echo "==> Listing s3://${S3_BUCKET}/daily/ for the latest *.sql.gz.age"
    LATEST_KEY=$(aws s3api list-objects-v2 \
        --bucket "$S3_BUCKET" --prefix "daily/" \
        --query 'sort_by(Contents,&LastModified)[?ends_with(Key,`.sql.gz.age`)][-1].Key' \
        --output text 2>/dev/null || true)
    [ -n "$LATEST_KEY" ] && [ "$LATEST_KEY" != "None" ] \
        || die "No *.sql.gz.age objects found in s3://${S3_BUCKET}/daily/"
    ARCHIVE="$WORKDIR/$(basename "$LATEST_KEY")"
    echo "==> Downloading s3://${S3_BUCKET}/${LATEST_KEY}"
    aws s3 cp "s3://${S3_BUCKET}/${LATEST_KEY}" "$ARCHIVE" --quiet
fi

[ -f "$ARCHIVE" ] || die "Archive not found: $ARCHIVE"
ARCHIVE_SIZE=$(du -h "$ARCHIVE" | cut -f1)
echo "==> Archive: $ARCHIVE ($ARCHIVE_SIZE)"

# ---------------------------------------------------------------------------
# Spin up ephemeral Postgres on an ephemeral port (no port collisions in CI)
# ---------------------------------------------------------------------------
echo "==> Starting ephemeral $PG_IMAGE as $CONTAINER_NAME"
docker run -d --rm \
    --name "$CONTAINER_NAME" \
    -e POSTGRES_USER=drill \
    -e POSTGRES_PASSWORD=drill \
    -e POSTGRES_DB=drill \
    -P \
    "$PG_IMAGE" >/dev/null

# Wait for healthy
echo -n "==> Waiting for Postgres to accept connections"
for _ in $(seq 1 60); do
    if docker exec "$CONTAINER_NAME" pg_isready -U drill -d drill >/dev/null 2>&1; then
        echo " ready"
        break
    fi
    echo -n "."
    sleep 1
done
docker exec "$CONTAINER_NAME" pg_isready -U drill -d drill >/dev/null 2>&1 \
    || die "Ephemeral Postgres did not become ready"

# pgvector extension is needed if the dump references vector types
docker exec "$CONTAINER_NAME" psql -U drill -d drill -c "CREATE EXTENSION IF NOT EXISTS vector" >/dev/null 2>&1 || true

# ---------------------------------------------------------------------------
# Decrypt + restore (streamed, plaintext never on disk)
# ---------------------------------------------------------------------------
echo "==> Decrypting + restoring (streamed)"
RESTORE_LOG="$WORKDIR/restore.log"
if age -d -i "$IDENTITY" "$ARCHIVE" \
    | gunzip \
    | docker exec -i "$CONTAINER_NAME" psql -U drill -d drill -v ON_ERROR_STOP=0 \
    > "$RESTORE_LOG" 2>&1; then
    record pass "decrypt + restore stream completed"
else
    record fail "decrypt + restore stream failed (see $RESTORE_LOG)"
fi

# Surface the most informative restore errors (warnings are normal, hard
# errors are not — we count occurrences rather than failing on every WARNING)
ERR_COUNT=$(grep -cE "^psql:.*ERROR:" "$RESTORE_LOG" 2>/dev/null || echo 0)
if [ "$ERR_COUNT" -gt 0 ]; then
    record fail "restore produced $ERR_COUNT psql ERROR lines (see $RESTORE_LOG)"
else
    record pass "restore produced 0 psql ERROR lines"
fi

# ---------------------------------------------------------------------------
# Sanity queries
# ---------------------------------------------------------------------------
psql_q() {
    docker exec "$CONTAINER_NAME" psql -U drill -d drill -tA -c "$1" 2>/dev/null
}

TABLES=$(psql_q "SELECT count(*) FROM pg_tables WHERE schemaname = 'public';")
TABLES=${TABLES:-0}
if [ "$TABLES" -ge "$MIN_TABLES" ]; then
    record pass "$TABLES tables in public schema (>= $MIN_TABLES)"
else
    record fail "only $TABLES tables in public schema (expected >= $MIN_TABLES)"
fi

DB_SIZE=$(psql_q "SELECT pg_size_pretty(pg_database_size('drill'));")
record pass "restored database size: ${DB_SIZE:-unknown}"

# Spot-check a few tables likely to exist; absence is reported, not failed,
# because table names may evolve.
for t in patrons users items checkouts holds audit_log; do
    rows=$(psql_q "SELECT count(*) FROM \"$t\";" 2>/dev/null || echo "")
    if [ -n "$rows" ]; then
        record pass "table \"$t\": $rows rows"
    fi
done

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------
{
    echo "==========================================================="
    echo "L30 Backup Recovery Drill - $(date)"
    echo "Archive:   $ARCHIVE ($ARCHIVE_SIZE)"
    echo "Container: $CONTAINER_NAME"
    echo "==========================================================="
    for line in "${CHECKS[@]}"; do echo "  $line"; done
    echo "==========================================================="
    if [ "$PASS" = "1" ]; then
        echo "RESULT: PASS"
    else
        echo "RESULT: FAIL"
    fi
} | tee "$SUMMARY_FILE"

if [ "$PASS" = "1" ]; then
    exit 0
else
    exit 1
fi
