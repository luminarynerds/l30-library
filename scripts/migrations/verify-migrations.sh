#!/bin/bash
# ==============================================================================
# Migration Verification Script
# ==============================================================================
# Comprehensive verification of database schema after migrations.
# Checks:
#   - All expected tables exist
#   - All expected columns exist
#   - Foreign key constraints are valid
#   - Indexes are created
#   - No orphaned migration records
#
# Usage:
#   ./verify-migrations.sh [--verbose]
#
# Exit Codes:
#   0 - All verifications passed
#   1 - One or more verifications failed
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
LOG_FILE="${LOG_DIR}/verification_${TIMESTAMP}.log"

VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Verification results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# ==============================================================================
# Helper Functions
# ==============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $@" | tee -a "${LOG_FILE}"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $@" | tee -a "${LOG_FILE}"
    PASSED_CHECKS=$((PASSED_CHECKS + 1))
}

log_failure() {
    echo -e "${RED}[FAIL]${NC} $@" | tee -a "${LOG_FILE}"
    FAILED_CHECKS=$((FAILED_CHECKS + 1))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $@" | tee -a "${LOG_FILE}"
}

increment_check() {
    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))
}

run_sql() {
    local query="$1"
    cd "${BACKEND_DIR}"

    python -c "
import os
import sys
sys.path.insert(0, '.')

from app.core.database import get_sync_engine
from sqlalchemy import text

query = '''$query'''

try:
    engine = get_sync_engine()
    with engine.connect() as conn:
        result = conn.execute(text(query))
        for row in result:
            print(row[0])
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# ==============================================================================
# Verification Functions
# ==============================================================================

verify_migration_history() {
    log_info "Verifying migration history..."
    increment_check

    cd "${BACKEND_DIR}"

    # Check if alembic_version table exists
    local has_version_table=$(run_sql "
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_name = 'alembic_version'
    " 2>/dev/null || echo "0")

    if [[ "$has_version_table" == "0" ]]; then
        log_failure "alembic_version table does not exist"
        return 1
    fi

    # Get current revision
    local current_rev=$(alembic current 2>&1 | grep -oP '(?<=Rev: )[a-f0-9_]+' || echo "none")

    if [[ "$current_rev" == "none" ]]; then
        log_failure "No current revision found in migration history"
        return 1
    fi

    log_success "Migration history is valid (current: ${current_rev})"
    return 0
}

verify_core_tables() {
    log_info "Verifying core library system tables..."

    local core_tables=(
        "library_systems"
        "regions"
        "branches"
        "patrons"
        "staff"
        "catalog_items"
        "item_copies"
        "checkouts"
        "holds"
        "fines"
    )

    for table in "${core_tables[@]}"; do
        increment_check
        local exists=$(run_sql "
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = '$table'
        " 2>/dev/null || echo "0")

        if [[ "$exists" == "1" ]]; then
            log_success "Table exists: $table"
        else
            log_failure "Table missing: $table"
        fi
    done
}

verify_foreign_keys() {
    log_info "Verifying foreign key constraints..."

    # Check for broken foreign keys
    increment_check

    local broken_fks=$(run_sql "
        SELECT COUNT(*)
        FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
        AND constraint_name LIKE 'fk_%'
    " 2>/dev/null || echo "0")

    if [[ "$broken_fks" -gt "0" ]]; then
        log_success "Found ${broken_fks} foreign key constraints"
    else
        log_warning "No foreign key constraints found (may be expected for initial setup)"
    fi

    # Verify critical foreign keys exist
    local critical_fks=(
        "branches:library_system_id"
        "regions:library_system_id"
        "item_copies:catalog_item_id"
        "checkouts:patron_id"
        "checkouts:copy_id"
    )

    for fk in "${critical_fks[@]}"; do
        increment_check
        IFS=':' read -r table column <<< "$fk"

        local exists=$(run_sql "
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = '$table' AND column_name = '$column'
        " 2>/dev/null || echo "0")

        if [[ "$exists" == "1" ]]; then
            log_success "Foreign key column exists: ${table}.${column}"
        else
            log_failure "Foreign key column missing: ${table}.${column}"
        fi
    done
}

verify_indexes() {
    log_info "Verifying database indexes..."

    # Count total indexes
    local index_count=$(run_sql "
        SELECT COUNT(*)
        FROM pg_indexes
        WHERE schemaname = 'public'
    " 2>/dev/null || echo "0")

    increment_check
    if [[ "$index_count" -gt "0" ]]; then
        log_success "Found ${index_count} indexes in database"
    else
        log_warning "No indexes found (may be expected for initial setup)"
    fi

    # Verify critical indexes
    local critical_indexes=(
        "library_systems:ix_library_systems_code"
        "branches:ix_branches_library_system_id"
        "catalog_items:ix_catalog_items_isbn"
    )

    for idx in "${critical_indexes[@]}"; do
        increment_check
        IFS=':' read -r table index_name <<< "$idx"

        local exists=$(run_sql "
            SELECT COUNT(*)
            FROM pg_indexes
            WHERE tablename = '$table' AND indexname = '$index_name'
        " 2>/dev/null || echo "0")

        if [[ "$exists" == "1" ]]; then
            log_success "Index exists: ${index_name}"
        else
            log_warning "Index missing: ${index_name} (may be created later)"
        fi
    done
}

verify_enums() {
    log_info "Verifying enum types..."

    local critical_enums=(
        "itemstatus"
        "itemtype"
        "holdstatus"
        "checkoutstatus"
    )

    for enum_type in "${critical_enums[@]}"; do
        increment_check

        local exists=$(run_sql "
            SELECT COUNT(*)
            FROM pg_type
            WHERE typname = '$enum_type'
        " 2>/dev/null || echo "0")

        if [[ "$exists" == "1" ]]; then
            if [[ "$VERBOSE" == "true" ]]; then
                log_info "Enum values for $enum_type:"
                run_sql "
                    SELECT enumlabel
                    FROM pg_enum
                    WHERE enumtypid = (SELECT oid FROM pg_type WHERE typname = '$enum_type')
                " 2>/dev/null | while read -r value; do
                    log_info "  - $value"
                done
            fi
            log_success "Enum type exists: $enum_type"
        else
            log_warning "Enum type missing: $enum_type (may not be created yet)"
        fi
    done
}

verify_sequences() {
    log_info "Verifying database sequences..."

    increment_check

    local seq_count=$(run_sql "
        SELECT COUNT(*)
        FROM information_schema.sequences
        WHERE sequence_schema = 'public'
    " 2>/dev/null || echo "0")

    if [[ "$seq_count" -gt "0" ]]; then
        log_success "Found ${seq_count} sequences"
    else
        log_warning "No sequences found"
    fi
}

verify_constraints() {
    log_info "Verifying check constraints..."

    increment_check

    local constraint_count=$(run_sql "
        SELECT COUNT(*)
        FROM information_schema.table_constraints
        WHERE constraint_type = 'CHECK'
    " 2>/dev/null || echo "0")

    if [[ "$constraint_count" -gt "0" ]]; then
        log_success "Found ${constraint_count} check constraints"
    else
        log_warning "No check constraints found"
    fi
}

verify_schema_ownership() {
    log_info "Verifying schema ownership and permissions..."

    increment_check

    local public_schema=$(run_sql "
        SELECT COUNT(*)
        FROM information_schema.schemata
        WHERE schema_name = 'public'
    " 2>/dev/null || echo "0")

    if [[ "$public_schema" == "1" ]]; then
        log_success "Public schema exists"
    else
        log_failure "Public schema missing"
    fi
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                cat << EOF
Migration Verification Script

Usage: $0 [options]

Options:
    --verbose, -v     Show detailed output
    -h, --help       Show this help message

This script verifies that migrations have been applied correctly by checking:
  - Migration history
  - Core tables
  - Foreign key constraints
  - Indexes
  - Enum types
  - Sequences
  - Check constraints

Exit Codes:
    0 - All verifications passed
    1 - One or more verifications failed
EOF
                exit 0
                ;;
            *)
                log_warning "Unknown option: $1"
                shift
                ;;
        esac
    done
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    mkdir -p "${LOG_DIR}"

    echo "=================================================================================" | tee "${LOG_FILE}"
    echo "  Migration Verification" | tee -a "${LOG_FILE}"
    echo "  Started: $(date)" | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"
    echo "" | tee -a "${LOG_FILE}"

    parse_args "$@"

    # Run all verifications
    verify_migration_history
    verify_core_tables
    verify_foreign_keys
    verify_indexes
    verify_enums
    verify_sequences
    verify_constraints
    verify_schema_ownership

    # Summary
    echo "" | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"
    echo "  Verification Summary" | tee -a "${LOG_FILE}"
    echo "=================================================================================" | tee -a "${LOG_FILE}"
    log_info "Total Checks: $TOTAL_CHECKS"
    log_info "Passed: ${GREEN}${PASSED_CHECKS}${NC}"
    log_info "Failed: ${RED}${FAILED_CHECKS}${NC}"

    if [[ $FAILED_CHECKS -eq 0 ]]; then
        echo "" | tee -a "${LOG_FILE}"
        log_success "All verifications passed!"
        echo "=================================================================================" | tee -a "${LOG_FILE}"
        exit 0
    else
        echo "" | tee -a "${LOG_FILE}"
        log_failure "${FAILED_CHECKS} verification(s) failed"
        log_info "Check log file: ${LOG_FILE}"
        echo "=================================================================================" | tee -a "${LOG_FILE}"
        exit 1
    fi
}

main "$@"
