# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for two backend correctness fixes:

1. ``get_or_create_progress`` race on first step
   Two concurrent first-step requests for the same patron both miss the SELECT
   and both INSERT a PatronOnboardingProgress row, violating the patron_id
   UNIQUE constraint. The fix wraps the INSERT in a SAVEPOINT and re-selects
   on IntegrityError, so the loser returns the winner's row.

2. ``is_resident`` auto-detect always no-ops at signup
   The previous code read ``user.zip_code`` which was never populated from
   the freeform address string, so detect_residency was a silent no-op.
   The auto-detect call was removed. A new patron's ``is_resident`` must
   remain NULL after registration (staff sets it during card-app review).
"""

import asyncio
import uuid

import pytest
from sqlalchemy import select

from app.api.v1.patron_onboarding import get_or_create_progress
from app.core.database import AsyncSessionLocal
from app.models.patron_onboarding import PatronOnboardingProgress
from app.models.user import User, UserRole


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _bootstrap_test_env():
    """Disable rate limiter, stub Redis, and bypass DNS for EmailStr."""
    from app.core.rate_limit import limiter

    limiter.enabled = False

    import app.core.security as sec_module

    if not hasattr(sec_module, "_fake_redis_store"):
        sec_module._fake_redis_store = {}

    class _FakeRedis:
        def exists(self, key):
            return 1 if key in sec_module._fake_redis_store else 0

        def ping(self):
            return True

        def setex(self, key, time, value):
            sec_module._fake_redis_store[key] = value

    sec_module._redis_client = _FakeRedis()
    sec_module._redis_available = True

    import email_validator

    email_validator.TEST_ENVIRONMENT = True


# ---------------------------------------------------------------------------
# 1. Race fix: get_or_create_progress under concurrent first-step calls
# ---------------------------------------------------------------------------


async def _create_patron(session) -> int:
    """Insert a fresh patron and return its id."""
    user = User(
        email=f"race_{uuid.uuid4().hex[:8]}@l30.test",
        password_hash="x",
        first_name="Race",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user.id


@pytest.mark.integration
async def test_get_or_create_progress_concurrent_first_call_is_race_safe(test_db):
    """Two independent sessions race on the first call -- only one row, both return it.

    Uses two separate AsyncSession instances so each goes through its own
    SELECT-then-INSERT, faithfully reproducing the prod race. The HTTP test
    client cannot do this because the conftest ``client`` fixture wires every
    request to a single shared session.
    """
    patron_id = await _create_patron(test_db)

    async def _first_call(session):
        """One request's worth of work: get-or-create, then commit.

        The commit has to happen inside the racing task, exactly as it does at the
        end of a real request. If both sessions hold their transactions open until
        after gather(), the loser's INSERT just blocks on the UNIQUE index waiting
        for the winner to end its transaction -- which cannot happen until gather()
        returns -- so it dies on a lock-wait timeout instead of the IntegrityError
        this test is about.
        """
        progress = await get_or_create_progress(patron_id, session)
        await session.commit()
        return progress

    # Two fresh sessions. Each will SELECT (None), then attempt INSERT.
    sess_a = AsyncSessionLocal()
    sess_b = AsyncSessionLocal()
    try:
        results = await asyncio.gather(
            _first_call(sess_a),
            _first_call(sess_b),
            return_exceptions=True,
        )

        # Neither call may raise. Before the fix one side's flush raises
        # IntegrityError on the UNIQUE(patron_id) constraint.
        for r in results:
            assert not isinstance(r, Exception), f"race raised: {r!r}"
    finally:
        await sess_a.close()
        await sess_b.close()

    # Exactly one row exists for this patron.
    rows = (
        (
            await test_db.execute(
                select(PatronOnboardingProgress).where(
                    PatronOnboardingProgress.patron_id == patron_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1, f"expected 1 progress row, got {len(rows)}"


# ---------------------------------------------------------------------------
# 2. Residency: registration must not silently flag is_resident
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_register_does_not_auto_set_is_resident(client, test_db):
    """A fresh registration leaves is_resident NULL (set by staff later)."""
    email = f"resid_{uuid.uuid4().hex[:8]}@l30.test"
    payload = {
        "email": email,
        "password": "StrongP@ss1word",
        "first_name": "Resi",
        "last_name": "Dent",
    }
    resp = await client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 201, resp.text

    row = (await test_db.execute(select(User).where(User.email == email))).scalar_one()
    assert row.is_resident is None, (
        f"is_resident should be NULL for new signup, got {row.is_resident!r}"
    )
