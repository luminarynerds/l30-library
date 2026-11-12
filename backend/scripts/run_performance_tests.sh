#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

# LSC Performance Testing Script
# Comprehensive performance testing suite for LSC with load testing, database profiling, and monitoring

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOAD_TEST_USERS=${1:-50}
LOAD_TEST_RATE=${2:-5}
LOAD_TEST_DURATION=${3:-"5m"}
OUTPUT_DIR="performance_reports_$(date +%Y%m%d_%H%M%S)"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}LSC Performance Testing Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓${NC} Output directory: $OUTPUT_DIR"

# Check dependencies
echo -e "\n${YELLOW}Checking dependencies...${NC}"
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}✗${NC} Python 3 not found"; exit 1; }
echo -e "${GREEN}✓${NC} Python 3 found"

# Test if locust is installed
if ! python3 -c "import locust" 2>/dev/null; then
    echo -e "${YELLOW}ℹ${NC} Installing locust for load testing..."
    pip install locust -q
fi

# Test if pytest is installed
if ! python3 -c "import pytest" 2>/dev/null; then
    echo -e "${YELLOW}ℹ${NC} Installing pytest for database testing..."
    pip install pytest pytest-asyncio -q
fi

echo -e "${GREEN}✓${NC} All dependencies available"

# Function to run performance tests
run_performance_tests() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}1. Running Load Performance Tests (Pytest)${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

    if [ -f "tests/test_performance_load.py" ]; then
        python3 -m pytest tests/test_performance_load.py -v -s \
            --tb=short \
            --json-report="$OUTPUT_DIR/load_test_report.json" \
            2>&1 | tee "$OUTPUT_DIR/load_test_output.txt"

        echo -e "${GREEN}✓${NC} Load performance tests completed"
    else
        echo -e "${YELLOW}⚠${NC} test_performance_load.py not found"
    fi
}

# Function to run database performance tests
run_database_tests() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}2. Running Database Performance Tests${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

    if [ -f "tests/test_performance_database.py" ]; then
        python3 -m pytest tests/test_performance_database.py -v -s \
            --tb=short \
            --json-report="$OUTPUT_DIR/database_test_report.json" \
            2>&1 | tee "$OUTPUT_DIR/database_test_output.txt"

        echo -e "${GREEN}✓${NC} Database performance tests completed"
    else
        echo -e "${YELLOW}⚠${NC} test_performance_database.py not found"
    fi
}

# Function to run load test with locust
run_locust_load_test() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}3. Running Concurrent Load Test (Locust)${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "Users: $LOAD_TEST_USERS | Spawn rate: $LOAD_TEST_RATE/sec | Duration: $LOAD_TEST_DURATION"

    if [ -f "tests/locustfile.py" ]; then
        # Start performance monitor in background
        echo -e "${YELLOW}ℹ${NC} Starting system performance monitor..."
        python3 scripts/performance_monitor.py \
            --duration 300 \
            --interval 2 \
            --output "$OUTPUT_DIR/system_metrics.json" &
        MONITOR_PID=$!

        # Run locust load test
        python3 -m locust \
            -f tests/locustfile.py \
            -u "$LOAD_TEST_USERS" \
            -r "$LOAD_TEST_RATE" \
            --run-time "$LOAD_TEST_DURATION" \
            --headless \
            --csv="$OUTPUT_DIR/locust_results" \
            http://localhost:8000 2>&1 | tee "$OUTPUT_DIR/locust_output.txt" || true

        # Wait for monitor to finish
        wait $MONITOR_PID 2>/dev/null || true

        echo -e "${GREEN}✓${NC} Locust load test completed"
    else
        echo -e "${YELLOW}⚠${NC} locustfile.py not found"
    fi
}

