# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Shared fixtures for integration tests.

The claims/lost-damaged circulation fixtures (test_settings, the *_for_claim
chain) live here so files like test_circulation_disputes_graceful.py can use
them. The unit-level test_claims_returned_service.py keeps its own copies
(different test root, doesn't see this conftest).
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.inventory import ItemCopy, ItemCondition
from app.models.lost_damaged import LostDamagedSettings
from app.models.user import User, UserRole


@pytest.fixture
async def test_settings(test_db):
    """Create test lost/damaged settings (system-wide)."""
    settings = LostDamagedSettings(
        branch_location=None,
        claims_returned_review_days=30,
        max_claims_per_patron_year=3,
        lost_item_processing_fee=Decimal("5.00"),
        default_replacement_cost=Decimal("25.00"),
        notify_staff_on_claims=True,
        is_active=True,
    )
    test_db.add(settings)
    await test_db.commit()
    await test_db.refresh(settings)
    return settings


@pytest.fixture
async def test_catalog_item_for_claim(test_db):
    """Create a test catalog item for claims tests."""
    item = CatalogItem(
        title="The Mystery Book",
        author="Jane Doe",
        isbn="978-1-234567-89-0",
        description="A book for testing claims returned",
        status=ItemStatus.checked_out,
        call_number="CLAIM-001",
        publication_year=2024,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_item_copy_for_claim(test_db, test_catalog_item_for_claim):
    """Create a test item copy for claims tests."""
    copy = ItemCopy(
        catalog_item_id=test_catalog_item_for_claim.id,
        barcode="CLAIM-COPY-001",
        condition=ItemCondition.GOOD,
        location="Main Branch",
        replacement_cost=Decimal("29.95"),
    )
    test_db.add(copy)
    await test_db.commit()
    await test_db.refresh(copy)
    return copy


@pytest.fixture
async def test_patron_for_claim(test_db):
    """Create a test patron for claims tests."""
    from app.core.security import hash_password

    user = User(
        email="claim_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Claim",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_staff_for_claim(test_db):
    """Create a test staff member for claims tests."""
    from app.core.security import hash_password

    user = User(
        email="claim_staff@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Claim",
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
async def test_active_checkout(test_db, test_patron_for_claim, test_catalog_item_for_claim, test_item_copy_for_claim):
    """Create an active checkout eligible for claims returned."""
    checkout = Checkout(
        user_id=test_patron_for_claim.id,
        item_id=test_catalog_item_for_claim.id,
        item_copy_id=test_item_copy_for_claim.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=14),
        due_date=datetime.now(timezone.utc) - timedelta(days=7),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def admin_client(test_db, test_admin):
    """Admin-authed client with the staff-scheduling feature guard bypassed."""
    from httpx import AsyncClient, ASGITransport
    from app.api.v1 import feature_guards
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_admin

    async def override_guard():
        return None

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[feature_guards.require_staff_scheduling_enabled] = override_guard
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(feature_guards.require_staff_scheduling_enabled, None)
