#!/bin/bash
# ==============================================================================
# Alembic Migration Deployment Script
# ==============================================================================
# This script safely runs Alembic migrations with comprehensive error handling,
# logging, and verification.
#
# Usage:
#   ./migrate.sh [options]
#
# Options:
#   --dry-run          Show what would be migrated without applying
#   --target REVISION  Migrate to specific revision (default: head)
#   --skip-verification Skip post-migration verification
#   --no-backup        Skip pre-migration backup (not recommended)
#
# Exit Codes:
#   0 - Success
#   1 - Migration failed
#   2 - Verification failed
#   3 - Database connection failed
#   4 - Pre-migration backup failed
# ==============================================================================

set -euo pipefail

# ==============================================================================
# Configuration
# ==============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKEND_DIR="${PROJECT_ROOT}/backend"
LOG_DIR="${PROJECT_ROOT}/logs/migrations"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${LOG_DIR}/migration_${TIMESTAMP}.log"

# Migration settings
DRY_RUN=false
TARGET_REVISION="head"
SKIP_VERIFICATION=false
NO_BACKUP=false
MAX_RETRIES=3
RETRY_DELAY=5

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ==============================================================================
# Helper Functions
# ==============================================================================

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $@" | tee -a "${LOG_FILE}"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $@" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@" | tee -a "${LOG_FILE}"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if running in correct directory
    if [[ ! -f "${BACKEND_DIR}/alembic.ini" ]]; then
        log_error "alembic.ini not found in ${BACKEND_DIR}"
        exit 1
    fi

    # Check database connection
    if ! check_db_connection; then
        log_error "Cannot connect to database"
        exit 3
    fi

    # Check if alembic is installed
    if ! command -v alembic &> /dev/null; then
        log_error "Alembic is not installed. Install with: pip install alembic"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

check_db_connection() {
    log_info "Testing database connection..."

    cd "${BACKEND_DIR}"

    # Try to connect using alembic
    local retry_count=0
    while [[ $retry_count -lt $MAX_RETRIES ]]; do
        if python -c "
from alembic import context
from alembic.config import Config
import sys

config = Config('alembic.ini')
sys.path.insert(0, '.')

try:
    from app.core.database import get_sync_engine
    engine = get_sync_engine()
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('Connection successful')
    sys.exit(0)
except Exception as e:
    print(f'Connection failed: {e}')
    sys.exit(1)
" 2>&1 | tee -a "${LOG_FILE}"; then
            log_success "Database connection verified"
            return 0
        fi

        retry_count=$((retry_count + 1))
        if [[ $retry_count -lt $MAX_RETRIES ]]; then
            log_warning "Connection attempt ${retry_count}/${MAX_RETRIES} failed. Retrying in ${RETRY_DELAY}s..."
            sleep $RETRY_DELAY
        fi
    done

    log_error "Failed to connect to database after ${MAX_RETRIES} attempts"
    return 1
}

get_current_revision() {
    cd "${BACKEND_DIR}"
    local current=$(alembic current 2>&1 | grep -oP '(?<=Rev: )[a-f0-9_]+' || echo "none")
    echo "$current"
}

get_pending_migrations() {
    cd "${BACKEND_DIR}"
    alembic history -r current:head 2>/dev/null | grep -c "^Rev:" || echo "0"
}

backup_database() {
    if [[ "$NO_BACKUP" == "true" ]]; then
        log_warning "Skipping database backup (--no-backup flag)"
        return 0
    fi

    log_info "Creating pre-migration backup..."

    local backup_script="${SCRIPT_DIR}/backup-migration.sh"
    if [[ ! -f "$backup_script" ]]; then
        log_warning "Backup script not found at ${backup_script}. Skipping backup."
        return 0
    fi

    if bash "${backup_script}" "${TIMESTAMP}"; then
        log_success "Backup created successfully"
        return 0
    else
        log_error "Backup failed"
        return 4
    fi
}

show_migration_plan() {
    log_info "Migration Plan:"
    echo "=================================================================================" | tee -a "${LOG_FILE}"

    cd "${BACKEND_DIR}"

    local current_rev=$(get_current_revision)
    log_info "Current Revision: ${current_rev}"

    local pending_count=$(get_pending_migrations)
    log_info "Pending Migrations: ${pending_count}"

    if [[ "$pending_count" == "0" ]]; then
        log_success "Database is already up to date!"
        return 1
    fi

    echo "" | tee -a "${LOG_FILE}"
    log_info "Migrations to be applied:"
    alembic history -r current:${TARGET_REVISION} 2>&1 | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"

    return 0
}

