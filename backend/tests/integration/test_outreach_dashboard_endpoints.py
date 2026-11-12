# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for outreach dashboard, statistics, and reports endpoints.

Tests cover:
- GET /outreach/dashboard - overall program metrics with top partners
- GET /outreach/statistics - detailed stats (visits, cards, checkouts)
- POST /outreach/reports - custom date-range report
"""

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient


# ============ Fixtures ============


@pytest.fixture
async def staff_user(test_db):
    """Create a staff user for outreach operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="dashboard_staff@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Dashboard",
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
async def patron_user(test_db):
    """Create a patron user for permission testing."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="dashboard_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Dashboard",
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
def staff_token(staff_user):
    """Create an access token for the staff user."""
    from app.core.security import create_access_token

    return create_access_token(staff_user.id, email=staff_user.email)


@pytest.fixture
def patron_token(patron_user):
    """Create an access token for the patron user."""
    from app.core.security import create_access_token

    return create_access_token(patron_user.id, email=patron_user.email)


@pytest.fixture
async def async_client(test_db, monkeypatch):
    """Create async test client with overridden database dependency."""
    import app.core.security as security_module
    from app.core.database import get_db
    from app.main import app

    # Routers are registered unconditionally at import time in app/main.py now
    # (register_all_routers(app, ...) runs at module load) -- no lazy/startup-event
    # registration or _routers_registered flag left to check.

    # Bypass token revocation check (no Redis in test environment)
    monkeypatch.setattr(security_module, "is_token_revoked", lambda token: False)

    async def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db

    # Bypass FirstBootMiddleware: tests use an empty DB with no admin users,
    # which would otherwise trip the setup-required check on every request.
    app.state.setup_complete = True

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def sample_partner(test_db, staff_user):
    """Create a sample outreach partner."""
    from app.models.outreach import OutreachPartner

    partner = OutreachPartner(
        name="Lincoln Elementary School",
        partner_type="school",
        status="active",
        address_line1="123 School St",
        city="Bébé Memorial",
        state="CA",
        zip_code="90210",
        primary_contact_name="Jane Smith",
        primary_contact_email="jsmith@lincoln.edu",
        school_level="elementary",
        student_count=450,
        allows_bulk_checkout=True,
        allows_institutional_card=True,
        requires_deposit=True,
        default_deposit_amount=50.0,
        checkout_limit=100,
        loan_period_days=28,
        partnership_start_date=date.today() - timedelta(days=30),
        created_by_id=staff_user.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


@pytest.fixture
async def second_partner(test_db, staff_user):
    """Create a second outreach partner."""
    from app.models.outreach import OutreachPartner

    partner = OutreachPartner(
        name="Sunrise Daycare",
        partner_type="daycare",
        status="active",
        city="Bébé Memorial",
        primary_contact_name="Bob Jones",
        allows_bulk_checkout=True,
        allows_institutional_card=False,
        checkout_limit=50,
        loan_period_days=14,
        partnership_start_date=date.today() - timedelta(days=10),
        created_by_id=staff_user.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


@pytest.fixture
async def completed_visit(test_db, sample_partner, staff_user):
    """Create a completed outreach visit for current month."""
    from app.models.outreach import OutreachVisit

    visit = OutreachVisit(
        partner_id=sample_partner.id,
        visit_type="storytime",
        status="completed",
        title="Weekly Storytime",
        scheduled_date=date.today() - timedelta(days=2),
        actual_attendees=25,
        new_cards_issued=3,
        books_checked_out=15,
        items_delivered=20,
        lead_staff_id=staff_user.id,
        created_by_id=staff_user.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)
    return visit


@pytest.fixture
async def scheduled_visit(test_db, sample_partner, staff_user):
    """Create a scheduled future visit."""
    from app.models.outreach import OutreachVisit

    visit = OutreachVisit(
        partner_id=sample_partner.id,
        visit_type="book_delivery",
        status="scheduled",
        title="Book Delivery",
        scheduled_date=date.today() + timedelta(days=5),
        expected_attendees=30,
        items_to_deliver=50,
        lead_staff_id=staff_user.id,
        created_by_id=staff_user.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)
    return visit


@pytest.fixture
async def bulk_checkout(test_db, sample_partner, staff_user):
    """Create a bulk checkout for testing."""
    from app.models.outreach import BulkCheckout

    checkout = BulkCheckout(
        partner_id=sample_partner.id,
        checkout_name="3rd Grade Reading",
        status="active",
        requestor_name="Mrs. Johnson",
        requestor_email="mjohnson@lincoln.edu",
        # Clamp to month start: the statistics endpoint windows on the calendar
        # month, so "5 days ago" lands in the prior month on the 1st-5th and
        # zeroes bulk_items_checked_out.
        checkout_date=max(date.today() - timedelta(days=5), date.today().replace(day=1)),
        due_date=date.today() + timedelta(days=23),
        total_items=30,
        processed_by_id=staff_user.id,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def overdue_bulk_checkout(test_db, sample_partner, staff_user):
    """Create an overdue bulk checkout."""
    from app.models.outreach import BulkCheckout

    checkout = BulkCheckout(
        partner_id=sample_partner.id,
        checkout_name="Overdue Classroom Set",
        status="active",
        requestor_name="Mr. Adams",
        checkout_date=date.today() - timedelta(days=40),
        due_date=date.today() - timedelta(days=5),
        total_items=20,
        processed_by_id=staff_user.id,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def institutional_card(test_db, sample_partner, staff_user):
    """Create an institutional card."""
    from app.models.outreach import InstitutionalCard

    card = InstitutionalCard(
        partner_id=sample_partner.id,
        card_number="INST-DASH-001",
        card_name="Lincoln Elementary Card",
        status="active",
        checkout_limit=100,
        # Clamp to month start: statistics windows on the calendar month, so
        # "7 days ago" is the prior month on the 1st-7th and zeroes
        # institutional_cards_issued.
        issued_date=max(date.today() - timedelta(days=7), date.today().replace(day=1)),
        issued_by_id=staff_user.id,
    )
    test_db.add(card)
    await test_db.commit()
    await test_db.refresh(card)
    return card


@pytest.fixture
async def deposit(test_db, sample_partner, staff_user):
    """Create a deposit."""
    from app.models.outreach import OutreachDeposit

    dep = OutreachDeposit(
        partner_id=sample_partner.id,
        deposit_type="classroom_checkout",
        status="held",
        amount=50.0,
        payment_method="check",
        collected_date=date.today() - timedelta(days=3),
        collected_by_id=staff_user.id,
    )
    test_db.add(dep)
    await test_db.commit()
    await test_db.refresh(dep)
    return dep


@pytest.fixture
async def populated_data(
    sample_partner,
    second_partner,
    completed_visit,
    scheduled_visit,
    bulk_checkout,
    overdue_bulk_checkout,
    institutional_card,
    deposit,
):
    """Aggregate fixture that ensures all sample data is created."""
    return {
        "partners": [sample_partner, second_partner],
        "visits": [completed_visit, scheduled_visit],
        "bulk_checkouts": [bulk_checkout, overdue_bulk_checkout],
        "institutional_card": institutional_card,
        "deposit": deposit,
    }


# ============ Dashboard Endpoint Tests ============


class TestOutreachDashboard:
    """Tests for GET /outreach/dashboard."""

    @pytest.mark.asyncio
    async def test_dashboard_returns_metrics(self, async_client, staff_token, populated_data):
        """Test that dashboard returns all required metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Verify partner counts
        assert "active_partners" in data
        assert data["active_partners"] >= 2

        # Verify visit totals
        assert "pending_visits" in data
        assert data["pending_visits"] >= 1  # scheduled_visit
        assert "visits_this_month" in data

        # Verify cards issued
        assert "new_cards_this_month" in data

        # Verify items circulated
        assert "items_circulated_this_month" in data

        # Verify overdue checkouts
        assert "overdue_bulk_checkouts" in data
        assert data["overdue_bulk_checkouts"] >= 1

        # Verify deposits held
        assert "deposits_held" in data
        assert data["deposits_held"] >= 50.0

    @pytest.mark.asyncio
    async def test_dashboard_includes_visit_lists(self, async_client, staff_token, populated_data):
        """Test that dashboard includes recent and upcoming visit lists."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert "recent_visits" in data
        assert "upcoming_visits" in data
        assert isinstance(data["recent_visits"], list)
        assert isinstance(data["upcoming_visits"], list)

        # Should have at least 1 recent completed visit
        assert len(data["recent_visits"]) >= 1
        # Should have at least 1 upcoming scheduled visit
        assert len(data["upcoming_visits"]) >= 1

    @pytest.mark.asyncio
    async def test_dashboard_includes_top_partners(self, async_client, staff_token, populated_data):
        """Test that dashboard includes top partners by checkouts and visits."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert "top_partners_by_checkouts" in data
        assert "top_partners_by_visits" in data
        assert isinstance(data["top_partners_by_checkouts"], list)
        assert isinstance(data["top_partners_by_visits"], list)

        # sample_partner has bulk checkouts so should appear
        if data["top_partners_by_checkouts"]:
            partner = data["top_partners_by_checkouts"][0]
            assert "id" in partner
            assert "name" in partner
            assert "partner_type" in partner

    @pytest.mark.asyncio
    async def test_dashboard_requires_auth(self, async_client):
        """Test that dashboard requires authentication."""
        response = await async_client.get("/api/v1/outreach/dashboard")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_dashboard_requires_staff(self, async_client, patron_token):
        """Test that dashboard requires staff role."""
        headers = {"Authorization": f"Bearer {patron_token}"}
        response = await async_client.get("/api/v1/outreach/dashboard", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_empty_data(self, async_client, staff_token):
        """Test dashboard with no outreach data returns zero metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/dashboard", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["active_partners"] == 0
        assert data["pending_visits"] == 0
        assert data["overdue_bulk_checkouts"] == 0
        assert data["visits_this_month"] == 0
        assert data["new_cards_this_month"] == 0
        assert data["items_circulated_this_month"] == 0


# ============ Statistics Endpoint Tests ============


class TestOutreachStatistics:
    """Tests for GET /outreach/statistics."""

    @pytest.mark.asyncio
    async def test_statistics_returns_all_metrics(self, async_client, staff_token, populated_data):
        """Test that statistics endpoint returns comprehensive metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # Partner metrics
        assert "total_partners" in data
        assert data["total_partners"] >= 2
        assert "active_partners" in data
        assert data["active_partners"] >= 2
        assert "new_partners" in data
        assert "partners_by_type" in data
        assert isinstance(data["partners_by_type"], dict)

        # Visit metrics
        assert "total_visits" in data
        assert "visits_completed" in data
        assert "visits_cancelled" in data
        assert "total_attendees" in data
        assert "visits_by_type" in data
        assert isinstance(data["visits_by_type"], dict)

        # Checkout metrics
        assert "bulk_checkouts_created" in data
        assert "bulk_items_checked_out" in data

        # Card metrics
        assert "institutional_cards_active" in data
        assert data["institutional_cards_active"] >= 1
        assert "institutional_cards_issued" in data
        assert "institutional_checkouts" in data

        # Deposit metrics
        assert "deposits_collected" in data

        # Impact metrics
        assert "new_cards_from_outreach" in data

    @pytest.mark.asyncio
    async def test_statistics_partner_counts(self, async_client, staff_token, populated_data):
        """Test partner counts include correct totals."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["total_partners"] >= 2
        assert data["active_partners"] >= 2
        # Check partners_by_type has school and daycare
        assert "school" in data["partners_by_type"]
        assert "daycare" in data["partners_by_type"]

    @pytest.mark.asyncio
    async def test_statistics_visit_totals(self, async_client, staff_token, populated_data):
        """Test visit totals are accurate."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # We have 1 completed visit in the current month
        assert data["visits_completed"] >= 1
        assert data["total_attendees"] >= 25  # from completed_visit

    @pytest.mark.asyncio
    async def test_statistics_cards_issued(self, async_client, staff_token, populated_data):
        """Test cards issued metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["institutional_cards_active"] >= 1
        # Fixture clamps issued_date into the current calendar month
        assert data["institutional_cards_issued"] >= 1

    @pytest.mark.asyncio
    async def test_statistics_items_circulated(self, async_client, staff_token, populated_data):
        """Test items circulated stats."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        # bulk_checkout has 30 items, overdue has 20 items
        assert data["bulk_items_checked_out"] >= 30

    @pytest.mark.asyncio
    async def test_statistics_requires_staff(self, async_client, patron_token):
        """Test that statistics requires staff role."""
        headers = {"Authorization": f"Bearer {patron_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_statistics_empty_data(self, async_client, staff_token):
        """Test statistics with no data returns zero metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["total_partners"] == 0
        assert data["total_visits"] == 0
        assert data["bulk_items_checked_out"] == 0
        assert data["institutional_cards_active"] == 0
        assert data["deposits_collected"] == 0.0

    @pytest.mark.asyncio
    async def test_statistics_period_is_current_month(
        self, async_client, staff_token, populated_data
    ):
        """Test that statistics period covers the current month."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await async_client.get("/api/v1/outreach/statistics", headers=headers)

        assert response.status_code == 200
        data = response.json()

        today = date.today()
        month_start = today.replace(day=1)
        assert data["period_start"] == str(month_start)
        assert data["period_end"] == str(today)


# ============ Reports Endpoint Tests ============


class TestOutreachReports:
    """Tests for POST /outreach/reports."""

    @pytest.mark.asyncio
    async def test_report_basic(self, async_client, staff_token, populated_data):
        """Test basic report generation with date range."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()

        assert "report_period" in data
        assert "generated_at" in data
        assert "statistics" in data

        stats = data["statistics"]
        # Verify all key metric categories are present
        assert "total_partners" in stats
        assert stats["total_partners"] >= 2
        assert "active_partners" in stats
        assert "total_visits" in stats
        assert "visits_completed" in stats
        assert "total_attendees" in stats
        assert "bulk_checkouts_created" in stats
        assert "bulk_items_checked_out" in stats
        assert "institutional_cards_active" in stats
        assert "institutional_cards_issued" in stats
        assert "deposits_collected" in stats
        assert "new_cards_from_outreach" in stats
        assert "partners_by_type" in stats
        assert "visits_by_type" in stats

    @pytest.mark.asyncio
    async def test_report_partner_counts(self, async_client, staff_token, populated_data):
        """Test report includes accurate partner counts."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=60)),
            "end_date": str(today),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        assert stats["total_partners"] >= 2
        assert stats["active_partners"] >= 2

    @pytest.mark.asyncio
    async def test_report_visit_totals(self, async_client, staff_token, populated_data):
        """Test report includes visit totals."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today + timedelta(days=30)),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        # Both completed_visit and scheduled_visit fall in range
        assert stats["total_visits"] >= 2
        assert stats["visits_completed"] >= 1
        assert stats["total_attendees"] >= 25

    @pytest.mark.asyncio
    async def test_report_cards_issued(self, async_client, staff_token, populated_data):
        """Test report includes cards issued metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        assert stats["institutional_cards_issued"] >= 1
        assert stats["new_cards_from_outreach"] >= 3  # from completed_visit

    @pytest.mark.asyncio
    async def test_report_items_circulated(self, async_client, staff_token, populated_data):
        """Test report includes items circulated."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=60)),
            "end_date": str(today),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        # bulk_checkout=30 items, overdue_bulk_checkout=20 items
        assert stats["bulk_items_checked_out"] >= 50

    @pytest.mark.asyncio
    async def test_report_with_include_details(self, async_client, staff_token, populated_data):
        """Test report with include_details returns detailed breakdowns."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=60)),
            "end_date": str(today + timedelta(days=30)),
            "include_details": True,
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        data = response.json()

        assert data["partner_details"] is not None
        assert len(data["partner_details"]) >= 2

        assert data["visit_details"] is not None
        assert len(data["visit_details"]) >= 1

        assert data["bulk_checkout_details"] is not None
        assert len(data["bulk_checkout_details"]) >= 1

    @pytest.mark.asyncio
    async def test_report_filter_by_partner_ids(self, async_client, staff_token, populated_data):
        """Test report filtered by specific partner IDs."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        partner_id = populated_data["partners"][0].id
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today + timedelta(days=30)),
            "partner_ids": [partner_id],
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        # Only visits for sample_partner should be included
        assert stats["total_visits"] >= 1

    @pytest.mark.asyncio
    async def test_report_filter_by_partner_types(self, async_client, staff_token, populated_data):
        """Test report filtered by partner types."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today),
            "partner_types": ["school"],
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        # Filtered to schools only
        assert stats["total_partners"] >= 1

    @pytest.mark.asyncio
    async def test_report_invalid_date_range(self, async_client, staff_token):
        """Test report with start_date after end_date returns 400."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        today = date.today()
        payload = {
            "start_date": str(today),
            "end_date": str(today - timedelta(days=30)),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_report_requires_staff(self, async_client, patron_token):
        """Test that reports require staff role."""
        headers = {"Authorization": f"Bearer {patron_token}"}
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today),
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_report_requires_auth(self, async_client):
        """Test that reports require authentication."""
        today = date.today()
        payload = {
            "start_date": str(today - timedelta(days=30)),
            "end_date": str(today),
        }
        response = await async_client.post("/api/v1/outreach/reports", json=payload)
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_report_empty_date_range(self, async_client, staff_token):
        """Test report with date range containing no data returns zero metrics."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "start_date": "2020-01-01",
            "end_date": "2020-01-31",
        }
        response = await async_client.post(
            "/api/v1/outreach/reports", headers=headers, json=payload
        )

        assert response.status_code == 200
        stats = response.json()["statistics"]
        assert stats["total_visits"] == 0
        assert stats["bulk_checkouts_created"] == 0
        assert stats["institutional_checkouts"] == 0
