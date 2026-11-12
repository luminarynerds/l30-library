#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

################################################################################
# Docker Health Check Script
#
# Purpose: Comprehensive Docker health verification for all services
#
# Usage: ./docker-health-check.sh [--verbose] [--timeout SECONDS]
#
# Exit codes:
#   0 = all services healthy
#   1 = one or more services unhealthy
#   2 = services not running
################################################################################

set -euo pipefail

# Configuration
TIMEOUT=${TIMEOUT:-120}
VERBOSE=false
CHECK_INTERVAL=5

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

################################################################################
# Utility Functions
################################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
}

log_verbose() {
    if [ "$VERBOSE" = true ]; then
        echo -e "${BLUE}[DEBUG]${NC} $1"
    fi
}

################################################################################
# Container Health Checks
################################################################################

check_container_running() {
    local container_name=$1

    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        log_verbose "Container $container_name is running"
        return 0
    else
        log_error "Container $container_name is not running"
        return 1
    fi
}

check_container_health() {
    local container_name=$1
    local max_wait=${2:-$TIMEOUT}

    log_info "Checking health of $container_name (timeout: ${max_wait}s)..."

    local elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        local health_status=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")

        case "$health_status" in
            "healthy")
                log_success "$container_name is healthy"
                return 0
                ;;
            "unhealthy")
                log_error "$container_name is unhealthy"
                if [ "$VERBOSE" = true ]; then
                    docker logs --tail 20 "$container_name" 2>&1 | sed 's/^/  /'
                fi
                return 1
                ;;
            "starting")
                log_verbose "$container_name is starting... (${elapsed}s elapsed)"
                ;;
            "none")
                log_warn "$container_name has no healthcheck defined"
                return 0
                ;;
            *)
                log_verbose "$container_name status: $health_status (${elapsed}s elapsed)"
                ;;
        esac

        sleep $CHECK_INTERVAL
        elapsed=$((elapsed + CHECK_INTERVAL))
    done

    log_error "$container_name failed to become healthy within ${max_wait}s"
    return 1
}

################################################################################
# Service-Specific Checks
################################################################################

check_database_service() {
    log_info "Verifying database service..."

    if ! check_container_running "lsc-database"; then
        return 1
    fi

    if ! check_container_health "lsc-database" 30; then
        return 1
    fi

    # Test database connectivity
    if docker exec lsc-database pg_isready -U lsc -d lsc_library &> /dev/null; then
        log_success "Database accepting connections"
    else
        log_error "Database not accepting connections"
        return 1
    fi

    # Check if pgvector extension is loaded
    if docker exec lsc-database psql -U lsc -d lsc_library -c "SELECT * FROM pg_extension WHERE extname='vector';" 2>/dev/null | grep -q vector; then
        log_success "pgvector extension is loaded"
    else
        log_warn "pgvector extension not found"
    fi

    return 0
}

check_redis_service() {
    log_info "Verifying Redis service..."

    if ! check_container_running "lsc-redis"; then
        return 1
    fi

    if ! check_container_health "lsc-redis" 30; then
        return 1
    fi

    # Test Redis connectivity (with password)
    local redis_password="${REDIS_PASSWORD:-}"
    if [ -n "$redis_password" ]; then
        if docker exec lsc-redis redis-cli -a "$redis_password" ping 2>/dev/null | grep -q PONG; then
            log_success "Redis responding to PING"
        else
            log_error "Redis not responding"
            return 1
        fi
    else
        log_warn "REDIS_PASSWORD not set, skipping authenticated ping"
    fi

    return 0
}

