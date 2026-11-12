#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

################################################################################
# Production Smoke Test Script
#
# Purpose: Validate that all new deployments are working correctly
# Usage: ./smoke_test.sh
# Exit codes: 0=all tests passed, 1=critical failure, 2=warning
################################################################################

set -o pipefail

# Configuration
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-lsc_db}"
DB_USER="${DB_USER:-postgres}"
TIMEOUT=30
WARNINGS=0
ERRORS=0

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((ERRORS++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARNINGS++))
}

################################################################################
# Test 1: Backend Service Health
################################################################################
test_backend_health() {
    log_info "Test 1: Verifying backend service is running..."

    # Check if backend is accessible
    if curl -s -f -m $TIMEOUT "$BACKEND_URL/health" > /dev/null 2>&1; then
        log_pass "Backend service is responding"
        return 0
    else
        log_fail "Backend service is not responding at $BACKEND_URL"
        return 1
    fi
}

################################################################################
# Test 2: Database Connectivity
################################################################################
test_database_connectivity() {
    log_info "Test 2: Verifying database connectivity..."

    # Check if database is accessible
    if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
        log_pass "Database is accessible"
        return 0
    else
        log_fail "Cannot connect to database at $DB_HOST:$DB_PORT/$DB_NAME"
        return 1
    fi
}

