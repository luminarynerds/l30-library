#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# L30 Library System - Backup Restore Verification
# Validates that a backup can be successfully restored into a temporary
# PostgreSQL instance and that critical tables contain data.
#
# Usage:
#   BACKUP_AGE_IDENTITY_FILE=/secure/path/key.txt \
#     ./verify-backup-restore.sh [/path/to/backup.sql.gz.age]
#
# If no backup path is given, the latest file in /opt/l30/backups/daily/ is used.
#
# Designed to run monthly via cron:
#   0 4 1 * * /opt/l30/scripts/verify-backup-restore.sh >> /opt/l30/backups/verify.log 2>&1

set -euo pipefail

BACKUP_DIR="/opt/l30/backups/daily"
CONTAINER_NAME="l30_backup_verify_$$"
PG_IMAGE="pgvector/pgvector:pg16"
PG_USER="l30"
PG_DB="l30_library"
PG_PASSWORD="verify_temp_$(date +%s)"
PG_PORT=54321  # Non-standard port to avoid conflicts
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

notify_slack() {
    local status="$1"
    local message="$2"

    if [ -z "$SLACK_WEBHOOK" ]; then
        return
    fi

    local color="good"
    if [ "$status" = "error" ]; then
        color="danger"
    elif [ "$status" = "warning" ]; then
        color="warning"
    fi

    local payload
    payload=$(cat <<EOF
{
  "attachments": [
    {
      "color": "${color}",
      "title": "L30 Restore Verification",
      "text": "${message}",
      "footer": "verify-backup-restore.sh",
      "ts": $(date +%s)
    }
  ]
}
EOF
)

    curl -X POST -H "Content-type: application/json" --data "$payload" "$SLACK_WEBHOOK" >/dev/null 2>&1 || true
}

fail_restore_verify() {
    local message="$1"
    echo "[$(date)] FAIL: ${message}"
    notify_slack "error" "${message} ($(hostname))"
    exit 1
}

cleanup() {
    echo "[$(date)] Cleaning up temporary container..."
    docker rm -f "$CONTAINER_NAME" 2>/dev/null || true
}
trap cleanup EXIT

