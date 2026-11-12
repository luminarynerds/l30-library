#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

# L30 Library Backup Verification Script
# Runs weekly to verify backup integrity and recency
# Cron entry: 0 3 * * 0 /opt/l30/scripts/verify-backups.sh >> /opt/l30/logs/backup-verify.log 2>&1

set -e

# Configuration
BACKUP_DIR="/opt/l30/backups"
LOG_DIR="/opt/l30/logs"
LOG_FILE="$LOG_DIR/backup-verify.log"
ALERT_EMAIL="${ALERT_EMAIL:-admin@l30.local}"
SLACK_WEBHOOK="${SLACK_WEBHOOK:-}"

# Verification thresholds
MIN_BACKUP_SIZE=1048576  # 1MB in bytes
MAX_BACKUP_AGE_HOURS=24
ALERT_THRESHOLD=0  # Alert if any backup fails

# Ensure log directory exists
mkdir -p "$LOG_DIR"

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

error() {
  echo "[ERROR] $1" | tee -a "$LOG_FILE"
}

warning() {
  echo "[WARNING] $1" | tee -a "$LOG_FILE"
}

success() {
  echo "[OK] $1" | tee -a "$LOG_FILE"
}

info() {
  echo "[INFO] $1" | tee -a "$LOG_FILE"
}

# Send Slack notification
send_slack_notification() {
  local status=$1
  local message=$2

  if [ -z "$SLACK_WEBHOOK" ]; then
    return
  fi

  local color="good"
  if [ "$status" = "error" ]; then
    color="danger"
  elif [ "$status" = "warning" ]; then
    color="warning"
  fi

  local payload=$(cat <<EOF
{
  "attachments": [
    {
      "color": "$color",
      "title": "L30 Backup Verification Report",
      "text": "$message",
      "footer": "L30 Backup Verification System",
      "ts": $(date +%s)
    }
  ]
}
EOF
)

  curl -X POST -H 'Content-type: application/json' \
    --data "$payload" \
    "$SLACK_WEBHOOK" 2>/dev/null || true
}

# Log header
{
  echo "=========================================="
  echo "Backup Verification Report - $(date)"
  echo "=========================================="
  echo ""
} >> "$LOG_FILE"

info "Starting backup verification..."

# Counters
TOTAL_BACKUPS=0
VALID_BACKUPS=0
FAILED_BACKUPS=0
WARNING_BACKUPS=0

# Check if backup directory exists
if [ ! -d "$BACKUP_DIR" ]; then
  error "Backup directory not found: $BACKUP_DIR"
  send_slack_notification "error" "Backup verification failed: backup directory not found"
  exit 1
fi

# Check for any backups
if [ -z "$(ls -A "$BACKUP_DIR" 2>/dev/null)" ]; then
  error "No backups found in $BACKUP_DIR"
  send_slack_notification "error" "No backups found in backup directory"
  exit 1
fi

# Get current time in seconds
CURRENT_TIME=$(date +%s)

# Verify each backup
info "Verifying backups in: $BACKUP_DIR"
echo "" >> "$LOG_FILE"

