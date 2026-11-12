#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# L30 Library System - Automated Database Backup
# Runs via cron to create daily backups with 30-day retention
#
# Usage: Add to crontab (adjust the install path to yours):
#   0 2 * * * /opt/l30/scripts/automated-backup.sh >> /opt/l30/backups/backup.log 2>&1
#
# Optional environment variables:
#   BACKUP_S3_BUCKET            - S3 bucket name for off-site replication via
#                                 the aws CLI.
#   BACKUP_RCLONE_REMOTE        - rclone remote name for off-site replication
#                                 (e.g. "b2backup" for Backblaze B2). Uses
#                                 ${BACKUP_RCLONE_PATH:-l30-backups/daily} as
#                                 the destination path within the remote.
#                                 S3 and rclone uploads are independent — both
#                                 can be configured for redundant replication.
#   BACKUP_WEBHOOK_URL          - Webhook URL for success/failure notifications
#   BACKUP_AGE_RECIPIENTS_FILE  - Path to a file with age public-key recipients
#                                 (one per line). When set, archives are encrypted
#                                 with `age -R` and written as *.sql.gz.age.
#                                 The matching private key is NEVER stored on
#                                 this host; restores require an operator with
#                                 the identity file.

set -euo pipefail
umask 077

# Resolve the install directory from this script's location instead of
# hardcoding /opt/l30 -- lets this script run from any install path.
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Source environment variables: prefer the operator .env.prod (the
# l30.org reference deployment, docker-compose.prod.yml), fall back to .env (dist
# installs, docker-compose.dist.yml -- .env.prod doesn't exist there).
if [ -f "$PROJECT_DIR/.env.prod" ]; then
    set -a
    source "$PROJECT_DIR/.env.prod"
    set +a
elif [ -f "$PROJECT_DIR/.env" ]; then
    set -a
    source "$PROJECT_DIR/.env"
    set +a
fi

# Same prod-then-dist resolution as rollback.sh.
if [ -f "$PROJECT_DIR/docker-compose.prod.yml" ]; then
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
elif [ -f "$PROJECT_DIR/docker-compose.dist.yml" ]; then
    COMPOSE_FILE="$PROJECT_DIR/docker-compose.dist.yml"
else
    echo "[$(date)] ERROR: No docker-compose.prod.yml or docker-compose.dist.yml found in $PROJECT_DIR"
    exit 1
fi

BACKUP_DIR="$PROJECT_DIR/backups/daily"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Encryption is on iff BACKUP_AGE_RECIPIENTS_FILE points at a non-empty file.
# Determined here so filename and downstream verification stay consistent.
#
# Hard-fail guard: encryption is the default invariant. If
# BACKUP_AGE_RECIPIENTS_FILE is unset, the script EXITS rather than silently
# writing patron PII in plaintext. The unencrypted path is opt-in via
# ALLOW_UNENCRYPTED_BACKUP=1 — intended for one-off bootstrap before the age
# recipients file is installed, not steady-state.
ENCRYPT_ENABLED=0
if [ -n "${BACKUP_AGE_RECIPIENTS_FILE:-}" ]; then
    if [ ! -s "$BACKUP_AGE_RECIPIENTS_FILE" ]; then
        echo "[$(date)] ERROR: BACKUP_AGE_RECIPIENTS_FILE is set but file is missing or empty: $BACKUP_AGE_RECIPIENTS_FILE"
        exit 1
    fi
    if ! command -v age >/dev/null 2>&1; then
        echo "[$(date)] ERROR: BACKUP_AGE_RECIPIENTS_FILE is set but \`age\` is not installed"
        exit 1
    fi
    ENCRYPT_ENABLED=1
    BACKUP_FILE="${BACKUP_DIR}/l30_backup_${TIMESTAMP}.sql.gz.age"
elif [ "${ALLOW_UNENCRYPTED_BACKUP:-0}" = "1" ]; then
    echo "[$(date)] WARNING: BACKUP_AGE_RECIPIENTS_FILE not set — ALLOW_UNENCRYPTED_BACKUP=1 honored, writing plaintext"
    BACKUP_FILE="${BACKUP_DIR}/l30_backup_${TIMESTAMP}.sql.gz"
else
    echo "[$(date)] ERROR: BACKUP_AGE_RECIPIENTS_FILE is not set and ALLOW_UNENCRYPTED_BACKUP is not 1"
    echo "[$(date)] ERROR: Refusing to write unencrypted patron PII."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

# ---------------------------------------------------------------------------
# Notification helper (optional, gated by BACKUP_WEBHOOK_URL)
# ---------------------------------------------------------------------------
send_notification() {
    local status="$1"
    local message="$2"
    if [ -n "${BACKUP_WEBHOOK_URL:-}" ]; then
        curl -sf -X POST "$BACKUP_WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"status\": \"$status\", \"message\": \"$message\", \"timestamp\": \"$(date -Iseconds)\"}" \
            || echo "[$(date)] WARNING: Failed to send notification"
    fi
}

echo "[$(date)] Starting automated backup..."

# ---------------------------------------------------------------------------
# Disk space pre-check
# ---------------------------------------------------------------------------
REQUIRED_SPACE_KB=5242880  # 5GB minimum
AVAILABLE_KB=$(df --output=avail "$BACKUP_DIR" | tail -1)
if [ "$AVAILABLE_KB" -lt "$REQUIRED_SPACE_KB" ]; then
    echo "[$(date)] CRITICAL: Insufficient disk space (${AVAILABLE_KB}KB available, need ${REQUIRED_SPACE_KB}KB)"
    send_notification "failure" "Insufficient disk space (${AVAILABLE_KB}KB available, need ${REQUIRED_SPACE_KB}KB)"
    exit 1
fi

# ---------------------------------------------------------------------------
# Dump database via Docker, compress with gzip, optionally encrypt with age.
# Streamed end-to-end so plaintext never touches disk when encryption is on.
# `set -o pipefail` is in effect so a failure at any stage aborts.
# ---------------------------------------------------------------------------
DUMP_CMD=(docker compose -f "$COMPOSE_FILE" exec -T database
          pg_dump -U "${DB_USER:-l30}" --clean --if-exists --no-owner "${DB_NAME:-l30_library}")

if [ "$ENCRYPT_ENABLED" = "1" ]; then
    BACKUP_OK=0
    "${DUMP_CMD[@]}" 2>/dev/null \
        | gzip \
        | age -R "$BACKUP_AGE_RECIPIENTS_FILE" > "$BACKUP_FILE" \
        && BACKUP_OK=1
else
    BACKUP_OK=0
    "${DUMP_CMD[@]}" 2>/dev/null | gzip > "$BACKUP_FILE" && BACKUP_OK=1
fi

if [ "$BACKUP_OK" = "1" ]; then
    SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "[$(date)] Backup completed: $BACKUP_FILE ($SIZE, encrypted=$ENCRYPT_ENABLED)"
else
    echo "[$(date)] ERROR: Backup failed!"
    send_notification "failure" "Database dump failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Verify backup is not empty
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[$(date)] ERROR: Backup file is empty!"
    send_notification "failure" "Backup file is empty"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# ---------------------------------------------------------------------------
# Backup integrity verification
#
# For encrypted backups we cannot run gzip -t without the private key (which
# must not live on this host). Verify the age framing instead: the file must
# start with the documented "age-encryption.org/v1" header line.
# For unencrypted backups, keep the existing gzip integrity check.
# ---------------------------------------------------------------------------
if [ "$ENCRYPT_ENABLED" = "1" ]; then
    if ! head -c 21 "$BACKUP_FILE" | grep -q '^age-encryption.org/v1$'; then
        echo "[$(date)] ERROR: Backup file failed age header check!"
        send_notification "failure" "Backup file is missing age header (encryption may have failed)"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
    echo "[$(date)] Backup integrity verified (age header check passed)"
else
    if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
        echo "[$(date)] ERROR: Backup file failed integrity check!"
        send_notification "failure" "Backup file failed gzip integrity check"
        rm -f "$BACKUP_FILE"
        exit 1
    fi
    echo "[$(date)] Backup integrity verified (gzip check passed)"
fi

# ---------------------------------------------------------------------------
# Optional S3 off-site replication (gated by BACKUP_S3_BUCKET)
# ---------------------------------------------------------------------------
if [ -n "${BACKUP_S3_BUCKET:-}" ]; then
    if aws s3 cp "$BACKUP_FILE" "s3://${BACKUP_S3_BUCKET}/daily/$(basename $BACKUP_FILE)" --quiet; then
        echo "[$(date)] Off-site backup uploaded to s3://${BACKUP_S3_BUCKET}"
    else
        echo "[$(date)] WARNING: Off-site backup upload failed!"
        send_notification "warning" "Off-site S3 upload failed (local backup succeeded)"
    fi
fi

# ---------------------------------------------------------------------------
# Optional rclone off-site replication (gated by BACKUP_RCLONE_REMOTE)
# Use for Backblaze B2, Cloudflare R2, Hetzner Storage Box, etc. The remote
# must be pre-configured via `rclone config` for the user running this cron
# (typically root). See docs/OFFSITE_BACKUP_SETUP.md.
# ---------------------------------------------------------------------------
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
    DEST_PATH="${BACKUP_RCLONE_PATH:-l30-backups/daily}"
    if rclone copy "$BACKUP_FILE" "${BACKUP_RCLONE_REMOTE}:${DEST_PATH}/" --quiet; then
        echo "[$(date)] Off-site backup uploaded to ${BACKUP_RCLONE_REMOTE}:${DEST_PATH}/"
    else
        echo "[$(date)] WARNING: rclone upload failed!"
        send_notification "warning" "Off-site rclone upload failed (local backup succeeded)"
    fi
fi

# ---------------------------------------------------------------------------
# Cleanup old backups (keep last RETENTION_DAYS days)
# ---------------------------------------------------------------------------
DELETED=$(find "$BACKUP_DIR" \( -name "l30_backup_*.sql.gz" -o -name "l30_backup_*.sql.gz.age" \) -mtime +${RETENTION_DAYS} -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[$(date)] Cleaned up $DELETED backup(s) older than ${RETENTION_DAYS} days"
fi

# Show backup inventory
TOTAL=$(find "$BACKUP_DIR" \( -name "l30_backup_*.sql.gz" -o -name "l30_backup_*.sql.gz.age" \) | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
echo "[$(date)] Backup inventory: $TOTAL backups, total size: $TOTAL_SIZE"
echo "[$(date)] Backup complete."

send_notification "success" "Backup completed successfully: $(basename $BACKUP_FILE) ($SIZE)"