check_backend_service() {
    log_info "Verifying backend service..."

    if ! check_container_running "lsc-backend"; then
        return 1
    fi

    if ! check_container_health "lsc-backend" 60; then
        return 1
    fi

    # Test health endpoint
    if docker exec lsc-backend curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        log_success "Backend /health endpoint responding"
    else
        log_error "Backend /health endpoint not responding"
        return 1
    fi

    # Test API docs
    if docker exec lsc-backend curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
        log_success "Backend /docs endpoint accessible"
    else
        log_warn "Backend /docs endpoint not accessible"
    fi

    # Test database connection from backend
    if docker exec lsc-backend curl -sf http://localhost:8000/api/v1/auth/status > /dev/null 2>&1; then
        log_success "Backend can connect to database"
    else
        log_warn "Backend may have database connectivity issues"
    fi

    return 0
}

check_frontend_service() {
    log_info "Verifying frontend service..."

    if ! check_container_running "lsc-frontend"; then
        return 1
    fi

    if ! check_container_health "lsc-frontend" 30; then
        return 1
    fi

    # Test frontend is serving
    if docker exec lsc-frontend curl -sf http://localhost:80 > /dev/null 2>&1; then
        log_success "Frontend serving content"
    else
        log_error "Frontend not serving content"
        return 1
    fi

    return 0
}

check_nginx_service() {
    log_info "Verifying nginx service..."

    if ! check_container_running "lsc-nginx"; then
        return 1
    fi

    # Nginx typically doesn't have a healthcheck, so just verify it's running
    log_success "Nginx container is running"

    # Test nginx configuration
    if docker exec lsc-nginx nginx -t &> /dev/null; then
        log_success "Nginx configuration is valid"
    else
        log_error "Nginx configuration has errors"
        return 1
    fi

    return 0
}

################################################################################
# Integration Tests
################################################################################

test_end_to_end_flow() {
    log_info "Running end-to-end integration test..."

    # Test that requests flow through nginx -> backend -> database
    local test_url="http://localhost/api/v1/health"

    if command -v curl &> /dev/null; then
        if curl -sf "$test_url" -m 10 > /dev/null 2>&1; then
            log_success "End-to-end flow: nginx -> backend -> response OK"
            return 0
        else
            log_error "End-to-end flow failed"
            return 1
        fi
    else
        log_warn "curl not available, skipping E2E test"
        return 0
    fi
}

check_resource_usage() {
    log_info "Checking container resource usage..."

    # Get container stats
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
        lsc-database lsc-redis lsc-backend lsc-frontend lsc-nginx 2>/dev/null || {
        log_warn "Could not retrieve container stats"
        return 0
    }

    return 0
}

################################################################################
# Main Function
################################################################################

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --timeout)
                TIMEOUT=$2
                shift 2
                ;;
            --help|-h)
                cat <<EOF
Usage: $0 [OPTIONS]

Options:
    --verbose, -v       Enable verbose output
    --timeout SECONDS   Set timeout for health checks (default: 120)
    --help, -h          Show this help message

Examples:
    $0                      # Run with default settings
    $0 --verbose            # Run with detailed output
    $0 --timeout 180        # Wait up to 3 minutes for services
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

main() {
    parse_args "$@"

    echo "========================================"
    echo "Docker Health Check"
    echo "========================================"
    echo "Timeout: ${TIMEOUT}s"
    echo "Verbose: $VERBOSE"
    echo "========================================"
    echo ""

    local failed=0

    # Check all services
    check_database_service || ((failed++))
    echo ""

    check_redis_service || ((failed++))
    echo ""

    check_backend_service || ((failed++))
    echo ""

    check_frontend_service || ((failed++))
    echo ""

    check_nginx_service || ((failed++))
    echo ""

    # Integration tests
    test_end_to_end_flow || ((failed++))
    echo ""

    # Resource usage
    check_resource_usage
    echo ""

    # Summary
    echo "========================================"
    echo "Health Check Summary"
    echo "========================================"

    if [ $failed -eq 0 ]; then
        log_success "All services are healthy!"
        echo "Status: READY"
        exit 0
    else
        log_error "$failed service(s) failed health checks"
        echo "Status: NOT READY"
        exit 1
    fi
}

main "$@"
