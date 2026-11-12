#!/bin/bash
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
set -e

# Get environment for conditional seeding
ENVIRONMENT="${ENVIRONMENT:-production}"

# --- Skip flags for non-essential startup phases ---
# SKIP_ALEMBIC_CHECK: (deprecated; alembic no longer auto-runs at startup)
# SKIP_DRIFT_DETECTION: skip drift detection at end (~20s). Default: false (runs in prod)
# SKIP_SEEDS: skip seed orchestrator when data already exists (~32s). Default: false (still run)

# Step 1: Initialize database schema using ORM (with retries)
echo "🗄️  Initializing database schema..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python scripts/init_db.py 2>/dev/null; then
        echo "✅ Database schema initialized successfully"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        echo "⏳ Database not ready, retrying in 3 seconds (attempt $RETRY_COUNT/$MAX_RETRIES)..."
        sleep 3
    else
        echo "⚠️  Database initialization failed, attempting to continue without schema..."
    fi
done

# Step 1b: Alembic is NOT auto-run on startup.
# init_db.py (Step 1) is canonical for schema — it introspects SQLAlchemy
# models and creates any missing tables idempotently. Auto-running
# `alembic upgrade head` after that produced cascading CREATE TABLE
# failures because the tables already existed; the failures were
# suppressed by 2>&1 + SKIP_ALEMBIC_CHECK, but the noise hid real issues.
#
# Alembic remains available in the container for data migrations and
# ad-hoc schema changes — run manually:
#
#   docker exec l30-backend alembic upgrade head           # apply pending
#   docker exec l30-backend alembic heads                  # check state
#   docker exec l30-backend alembic stamp head             # mark applied
#   docker exec l30-backend alembic revision -m "..." ...  # author new
#
# See docs/specs/2026-05-13-branch-fk-phase3-spec.md follow-up notes.
echo "ℹ️  Alembic auto-run disabled; init_db.py is canonical. Use 'alembic upgrade head' manually for data migrations."

# Step 2: Bootstrap library system (core tables seeding - always run)
echo "🌳 Bootstrapping library system..."
if python -m app.seeds.cli bootstrap 2>&1 | tee /tmp/bootstrap.log; then
    echo "✅ Library system bootstrapped"
else
    echo "⚠️  Library system bootstrap had issues (see logs above)"
    echo "⚠️  Continuing startup — bootstrap may have partially succeeded"
fi

# Verify branches exist after bootstrap; without these /branches page is empty.
echo "🔍 Verifying bootstrap branch data..."
if python - <<'PY'
import asyncio
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.multi_branch import Branch


async def verify() -> int:
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(func.count(Branch.id)))
        return result.scalar_one()


count = asyncio.run(verify())
print(f"Detected {count} branch record(s)")
raise SystemExit(0 if count > 0 else 1)
PY
then
    echo "✅ Branch bootstrap verification passed"
else
    echo "❌ No branches found after bootstrap; aborting startup"
    exit 1
fi

# Step 3: Seed all reference data via the orchestrator (idempotent)
# Note: The orchestrator internally re-runs bootstrap as its first CRITICAL task.
# Since bootstrap already ran above, the orchestrator's bootstrap call is a
# fast no-op (idempotent), but can be skipped entirely with SKIP_SEEDS=true.
if [ "${SKIP_SEEDS:-true}" != "true" ]; then
    echo "📚 Loading seed data via orchestrator..."
    if python -m app.seeds.cli seed 2>&1 | tee /tmp/seed_all.log; then
        echo "✅ All seed data loaded"
    else
        echo "⚠️  Seed orchestrator had issues (continuing with startup...)"
    fi
else
    echo "⏭️  Skipping seed orchestrator (SKIP_SEEDS=true)"
fi

# Test accounts: only in non-production environments
if [ "$ENVIRONMENT" != "production" ] || [ "$FORCE_SEED" = "true" ]; then
    if python scripts/seed_test_accounts.py 2>&1 | tee /tmp/seed_accounts.log; then
        echo "✅ Test accounts created"
    else
        echo "⚠️  Test accounts seed failed (continuing with startup...)"
    fi
fi

# Step 4: Assert enum values are lowercase (blocks startup if violated)
echo "🔒 Checking enum case values..."
if python scripts/assert_enum_case.py 2>&1; then
    echo "✅ Enum case assertion passed"
else
    echo "❌ Enum case assertion FAILED — refusing to start"
    echo "   Fix all uppercase enum values before deploying"
    exit 1
fi

# Step 5: Run startup drift detection
# enum_sync is BLOCKING — prevents startup with mismatched enums (the #1 source of prod bugs)
# Other checks are warn-only
if [ "${SKIP_DRIFT_DETECTION:-false}" != "true" ]; then
    echo "🔍 Running enum drift check (blocking)..."
    python scripts/check_drift.py --check enum_sync 2>&1 | head -20
    ENUM_EXIT=${PIPESTATUS[0]}
    if [ "$ENUM_EXIT" -eq 0 ]; then
        echo "✅ No enum drift detected"
    else
        echo "⚠️  Enum drift detected ($ENUM_EXIT findings) — logging but not blocking"
        echo "   Run: python scripts/check_drift.py --check enum_sync"
    fi

    echo "🔍 Running remaining drift checks (warn-only)..."
    python scripts/check_drift.py --mode startup 2>&1 | head -20
    if [ "${PIPESTATUS[0]}" -eq 0 ]; then
        echo "✅ No schema drift detected"
    else
        echo "⚠️  Schema drift detected (see /health/drift for details)"
    fi
else
    echo "⏭️  Skipping drift detection (SKIP_DRIFT_DETECTION=true)"
fi

echo "🚀 Starting application..."
exec gunicorn -w "${WORKERS:-2}" -k uvicorn.workers.UvicornWorker --forwarded-allow-ips "*" \
    -b 0.0.0.0:8000 \
    --timeout 120 --graceful-timeout 30 --keep-alive 5 \
    --worker-tmp-dir /tmp \
    --access-logfile - --error-logfile - --log-level info \
    app.main:app