while IFS= read -r -d '' backup_file; do
  if [ -f "$backup_file" ]; then
    TOTAL_BACKUPS=$((TOTAL_BACKUPS + 1))
    backup_name=$(basename "$backup_file")
    file_size=$(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null)
    file_mtime=$(stat -f%m "$backup_file" 2>/dev/null || stat -c%Y "$backup_file" 2>/dev/null)
    file_age_hours=$(( ($CURRENT_TIME - $file_mtime) / 3600 ))

    echo "Backup: $backup_name" >> "$LOG_FILE"
    echo "  Size: $file_size bytes" >> "$LOG_FILE"
    echo "  Age: $file_age_hours hours" >> "$LOG_FILE"

    # Check size
    if [ "$file_size" -lt "$MIN_BACKUP_SIZE" ]; then
      warning "Backup too small: $backup_name ($file_size bytes, expected >= $MIN_BACKUP_SIZE)"
      FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
      echo "  Status: FAILED (size too small)" >> "$LOG_FILE"
      continue
    fi

    # Check file integrity
    if [[ "$backup_file" == *.age ]]; then
      # Encrypted archives: header check only. The private key lives off-host,
      # so deeper verification (decrypt + gzip -t) belongs in a recovery drill,
      # not the live cron.
      if head -c 21 "$backup_file" 2>/dev/null | grep -q '^age-encryption.org/v1$'; then
        success "Backup verified: $backup_name (size: $file_size bytes, age: $file_age_hours hours)"
        VALID_BACKUPS=$((VALID_BACKUPS + 1))
        echo "  Status: VALID (age header verified)" >> "$LOG_FILE"
      else
        error "Backup corrupted (invalid age header): $backup_name"
        FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
        echo "  Status: FAILED (age header missing)" >> "$LOG_FILE"
      fi
    elif [[ "$backup_file" == *.tar.gz ]]; then
      if tar -tzf "$backup_file" >/dev/null 2>&1; then
        success "Backup verified: $backup_name (size: $file_size bytes, age: $file_age_hours hours)"
        VALID_BACKUPS=$((VALID_BACKUPS + 1))
        echo "  Status: VALID (tar integrity verified)" >> "$LOG_FILE"
      else
        error "Backup corrupted (invalid tar): $backup_name"
        FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
        echo "  Status: FAILED (tar corruption detected)" >> "$LOG_FILE"
      fi
    elif [[ "$backup_file" == *.gz ]]; then
      if gzip -t "$backup_file" 2>/dev/null; then
        success "Backup verified: $backup_name (size: $file_size bytes, age: $file_age_hours hours)"
        VALID_BACKUPS=$((VALID_BACKUPS + 1))
        echo "  Status: VALID (gzip integrity verified)" >> "$LOG_FILE"
      else
        error "Backup corrupted (invalid gzip): $backup_name"
        FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
        echo "  Status: FAILED (gzip corruption detected)" >> "$LOG_FILE"
      fi
    elif [[ "$backup_file" == *.rdb ]]; then
      # RDB files don't have a simple integrity check, just verify readable
      if [ -r "$backup_file" ]; then
        success "Backup verified: $backup_name (size: $file_size bytes, age: $file_age_hours hours)"
        VALID_BACKUPS=$((VALID_BACKUPS + 1))
        echo "  Status: VALID (readable)" >> "$LOG_FILE"
      else
        error "Backup not readable: $backup_file"
        FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
        echo "  Status: FAILED (not readable)" >> "$LOG_FILE"
      fi
    else
      info "Backup file type not recognized, skipping integrity check: $backup_name"
      echo "  Status: SKIPPED (unknown format)" >> "$LOG_FILE"
    fi

    echo "" >> "$LOG_FILE"
  fi
done < <(find "$BACKUP_DIR" -type f \
  \( -name 'l30_backup_*.sql.gz.age' -o -name 'l30_backup_*.sql.gz' \
     -o -name '*.tar.gz' -o -name '*.rdb' \) -print0)

# Freshness applies to the backup set, not every retained historical archive.
# Verify integrity for all retained files above, then require only the newest
# database backup to be no older than MAX_BACKUP_AGE_HOURS.
latest_backup=$(find "$BACKUP_DIR" -type f \
  \( -name 'l30_backup_*.sql.gz.age' -o -name 'l30_backup_*.sql.gz' \) \
  -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)
if [ -z "$latest_backup" ]; then
  error "No L30 database backup archives found"
  FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
else
  latest_mtime=$(stat -c%Y "$latest_backup")
  latest_age_hours=$(( (CURRENT_TIME - latest_mtime) / 3600 ))
  if [ "$latest_age_hours" -gt "$MAX_BACKUP_AGE_HOURS" ]; then
    warning "Latest backup is stale: $(basename "$latest_backup") (${latest_age_hours} hours old, max: $MAX_BACKUP_AGE_HOURS)"
    WARNING_BACKUPS=$((WARNING_BACKUPS + 1))
  fi
