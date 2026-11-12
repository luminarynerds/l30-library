#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
#
# dist-smoke.sh
#
# Install-path integration smoke test. Proves a fresh clone of this repo
# stands up end-to-end via the documented dist install path:
#
#   ./setup.sh --domain ... --email ... --name ...
#   docker compose -f docker-compose.dist.yml build   (no ghcr login)
#   docker compose -f docker-compose.dist.yml up -d
#
# ...and then exercises the stack: health, admin login (no turnstile block,
# email pre-verified), demo data load, catalog size, and one real checkout.
# It also asserts the backend/scheduler boot log is clean of the two
# recurring dist-install failure modes: undefined relations and raw SQL
# syntax errors (see docs/dist-install-characterization.md).
#
# Runs against an ISOLATED compose project name so it never touches a real
# /opt/l30-style deployment's containers, volumes, or network. Container
# names are overridden to l30smoke-* because compose project scoping does
# NOT rename fixed container_name literals, and Docker reserves container
# names daemon-wide (running or stopped) -- without the override, up -d
# dies with "Conflict. The container name ... is already in use" on any
# machine that has an existing L30 stack. Any existing dev .env /
# branding.json in this tree are backed up and restored, never clobbered.
#
# Usage:
#   ./scripts/dist-smoke.sh
#
# Exit codes:
#   0  all assertions passed
#   1  a step failed or an assertion did not hold
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

PROJECT="l30distsmoke"
COMPOSE_FILE="docker-compose.dist.yml"
# Rename every fixed container_name so the smoke coexists with a real L30
# stack on the same daemon. Service names -- and therefore all intra-stack
# DNS (database, redis, l30-backend, frontend) -- are unchanged; nothing in
# the stack resolves peers by container_name.
OVERRIDE_FILE=".dist-smoke.override.yml"
cat > "$OVERRIDE_FILE" <<'YAML'
services:
  database:
    container_name: l30smoke-database
  redis:
    container_name: l30smoke-redis
  l30-backend:
    container_name: l30smoke-backend
  frontend:
    container_name: l30smoke-frontend
  nginx:
    container_name: l30smoke-nginx
YAML
COMPOSE=(docker compose -f "$COMPOSE_FILE" -f "$OVERRIDE_FILE" -p "$PROJECT")

DOMAIN="yourlibrary.example"
EMAIL="admin@yourlibrary.example"
LIBRARY_NAME="Example Public Library"
ADMIN_PASSWORD="Sm0ke-Test-Passw0rd-1"

HOST="127.0.0.1"
HOST_HEADER="localhost"   # always in TRUSTED_HOSTS regardless of --domain
# docker-compose.dist.yml binds nginx to 127.0.0.1:8081 (TLS lives on a host
# proxy in real deployments -- see INSTALL.md Step 7).
BASE="http://${HOST}:8081"

NGINX_WAIT_SECS=300

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
FAIL=0

info() { printf "${BLUE}[INFO]${NC} %s\n" "$1"; }
pass() { printf "${GREEN}[PASS]${NC} %s\n" "$1"; }
fail() { printf "${RED}[FAIL]${NC} %s\n" "$1"; FAIL=1; }
warn() { printf "${YELLOW}[WARN]${NC} %s\n" "$1"; }

# --- curl helper: always sends the Host header that satisfies backend
# TRUSTED_HOSTS, and always connects via 127.0.0.1 (avoids IPv6-loopback
# surprises) regardless of what --domain was configured. ---
chost() {
    curl -sS -H "Host: ${HOST_HEADER}" "$@"
}

# =============================================================================
# .env / branding.json isolation: back up any existing dev files, restore on exit
# =============================================================================
BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/l30-dist-smoke.XXXXXX")"
ENV_HAD_FILE=0
BRANDING_HAD_FILE=0
[ -f .env ] && { cp .env "$BACKUP_DIR/.env"; ENV_HAD_FILE=1; }
[ -f branding.json ] && { cp branding.json "$BACKUP_DIR/branding.json"; BRANDING_HAD_FILE=1; }

cleanup() {
    info "Tearing down smoke stack (project: ${PROJECT})..."
    "${COMPOSE[@]}" down -v --remove-orphans >/dev/null 2>&1 || true
    rm -f "$OVERRIDE_FILE"

    rm -f .env branding.json
    if [ "$ENV_HAD_FILE" -eq 1 ]; then
        cp "$BACKUP_DIR/.env" .env
        info "Restored pre-existing .env"
    fi
    if [ "$BRANDING_HAD_FILE" -eq 1 ]; then
        cp "$BACKUP_DIR/branding.json" branding.json
        info "Restored pre-existing branding.json"
    fi
    rm -rf "$BACKUP_DIR"
}
trap cleanup EXIT