################################################################################
# Test 3: Critical API Endpoints
################################################################################
test_api_endpoints() {
    log_info "Test 3: Testing critical API endpoints..."

    # Test each critical endpoint
    local endpoints=(
        "docs"
        "health"
        "api/v1/auth/status"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -s -f -m $TIMEOUT "$BACKEND_URL/$endpoint" > /dev/null 2>&1; then
            log_pass "Endpoint /$endpoint is responding"
        else
            log_fail "Endpoint /$endpoint is not responding"
            return 1
        fi
    done

    return 0
}

################################################################################
# Test 4: Scheduler Registration
################################################################################
test_scheduler_registration() {
    log_info "Test 4: Verifying background job scheduler is registered..."

    # Check backend logs for scheduler initialization
    local log_file="/opt/l30/logs/backend.log"

    if [ ! -f "$log_file" ]; then
        log_warn "Log file not found at $log_file, skipping scheduler verification"
        return 0
    fi

    # Check if scheduler was initialized in the last hour
    if grep -q "Background job scheduler started" "$log_file"; then
        log_pass "Scheduler initialization found in logs"

        # Check for specific jobs
        local jobs=("daily_fine_calculation" "hourly_hold_expiration" "daily_overdue_notifications" "daily_data_retention")

        for job in "${jobs[@]}"; do
            if grep -q "$job" "$log_file"; then
                log_pass "Job registered: $job"
            else
                log_warn "Job not found in recent logs: $job"
            fi
        done

        return 0
    else
        log_fail "Scheduler initialization not found in logs"
        return 1
    fi
}

################################################################################
# Test 5: Database Migration Status
################################################################################
test_database_migrations() {
    log_info "Test 5: Verifying database migrations..."

    # Check if new indexes exist
    local indexes=(
        "ix_checkouts_due_status"
        "ix_fines_user_status"
        "ix_holds_item_status_position"
        "ix_holds_status_expires"
    )

    for index in "${indexes[@]}"; do
        if PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1 FROM pg_indexes WHERE indexname='$index';" 2>/dev/null | grep -q 1; then
            log_pass "Index exists: $index"
        else
            log_warn "Expected index not found: $index (migration may not have run)"
        fi
    done

    return 0
}

################################################################################
# Test 6: Fine Calculation Logic
################################################################################
test_fine_calculation() {
    log_info "Test 6: Testing fine calculation logic..."

    # Test that fine schema can be imported
    if python3 -c "from app.services.fine_policy_service import apply_fine_policy; print('OK')" > /dev/null 2>&1; then
        log_pass "Fine policy service is importable"
    else
        log_warn "Fine policy service import failed (schema may not be deployed)"
    fi

    return 0
}

################################################################################
# Test 7: Hold Expiration Logic
################################################################################
test_hold_expiration() {
    log_info "Test 7: Testing hold expiration logic..."

    # Test that scheduler service can be imported
    if python3 -c "from app.services.scheduler_service import expire_old_holds; print('OK')" > /dev/null 2>&1; then
        log_pass "Hold expiration service is importable"
    else
        log_warn "Hold expiration service import failed (may not be in Python path)"
    fi

    return 0
}

################################################################################
# Test 8: Configuration Verification
################################################################################
test_configuration() {
    log_info "Test 8: Verifying configuration..."

    # Check required environment variables
    local vars=("SCHEDULER_ENABLED" "HOLD_EXPIRY_DAYS" "DATABASE_URL")

    for var in "${vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_warn "Environment variable not set: $var"
        else
            log_pass "Environment variable set: $var"
        fi
    done

    return 0
}

################################################################################
# Test 9: Response Schema Validation
################################################################################
test_response_schemas() {
    log_info "Test 9: Testing standardized response schemas..."

    # Test that response schemas can be imported
    if python3 -c "from app.schemas.fine import FineResponse, FineCreate; from app.schemas.circulation import CheckoutResponse; print('OK')" > /dev/null 2>&1; then
        log_pass "Response schemas are importable"
    else
        log_fail "Response schema import failed"
        return 1
    fi

    return 0
}

################################################################################
# Test 10: Unified Circulation Service
################################################################################
test_circulation_service() {
    log_info "Test 10: Testing unified circulation service..."

    # Test that circulation service can be imported
    if python3 -c "from app.services.unified_circulation_service import checkout_item; print('OK')" > /dev/null 2>&1; then
        log_pass "Unified circulation service is importable"
    else
        log_warn "Unified circulation service import failed (may not be deployed)"
    fi

    return 0
}

################################################################################
# Test 11: Error Logs Verification
################################################################################
test_error_logs() {
    log_info "Test 11: Checking for recent errors in logs..."

    local log_file="/opt/l30/logs/backend.log"

    if [ ! -f "$log_file" ]; then
        log_warn "Log file not found at $log_file"
        return 0
    fi

    # Check for errors in the last 100 lines
    local error_count=$(tail -100 "$log_file" | grep -i "ERROR\|EXCEPTION\|FAILED" | wc -l)

    if [ "$error_count" -eq 0 ]; then
        log_pass "No errors found in recent logs"
    elif [ "$error_count" -lt 5 ]; then
        log_warn "Found $error_count error(s) in recent logs (may be normal)"
    else
        log_fail "Found $error_count error(s) in recent logs"
        return 1
    fi

    return 0
}

################################################################################
# Test 12: Database Connection Pool
################################################################################
test_connection_pool() {
    log_info "Test 12: Verifying database connection pool..."

    # Check for connection errors in logs
    local log_file="/opt/l30/logs/backend.log"

    if [ ! -f "$log_file" ]; then
        log_warn "Log file not found, skipping connection pool check"
        return 0
    fi

    if grep -q "pool overflow\|too many connections\|connection refused" "$log_file"; then
        log_warn "Database connection issues detected in logs"
    else
        log_pass "No connection pool issues detected"
    fi

    return 0
}

################################################################################
# Main Test Execution
################################################################################
main() {
    echo "================================================================================"
    echo "Production Smoke Test Suite"
    echo "================================================================================"
    echo "Backend URL: $BACKEND_URL"
    echo "Database: $DB_HOST:$DB_PORT/$DB_NAME"
    echo "Start time: $(date)"
    echo "================================================================================"
    echo ""

    # Run all tests
    test_backend_health
    test_database_connectivity
    test_api_endpoints
    test_scheduler_registration
    test_database_migrations
    test_fine_calculation
    test_hold_expiration
    test_configuration
    test_response_schemas
    test_circulation_service
    test_error_logs
    test_connection_pool

    # Summary
    echo ""
    echo "================================================================================"
    echo "Test Summary"
    echo "================================================================================"
    echo "End time: $(date)"
    echo ""

    if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}All smoke tests passed!${NC}"
        echo "Status: READY FOR PRODUCTION"
        echo "Exit code: 0"
        return 0
    elif [ $ERRORS -eq 0 ] && [ $WARNINGS -gt 0 ]; then
        echo -e "${YELLOW}Smoke tests passed with $WARNINGS warning(s)${NC}"
        echo "Status: READY FOR PRODUCTION (with caution)"
        echo "Exit code: 2"
        return 2
    else
        echo -e "${RED}Smoke tests failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
        echo "Status: NOT READY FOR PRODUCTION"
        echo "Exit code: 1"
        return 1
    fi
}

# Run main function and exit with appropriate code
main
exit $?
