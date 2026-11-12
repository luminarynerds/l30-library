# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Interlibrary Loan (ILL) service and API endpoints.

Tests cover:
- Partner library CRUD
- ILL request lifecycle (create, update, cancel, renew)
- Auto-search partner catalogs
- Tracking updates
- Cost tracking
- Due date reminders
- Shipping label generation
- Fill rate reporting
- Reciprocal lending dashboard
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.interlibrary_loan import (
    ILLCostCategory,
    ILLCostRecord,
    ILLRequest,
    ILLRequestStatus,
    ILLRequestType,
    ILLTrackingUpdate,
    PartnerLibrary,
    PartnerLibraryStatus,
    ShippingMethod,
)
from app.services.interlibrary_loan_service import InterlibraryLoanService, STATUS_LABELS


# =========================================================================
# Fixtures
# =========================================================================


@pytest.fixture
async def ill_service(test_db):
    """Create an ILL service instance backed by the test database."""
    return InterlibraryLoanService(test_db)


@pytest.fixture
async def partner_library(test_db):
    """Create a test partner library."""
    partner = PartnerLibrary(
        name="Elm Street Public Library",
        code="ESPL",
        address="123 Elm Street",
        city="Springfield",
        state="IL",
        zip_code="62704",
        country="US",
        contact_name="Jane Librarian",
        contact_email="jane@elmstreetlibrary.org",
        status=PartnerLibraryStatus.active,
        lending_fee=Decimal("0"),
        borrowing_fee=Decimal("0"),
        max_loan_days=21,
        max_renewals=1,
        reciprocal_agreement=True,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


@pytest.fixture
async def second_partner(test_db):
    """Create a second partner library with a fee."""
    partner = PartnerLibrary(
        name="Oak Valley Regional Library",
        code="OVRL",
        city="Oak Valley",
        state="CA",
        status=PartnerLibraryStatus.active,
        lending_fee=Decimal("5.00"),
        borrowing_fee=Decimal("3.00"),
        max_loan_days=14,
        max_renewals=0,
        reciprocal_agreement=False,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


@pytest.fixture
async def ill_request(test_db, test_patron, partner_library):
    """Create a test ILL borrow request."""
    req = ILLRequest(
        patron_id=test_patron.id,
        request_type=ILLRequestType.borrow,
        partner_library_id=partner_library.id,
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        isbn="978-0-7432-7356-5",
        status=ILLRequestStatus.pending,
    )
    test_db.add(req)
    await test_db.commit()
    await test_db.refresh(req)
    return req


# =========================================================================
# Partner Library Tests
# =========================================================================


@pytest.mark.integration
class TestPartnerLibraryManagement:
    """Test partner library CRUD operations."""

    async def test_create_partner_library(self, ill_service, test_db):
        partner = await ill_service.create_partner_library(
            name="New Partner Library",
            code="NPL",
            city="New Town",
            state="NY",
            lending_fee=Decimal("2.50"),
            reciprocal_agreement=False,
        )
        await test_db.commit()
        assert partner.id is not None
        assert partner.name == "New Partner Library"
        assert partner.code == "NPL"
        assert partner.lending_fee == Decimal("2.50")
        assert partner.status == PartnerLibraryStatus.active

    async def test_update_partner_library(self, ill_service, partner_library, test_db):
        updated = await ill_service.update_partner_library(
            partner_library.id,
            {"contact_email": "updated@example.com", "lending_fee": Decimal("1.00")},
        )
        await test_db.commit()
        assert updated is not None
        assert updated.contact_email == "updated@example.com"
        assert updated.lending_fee == Decimal("1.00")

    async def test_update_nonexistent_partner(self, ill_service):
        result = await ill_service.update_partner_library(99999, {"name": "X"})
        assert result is None

    async def test_get_partner_library(self, ill_service, partner_library):
        fetched = await ill_service.get_partner_library(partner_library.id)
        assert fetched is not None
        assert fetched.code == "ESPL"

    async def test_get_nonexistent_partner(self, ill_service):
        assert await ill_service.get_partner_library(99999) is None

    async def test_list_partner_libraries(self, ill_service, partner_library, second_partner):
        partners = await ill_service.list_partner_libraries()
        assert len(partners) >= 2
        names = {p.name for p in partners}
        assert "Elm Street Public Library" in names
        assert "Oak Valley Regional Library" in names

    async def test_list_partners_filter_by_status(self, ill_service, partner_library, test_db):
        # Suspend one partner
        partner_library.status = PartnerLibraryStatus.suspended
        await test_db.commit()
        active = await ill_service.list_partner_libraries(status=PartnerLibraryStatus.active)
        suspended = await ill_service.list_partner_libraries(status=PartnerLibraryStatus.suspended)
        assert all(p.status == PartnerLibraryStatus.active for p in active)
        assert all(p.status == PartnerLibraryStatus.suspended for p in suspended)

    async def test_list_partners_search(self, ill_service, partner_library, second_partner):
        results = await ill_service.list_partner_libraries(search="Elm")
        assert len(results) >= 1
        assert results[0].code == "ESPL"


# =========================================================================
# ILL Request Lifecycle Tests
# =========================================================================


@pytest.mark.integration
class TestILLRequestLifecycle:
    """Test the full ILL request lifecycle."""

    async def test_create_request(self, ill_service, test_patron, test_db):
        req = await ill_service.create_request(
            patron_id=test_patron.id,
            title="Moby Dick",
            author="Herman Melville",
            isbn="978-0-14-243724-7",
        )
        await test_db.commit()
        assert req.id is not None
        assert req.status == ILLRequestStatus.pending
        assert req.title == "Moby Dick"
        assert req.patron_id == test_patron.id
        assert req.request_type == ILLRequestType.borrow

    async def test_create_request_generates_tracking(self, ill_service, test_patron, test_db):
        req = await ill_service.create_request(
            patron_id=test_patron.id,
            title="A Test Book",
        )
        await test_db.commit()
        tracking = await ill_service.get_patron_tracking(req.id)
        assert len(tracking) >= 1
        assert tracking[0].status == ILLRequestStatus.pending

    async def test_get_request_with_relations(self, ill_service, ill_request):
        fetched = await ill_service.get_request(ill_request.id)
        assert fetched is not None
        assert fetched.partner_library is not None
        assert fetched.partner_library.code == "ESPL"

    async def test_list_requests_by_patron(self, ill_service, ill_request, test_patron):
        requests = await ill_service.list_requests(patron_id=test_patron.id)
        assert len(requests) >= 1
        assert all(r.patron_id == test_patron.id for r in requests)

    async def test_list_requests_active_only(self, ill_service, ill_request, test_db):
        # Complete the request
        ill_request.status = ILLRequestStatus.completed
        await test_db.commit()

        active = await ill_service.list_requests(active_only=True)
        assert all(r.status != ILLRequestStatus.completed for r in active)

    async def test_update_request_status(self, ill_service, ill_request, test_staff, test_db):
        # VALID_TRANSITIONS only allows submitted from 'located', not directly
        # from 'pending' (pending -> searching/cancelled only).
        ill_request.status = ILLRequestStatus.located
        await test_db.commit()
        result = await ill_service.update_request(
            ill_request.id,
            test_staff.id,
            {"status": ILLRequestStatus.submitted},
        )
        await test_db.commit()
        assert result is not None
        assert result.status == ILLRequestStatus.submitted

    async def test_update_request_sets_shipped_at(
        self, ill_service, ill_request, test_staff, test_db
    ):
        # VALID_TRANSITIONS only allows in_transit from 'approved', not
        # directly from 'pending'.
        ill_request.status = ILLRequestStatus.approved
        await test_db.commit()
        result = await ill_service.update_request(
            ill_request.id,
            test_staff.id,
            {"status": ILLRequestStatus.in_transit},
        )
        await test_db.commit()
        assert result.shipped_at is not None

    async def test_update_request_sets_received_at(
        self, ill_service, ill_request, test_staff, test_db
    ):
        ill_request.status = ILLRequestStatus.in_transit
        await test_db.commit()
        result = await ill_service.update_request(
            ill_request.id,
            test_staff.id,
            {"status": ILLRequestStatus.received},
        )
        await test_db.commit()
        assert result.received_at is not None

    async def test_update_request_checkout_sets_due_date(
        self, ill_service, ill_request, test_staff, test_db
    ):
        ill_request.status = ILLRequestStatus.received
        await test_db.commit()
        result = await ill_service.update_request(
            ill_request.id,
            test_staff.id,
            {"status": ILLRequestStatus.checked_out},
        )
        await test_db.commit()
        assert result.checked_out_at is not None
        assert result.due_date is not None

    async def test_cancel_request(self, ill_service, ill_request, test_patron, test_db):
        result = await ill_service.cancel_request(ill_request.id, test_patron.id)
        await test_db.commit()
        assert result is not None
        assert result.status == ILLRequestStatus.cancelled

    async def test_cancel_non_cancellable_request(
        self, ill_service, ill_request, test_patron, test_db
    ):
        ill_request.status = ILLRequestStatus.checked_out
        await test_db.commit()
        result = await ill_service.cancel_request(ill_request.id, test_patron.id)
        assert result is None

    async def test_renew_request(self, ill_service, ill_request, test_staff, test_db):
        ill_request.status = ILLRequestStatus.checked_out
        ill_request.due_date = date.today() + timedelta(days=5)
        await test_db.commit()

        result = await ill_service.renew_request(ill_request.id, test_staff.id)
        await test_db.commit()
        assert result is not None
        assert result.renewal_count == 1
        assert result.due_date > date.today() + timedelta(days=5)

    async def test_renew_max_reached(self, ill_service, ill_request, test_staff, test_db):
        ill_request.status = ILLRequestStatus.checked_out
        ill_request.renewal_count = 1
        ill_request.max_renewals = 1
        ill_request.due_date = date.today() + timedelta(days=5)
        await test_db.commit()

        result = await ill_service.renew_request(ill_request.id, test_staff.id)
        assert result is None

    async def test_renew_not_checked_out(self, ill_service, ill_request, test_staff):
        result = await ill_service.renew_request(ill_request.id, test_staff.id)
        assert result is None  # Status is pending, not checked_out


# =========================================================================
# Auto-Search Tests
# =========================================================================


@pytest.mark.integration
class TestAutoSearch:
    """Test partner catalog auto-search functionality."""

    async def test_search_partner_catalogs(self, ill_service, partner_library):
        results = await ill_service.search_partner_catalogs(title="Any Book")
        assert len(results) >= 1
        assert results[0]["partner_library_name"] == partner_library.name

    async def test_auto_search_and_submit(
        self, ill_service, ill_request, test_staff, partner_library, test_db
    ):
        result = await ill_service.auto_search_and_submit(ill_request.id, test_staff.id)
        await test_db.commit()
        assert result is not None
        assert result.status == ILLRequestStatus.submitted
        assert result.partner_library_id == partner_library.id

    async def test_auto_search_prefers_free_partners(
        self, ill_service, ill_request, test_staff, partner_library, second_partner, test_db
    ):
        # Reciprocal (free) partner should be preferred
        result = await ill_service.auto_search_and_submit(ill_request.id, test_staff.id)
        await test_db.commit()
        assert result.partner_library_id == partner_library.id  # Free partner


# =========================================================================
# Tracking Updates Tests
# =========================================================================


@pytest.mark.integration
class TestTrackingUpdates:
    """Test patron-visible tracking updates."""

    async def test_add_tracking_update(self, ill_service, ill_request, test_staff, test_db):
        tracking = await ill_service.add_tracking_update(
            request_id=ill_request.id,
            status=ILLRequestStatus.pending,
            message="We are working on your request.",
            created_by_id=test_staff.id,
        )
        await test_db.commit()
        assert tracking.id is not None
        assert tracking.message == "We are working on your request."

    async def test_get_patron_tracking_only_visible(
        self, ill_service, ill_request, test_staff, test_db
    ):
        await ill_service.add_tracking_update(
            ill_request.id, ILLRequestStatus.pending, "Visible", is_patron_visible=True
        )
        await ill_service.add_tracking_update(
            ill_request.id, ILLRequestStatus.pending, "Staff-only", is_patron_visible=False
        )
        await test_db.commit()
        visible = await ill_service.get_patron_tracking(ill_request.id)
        messages = [t.message for t in visible]
        assert "Visible" in messages
        assert "Staff-only" not in messages


# =========================================================================
# Cost Tracking Tests
# =========================================================================


@pytest.mark.integration
class TestCostTracking:
    """Test ILL cost tracking."""

    async def test_add_cost_record(self, ill_service, ill_request, test_staff, test_db):
        cost = await ill_service.add_cost_record(
            request_id=ill_request.id,
            category=ILLCostCategory.shipping,
            amount=Decimal("4.50"),
            description="USPS Media Mail",
            created_by_id=test_staff.id,
        )
        await test_db.commit()
        assert cost.id is not None
        assert cost.amount == Decimal("4.50")
        assert cost.category == ILLCostCategory.shipping

    async def test_cost_updates_request_total(self, ill_service, ill_request, test_staff, test_db):
        await ill_service.add_cost_record(ill_request.id, ILLCostCategory.shipping, Decimal("4.50"))
        await ill_service.add_cost_record(
            ill_request.id, ILLCostCategory.lending_fee, Decimal("5.00")
        )
        await test_db.commit()
        await test_db.refresh(ill_request)
        assert ill_request.actual_cost == Decimal("9.50")

    async def test_get_cost_records(self, ill_service, ill_request, test_staff, test_db):
        await ill_service.add_cost_record(ill_request.id, ILLCostCategory.shipping, Decimal("3.00"))
        await ill_service.add_cost_record(
            ill_request.id, ILLCostCategory.processing, Decimal("2.00")
        )
        await test_db.commit()
        records = await ill_service.get_cost_records(ill_request.id)
        assert len(records) == 2

    async def test_get_cost_summary(self, ill_service, ill_request, test_staff, test_db):
        await ill_service.add_cost_record(ill_request.id, ILLCostCategory.shipping, Decimal("5.00"))
        await test_db.commit()
        summary = await ill_service.get_cost_summary(
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() + timedelta(days=1),
        )
        assert summary["total_borrowing_costs"] >= Decimal("5.00")


# =========================================================================
# Due Date Reminders Tests
# =========================================================================


@pytest.mark.integration
class TestDueDateReminders:
    """Test due date reminder queries."""

    async def test_get_upcoming_due_requests(self, ill_service, ill_request, test_db):
        ill_request.status = ILLRequestStatus.checked_out
        ill_request.due_date = date.today() + timedelta(days=3)
        await test_db.commit()

        upcoming = await ill_service.get_upcoming_due_requests(days_ahead=7)
        assert len(upcoming) >= 1
        assert any(r.id == ill_request.id for r in upcoming)

    async def test_get_overdue_requests(self, ill_service, ill_request, test_db):
        ill_request.status = ILLRequestStatus.checked_out
        ill_request.due_date = date.today() - timedelta(days=2)
        await test_db.commit()

        overdue = await ill_service.get_overdue_requests()
        assert len(overdue) >= 1
        assert any(r.id == ill_request.id for r in overdue)

    async def test_upcoming_excludes_far_dates(self, ill_service, ill_request, test_db):
        ill_request.status = ILLRequestStatus.checked_out
        ill_request.due_date = date.today() + timedelta(days=30)
        await test_db.commit()

        upcoming = await ill_service.get_upcoming_due_requests(days_ahead=7)
        assert not any(r.id == ill_request.id for r in upcoming)


# =========================================================================
# Shipping Label Tests
# =========================================================================


@pytest.mark.integration
class TestShippingLabel:
    """Test return shipping label generation."""

    async def test_generate_label(self, ill_service, ill_request, partner_library):
        label = await ill_service.generate_return_shipping_label(ill_request.id)
        assert label is not None
        assert label["to_library"] == "Elm Street Public Library"
        assert label["to_city"] == "Springfield"
        assert label["label_format"] == "pdf"

    async def test_generate_label_nonexistent_request(self, ill_service):
        label = await ill_service.generate_return_shipping_label(99999)
        assert label is None


# =========================================================================
# Fill Rate Reporting Tests
# =========================================================================


@pytest.mark.integration
class TestFillRateReporting:
    """Test fill rate report generation."""

    async def test_fill_rate_report_empty(self, ill_service):
        report = await ill_service.get_fill_rate_report(
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() + timedelta(days=1),
        )
        assert report["total_requests"] == 0
        assert report["fill_rate_percent"] == 0

    async def test_fill_rate_with_data(self, ill_service, ill_request, test_db):
        ill_request.status = ILLRequestStatus.completed
        await test_db.commit()

        report = await ill_service.get_fill_rate_report(
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() + timedelta(days=1),
        )
        assert report["total_requests"] >= 1


# =========================================================================
# Reciprocal Lending Dashboard Tests
# =========================================================================


@pytest.mark.integration
class TestReciprocalLendingDashboard:
    """Test reciprocal lending dashboard."""

    async def test_dashboard_empty(self, ill_service, partner_library):
        dashboard = await ill_service.get_reciprocal_lending_dashboard(
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() + timedelta(days=1),
        )
        assert dashboard["total_partners"] >= 1
        assert dashboard["active_partners"] >= 1

    async def test_dashboard_with_data(self, ill_service, ill_request, partner_library, test_db):
        dashboard = await ill_service.get_reciprocal_lending_dashboard(
            period_start=date.today() - timedelta(days=30),
            period_end=date.today() + timedelta(days=1),
        )
        stats = dashboard["partner_stats"]
        espl = next((s for s in stats if s["partner_library_code"] == "ESPL"), None)
        assert espl is not None
        assert espl["items_borrowed"] >= 1


# =========================================================================
# Status Labels Tests
# =========================================================================


@pytest.mark.integration
class TestStatusLabels:
    """Test human-readable status labels."""

    def test_all_statuses_have_labels(self):
        for status in ILLRequestStatus:
            assert status in STATUS_LABELS, f"Missing label for {status}"

    def test_labels_are_nonempty(self):
        for status, label in STATUS_LABELS.items():
            assert label, f"Empty label for {status}"