echo "================================================================================"
echo "L30 dist-install smoke test"
echo "================================================================================"
echo "Repo:    $REPO_ROOT"
echo "Project: $PROJECT (isolated compose project; will not touch other stacks)"
echo "Domain:  $DOMAIN"
echo "Start:   $(date)"
echo "================================================================================"
echo ""

# =============================================================================
# Step 1: Clean slate, run setup.sh non-interactively
# =============================================================================
info "Step 1: ./setup.sh --domain $DOMAIN --email $EMAIL --name \"$LIBRARY_NAME\""
rm -f .env branding.json

if ./setup.sh --domain "$DOMAIN" --email "$EMAIL" --name "$LIBRARY_NAME"; then
    pass "setup.sh completed"
else
    fail "setup.sh exited non-zero"
fi

if [ -f .env ]; then
    pass ".env generated"
else
    fail ".env was not generated -- aborting"
    exit 1
fi

if [ "$FAIL" -eq 1 ]; then
    fail "Setup step failed -- aborting before touching Docker"
    exit 1
fi

# =============================================================================
# Step 2: Build images from source -- must not require any ghcr.io login
# =============================================================================
echo ""
info "Step 2: docker compose -f $COMPOSE_FILE build (no registry login)"
BUILD_LOG="$(mktemp "${TMPDIR:-/tmp}/l30-dist-smoke-build.XXXXXX")"
if "${COMPOSE[@]}" build >"$BUILD_LOG" 2>&1; then
    pass "Images built from source"
else
    fail "docker compose build failed -- see $BUILD_LOG"
    tail -60 "$BUILD_LOG"
    exit 1
fi

if grep -qiE "ghcr\.io|unauthorized|denied: requested access" "$BUILD_LOG"; then
    fail "Build log references a registry pull/auth -- dist build should be source-only"
    grep -iE "ghcr\.io|unauthorized|denied" "$BUILD_LOG"
else
    pass "No ghcr.io / registry-auth references in build log"
fi
rm -f "$BUILD_LOG"

# =============================================================================
# Step 3: Bring the stack up, wait for nginx healthy (backend boot is slow)
# =============================================================================
echo ""
info "Step 3: docker compose up -d, waiting up to ${NGINX_WAIT_SECS}s for l30-nginx healthy"
if ! "${COMPOSE[@]}" up -d; then
    fail "docker compose up -d failed"
    exit 1
fi

elapsed=0
nginx_status=""
while [ "$elapsed" -lt "$NGINX_WAIT_SECS" ]; do
    # container_name is overridden to l30smoke-nginx (see OVERRIDE_FILE) so
    # the smoke never collides with a real stack's l30-nginx.
    nginx_status="$(docker inspect -f '{{.State.Health.Status}}' l30smoke-nginx 2>/dev/null || echo "unknown")"
    if [ "$nginx_status" = "healthy" ]; then
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    if [ $((elapsed % 30)) -eq 0 ]; then
        info "  ...waiting (${elapsed}s/${NGINX_WAIT_SECS}s), nginx=${nginx_status}"
    fi
done

if [ "$nginx_status" = "healthy" ]; then
    pass "l30-nginx healthy after ${elapsed}s"
else
    fail "l30-nginx did not become healthy within ${NGINX_WAIT_SECS}s (status: ${nginx_status})"
    echo "--- docker compose ps ---"
    "${COMPOSE[@]}" ps
    echo "--- l30-backend logs (tail) ---"
    "${COMPOSE[@]}" logs --tail=100 l30-backend
    echo "--- l30-nginx logs (tail) ---"
    "${COMPOSE[@]}" logs --tail=60 nginx
    exit 1
fi

# =============================================================================
# Step 4: GET /health -> 200
# =============================================================================
echo ""
info "Step 4: GET /health"
health_code="$(chost -o /dev/null -w '%{http_code}' "${BASE}/health")"
if [ "$health_code" = "200" ]; then
    pass "GET /health -> 200"
else
    fail "GET /health -> ${health_code} (expected 200)"
fi

