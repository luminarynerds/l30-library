#!/bin/bash
# ==============================================================================
# Auto-generate Missing Alembic Migrations
# ==============================================================================
# Automatically detects schema changes between ORM models and database,
# then generates migration files.
#
# Usage:
#   ./generate-migrations.sh [options]
#
# Options:
#   --message MSG      Custom migration message (required)
#   --autogenerate     Use alembic autogenerate (default)
#   --empty            Create empty migration file
#   --review           Review generated migration before saving
#
# Exit Codes:
#   0 - Success
#   1 - Generation failed
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

MESSAGE=""
AUTOGENERATE=true
EMPTY=false
REVIEW=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $@"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $@"
}

check_prerequisites() {
    log_info "Checking prerequisites..."

    cd "${BACKEND_DIR}"

    # Check if alembic is installed
    if ! command -v alembic &> /dev/null; then
        log_error "Alembic is not installed"
        exit 1
    fi

    # Check database connection
    if ! python -c "
import sys
sys.path.insert(0, '.')
from app.core.database import get_sync_engine
try:
    engine = get_sync_engine()
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('Connected')
except Exception as e:
    print(f'Failed: {e}')
    sys.exit(1)
" > /dev/null 2>&1; then
        log_error "Cannot connect to database"
        exit 1
    fi

    log_success "Prerequisites check passed"
}

detect_schema_changes() {
    log_info "Detecting schema changes..."

    cd "${BACKEND_DIR}"

    # Use alembic to detect changes
    local changes=$(alembic check 2>&1 || true)

    if echo "$changes" | grep -q "No new upgrade operations detected"; then
        log_info "No schema changes detected"
        return 1
    else
        log_warning "Schema changes detected:"
        echo "$changes"
        return 0
    fi
}

generate_revision_id() {
    # Generate next sequential revision ID
    cd "${BACKEND_DIR}"

    local last_revision=$(ls -1 alembic/versions/ | grep -E '^[0-9]{3}_' | sort -r | head -n1 | cut -d_ -f1 || echo "005")
    local next_number=$((10#$last_revision + 1))
    printf "%03d" $next_number
}

generate_migration() {
    log_info "Generating migration..."

    cd "${BACKEND_DIR}"

    local revision_id=$(generate_revision_id)
    local slug=$(echo "$MESSAGE" | tr '[:upper:]' '[:lower:]' | tr ' ' '_' | tr -cd '[:alnum:]_')
    local filename="${revision_id}_${slug}"

    if [[ "$EMPTY" == "true" ]]; then
        log_info "Creating empty migration: $filename"
        alembic revision -m "$MESSAGE" --rev-id "$revision_id"
    else
        log_info "Auto-generating migration: $filename"
        alembic revision --autogenerate -m "$MESSAGE" --rev-id "$revision_id"
    fi

    # Find the generated file
    local generated_file=$(ls -t alembic/versions/${revision_id}_*.py 2>/dev/null | head -n1)

    if [[ -f "$generated_file" ]]; then
        log_success "Migration generated: $generated_file"
        echo "$generated_file"
        return 0
    else
        log_error "Failed to generate migration"
        return 1
    fi
}

review_migration() {
    local migration_file="$1"

    log_info "Reviewing migration file..."
    echo "================================================================================="
    cat "$migration_file"
    echo "================================================================================="
    echo ""

    read -p "Does this migration look correct? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        log_warning "Migration rejected by user"

        # Create backup before deletion for recovery
        local backup_file="${migration_file}.rejected.backup"
        cp "$migration_file" "$backup_file"
        log_info "Migration file backed up to: $backup_file"

        rm -f "$migration_file"
        log_info "Migration file deleted (backup saved for recovery)"
        return 1
    fi

    log_success "Migration approved"
    return 0
}

validate_migration() {
    local migration_file="$1"

    log_info "Validating migration syntax..."

    cd "${BACKEND_DIR}"

    # Check Python syntax
    if ! python -m py_compile "$migration_file" 2>/dev/null; then
        log_error "Migration has syntax errors"
        return 1
    fi

    # Check if it has upgrade and downgrade functions
    if ! grep -q "def upgrade()" "$migration_file"; then
        log_error "Migration missing upgrade() function"
        return 1
    fi

    if ! grep -q "def downgrade()" "$migration_file"; then
        log_error "Migration missing downgrade() function"
        return 1
    fi

    log_success "Migration validation passed"
    return 0
}

add_migration_metadata() {
    local migration_file="$1"

    log_info "Adding migration metadata..."

    # Add helpful comments at the top
    local temp_file="${migration_file}.tmp"
    local header="\"\"\"${MESSAGE}

Generated: $(date)
Revision: $(basename "$migration_file" .py | cut -d_ -f1)

This migration was auto-generated. Please review carefully before applying.

IMPORTANT:
- Verify all schema changes are intentional
- Check for data loss operations (DROP TABLE, DROP COLUMN)
- Add data migrations if needed
- Test both upgrade() and downgrade() functions
\"\"\"

"

    # Insert header after the initial docstring
    awk -v header="$header" '
        /^""".*"""/ && !done { print; print header; done=1; next }
        { print }
    ' "$migration_file" > "$temp_file"

    mv "$temp_file" "$migration_file"

    log_success "Migration metadata added"
}

# ==============================================================================
# Parse Arguments
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --message)
                MESSAGE="$2"
                shift 2
                ;;
            --autogenerate)
                AUTOGENERATE=true
                EMPTY=false
                shift
                ;;
            --empty)
                EMPTY=true
                AUTOGENERATE=false
                shift
                ;;
            --review)
                REVIEW=true
                shift
                ;;
            -h|--help)
                cat << EOF
