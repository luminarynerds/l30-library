#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# =============================================================================
# diagnostic-probe.sh — Maximum-information diagnostic for L30
#
# Strategy: Binary search through the system's dependency chain.
# Each probe is designed so that EITHER outcome (pass or fail) tells us
# something specific. We stop as soon as we find the fault boundary.
#
# Usage: ./scripts/diagnostic-probe.sh [backend_url]
# =============================================================================
set -euo pipefail

BASE_URL="${1:-http://localhost:8000}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

pass_count=0
fail_count=0
findings=()

probe() {
    local label="$1"
    local pass_means="$2"
    local fail_means="$3"
    shift 3
    # remaining args are the command to run

    printf "${CYAN}[PROBE]${NC} %-50s " "$label"
    if output=$("$@" 2>&1); then
        printf "${GREEN}PASS${NC}\n"
        printf "        ${GREEN}→ %s${NC}\n" "$pass_means"
        ((pass_count++))
        return 0
    else
        printf "${RED}FAIL${NC}\n"
        printf "        ${RED}→ %s${NC}\n" "$fail_means"
        findings+=("$label: $fail_means")
        ((fail_count++))
        return 1
    fi
}

probe_http() {
    local label="$1"
    local pass_means="$2"
    local fail_means="$3"
    local url="$4"
    local expected_status="${5:-200}"

    printf "${CYAN}[PROBE]${NC} %-50s " "$label"
    local status
    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "$url" 2>/dev/null) || status="000"

    if [ "$status" = "$expected_status" ]; then
        printf "${GREEN}PASS${NC} (HTTP %s)\n" "$status"
        printf "        ${GREEN}→ %s${NC}\n" "$pass_means"
        ((pass_count++))
        return 0
    else
        printf "${RED}FAIL${NC} (HTTP %s)\n" "$status"
        printf "        ${RED}→ %s${NC}\n" "$fail_means"
        findings+=("$label: $fail_means (got HTTP $status)")
        ((fail_count++))
        return 1
    fi
}

echo ""
echo "============================================================================="
echo "${BOLD} L30 Diagnostic Probe — Maximum Information Strategy${NC}"
echo "============================================================================="
echo " Target: $BASE_URL"
echo " Time:   $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================================="
echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 1: Is anything running at all?
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 1: Process Liveness ──${NC}"
echo "   If this fails, everything else is moot."
echo ""

layer1_ok=true
probe_http \
    "Health endpoint (no deps)" \
    "FastAPI process is alive and routing requests" \
    "Backend process is down or unreachable — STOP HERE" \
    "${BASE_URL}/api/v1/health" || layer1_ok=false

if [ "$layer1_ok" = false ]; then
    echo ""
    echo "${RED}${BOLD}HALT: Backend not reachable. Fix infrastructure first.${NC}"
    echo "  Check: docker compose ps | grep l30-backend"
    echo "  Check: docker compose logs l30-backend --tail 50"
    exit 1
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 2: Are dependencies (DB, Redis) connected?
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 2: Dependency Health ──${NC}"
echo "   Readiness endpoint touches DB + Redis. This is the most"
echo "   informative single endpoint in the system."
echo ""