# =============================================================================
# Step 5: Create founding admin (auto-verified, no turnstile) and log in
# =============================================================================
echo ""
info "Step 5: POST /api/v1/setup/admin + login"
admin_create_resp="$(chost -w '\n%{http_code}' -X POST "${BASE}/api/v1/setup/admin" \
    -H "Content-Type: application/json" \
    -d "{\"first_name\":\"Smoke\",\"last_name\":\"Test\",\"email\":\"${EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
admin_create_code="$(echo "$admin_create_resp" | tail -1)"
if [ "$admin_create_code" = "201" ]; then
    pass "Admin account created (201)"
else
    fail "POST /api/v1/setup/admin -> ${admin_create_code} (expected 201): $(echo "$admin_create_resp" | head -1)"
fi

login_resp="$(chost -X POST "${BASE}/api/v1/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"${EMAIL}\",\"password\":\"${ADMIN_PASSWORD}\"}")"
admin_token="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('access_token',''))" "$login_resp" 2>/dev/null || true)"

if [ -n "$admin_token" ]; then
    pass "Admin login returned an access token (no turnstile block, email pre-verified)"
else
    fail "Admin login did not return access_token. Response: $login_resp"
fi

# =============================================================================
# Step 6: Load demo data, assert catalog size >= 2000
# =============================================================================
echo ""
info "Step 6: POST /api/v1/setup/demo/load"
# Admin-gated once the founding admin exists (require_setup_access)
demo_resp="$(chost -w '\n%{http_code}' -X POST "${BASE}/api/v1/setup/demo/load" \
    -H "Authorization: Bearer ${admin_token}")"
demo_code="$(echo "$demo_resp" | tail -1)"
if [ "$demo_code" = "200" ]; then
    pass "Demo data load -> 200 ($(echo "$demo_resp" | head -1))"
else
    fail "POST /api/v1/setup/demo/load -> ${demo_code} (expected 200): $(echo "$demo_resp" | head -1)"
fi

catalog_resp="$(chost "${BASE}/api/v1/catalog/?per_page=1")"
catalog_total="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('total',0))" "$catalog_resp" 2>/dev/null || echo 0)"
if [ "$catalog_total" -ge 2000 ] 2>/dev/null; then
    pass "Catalog total = ${catalog_total} (>= 2000)"
else
    fail "Catalog total = ${catalog_total:-<unparseable>} (expected >= 2000). Response: $catalog_resp"
fi

# =============================================================================
# Step 7: One real checkout -- pick an available item + a zero-checkout patron
# =============================================================================
echo ""
info "Step 7: one checkout flow"

available_resp="$(chost "${BASE}/api/v1/catalog/?status=available&per_page=1")"
item_id="$(python3 -c "import json,sys; items=json.loads(sys.argv[1]).get('items',[]); print(items[0]['id'] if items else '')" "$available_resp" 2>/dev/null || true)"

if [ -n "$item_id" ]; then
    pass "Found available item id=${item_id} to check out"
else
    fail "Could not find an available catalog item. Response: $available_resp"
fi

# NOTE: users.email is Fernet-encrypted at rest (EncryptedString column type,
# see backend/app/core/encryption.py). Raw psql only ever sees ciphertext --
# decryption happens transparently in the ORM's process_result_value. So this
# has to run inside the backend container through SQLAlchemy, not a raw SQL
# query against the database container.
patron_email="$("${COMPOSE[@]}" exec -T l30-backend python3 -c "
import asyncio
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.circulation import Checkout, CheckoutStatus

async def main():
    async with AsyncSessionLocal() as db:
        busy = select(Checkout.user_id).where(
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue])
        )
        result = await db.execute(
            select(User.email)
            .where(User.role == UserRole.PATRON, User.id.notin_(busy))
            .order_by(User.id)
            .limit(1)
        )
        email = result.scalar_one_or_none()
        print(email or '', end='')

asyncio.run(main())
" 2>/dev/null | tr -d '[:space:]')"

if [ -n "$patron_email" ]; then
    pass "Selected demo patron ${patron_email} (zero active checkouts) for checkout"
else
    fail "Could not find a demo patron with zero active checkouts"
fi

if [ -n "$item_id" ] && [ -n "$patron_email" ]; then
    # Demo per-role passwords are "{DEMO_LOGIN_PASSWORD:-demo-2026}-{role}"
    # (backend/app/seeds/demo_seeder.py). setup.sh never writes
    # DEMO_LOGIN_PASSWORD, but honor an operator-set value in .env anyway.
    demo_base="$(sed -n 's/^DEMO_LOGIN_PASSWORD=//p' .env | tail -1)"
    patron_password="${demo_base:-demo-2026}-patron"
    patron_login_resp="$(chost -X POST "${BASE}/api/v1/auth/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"${patron_email}\",\"password\":\"${patron_password}\"}")"
    patron_token="$(python3 -c "import json,sys; print(json.loads(sys.argv[1]).get('access_token',''))" "$patron_login_resp" 2>/dev/null || true)"

    if [ -n "$patron_token" ]; then
        pass "Demo patron login returned an access token"

        checkout_resp="$(chost -w '\n%{http_code}' -X POST "${BASE}/api/v1/circulation/checkout" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${patron_token}" \
            -d "{\"item_id\": ${item_id}}")"
        checkout_code="$(echo "$checkout_resp" | tail -1)"
        if [ "$checkout_code" = "201" ]; then
            pass "Checkout of item ${item_id} by ${patron_email} -> 201"
        else
            fail "Checkout -> ${checkout_code} (expected 201): $(echo "$checkout_resp" | head -1)"
        fi
    else
        fail "Demo patron login did not return access_token. Response: $patron_login_resp"
    fi