run_migrations() {
    log_info "Starting migration to revision: ${TARGET_REVISION}"

    cd "${BACKEND_DIR}"

    # Record start time
    local start_time=$(date +%s)

    # Run the migration
    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "DRY RUN - Migration commands that would be executed:"
        alembic upgrade ${TARGET_REVISION} --sql 2>&1 | tee -a "${LOG_FILE}"
        log_success "Dry run completed"
        return 0
    else
        log_info "Executing migrations..."
        if alembic upgrade ${TARGET_REVISION} 2>&1 | tee -a "${LOG_FILE}"; then
            local end_time=$(date +%s)
            local duration=$((end_time - start_time))
            log_success "Migrations applied successfully in ${duration} seconds"
            return 0
        else
            log_error "Migration failed"
            return 1
        fi
    fi
}

verify_migrations() {
    if [[ "$SKIP_VERIFICATION" == "true" ]]; then
        log_warning "Skipping post-migration verification (--skip-verification flag)"
        return 0
    fi

    log_info "Running post-migration verification..."

    local verification_script="${SCRIPT_DIR}/verify-migrations.sh"
    if [[ ! -f "$verification_script" ]]; then
        log_warning "Verification script not found at ${verification_script}. Skipping verification."
        return 0
    fi

    if bash "${verification_script}"; then
        log_success "Migration verification passed"
        return 0
    else
        log_error "Migration verification failed"
        return 2
    fi
}

record_migration_metrics() {
    log_info "Recording migration metrics..."

    local metrics_file="${LOG_DIR}/metrics.json"
    local current_rev=$(get_current_revision)

    cat > "${metrics_file}" << EOF
{
    "timestamp": "${TIMESTAMP}",
    "revision": "${current_rev}",
    "target_revision": "${TARGET_REVISION}",
    "duration_seconds": ${1:-0},
    "success": ${2:-false},
    "log_file": "${LOG_FILE}"
}
EOF

    log_info "Metrics recorded to ${metrics_file}"
}

# ==============================================================================
# Parse Command Line Arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --target)
                TARGET_REVISION="$2"
                shift 2
                ;;
            --skip-verification)
                SKIP_VERIFICATION=true
                shift
                ;;
            --no-backup)
                NO_BACKUP=true
                shift
                ;;
            -h|--help)
                cat << EOF
Alembic Migration Deployment Script

Usage: $0 [options]

Options:
    --dry-run              Show what would be migrated without applying
    --target REVISION      Migrate to specific revision (default: head)
    --skip-verification    Skip post-migration verification
    --no-backup           Skip pre-migration backup (not recommended)
    -h, --help            Show this help message

Examples:
    $0                                    # Migrate to latest
    $0 --dry-run                          # Preview migrations
    $0 --target 005                       # Migrate to specific revision
    $0 --no-backup --skip-verification    # Fast migration (risky)

Exit Codes:
    0 - Success
    1 - Migration failed
    2 - Verification failed
    3 - Database connection failed
    4 - Pre-migration backup failed
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    local start_time=$(date +%s)

    # Create log directory
    mkdir -p "${LOG_DIR}"

    echo "=================================================================================" | tee "${LOG_FILE}"
    echo "  Alembic Migration Deployment" | tee -a "${LOG_FILE}"
    echo "  Started: $(date)" | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"
    echo "" | tee -a "${LOG_FILE}"

    # Parse arguments
    parse_args "$@"

    # Run migration workflow
    check_prerequisites

    if ! show_migration_plan; then
        exit 0  # Already up to date
    fi

    # Confirm if not dry-run
    if [[ "$DRY_RUN" == "false" ]]; then
        echo "" | tee -a "${LOG_FILE}"
        read -p "Proceed with migration? (yes/no): " -r
        echo "" | tee -a "${LOG_FILE}"
        if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
            log_info "Migration cancelled by user"
            exit 0
        fi
    fi

    # Create backup
    backup_database

    # Run migrations
    if ! run_migrations; then
        log_error "Migration failed - check logs at ${LOG_FILE}"
        record_migration_metrics 0 false
        exit 1
    fi

    # Verify migrations
    if ! verify_migrations; then
        log_error "Migration verification failed - check logs at ${LOG_FILE}"
        record_migration_metrics 0 false
        exit 2
    fi

    # Calculate duration and record metrics
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    record_migration_metrics $total_duration true

    echo "" | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"
    log_success "Migration completed successfully in ${total_duration} seconds"
    log_info "Current revision: $(get_current_revision)"
    log_info "Log file: ${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"

    exit 0
}

# Run main function
main "$@"