fi

# ----------------------------------------------------------------------------
# Off-site replication check (optional, gated by BACKUP_RCLONE_REMOTE)
# Confirms the latest local backup exists on the remote with matching size.
# Sourced from .env.prod so cron picks up the same config the backup script uses.
# ----------------------------------------------------------------------------
if [ -f /opt/l30/.env.prod ]; then
  set -a
  # shellcheck disable=SC1091
  source /opt/l30/.env.prod
  set +a
fi

if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
  DEST_PATH="${BACKUP_RCLONE_PATH:-l30-backups/daily}"
  latest_local=$(find "$BACKUP_DIR/daily" \( -name "l30_backup_*.sql.gz" -o -name "l30_backup_*.sql.gz.age" \) -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | awk '{print $2}')
  if [ -z "$latest_local" ]; then
    warning "Off-site check skipped: no local backup found to compare against"
  else
    latest_name=$(basename "$latest_local")
    local_size=$(stat -c%s "$latest_local" 2>/dev/null)
    remote_size=$(rclone size --json "${BACKUP_RCLONE_REMOTE}:${DEST_PATH}/${latest_name}" 2>/dev/null | sed -n 's/.*"bytes":\([0-9]*\).*/\1/p')
    if [ -z "$remote_size" ] || [ "$remote_size" = "0" ]; then
      error "Off-site replication: latest backup not found on ${BACKUP_RCLONE_REMOTE}:${DEST_PATH}/${latest_name}"
      FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
    elif [ "$local_size" != "$remote_size" ]; then
      error "Off-site replication: size mismatch for $latest_name (local: $local_size, remote: $remote_size)"
      FAILED_BACKUPS=$((FAILED_BACKUPS + 1))
    else
      success "Off-site replication verified: $latest_name on ${BACKUP_RCLONE_REMOTE}:${DEST_PATH}/ ($local_size bytes)"
    fi
  fi
fi

# Verification summary
{
  echo "=========================================="
  echo "Backup Verification Summary"
  echo "=========================================="
  echo "Total Backups: $TOTAL_BACKUPS"
  echo "Valid Backups: $VALID_BACKUPS"
  echo "Failed Backups: $FAILED_BACKUPS"
  echo "Stale Backups: $WARNING_BACKUPS"
  echo "Total Backup Size: $(du -sh "$BACKUP_DIR" | awk '{print $1}')"
  echo "Verification Time: $(date)"
  echo ""
} >> "$LOG_FILE"

# Determine overall status
overall_status="good"
status_message="All backups verified successfully. Valid: $VALID_BACKUPS, Warnings: $WARNING_BACKUPS, Failures: $FAILED_BACKUPS"

if [ "$FAILED_BACKUPS" -gt 0 ]; then
  overall_status="error"
  status_message="Backup verification FAILED. Valid: $VALID_BACKUPS, Warnings: $WARNING_BACKUPS, Failures: $FAILED_BACKUPS"
  error "Backup verification completed with $FAILED_BACKUPS failure(s)"
elif [ "$WARNING_BACKUPS" -gt 0 ]; then
  overall_status="warning"
  status_message="Backup verification completed with warnings. Valid: $VALID_BACKUPS, Warnings: $WARNING_BACKUPS, Failures: $FAILED_BACKUPS"
  warning "Backup verification completed with $WARNING_BACKUPS warning(s)"
else
  success "Backup verification completed successfully"
fi

# Send notification
send_slack_notification "$overall_status" "$status_message"

# Log footer
{
  echo "=========================================="
  echo ""
} >> "$LOG_FILE"

# Exit with appropriate code
if [ "$FAILED_BACKUPS" -gt "$ALERT_THRESHOLD" ]; then
  exit 1
else
  exit 0
fi