Auto-generate Missing Alembic Migrations

Usage: $0 --message "description" [options]

Options:
    --message MSG      Custom migration message (required)
    --autogenerate     Use alembic autogenerate (default)
    --empty            Create empty migration file
    --review           Review generated migration before saving
    -h, --help         Show this help message

Examples:
    $0 --message "add user email column"
    $0 --message "create notifications table" --review
    $0 --message "custom data migration" --empty

The script will:
1. Detect schema changes between ORM and database
2. Generate sequential revision ID
3. Create migration file with proper structure
4. Validate syntax
5. Optionally review before finalizing

Exit Codes:
    0 - Success
    1 - Generation failed
EOF
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate required arguments
    if [[ -z "$MESSAGE" ]]; then
        log_error "Migration message is required (use --message)"
        exit 1
    fi
}

# ==============================================================================
# Main Execution
# ==============================================================================

main() {
    mkdir -p "${LOG_DIR}"

    echo "================================================================================="
    echo "  Auto-generate Alembic Migration"
    echo "  Started: $(date)"
    echo "================================================================================="
    echo ""

    parse_args "$@"

    # Check prerequisites
    check_prerequisites

    # Detect schema changes (informational)
    if detect_schema_changes; then
        log_info "Schema changes will be captured in migration"
    else
        log_warning "No automatic schema changes detected"
        if [[ "$EMPTY" == "false" ]]; then
            log_warning "Consider using --empty for manual migrations"
        fi
    fi

    # Generate migration
    local migration_file=$(generate_migration)

    if [[ -z "$migration_file" ]]; then
        log_error "Failed to generate migration file"
        exit 1
    fi

    # Validate migration
    if ! validate_migration "$migration_file"; then
        log_error "Migration validation failed"
        exit 1
    fi

    # Add metadata
    add_migration_metadata "$migration_file"

    # Review if requested
    if [[ "$REVIEW" == "true" ]]; then
        if ! review_migration "$migration_file"; then
            log_warning "Migration generation cancelled"
            exit 1
        fi
    fi

    # Summary
    echo ""
    echo "================================================================================="
    log_success "Migration generated successfully!"
    echo ""
    log_info "Migration file: $migration_file"
    log_info "Revision ID: $(basename "$migration_file" .py | cut -d_ -f1)"
    echo ""
    log_info "Next steps:"
    log_info "  1. Review the migration: cat $migration_file"
    log_info "  2. Test the migration: ./migrate.sh --dry-run"
    log_info "  3. Apply the migration: ./migrate.sh"
    echo "================================================================================="

    exit 0
}

main "$@"