else
    fail "Skipped checkout attempt (missing item or patron from prior steps)"
fi

# =============================================================================
# Step 8: Backend/scheduler logs are clean -- no undefined relations, no SQL
# syntax errors. This guards the Task 4 un-deferred-scheduler-tables fix.
# =============================================================================
echo ""
info "Step 8: backend + scheduler log cleanliness"
BACKEND_LOG="$(mktemp "${TMPDIR:-/tmp}/l30-dist-smoke-backend.XXXXXX")"
"${COMPOSE[@]}" logs l30-backend >"$BACKEND_LOG" 2>&1 || true

if grep -qiE "relation \"[a-z0-9_]+\" does not exist" "$BACKEND_LOG"; then
    fail "Backend log contains 'relation ... does not exist' -- undefined table at boot"
    grep -iE "relation \"[a-z0-9_]+\" does not exist" "$BACKEND_LOG" | head -10
else
    pass "No 'relation ... does not exist' errors in backend log"
fi

if grep -qiE "syntax error" "$BACKEND_LOG"; then
    fail "Backend log contains a SQL 'syntax error'"
    grep -iE "syntax error" "$BACKEND_LOG" | head -10
else
    pass "No 'syntax error' lines in backend log"
fi
rm -f "$BACKEND_LOG"

# =============================================================================
# Step 9: Verify the packages actually installed in the production image.
# The Docker build resolves pyproject.toml independently of uv.lock, including
# the heavy reranker extra. Import it without fetching or loading model weights.
# =============================================================================
echo ""
info "Step 9: patched runtime dependency imports and image/token round trips"
if "${COMPOSE[@]}" exec -T l30-backend python3 - <<'PYTHON'
import os
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
from io import BytesIO

import certifi
import jwt
from packaging.version import Version
from PIL import Image
from sentence_transformers import CrossEncoder
from scripts.check_reranker_compatibility import main as check_reranker

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
check_reranker()

for package, minimum in {
    "Pillow": "13.0.0",
    "PyJWT": "2.15.0",
    "certifi": "2026.10.19",
    "sentence-transformers": "5.6.0",
}.items():
    installed = version(package)
    assert Version(installed) >= Version(minimum), (package, installed, minimum)
    print(f"{package}={installed}")
assert callable(CrossEncoder)
assert certifi.where()
for image_format in ("PNG", "JPEG", "WEBP"):
    output = BytesIO()
    Image.new("RGB", (16, 24), (12, 34, 56)).save(output, format=image_format)
    output.seek(0)
    with Image.open(output) as image:
        image.load()
        assert image.size == (16, 24)
key = "synthetic-container-check-key-32-bytes-long"
encoded = jwt.encode({"sub": "synthetic", "exp": datetime.now(timezone.utc) + timedelta(minutes=1)}, key, algorithm="HS256")
assert jwt.decode(encoded, key, algorithms=["HS256"])["sub"] == "synthetic"
expired = jwt.encode({"sub": "synthetic", "exp": datetime.now(timezone.utc) - timedelta(minutes=1)}, key, algorithm="HS256")
try:
    jwt.decode(expired, key, algorithms=["HS256"])
except jwt.ExpiredSignatureError:
    pass
else:
    raise AssertionError("Expired JWT was accepted")
print("Runtime package imports, three image formats and JWT expiry checks passed")
PYTHON
then
    pass "Patched runtime packages import; image formats and JWT expiry work"
else
    fail "Runtime dependency verification failed"
fi

# =============================================================================
# Summary
# =============================================================================
echo ""
echo "================================================================================"
echo "Summary"
echo "================================================================================"
echo "End: $(date)"
if [ "$FAIL" -eq 0 ]; then
    printf "${GREEN}ALL ASSERTIONS PASSED${NC}\n"
    exit 0
else
    printf "${RED}ONE OR MORE ASSERTIONS FAILED${NC}\n"
    exit 1
fi
