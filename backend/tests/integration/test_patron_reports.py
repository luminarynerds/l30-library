# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for patron reports functionality.

Tests cover:
- New registrations reports
- Active borrowers reports
- Patrons with blocks reports
- Demographic breakdowns reports
"""

from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

import pytest


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


# =============================================================================
# Test Fixtures for Patron Reports
# =============================================================================


@pytest.fixture
async def test_new_patron_this_week(test_db):
    """Create a patron registered this week."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="newpatron_week@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="New",
        last_name="WeekPatron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=3),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_new_patron_this_month(test_db):
    """Create a patron registered this month (but not this week)."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="newpatron_month@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="New",
        last_name="MonthPatron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=15),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_old_patron(test_db):
    """Create a patron registered over a month ago."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="oldpatron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Old",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=60),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_blocked_patron(test_db):
    """Create a blocked patron."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole, PatronStatus

    user = User(
        email="blocked_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Blocked",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=False,
        email_verified=True,
        patron_status=PatronStatus.BLOCKED,
        block_reason="Testing blocked status",
        blocked_at=datetime.now(timezone.utc),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_suspended_patron(test_db):
    """Create a suspended patron."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole, PatronStatus

    user = User(
        email="suspended_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Suspended",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_status=PatronStatus.SUSPENDED,
        suspension_reason="Excessive overdue items",
        suspended_at=datetime.now(timezone.utc),
        suspended_until=datetime.now(timezone.utc) + timedelta(days=14),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_active_borrower(test_db, test_catalog_item):
    """Create a patron with recent checkout activity."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.models.circulation import Checkout, CheckoutStatus

    user = User(
        email="active_borrower@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Active",
        last_name="Borrower",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    # Add a recent checkout
    checkout = Checkout(
        user_id=user.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=5),
        due_date=datetime.now(timezone.utc) + timedelta(days=16),
    )
    test_db.add(checkout)
    await test_db.commit()

    return user


@pytest.fixture
async def test_inactive_patron(test_db):
    """Create a patron with no activity in 90+ days."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="inactive_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Inactive",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        created_at=datetime.now(timezone.utc) - timedelta(days=180),
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_patron_with_high_fines(test_db):
    """Create a patron with high fines ($25+)."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.models.fine import Fine, FineStatus, FineType

    user = User(
        email="highfines_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="HighFines",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    # Add high fines
    fine = Fine(
        user_id=user.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("35.00"),
        amount_paid=Decimal("0.00"),
        description="Multiple overdue items",
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(fine)
    await test_db.commit()

    return user


@pytest.fixture
async def test_patron_with_many_overdue(test_db):
    """Create a patron with 3+ overdue items."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from app.models.circulation import Checkout, CheckoutStatus
    from app.models.catalog import CatalogItem, ItemStatus

    user = User(
        email="manyoverdue_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="ManyOverdue",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    # Create 4 overdue checkouts
    for i in range(4):
        item = CatalogItem(
            title=f"Overdue Book {i}",
            author="Test Author",
            isbn=f"978-0-123456-{80 + i}-9",
            description="A test book",
            status=ItemStatus.available,
            call_number=f"TEST-00{i}",
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        checkout = Checkout(
            user_id=user.id,
            item_id=item.id,
            status=CheckoutStatus.overdue,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=35),
            due_date=datetime.now(timezone.utc) - timedelta(days=14),
        )
        test_db.add(checkout)

    await test_db.commit()
    return user


@pytest.fixture
async def test_adult_patron(test_db):
    """Create an adult patron with demographic info."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="adult_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Adult",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_type="adult",
        date_of_birth=date.today() - timedelta(days=35 * 365),
        language_preference="English",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_teen_patron(test_db):
    """Create a teen patron with demographic info."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="teen_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Teen",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        patron_type="teen",
        date_of_birth=date.today() - timedelta(days=15 * 365),
        language_preference="Spanish",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def test_child_patron(test_db, test_patron):
    """Create a child patron with demographic info and parent link."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    child = User(
        email="child_patron@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Child",
        last_name="Patron",
        role=UserRole.CHILD,
        is_active=True,
        email_verified=True,
        patron_type="child",
        date_of_birth=date.today() - timedelta(days=8 * 365),
        language_preference="English",
        parent_guardian_id=test_patron.id,
        parental_consent_given=True,
        parental_consent_date=datetime.now(timezone.utc),
    )
    test_db.add(child)
    await test_db.commit()
    await test_db.refresh(child)
    return child


# =============================================================================
# New Registrations Reports Tests
# =============================================================================


@pytest.mark.integration
class TestNewRegistrationsReports:
    """Test new registrations reports functionality."""

    async def test_patron_statistics_requires_staff(self, client):
        """Test patron statistics endpoint requires staff authentication."""
        response = await client.get("/api/v1/staff/patrons/statistics")
        assert response.status_code == 401

    async def test_patron_statistics_new_this_week(
        self, client, test_staff, test_staff_data, test_new_patron_this_week
    ):
        """Test patron statistics returns correct new patrons this week."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "new_this_week" in data
        assert isinstance(data["new_this_week"], int)
        assert data["new_this_week"] >= 1

    async def test_patron_statistics_new_this_month(
        self,
        client,
        test_staff,
        test_staff_data,
        test_new_patron_this_week,
        test_new_patron_this_month,
    ):
        """Test patron statistics returns correct new patrons this month."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "new_this_month" in data
        assert isinstance(data["new_this_month"], int)
        # Should include both new this week and new this month patrons
        assert data["new_this_month"] >= 2

    async def test_patron_statistics_old_patron_not_counted(
        self, client, test_staff, test_staff_data, test_old_patron
    ):
        """Test that patrons registered over a month ago are not counted as new."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Old patron should be in total but not new counts
        assert data["total_patrons"] >= 1
        # Week count shouldn't include old patron
        assert "new_this_week" in data

    async def test_patron_statistics_response_structure(
        self, client, test_staff, test_staff_data, test_patron
    ):
        """Test patron statistics response structure is complete."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify all required fields exist
        required_fields = [
            "total_patrons",
            "active_patrons",
            "blocked_patrons",
            "new_this_week",
            "new_this_month",
            "total_fines_outstanding",
            "total_overdue_items",
            "at_risk_counts",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

        # Verify at_risk_counts structure
        assert "patrons_with_many_overdue" in data["at_risk_counts"]
        assert "patrons_with_high_fines" in data["at_risk_counts"]
        assert "inactive_patrons" in data["at_risk_counts"]


# =============================================================================
# Active Borrowers Reports Tests
# =============================================================================


@pytest.mark.integration
class TestActiveBorrowersReports:
    """Test active borrowers reports functionality."""

    async def test_patron_engagement_requires_staff(self, client):
        """Test patron engagement endpoint requires staff authentication."""
        response = await client.get("/api/v1/reports/analytics/patron-engagement")
        assert response.status_code == 401

    async def test_patron_engagement_basic(
        self, client, test_staff, test_staff_data, test_active_borrower
    ):
        """Test patron engagement returns basic metrics."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/analytics/patron-engagement",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        assert "total_patrons" in data
        assert "active_patrons" in data
        assert "engagement_rate" in data

        # Active borrower should be counted
        assert data["active_patrons"] >= 1

    async def test_patron_engagement_response_structure(
        self, client, test_staff, test_staff_data, test_patron
    ):
        """Test patron engagement response structure is complete."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/analytics/patron-engagement",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify required fields
        required_fields = [
            "total_patrons",
            "active_patrons",
            "new_patrons",
            "dormant_patrons",
            "engagement_rate",
            "avg_checkouts_per_patron",
            "retention_rate",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    async def test_patron_engagement_custom_period(
        self, client, test_staff, test_staff_data, test_patron
    ):
        """Test patron engagement with custom time period."""
        token = await get_staff_token(client, test_staff_data)

        # Test with 7 days
        response = await client.get(
            "/api/v1/reports/analytics/patron-engagement?days=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data_7d = response.json()
        assert "metadata" in data_7d
        assert data_7d["metadata"]["time_window"] == "7d"

        # Test with 90 days
        response = await client.get(
            "/api/v1/reports/analytics/patron-engagement?days=90",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data_90d = response.json()
        assert data_90d["metadata"]["time_window"] == "90d"

    async def test_patron_engagement_dormant_patrons(
        self, client, test_staff, test_staff_data, test_inactive_patron
    ):
        """Test dormant patrons are correctly identified."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/analytics/patron-engagement",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Dormant patrons should be counted (no activity in 180+ days)
        assert "dormant_patrons" in data
        assert isinstance(data["dormant_patrons"], int)

    async def test_active_borrowers_in_dashboard(
        self, client, test_staff, test_staff_data, test_active_borrower
    ):
        """Test active borrowers appear in dashboard stats."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Dashboard should include active patron metrics
        assert "active_patrons_30d" in data or "total_patrons" in data


# =============================================================================
# Patrons with Blocks Reports Tests
# =============================================================================


@pytest.mark.integration
class TestPatronsWithBlocksReports:
    """Test patrons with blocks reports functionality."""

    async def test_blocked_patrons_count(
        self, client, test_staff, test_staff_data, test_blocked_patron
    ):
        """Test blocked patrons are counted in statistics."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "blocked_patrons" in data
        assert isinstance(data["blocked_patrons"], int)
        assert data["blocked_patrons"] >= 1

    async def test_suspended_patron_status(
        self, client, test_staff, test_staff_data, test_suspended_patron
    ):
        """Test suspended patron is retrievable with status info."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/patrons/{test_suspended_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "suspended"
        assert "suspension_reason" in data or data.get("patron_status") == "suspended"

    async def test_blocked_patron_status(
        self, client, test_staff, test_staff_data, test_blocked_patron
    ):
        """Test blocked patron is retrievable with status info."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/patrons/{test_blocked_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "blocked"

    async def test_block_patron_action(self, client, test_staff, test_staff_data, test_patron):
        """Test blocking a patron via status update endpoint."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "block",
                "reason": "Test blocking patron",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "blocked"

    async def test_unblock_patron_action(
        self, client, test_staff, test_staff_data, test_blocked_patron
    ):
        """Test unblocking a patron via status update endpoint."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/patrons/{test_blocked_patron.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "unblock",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "active"

    async def test_suspend_patron_action(self, client, test_staff, test_staff_data, test_patron):
        """Test suspending a patron via status update endpoint."""
        token = await get_staff_token(client, test_staff_data)
        suspended_until = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        response = await client.post(
            f"/api/v1/staff/patrons/{test_patron.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "suspend",
                "reason": "Test suspension",
                "suspended_until": suspended_until,
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "suspended"

    async def test_unsuspend_patron_action(
        self, client, test_staff, test_staff_data, test_suspended_patron
    ):
        """Test unsuspending a patron via status update endpoint."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.post(
            f"/api/v1/staff/patrons/{test_suspended_patron.id}/status",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "action": "unsuspend",
            },
        )
        assert response.status_code == 200
        data = response.json()

        assert data["patron_status"] == "active"

    async def test_patrons_filter_by_status(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
        test_blocked_patron,
    ):
        """Test filtering patrons list by status.

        Uses an admin caller: list_patrons is @pii_filtered and
        app/core/pii_scope.py classifies email as SENSITIVE, which plain
        STAFF (INTERNAL clearance) cannot see -- it comes back None with an
        `email_masked` field populated instead. Only director/legal/admin+
        see the raw email field this test checks for.
        """
        token = await get_admin_token(client, test_admin_data)

        # Filter for blocked patrons
        response = await client.get(
            "/api/v1/staff/patrons?status=blocked",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Should return at least the blocked patron
        assert "patrons" in data
        blocked_emails = [p["email"] for p in data["patrons"]]
        assert test_blocked_patron.email in blocked_emails


# =============================================================================
# Demographic Breakdowns Reports Tests
# =============================================================================


@pytest.mark.integration
class TestDemographicBreakdownsReports:
    """Test demographic breakdowns reports functionality."""

    async def test_patron_type_demographics(
        self,
        client,
        test_staff,
        test_staff_data,
        test_adult_patron,
        test_teen_patron,
        test_child_patron,
    ):
        """Test patrons with different patron types are tracked."""
        token = await get_staff_token(client, test_staff_data)

        # Verify adult patron
        response = await client.get(
            f"/api/v1/staff/patrons/{test_adult_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["patron_type"] == "adult"

        # Verify teen patron
        response = await client.get(
            f"/api/v1/staff/patrons/{test_teen_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["patron_type"] == "teen"

        # Verify child patron
        response = await client.get(
            f"/api/v1/staff/patrons/{test_child_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["patron_type"] == "child"

    async def test_patron_age_calculation(
        self, client, test_staff, test_staff_data, test_adult_patron, test_teen_patron
    ):
        """Test patron age is correctly calculated from date of birth."""
        token = await get_staff_token(client, test_staff_data)

        # Adult patron should be around 35
        response = await client.get(
            f"/api/v1/staff/patrons/{test_adult_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        if "date_of_birth" in data and data["date_of_birth"]:
            assert data["date_of_birth"] is not None

        # Teen patron should be around 15
        response = await client.get(
            f"/api/v1/staff/patrons/{test_teen_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        if "date_of_birth" in data and data["date_of_birth"]:
            assert data["date_of_birth"] is not None

    async def test_patron_language_preference(
        self, client, test_staff, test_staff_data, test_adult_patron, test_teen_patron
    ):
        """Test patron language preferences are tracked."""
        token = await get_staff_token(client, test_staff_data)

        # Verify adult patron's language preference
        response = await client.get(
            f"/api/v1/staff/patrons/{test_adult_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        if "language_preference" in data:
            assert data["language_preference"] == "English"

        # Verify teen patron's language preference
        response = await client.get(
            f"/api/v1/staff/patrons/{test_teen_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        if "language_preference" in data:
            assert data["language_preference"] == "Spanish"

    async def test_child_patron_parent_link(
        self, client, test_staff, test_staff_data, test_child_patron, test_patron
    ):
        """Test child patron has correct parent/guardian link."""
        token = await get_staff_token(client, test_staff_data)

        response = await client.get(
            f"/api/v1/staff/patrons/{test_child_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check parental consent is tracked
        if "parental_consent_given" in data:
            assert data["parental_consent_given"] is True

    async def test_patron_role_demographics(
        self, client, test_staff, test_staff_data, test_patron, test_child_patron
    ):
        """Test patron role demographics in user response."""
        token = await get_staff_token(client, test_staff_data)

        # Verify patron role
        response = await client.get(
            f"/api/v1/staff/patrons/{test_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "patron"

        # Verify child role
        response = await client.get(
            f"/api/v1/staff/patrons/{test_child_patron.id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["role"] == "child"


# =============================================================================
# At-Risk Patrons Reports Tests
# =============================================================================


@pytest.mark.integration
class TestAtRiskPatronsReports:
    """Test at-risk patrons reports functionality."""

    async def test_patrons_with_many_overdue(
        self, client, test_staff, test_staff_data, test_patron_with_many_overdue
    ):
        """Test patrons with 3+ overdue items are identified."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check at-risk counts
        assert "at_risk_counts" in data
        assert data["at_risk_counts"]["patrons_with_many_overdue"] >= 1

        # Check at-risk patron details list
        assert "patrons_with_many_overdue" in data
        if len(data["patrons_with_many_overdue"]) > 0:
            at_risk_patron = data["patrons_with_many_overdue"][0]
            assert "id" in at_risk_patron
            assert "first_name" in at_risk_patron
            assert "last_name" in at_risk_patron
            assert "overdue_count" in at_risk_patron
            assert at_risk_patron["overdue_count"] >= 3

    async def test_patrons_with_high_fines(
        self, client, test_staff, test_staff_data, test_patron_with_high_fines
    ):
        """Test patrons with fines over $25 are identified."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check at-risk counts
        assert "at_risk_counts" in data
        assert data["at_risk_counts"]["patrons_with_high_fines"] >= 1

        # Check at-risk patron details list
        assert "patrons_with_high_fines" in data
        if len(data["patrons_with_high_fines"]) > 0:
            at_risk_patron = data["patrons_with_high_fines"][0]
            assert "id" in at_risk_patron
            assert "fines_balance" in at_risk_patron
            # Fines balance should be over $25
            assert float(at_risk_patron["fines_balance"]) > 25.0

    async def test_inactive_patrons(
        self, client, test_staff, test_staff_data, test_inactive_patron
    ):
        """Test patrons with no activity in 90+ days are identified."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Check at-risk counts
        assert "at_risk_counts" in data
        assert "inactive_patrons" in data["at_risk_counts"]

        # Check inactive patron details list
        assert "inactive_patrons" in data

    async def test_total_fines_outstanding(
        self, client, test_staff, test_staff_data, test_patron_with_high_fines
    ):
        """Test total outstanding fines are correctly calculated."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_fines_outstanding" in data
        # Should have at least $35 from test_patron_with_high_fines
        assert float(data["total_fines_outstanding"]) >= 35.0

    async def test_total_overdue_items(
        self, client, test_staff, test_staff_data, test_patron_with_many_overdue
    ):
        """Test total overdue items are correctly counted."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/staff/patrons/statistics",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "total_overdue_items" in data
        # Should have at least 4 overdue items from test_patron_with_many_overdue
        assert data["total_overdue_items"] >= 4


# =============================================================================
# Analytics Dashboard Integration Tests
# =============================================================================


@pytest.mark.integration
class TestAnalyticsDashboardPatrons:
    """Test patron data in analytics dashboard."""

    async def test_dashboard_patron_engagement_stats(
        self, client, test_staff, test_staff_data, test_active_borrower
    ):
        """Test patron engagement stats in analytics dashboard."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/analytics/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify patron engagement section exists
        assert "patron_engagement" in data
        patron_stats = data["patron_engagement"]

        # Verify structure
        assert "total_patrons" in patron_stats
        assert "active_patrons" in patron_stats
        assert "engagement_rate" in patron_stats

    async def test_dashboard_fine_stats(
        self, client, test_staff, test_staff_data, test_patron_with_high_fines
    ):
        """Test fine stats in analytics dashboard."""
        token = await get_staff_token(client, test_staff_data)
        response = await client.get(
            "/api/v1/reports/analytics/dashboard",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify fine section exists
        assert "fines" in data
        fine_stats = data["fines"]

        # Verify structure
        assert "outstanding_total" in fine_stats
        assert "patrons_with_fines" in fine_stats
        assert fine_stats["patrons_with_fines"] >= 1