# ---------------------------------------------------------------------------
# Determine backup file
# ---------------------------------------------------------------------------
if [ $# -ge 1 ]; then
    BACKUP_FILE="$1"
else
    BACKUP_FILE=$(find "$BACKUP_DIR" -maxdepth 1 -type f \
        \( -name 'l30_backup_*.sql.gz.age' -o -name 'l30_backup_*.sql.gz' \) \
        -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
fi

if [ -z "${BACKUP_FILE:-}" ] || [ ! -f "$BACKUP_FILE" ]; then
    echo "[$(date)] ERROR: No backup file found."
    echo "  Usage: BACKUP_AGE_IDENTITY_FILE=/secure/path/key.txt $0 [/path/to/backup.sql.gz.age]"
    exit 1
fi

echo "[$(date)] Verifying backup: $BACKUP_FILE"
echo "[$(date)] File size: $(du -h "$BACKUP_FILE" | cut -f1)"

# ---------------------------------------------------------------------------
# Step 1: Verify gzip integrity
# ---------------------------------------------------------------------------
echo "[$(date)] Checking archive integrity..."
if [[ "$BACKUP_FILE" == *.age ]]; then
    if ! head -c 21 "$BACKUP_FILE" | grep -q '^age-encryption.org/v1$'; then
        fail_restore_verify "Backup file has an invalid age header"
    fi
    if [ -z "${BACKUP_AGE_IDENTITY_FILE:-}" ] || [ ! -s "$BACKUP_AGE_IDENTITY_FILE" ]; then
        fail_restore_verify "Encrypted backup requires BACKUP_AGE_IDENTITY_FILE for a real restore test"
    fi
    if ! command -v age >/dev/null 2>&1; then
        fail_restore_verify "age is required to decrypt the selected backup"
    fi
    if ! age --decrypt -i "$BACKUP_AGE_IDENTITY_FILE" "$BACKUP_FILE" | gzip -t; then
        fail_restore_verify "Backup decryption or gzip integrity check failed"
    fi
else
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        fail_restore_verify "Backup file failed gzip integrity check"
    fi
fi
echo "[$(date)] Archive integrity OK."

# ---------------------------------------------------------------------------
# Step 2: Start temporary PostgreSQL container
# ---------------------------------------------------------------------------
echo "[$(date)] Starting temporary PostgreSQL container ($CONTAINER_NAME)..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -e POSTGRES_USER="$PG_USER" \
    -e POSTGRES_PASSWORD="$PG_PASSWORD" \
    -e POSTGRES_DB="$PG_DB" \
    -p "127.0.0.1:${PG_PORT}:5432" \
    "$PG_IMAGE" > /dev/null

# Wait for PostgreSQL to be ready
echo "[$(date)] Waiting for PostgreSQL to be ready..."
RETRIES=30
until docker exec "$CONTAINER_NAME" pg_isready -U "$PG_USER" -d "$PG_DB" -q 2>/dev/null; do
    RETRIES=$((RETRIES - 1))
    if [ "$RETRIES" -le 0 ]; then
        fail_restore_verify "Temporary PostgreSQL did not become ready in time"
    fi
    sleep 1
done
echo "[$(date)] PostgreSQL is ready."

# ---------------------------------------------------------------------------
# Step 3: Restore the backup
# ---------------------------------------------------------------------------
echo "[$(date)] Restoring backup into temporary database..."
RESTORE_LOG=$(mktemp)
restore_stream() {
    if [[ "$BACKUP_FILE" == *.age ]]; then
        age --decrypt -i "$BACKUP_AGE_IDENTITY_FILE" "$BACKUP_FILE" | gunzip -c
    else
        gunzip -c "$BACKUP_FILE"
    fi
}

if ! restore_stream | docker exec -i "$CONTAINER_NAME" psql -U "$PG_USER" -d "$PG_DB" --quiet --no-psqlrc >"$RESTORE_LOG" 2>&1; then
    echo "[$(date)] Last restore output lines:"
    tail -20 "$RESTORE_LOG" || true
    rm -f "$RESTORE_LOG"
    fail_restore_verify "Backup restore command failed"
fi

if grep -Eq '^(ERROR|FATAL|PANIC):' "$RESTORE_LOG"; then
    echo "[$(date)] Last restore output lines:"
    tail -20 "$RESTORE_LOG" || true
    rm -f "$RESTORE_LOG"
    fail_restore_verify "Restore completed with SQL errors present"
fi

echo "[$(date)] Restore completed."
rm -f "$RESTORE_LOG"

# ---------------------------------------------------------------------------
# Step 4: Run verification queries
# ---------------------------------------------------------------------------
echo "[$(date)] Running verification queries..."

VERIFY_FAILED=0

run_count_check() {
    local table="$1"
    local count
    count=$(docker exec "$CONTAINER_NAME" \
        psql -U "$PG_USER" -d "$PG_DB" -t -A -c "SELECT count(*) FROM $table" 2>/dev/null || echo "ERROR")

    if [ "$count" = "ERROR" ]; then
        echo "[$(date)]   $table: FAIL (query error)"
        VERIFY_FAILED=1
    elif [ "$count" -gt 0 ] 2>/dev/null; then
        echo "[$(date)]   $table: OK ($count rows)"
    else
        echo "[$(date)]   $table: WARNING (0 rows)"
    fi
}

run_count_check "users"
run_count_check "checkouts"
run_count_check "catalog_items"

# Also verify we can query the information schema (general DB sanity)
TABLE_COUNT=$(docker exec "$CONTAINER_NAME" \
    psql -U "$PG_USER" -d "$PG_DB" -t -A -c \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'" 2>/dev/null || echo "0")
echo "[$(date)]   Total public tables: $TABLE_COUNT"

if [ "$TABLE_COUNT" -lt 1 ] 2>/dev/null; then
    fail_restore_verify "No tables found in restored database"
fi

# ---------------------------------------------------------------------------
# Step 5: Report result
# ---------------------------------------------------------------------------
if [ "$VERIFY_FAILED" -ne 0 ]; then
    fail_restore_verify "Backup restore verification found issues"
fi

PASS_MSG="Backup $(basename "$BACKUP_FILE") restored and verified successfully"
echo "[$(date)] RESULT: PASS - ${PASS_MSG}."
notify_slack "good" "${PASS_MSG} ($(hostname))"
exit 0