readiness_body=$(curl -s --max-time 10 "${BASE_URL}/api/v1/health/ready" 2>/dev/null) || readiness_body=""
readiness_status=$(echo "$readiness_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null) || readiness_status="error"

if [ "$readiness_status" = "ready" ]; then
    printf "${CYAN}[PROBE]${NC} %-50s ${GREEN}PASS${NC}\n" "Readiness (DB + Redis)"
    printf "        ${GREEN}→ Database and Redis both connected${NC}\n"
    ((pass_count++))

    # Extract sub-check details
    db_status=$(echo "$readiness_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('checks',{}).get('database',{}).get('status','unknown'))" 2>/dev/null) || db_status="unknown"
    redis_status=$(echo "$readiness_body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('checks',{}).get('redis',{}).get('status','unknown'))" 2>/dev/null) || redis_status="unknown"
    printf "        Database: %s | Redis: %s\n" "$db_status" "$redis_status"
else
    printf "${CYAN}[PROBE]${NC} %-50s ${RED}FAIL${NC}\n" "Readiness (DB + Redis)"
    printf "        ${RED}→ Dependency failure — DB or Redis unreachable${NC}\n"
    findings+=("Readiness: dependencies unhealthy (status=$readiness_status)")
    ((fail_count++))

    # Try to determine which dependency failed
    echo ""
    echo "   Isolating which dependency is down..."
    # Direct DB check via docker
    if docker exec lsc-database pg_isready -q 2>/dev/null; then
        printf "        Database container: ${GREEN}reachable${NC}\n"
    else
        printf "        Database container: ${RED}unreachable${NC}\n"
        findings+=("PostgreSQL container not responding to pg_isready")
    fi

    if docker exec lsc-redis redis-cli ping 2>/dev/null | grep -q PONG; then
        printf "        Redis container:    ${GREEN}reachable${NC}\n"
    else
        printf "        Redis container:    ${RED}unreachable${NC}\n"
        findings+=("Redis container not responding to ping")
    fi
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 3: Does the ORM actually work?
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 3: ORM / Mapper Integrity ──${NC}"
echo "   The health endpoint bypasses SQLAlchemy ORM. This layer"
echo "   tests whether real model queries work (the WeedingCandidate"
echo "   mapper issue lives here)."
echo ""

# Hit an endpoint that requires ORM model loading
# /api/v1/catalog is a good candidate — it queries the catalog model
probe_http \
    "Catalog endpoint (ORM query)" \
    "SQLAlchemy mappers initialized successfully" \
    "ORM mapper initialization may be broken" \
    "${BASE_URL}/api/v1/catalog" || true

# Try a second ORM-dependent endpoint to confirm the pattern
probe_http \
    "Circulation endpoint (ORM query)" \
    "Circulation models load correctly" \
    "Circulation ORM queries failing" \
    "${BASE_URL}/api/v1/circulation/checkouts" || true

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 4: Domain group sweep — which subsystems work?
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 4: Domain Group Sweep ──${NC}"
echo "   One GET per router group. This classifies every major"
echo "   subsystem as working, auth-gated, or broken."
echo ""

# For each domain, we pick one GET endpoint that should exist.
# Auth-gated endpoints returning 401/403 = infrastructure works, just need auth.
# 500 = broken. 404 = endpoint may not exist or need path params.

domain_endpoints=(
    "Auth|/api/v1/auth/me"
    "Users|/api/v1/users/"
    "Events|/api/v1/events/"
    "Branches|/api/v1/branches/"
    "Strategic|/api/v1/strategic/plans"
    "Acquisitions|/api/v1/acquisitions/orders"
    "Staff Fines|/api/v1/staff/fines"
    "Reports|/api/v1/reports/"
    "Learning|/api/v1/learning/courses"
    "Announcements|/api/v1/announcements/"
    "Book Clubs|/api/v1/book-clubs/"
    "Volunteers|/api/v1/volunteers/"
    "Home Delivery|/api/v1/home-delivery/applications"
    "Makerspace|/api/v1/makerspace/equipment"
    "Rooms|/api/v1/rooms/"
    "Equipment|/api/v1/equipment/"
)

working=0
auth_gated=0
broken=0
not_found=0

for entry in "${domain_endpoints[@]}"; do
    IFS='|' read -r domain path <<< "$entry"
    status=$(curl -s -o /dev/null -w '%{http_code}' --max-time 10 "${BASE_URL}${path}" 2>/dev/null) || status="000"

    case "$status" in
        200|201)
            printf "  %-20s ${GREEN}%s${NC}  (working)\n" "$domain" "$status"
            ((working++))
            ;;
        401|403)
            printf "  %-20s ${YELLOW}%s${NC}  (auth-gated, infrastructure OK)\n" "$domain" "$status"
            ((auth_gated++))
            ;;
        404|405)
            printf "  %-20s ${YELLOW}%s${NC}  (route not matched — check path)\n" "$domain" "$status"
            ((not_found++))
            ;;
        500|502|503)
            printf "  %-20s ${RED}%s${NC}  (SERVER ERROR)\n" "$domain" "$status"
            findings+=("$domain ($path): HTTP $status")
            ((broken++))
            ;;
        000)
            printf "  %-20s ${RED}%s${NC}  (timeout/unreachable)\n" "$domain" "$status"
            findings+=("$domain ($path): connection failed")
            ((broken++))
            ;;
        *)
            printf "  %-20s ${YELLOW}%s${NC}  (unexpected)\n" "$domain" "$status"
            ;;
    esac
