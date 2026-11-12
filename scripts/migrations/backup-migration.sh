#!/bin/bash
# ==============================================================================
# Database Backup Script for Migrations
# ==============================================================================
# Creates timestamped database backups before migrations.
#
# Usage:
#   ./backup-migration.sh [backup_label]
#
# Arguments:
#   backup_label - Optional label for backup (default: migration_TIMESTAMP)
#
# Exit Codes:
#   0 - Success
#   1 - Backup failed
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups/migrations"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_LABEL="${1:-migration_${TIMESTAMP}}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $@"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@"
}

get_db_credentials() {
    # Extract database credentials from DATABASE_URL
    if [[ -z "${DATABASE_URL:-}" ]]; then
        log_error "DATABASE_URL environment variable not set"
        return 1
    fi

    # Parse DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/dbname
    DB_URL="${DATABASE_URL}"
    DB_URL="${DB_URL#postgresql+asyncpg://}"
    DB_URL="${DB_URL#postgresql://}"

    # Extract components
    DB_USER=$(echo "$DB_URL" | cut -d: -f1)
    DB_PASS=$(echo "$DB_URL" | cut -d: -f2 | cut -d@ -f1)
    DB_HOST=$(echo "$DB_URL" | cut -d@ -f2 | cut -d: -f1)
    DB_PORT=$(echo "$DB_URL" | cut -d: -f3 | cut -d/ -f1)
    DB_NAME=$(echo "$DB_URL" | cut -d/ -f2 | cut -d? -f1)

    export PGPASSWORD="$DB_PASS"
}

create_backup() {
    local backup_file="${BACKUP_DIR}/${BACKUP_LABEL}.sql.gz"

    log_info "Creating database backup..."
    log_info "Database: ${DB_NAME}"
    log_info "Backup file: ${backup_file}"

    # Create backup directory
    mkdir -p "${BACKUP_DIR}"

    # Create backup with pg_dump
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --format=plain \
        --no-owner \
        --no-acl \
        --clean \
        --if-exists \
        | gzip > "$backup_file"; then

        local backup_size=$(du -h "$backup_file" | cut -f1)
        log_success "Backup created successfully (${backup_size})"

        # Create metadata file
        create_metadata "$backup_file"

        return 0
    else
        log_error "Backup failed"
        return 1
    fi
}

create_metadata() {
    local backup_file="$1"
    local metadata_file="${backup_file}.meta"

    cat > "$metadata_file" << EOF
{
    "backup_label": "${BACKUP_LABEL}",
    "timestamp": "${TIMESTAMP}",
    "database": "${DB_NAME}",
    "host": "${DB_HOST}",
    "port": "${DB_PORT}",
    "size_bytes": $(stat -f%z "$backup_file" 2>/dev/null || stat -c%s "$backup_file" 2>/dev/null),
    "created_by": "backup-migration.sh"
}
EOF

    log_info "Metadata saved to ${metadata_file}"
}

cleanup_old_backups() {
    log_info "Cleaning up old backups (keeping last 10)..."

    cd "${BACKUP_DIR}"

    # Keep only the 10 most recent backups
    ls -t *.sql.gz 2>/dev/null | tail -n +11 | while read -r old_backup; do
        rm -f "$old_backup" "${old_backup}.meta"
        log_info "Removed old backup: $old_backup"
    done
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    echo "================================================================================="
    echo "  Database Backup for Migration"
    echo "  Started: $(date)"
    echo "================================================================================="
    echo ""

    # Load database credentials
    if ! get_db_credentials; then
        log_error "Failed to get database credentials"
        exit 1
    fi

    # Create backup
    if ! create_backup; then
        log_error "Backup failed"
        exit 1
    fi

    # Cleanup old backups
    cleanup_old_backups

    echo ""
    echo "================================================================================="
    log_success "Backup completed successfully"
    echo "================================================================================="

    exit 0
}

main "$@"