# Function to run API endpoint tests
run_endpoint_tests() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}4. Running API Endpoint Performance Tests${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

    # Test critical endpoints
    endpoints=(
        "/api/v1/health"
        "/api/v1/catalog?q=test&limit=20"
        "/api/v1/search/unified?q=fiction"
    )

    for endpoint in "${endpoints[@]}"; do
        echo -e "\nTesting: $endpoint"

        # Run 100 requests and measure response time
        total_time=0
        for i in {1..100}; do
            start=$(date +%s%N)
            curl -s "http://localhost:8000${endpoint}" > /dev/null 2>&1 || true
            end=$(date +%s%N)
            elapsed=$((($end - $start) / 1000000))
            total_time=$(($total_time + $elapsed))
        done

        avg_time=$((total_time / 100))
        echo -e "  Average response time: ${avg_time}ms"
    done

    echo -e "${GREEN}✓${NC} API endpoint tests completed"
}

# Function to check Redis cache performance
check_redis_cache() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}5. Checking Redis Cache Performance${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

    if command -v redis-cli >/dev/null 2>&1; then
        echo -e "Redis Statistics:"

        # Get Redis info
        redis-cli INFO memory | grep -E "used_memory|used_memory_peak" | sed 's/^/  /'
        redis-cli INFO stats | grep -E "total_commands|instantaneous_ops" | sed 's/^/  /'

        # Get key stats
        keys_count=$(redis-cli DBSIZE | awk '{print $2}')
        echo -e "  Keys in database: $keys_count"

        echo -e "${GREEN}✓${NC} Redis cache check completed"
    else
        echo -e "${YELLOW}⚠${NC} redis-cli not found (skipping Redis checks)"
    fi
}

# Function to generate summary report
generate_summary_report() {
    echo -e "\n${BLUE}───────────────────────────────────────────────────────────────${NC}"
    echo -e "${BLUE}6. Generating Summary Report${NC}"
    echo -e "${BLUE}───────────────────────────────────────────────────────────────${NC}"

    cat > "$OUTPUT_DIR/SUMMARY.md" << 'EOF'
# LSC Performance Testing Report

## Test Execution Summary

- **Date**: $(date)
- **Load Test Users**: $LOAD_TEST_USERS
- **Spawn Rate**: $LOAD_TEST_RATE users/sec
- **Test Duration**: $LOAD_TEST_DURATION

## Test Results

### 1. Load Performance (Pytest)
- See: `load_test_report.json`
- Log: `load_test_output.txt`

### 2. Database Performance
- See: `database_test_report.json`
- Log: `database_test_output.txt`

### 3. Concurrent Load Test (Locust)
- See: `locust_results_stats.csv`
- Log: `locust_output.txt`

### 4. API Endpoint Performance
- See: `locust_results_requests.csv`

### 5. System Metrics
- See: `system_metrics.json`

## Key Metrics to Review

- **Response Times**: Check p95 and p99 latencies
- **Success Rate**: Should be > 90% under load
- **Cache Hit Rate**: Should be > 70%
- **Database Query Time**: Should average < 300ms
- **Memory Usage**: Should stay under 500MB peak
- **CPU Usage**: Should stay under 80%

## Recommendations

1. **If p95 latency > 1000ms**: Consider database optimization or caching
2. **If success rate < 90%**: Check error logs and rate limiting
3. **If memory usage > 500MB**: Profile for memory leaks or increase instance size
4. **If cache hit rate < 70%**: Review cache keys and TTL settings

## Performance Bottlenecks

Review the detailed reports for slow queries and error patterns.

EOF

    echo -e "${GREEN}✓${NC} Summary report generated: $OUTPUT_DIR/SUMMARY.md"
}

# Main execution
main() {
    # Check if server is running
    echo -e "\n${YELLOW}Checking if LSC server is running...${NC}"
    if ! curl -s http://localhost:8000/api/v1/health > /dev/null 2>&1; then
        echo -e "${YELLOW}⚠${NC} LSC server not responding at http://localhost:8000"
        echo -e "${YELLOW}ℹ${NC} Skipping load tests (server required)"
        echo -e "${YELLOW}   Start the server with: docker-compose up"
    else
        echo -e "${GREEN}✓${NC} LSC server is running"

        # Run all tests
        run_performance_tests
        run_database_tests
        run_locust_load_test
        run_endpoint_tests
        check_redis_cache
    fi

    generate_summary_report

    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Performance Testing Complete${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "Results saved to: ${GREEN}$OUTPUT_DIR/${NC}"
    echo ""
}

# Run main
main "$@"