done

echo ""
printf "  Summary: ${GREEN}%d working${NC} | ${YELLOW}%d auth-gated${NC} | ${YELLOW}%d not-found${NC} | ${RED}%d broken${NC}\n" \
    "$working" "$auth_gated" "$not_found" "$broken"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 5: OpenAPI schema — does the app know about its own routes?
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 5: OpenAPI Route Census ──${NC}"
echo "   Fetch /openapi.json to see how many routes the running app"
echo "   actually registered (vs. the ~3,464 in source code)."
echo ""

route_count=$(curl -s --max-time 15 "${BASE_URL}/openapi.json" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    schema = json.load(sys.stdin)
    paths = schema.get('paths', {})
    total = sum(len(methods) for methods in paths.values())
    print(f'{len(paths)} paths, {total} operations')
except:
    print('ERROR: could not parse OpenAPI schema')
" 2>/dev/null) || route_count="ERROR: endpoint unreachable"

printf "  Registered routes: ${BOLD}%s${NC}\n" "$route_count"

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# LAYER 6: Recent error signal from logs
# ─────────────────────────────────────────────────────────────────────────────
echo "${BOLD}── Layer 6: Error Signal (last 200 log lines) ──${NC}"
echo ""

if docker logs lsc-backend --tail 200 2>&1 > /tmp/lsc-diag-logs.txt 2>/dev/null; then
    error_count=$(grep -ci 'error\|exception\|traceback' /tmp/lsc-diag-logs.txt 2>/dev/null) || error_count=0
    mapper_count=$(grep -c 'WeedingCandidate' /tmp/lsc-diag-logs.txt 2>/dev/null) || mapper_count=0
    unique_errors=$(grep -i 'error\|exception' /tmp/lsc-diag-logs.txt 2>/dev/null | sort -u | wc -l) || unique_errors=0

    printf "  Total error/exception lines: %s\n" "$error_count"
    printf "  WeedingCandidate mapper errors: %s\n" "$mapper_count"
    printf "  Unique error patterns: %s\n" "$unique_errors"

    if [ "$unique_errors" -gt 0 ]; then
        echo ""
        echo "  Top error patterns:"
        grep -i 'error\|exception' /tmp/lsc-diag-logs.txt 2>/dev/null \
            | sed 's/^.*ERROR/ERROR/' \
            | sort | uniq -c | sort -rn | head -5 \
            | while read -r count line; do
                printf "    %3dx  %s\n" "$count" "${line:0:100}"
            done
    fi
    rm -f /tmp/lsc-diag-logs.txt
else
    echo "  ${YELLOW}Could not read backend logs (docker not available?)${NC}"
fi

echo ""

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
echo "============================================================================="
echo "${BOLD} DIAGNOSTIC SUMMARY${NC}"
echo "============================================================================="
printf "  Probes passed: ${GREEN}%d${NC}\n" "$pass_count"
printf "  Probes failed: ${RED}%d${NC}\n" "$fail_count"
echo ""

if [ ${#findings[@]} -gt 0 ]; then
    echo "${BOLD}  Findings requiring attention:${NC}"
    for f in "${findings[@]}"; do
        echo "    ${RED}•${NC} $f"
    done
else
    echo "  ${GREEN}No critical findings.${NC}"
fi

echo ""
echo "  ${BOLD}Next steps based on results:${NC}"
if [ "$fail_count" -eq 0 ]; then
    echo "    All probes passed. System is operational."
    echo "    → Focus on: memory leaks, test coverage, 500 error cleanup"
elif [ "$broken" -gt 0 ]; then
    echo "    ${RED}Server errors detected in domain endpoints.${NC}"
    echo "    → Investigate the 5xx domains listed above"
    echo "    → Check: docker compose logs l30-backend --tail 100 2>&1 | grep ERROR"
else
    echo "    Some probes failed but no 5xx server errors in domain sweep."
    echo "    → Likely auth/routing issues, not infrastructure problems"
fi
echo ""
echo "============================================================================="
echo "  Completed: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "============================================================================="
