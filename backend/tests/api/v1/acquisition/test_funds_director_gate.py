# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for Fund-route director gate (security fix 2026-05-21).

The acquisition funds routes (create_fund, update_fund, rollover_funds) had
three calls to ``require_director(current_user)`` without ``await``. Because
``require_director`` is ``async def``, the bare call returned a coroutine
that was discarded - the role check never executed. Any STAFF user could
create funds, patch funds, or trigger fiscal-year rollover.

These tests assert a non-director STAFF user is rejected with 403 on all
three endpoints, locking the fix in.
"""

from datetime import datetime
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import hash_password
from app.models.acquisition import Fund, FundStatus
from app.models.user import User, UserRole


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def staff_only_user(test_db: AsyncSession) -> User:
    """Create a STAFF (non-director) user for director-gate tests."""
    user = User(
        email="funds_staff@library.local",
        password_hash=hash_password("StaffUser123!"),
        first_name="Funds",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def existing_fund(test_db: AsyncSession) -> Fund:
    """Create an existing fund for PATCH tests."""
    current_year = datetime.now().year
    fund = Fund(
        code="EXIST-001",
        name="Existing Fund",
        fiscal_year=current_year,
        status=FundStatus.ACTIVE,
        allocated_amount=Decimal("5000.00"),
        encumbered_amount=Decimal("0.00"),
        spent_amount=Decimal("0.00"),
    )
    test_db.add(fund)
    await test_db.commit()
    await test_db.refresh(fund)
    return fund


@pytest.fixture
async def staff_client(test_db: AsyncSession, staff_only_user: User):
    """Async HTTP client authenticated as a non-director STAFF user.

    Uses dependency_overrides to bypass JWT and inject the staff user
    directly, mirroring the pattern from test_immigrant_services_role_guards.
    """
    from app.api.v1.auth import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return staff_only_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


# ============================================================================
# Director-gate regression tests
# ============================================================================


@pytest.mark.asyncio
class TestFundDirectorGate:
    """STAFF (non-director) must be rejected on funds create/update/rollover.

    Before fix: ``require_director(current_user)`` was called without
    ``await`` in main.py at lines 90, 125, 151. The async function returned
    a discarded coroutine, the role check never ran, and STAFF could mutate
    funds. These three tests would have failed against that bug.
    """

    async def test_staff_cannot_create_fund(self, staff_client: AsyncClient):
        """POST /acquisition/funds must return 403 for STAFF."""
        payload = {
            "code": "NEW-FUND-001",
            "name": "Bypass Attempt Fund",
            "fiscal_year": datetime.now().year,
            "allocated_amount": "1000.00",
        }

        response = await staff_client.post(
            "/api/v1/acquisition/funds", json=payload
        )

        assert response.status_code == 403, (
            f"Expected 403 for STAFF POST /acquisition/funds, "
            f"got {response.status_code}: {response.text}"
        )

    async def test_staff_cannot_update_fund(
        self, staff_client: AsyncClient, existing_fund: Fund
    ):
        """PATCH /acquisition/funds/{id} must return 403 for STAFF."""
        payload = {"name": "Renamed By Staff"}

        response = await staff_client.patch(
            f"/api/v1/acquisition/funds/{existing_fund.id}",
            json=payload,
        )

        assert response.status_code == 403, (
            f"Expected 403 for STAFF PATCH /acquisition/funds/{existing_fund.id}, "
            f"got {response.status_code}: {response.text}"
        )

    async def test_staff_cannot_rollover_funds(self, staff_client: AsyncClient):
        """POST /acquisition/funds/rollover must return 403 for STAFF."""
        current_year = datetime.now().year
        payload = {
            "source_fiscal_year": current_year,
            "target_fiscal_year": current_year + 1,
            "carry_forward_unspent": False,
        }

        response = await staff_client.post(
            "/api/v1/acquisition/funds/rollover",
            json=payload,
        )

        assert response.status_code == 403, (
            f"Expected 403 for STAFF POST /acquisition/funds/rollover, "
            f"got {response.status_code}: {response.text}"
        )
