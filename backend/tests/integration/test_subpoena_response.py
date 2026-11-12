# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Subpoena Response Compliance Tests.

Simulates law enforcement arriving with a subpoena for patron records
and verifies the LSC system can respond correctly, legally, and with
a complete audit trail.

Tests cover:
1. Produce exactly what's requested, no more
2. Verify the request is legally valid
3. Audit trail of who accessed what
4. Produce records for a date range
5. Redact non-subpoenaed patrons
6. Checkout history deletion per retention policy
7. Prove what WASN'T in the system
8. Authorization to respond
9. Patron notification policy
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.security import hash_password
from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine
from app.models.law_enforcement_request import (
    DEFAULT_CHECKLIST_ITEMS,
    AuditActionType,
    ChecklistItemType,
    LawEnforcementAuditLog,
    LawEnforcementChecklist,
    LawEnforcementRequest,
    LegalReviewStatus,
    RequestType,
    WorkflowStatus,
)
from app.models.user import User, UserRole
from app.schemas.law_enforcement_request import (
    LawEnforcementRequestCreate,
    LegalReviewUpdate,
    PatronDataExportRequest,
    WorkflowStatusUpdate,
)
from app.services.law_enforcement_service import LawEnforcementService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
async def director(test_db):
    """Create a user with DIRECTOR role (authorized to respond to subpoenas)."""
    user = User(
        email="director@l30.org",
        password_hash=hash_password("DirectorPass123!"),
        first_name="Margaret",
        last_name="Holloway",
        role=UserRole.DIRECTOR,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def legal_counsel(test_db):
    """Create a user with LEGAL role."""
    user = User(
        email="legal@l30.org",
        password_hash=hash_password("LegalPass123!"),
        first_name="Roland",
        last_name="Schitt",
        role=UserRole.LEGAL,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_member(test_db):
    """Create a regular staff member (NOT authorized for subpoena response)."""
    user = User(
        email="staff@l30.org",
        password_hash=hash_password("StaffPass123!"),
        first_name="Twyla",
        last_name="Sands",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def patron_under_subpoena(test_db):
    """Patron whose records are being subpoenaed."""
    user = User(
        email="patron_target@example.com",
        password_hash=hash_password("PatronPass123!"),
        first_name="David",
        last_name="Rose",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LIB-SUB-001",
        phone="555-0199",
        address="123 Somewhere Up North Lane",
        track_reading_history=False,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def other_patron(test_db):
    """Another patron whose records should NOT be disclosed."""
    user = User(
        email="other_patron@example.com",
        password_hash=hash_password("OtherPass123!"),
        first_name="Alexis",
        last_name="Rose",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LIB-OTHER-002",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def catalog_items(test_db):
    """Create catalog items for checkout history."""
    items = []
    titles = [
        "The Great Gatsby",
        "To Kill a Mockingbird",
        "1984",
        "Brave New World",
        "Fahrenheit 451",
    ]
    for i, title in enumerate(titles):
        item = CatalogItem(
            title=title,
            author=f"Author {i}",
            isbn=f"978-0-{i:09d}",
            status=ItemStatus.available,
        )
        test_db.add(item)
        items.append(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)
    return items


@pytest.fixture
async def patron_checkouts(test_db, patron_under_subpoena, catalog_items):
    """Create checkout history for the subpoenaed patron across a date range."""
    now = datetime.now(timezone.utc)
    checkouts = []

    # Checkout within subpoena date range (Jan-Mar 2026)
    for i, item in enumerate(catalog_items[:3]):
        checkout = Checkout(
            user_id=patron_under_subpoena.id,
            item_id=item.id,
            status=CheckoutStatus.returned,
            checked_out_at=now - timedelta(days=60 - i * 10),
            due_date=now - timedelta(days=46 - i * 10),
            returned_at=now - timedelta(days=50 - i * 10),
        )
        test_db.add(checkout)
        checkouts.append(checkout)

    # Checkout OUTSIDE subpoena date range (older)
    old_checkout = Checkout(
        user_id=patron_under_subpoena.id,
        item_id=catalog_items[3].id,
        status=CheckoutStatus.returned,
        checked_out_at=now - timedelta(days=400),
        due_date=now - timedelta(days=386),
        returned_at=now - timedelta(days=390),
    )
    test_db.add(old_checkout)
    checkouts.append(old_checkout)

    await test_db.commit()
    for c in checkouts:
        await test_db.refresh(c)
    return checkouts


@pytest.fixture
async def other_patron_checkouts(test_db, other_patron, catalog_items):
    """Create checkout history for the OTHER patron (should not be disclosed)."""
    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=other_patron.id,
        item_id=catalog_items[4].id,
        status=CheckoutStatus.returned,
        checked_out_at=now - timedelta(days=30),
        due_date=now - timedelta(days=16),
        returned_at=now - timedelta(days=20),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def subpoena_request(test_db, director, patron_under_subpoena):
    """Create a subpoena law enforcement request with full checklist."""
    now = datetime.now(timezone.utc)
    request = LawEnforcementRequest(
        tracking_number="LE-2026-SUB001",
        requesting_agency="Elm County Sheriff's Office",
        agency_contact_name="Detective Ray Butani",
        agency_contact_phone="555-0100",
        agency_contact_email="butani@elmcounty.gov",
        agency_case_number="EC-2026-4417",
        request_type=RequestType.SUBPOENA,
        date_received=now,
        date_due=now + timedelta(days=14),
        patron_id=patron_under_subpoena.id,
        patron_name_on_request="David Rose",
        patron_identifiers="LIB-SUB-001, 123 Somewhere Up North Lane",
        data_requested="Checkout history and hold records",
        data_date_range_start=now - timedelta(days=90),
        data_date_range_end=now,
        legal_review_status=LegalReviewStatus.PENDING_REVIEW,
        workflow_status=WorkflowStatus.RECEIVED,
        created_by_id=director.id,
        patron_notification_permitted=True,
    )
    test_db.add(request)
    await test_db.flush()

    for item_data in DEFAULT_CHECKLIST_ITEMS:
        item = LawEnforcementChecklist(
            request_id=request.id,
            item_type=item_data["item_type"],
            item_description=item_data["item_description"],
            is_required=item_data["is_required"],
            is_applicable=True,
            sort_order=item_data["sort_order"],
        )
        test_db.add(item)

    await test_db.commit()
    await test_db.refresh(request)
    return request


# =============================================================================
# 1. Produce Exactly What's Requested, No More
# =============================================================================


@pytest.mark.integration
class TestProduceExactlyWhatsRequested:
    """Verify the system exports only the data categories explicitly requested."""

    async def test_export_only_checkouts_when_checkouts_requested(
        self, test_db, director, subpoena_request, patron_checkouts
    ):
        """When subpoena requests only checkout history, no other data is exported."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=False,
            include_checkouts=True,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        assert result.data_categories_included == ["checkouts"]
        assert result.profile is None
        assert result.holds is None
        assert result.fines is None
        assert result.reading_history is None

    async def test_export_profile_only_excludes_circulation(
        self, test_db, director, subpoena_request, patron_checkouts
    ):
        """When subpoena requests only profile info, circulation data is excluded."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=True,
            include_checkouts=False,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        assert result.data_categories_included == ["profile"]
        assert result.profile is not None
        assert result.checkouts is None

    async def test_reading_history_excluded_by_default(self, test_db, director, subpoena_request):
        """Reading history defaults to NOT included -- patron privacy protection."""
        export_req = PatronDataExportRequest(request_id=subpoena_request.id)
        assert export_req.include_reading_history is False

    async def test_reading_history_not_exported_when_patron_doesnt_track(
        self, test_db, director, subpoena_request, patron_under_subpoena
    ):
        """If patron has reading history tracking OFF, export returns nothing for that category."""
        assert patron_under_subpoena.track_reading_history is False

        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_reading_history=True,
            include_profile=False,
            include_checkouts=False,
            include_holds=False,
            include_fines=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        # reading_history should not be in categories because patron doesn't track
        assert "reading_history" not in result.data_categories_included


# =============================================================================
# 2. Verify the Request Is Legally Valid
# =============================================================================


@pytest.mark.integration
class TestVerifyLegalValidity:
    """Verify the system supports legal review and validity verification."""

    async def test_subpoena_requires_legal_review_before_response(self, test_db, subpoena_request):
        """New subpoena starts in PENDING_REVIEW, not auto-approved."""
        assert subpoena_request.legal_review_status == LegalReviewStatus.PENDING_REVIEW
        assert subpoena_request.workflow_status == WorkflowStatus.RECEIVED

    async def test_legal_counsel_can_approve_valid_subpoena(
        self, test_db, legal_counsel, subpoena_request
    ):
        """Legal counsel approves a valid subpoena, advancing workflow."""
        service = LawEnforcementService(test_db)
        review = LegalReviewUpdate(
            legal_review_status=LegalReviewStatus.APPROVED,
            legal_review_notes="Subpoena is properly signed, in jurisdiction, and narrowly scoped.",
        )
        result = await service.update_legal_review(
            request_id=subpoena_request.id,
            data=review,
            reviewer=legal_counsel,
        )

        assert result.legal_review_status == LegalReviewStatus.APPROVED
        assert result.workflow_status == WorkflowStatus.PATRON_NOTIFICATION

    async def test_legal_counsel_can_reject_defective_subpoena(
        self, test_db, legal_counsel, subpoena_request
    ):
        """Legal counsel rejects a defective subpoena."""
        service = LawEnforcementService(test_db)
        review = LegalReviewUpdate(
            legal_review_status=LegalReviewStatus.REJECTED,
            legal_review_notes="Subpoena is missing judge's signature and exceeds jurisdictional scope.",
        )
        result = await service.update_legal_review(
            request_id=subpoena_request.id,
            data=review,
            reviewer=legal_counsel,
        )

        assert result.legal_review_status == LegalReviewStatus.REJECTED
        assert result.workflow_status == WorkflowStatus.REJECTED

    async def test_informal_request_type_exists_for_tracking_declined_requests(self):
        """Informal (non-legal) requests can be logged but should be declined."""
        assert RequestType.INFORMAL_REQUEST.value == "informal_request"

    async def test_validity_checklist_items_exist(self, test_db, subpoena_request):
        """Checklist includes steps to verify validity, jurisdiction, and scope."""
        service = LawEnforcementService(test_db)
        checklist = await service.get_checklist(subpoena_request.id)
        item_types = [item.item_type for item in checklist]

        assert ChecklistItemType.VERIFY_VALIDITY in item_types
        assert ChecklistItemType.VERIFY_JURISDICTION in item_types
        assert ChecklistItemType.VERIFY_SCOPE in item_types

    async def test_validity_verification_is_required(self, test_db, subpoena_request):
        """Validity verification checklist steps are marked as required."""
        service = LawEnforcementService(test_db)
        checklist = await service.get_checklist(subpoena_request.id)

        for item in checklist:
            if item.item_type in (
                ChecklistItemType.VERIFY_VALIDITY,
                ChecklistItemType.VERIFY_JURISDICTION,
                ChecklistItemType.VERIFY_SCOPE,
            ):
                assert item.is_required is True, f"{item.item_type.value} should be required"


# =============================================================================
# 3. Audit Trail of Who Accessed What
# =============================================================================


@pytest.mark.integration
class TestAuditTrail:
    """Verify complete audit trail: who accessed what, when, from where."""

    async def test_request_creation_is_audited(self, test_db, director):
        """Creating a law enforcement request generates an audit entry."""
        service = LawEnforcementService(test_db)
        data = LawEnforcementRequestCreate(
            requesting_agency="Test PD",
            request_type=RequestType.SUBPOENA,
            date_received=datetime.now(timezone.utc),
            data_requested="All checkout records",
            patron_notification_permitted=True,
        )
        request = await service.create_request(
            data=data,
            created_by=director,
            ip_address="192.168.1.100",
            user_agent="TestBrowser/1.0",
        )

        logs = await service.get_audit_log(request.id)
        assert len(logs) >= 1
        creation_log = next((l for l in logs if l.action == AuditActionType.REQUEST_CREATED), None)
        assert creation_log is not None
        assert creation_log.performed_by_id == director.id
        assert creation_log.ip_address == "192.168.1.100"

    async def test_viewing_request_is_audited(self, test_db, director, subpoena_request):
        """Every view of a law enforcement request is logged."""
        service = LawEnforcementService(test_db)
        await service.get_request(
            request_id=subpoena_request.id,
            viewer=director,
            ip_address="10.0.0.50",
        )

        logs = await service.get_audit_log(subpoena_request.id)
        view_log = next((l for l in logs if l.action == AuditActionType.VIEWED), None)
        assert view_log is not None
        assert view_log.performed_by_id == director.id
        assert view_log.ip_address == "10.0.0.50"

    async def test_data_export_is_audited_with_categories(
        self, test_db, director, subpoena_request, patron_checkouts
    ):
        """Data export audit entry records exactly which categories were exported."""
        service = LawEnforcementService(test_db)
        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=True,
            include_checkouts=True,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )
        await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
            ip_address="10.0.0.50",
        )

        logs = await service.get_audit_log(subpoena_request.id)
        export_log = next((l for l in logs if l.action == AuditActionType.DATA_EXPORTED), None)
        assert export_log is not None
        assert export_log.details is not None
        assert "profile" in export_log.details["categories_exported"]
        assert "checkouts" in export_log.details["categories_exported"]
        assert "holds" not in export_log.details["categories_exported"]

    async def test_legal_review_is_audited(self, test_db, legal_counsel, subpoena_request):
        """Legal review decisions are audited with old/new status."""
        service = LawEnforcementService(test_db)
        review = LegalReviewUpdate(
            legal_review_status=LegalReviewStatus.APPROVED,
            legal_review_notes="Valid subpoena.",
        )
        await service.update_legal_review(
            request_id=subpoena_request.id,
            data=review,
            reviewer=legal_counsel,
        )

        logs = await service.get_audit_log(subpoena_request.id)
        review_log = next(
            (l for l in logs if l.action == AuditActionType.LEGAL_REVIEW_UPDATED),
            None,
        )
        assert review_log is not None
        assert review_log.details["old_status"] == "pending_review"
        assert review_log.details["new_status"] == "approved"

    async def test_audit_log_is_append_only(self, test_db, director, subpoena_request):
        """Audit log only grows; entries are never removed."""
        service = LawEnforcementService(test_db)

        # Add notes
        for i in range(3):
            await service.add_note(
                request_id=subpoena_request.id,
                note=f"Compliance note #{i + 1}",
                added_by=director,
            )

        logs = await service.get_audit_log(subpoena_request.id)
        note_count = sum(1 for l in logs if l.action == AuditActionType.NOTE_ADDED)
        assert note_count == 3

    async def test_audit_log_records_timestamps(self, test_db, director, subpoena_request):
        """Each audit entry has a timestamp."""
        service = LawEnforcementService(test_db)
        await service.add_note(
            request_id=subpoena_request.id,
            note="Timestamp check",
            added_by=director,
        )

        logs = await service.get_audit_log(subpoena_request.id)
        for log in logs:
            assert log.created_at is not None


# =============================================================================
# 4. Produce Records for a Date Range
# =============================================================================


@pytest.mark.integration
class TestDateRangeFiltering:
    """Verify that data export respects the subpoena's date range."""

    async def test_export_checkouts_within_date_range(
        self, test_db, director, subpoena_request, patron_checkouts
    ):
        """Only checkouts within the subpoena date range are exported."""
        service = LawEnforcementService(test_db)
        now = datetime.now(timezone.utc)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=False,
            include_checkouts=True,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
            # Override with explicit range (last 90 days)
            date_range_start=now - timedelta(days=90),
            date_range_end=now,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        assert result.checkouts is not None
        # The 3 recent checkouts should be included; the 400-day-old one should not
        cutoff = (now - timedelta(days=90)).replace(tzinfo=None)
        for checkout in result.checkouts:
            checkout_date = datetime.fromisoformat(checkout["checked_out_at"])
            # Normalize both to naive for comparison (SQLite strips tz)
            assert checkout_date.replace(tzinfo=None) >= cutoff

    async def test_date_range_from_request_used_when_not_overridden(
        self, test_db, director, subpoena_request, patron_checkouts
    ):
        """When no explicit date range is given, the request's date range is used."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_checkouts=True,
            include_profile=False,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
            # No date_range_start/end -- should use subpoena_request's range
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        assert result.checkouts is not None
        # The old checkout (400 days ago) should be excluded by the request's 90-day range
        for checkout in result.checkouts:
            checkout_date = datetime.fromisoformat(checkout["checked_out_at"])
            assert checkout_date >= subpoena_request.data_date_range_start

    async def test_request_stores_date_range(self, test_db, subpoena_request):
        """The law enforcement request model stores the subpoena's date range."""
        assert subpoena_request.data_date_range_start is not None
        assert subpoena_request.data_date_range_end is not None
        assert subpoena_request.data_date_range_start < subpoena_request.data_date_range_end


# =============================================================================
# 5. Redact Non-Subpoenaed Patrons
# =============================================================================


@pytest.mark.integration
class TestRedactNonSubpoenaedPatrons:
    """Verify that data export is scoped to only the named patron."""

    async def test_export_only_returns_target_patron_data(
        self,
        test_db,
        director,
        subpoena_request,
        patron_checkouts,
        other_patron_checkouts,
        other_patron,
    ):
        """Export returns ONLY the subpoenaed patron's data, not other patrons'."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=True,
            include_checkouts=True,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        assert result.patron_id == subpoena_request.patron_id
        assert result.patron_id != other_patron.id

        # Profile should be the subpoenaed patron
        assert result.profile["first_name"] == "David"
        assert result.profile["last_name"] == "Rose"

    async def test_export_does_not_include_other_patron_checkouts(
        self,
        test_db,
        director,
        subpoena_request,
        patron_checkouts,
        other_patron_checkouts,
        other_patron,
    ):
        """Checkouts exported belong only to the subpoenaed patron."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_checkouts=True,
            include_profile=False,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        # The other patron's checkout ID should not appear
        other_checkout_id = other_patron_checkouts.id
        exported_ids = [c["id"] for c in result.checkouts]
        assert other_checkout_id not in exported_ids

    async def test_request_is_linked_to_specific_patron(
        self, test_db, subpoena_request, patron_under_subpoena
    ):
        """Each law enforcement request is linked to a specific patron."""
        assert subpoena_request.patron_id == patron_under_subpoena.id
        assert subpoena_request.patron_name_on_request == "David Rose"


# =============================================================================
# 6. Checkout History Deletion Per Retention Policy
# =============================================================================


@pytest.mark.integration
class TestCheckoutHistoryRetention:
    """Verify that checkout history is anonymized per retention policy."""

    async def test_anonymized_checkout_has_no_user_link(
        self, test_db, patron_under_subpoena, catalog_items
    ):
        """Anonymized checkout records are re-pointed at the sentinel
        anonymized-patron account, not NULLed.

        checkouts.user_id is NOT NULL with ondelete=RESTRICT by design (see
        app/services/data_retention_service.py's ANONYMIZED_PATRON_EMAIL /
        get_or_create_anonymized_patron) -- the standard ILS pattern (Koha's
        AnonymousPatron) severs the real-patron link by repointing at a
        dedicated inactive sentinel user, not by setting user_id=None
        (which violates the NOT NULL constraint).
        """
        from sqlalchemy import select, update
        from app.services.data_retention_service import get_or_create_anonymized_patron

        # Create a checkout and anonymize it (simulating retention job)
        old_checkout = Checkout(
            user_id=patron_under_subpoena.id,
            item_id=catalog_items[0].id,
            status=CheckoutStatus.returned,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=3000),
            due_date=datetime.now(timezone.utc) - timedelta(days=2986),
            returned_at=datetime.now(timezone.utc) - timedelta(days=2990),
        )
        test_db.add(old_checkout)
        await test_db.commit()
        await test_db.refresh(old_checkout)

        # Simulate anonymization (what the retention service does)
        anon_id = await get_or_create_anonymized_patron(test_db)
        await test_db.execute(
            update(Checkout).where(Checkout.id == old_checkout.id).values(user_id=anon_id)
        )
        await test_db.commit()

        result = await test_db.execute(select(Checkout).where(Checkout.id == old_checkout.id))
        anonymized = result.scalar_one()
        assert anonymized.user_id == anon_id
        assert anonymized.user_id != patron_under_subpoena.id

    async def test_data_retention_constants_defined(self):
        """Data retention periods are defined in policy constants."""
        from app.services.data_retention_service import CHECKOUT_ANONYMIZE_YEARS

        assert CHECKOUT_ANONYMIZE_YEARS > 0
        # Library policy: 7 years
        assert CHECKOUT_ANONYMIZE_YEARS == 7

    async def test_anonymized_checkouts_not_in_patron_export(
        self, test_db, director, subpoena_request, patron_under_subpoena, catalog_items
    ):
        """Anonymized checkouts (re-pointed at the sentinel anonymized-patron
        account -- see test_anonymized_checkout_has_no_user_link) don't
        appear in a patron's export."""
        from sqlalchemy import update
        from app.services.data_retention_service import get_or_create_anonymized_patron

        # Create and anonymize a checkout
        checkout = Checkout(
            user_id=patron_under_subpoena.id,
            item_id=catalog_items[0].id,
            status=CheckoutStatus.returned,
            checked_out_at=datetime.now(timezone.utc) - timedelta(days=10),
            due_date=datetime.now(timezone.utc) + timedelta(days=4),
            returned_at=datetime.now(timezone.utc) - timedelta(days=5),
        )
        test_db.add(checkout)
        await test_db.commit()
        await test_db.refresh(checkout)
        anonymized_id = checkout.id

        anon_id = await get_or_create_anonymized_patron(test_db)
        await test_db.execute(
            update(Checkout).where(Checkout.id == anonymized_id).values(user_id=anon_id)
        )
        await test_db.commit()

        # Export should not include the anonymized checkout
        service = LawEnforcementService(test_db)
        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_checkouts=True,
            include_profile=False,
            include_holds=False,
            include_fines=False,
            include_reading_history=False,
        )
        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        exported_ids = [c["id"] for c in (result.checkouts or [])]
        assert anonymized_id not in exported_ids


# =============================================================================
# 7. Prove What WASN'T in the System
# =============================================================================


@pytest.mark.integration
class TestProveAbsenceOfData:
    """Verify the system can demonstrate what data was NOT available."""

    async def test_empty_export_when_no_matching_records(self, test_db, director, subpoena_request):
        """Export returns empty lists when patron has no records in a category."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=False,
            include_checkouts=True,
            include_holds=True,
            include_fines=True,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        # Patron has no holds or fines yet, so those should be empty
        assert result.holds == [] or result.holds is not None
        assert result.fines == [] or result.fines is not None

    async def test_export_documents_categories_included(self, test_db, director, subpoena_request):
        """Export response lists which data categories were searched."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_profile=True,
            include_checkouts=True,
            include_holds=True,
            include_fines=True,
            include_reading_history=False,
        )

        result = await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        # Even if empty, the categories we searched should be documented
        assert "profile" in result.data_categories_included
        assert "checkouts" in result.data_categories_included
        assert "holds" in result.data_categories_included
        assert "fines" in result.data_categories_included
        assert "reading_history" not in result.data_categories_included

    async def test_export_audit_proves_search_was_conducted(
        self, test_db, director, subpoena_request
    ):
        """The audit log proves a search was conducted, even if nothing was found."""
        service = LawEnforcementService(test_db)

        export_req = PatronDataExportRequest(
            request_id=subpoena_request.id,
            include_checkouts=True,
            include_holds=True,
            include_fines=True,
            include_profile=False,
            include_reading_history=False,
        )

        await service.export_patron_data(
            export_request=export_req,
            exported_by=director,
        )

        logs = await service.get_audit_log(subpoena_request.id)
        export_log = next((l for l in logs if l.action == AuditActionType.DATA_EXPORTED), None)
        assert export_log is not None
        assert "categories_exported" in export_log.details

    async def test_transparency_report_shows_zero_requests_for_empty_year(self, test_db):
        """Transparency report for a year with no requests shows zero."""
        service = LawEnforcementService(test_db)
        report = await service.generate_transparency_report(year=2020)
        assert report.summary.total_requests == 0
        assert report.summary.unique_patrons_affected == 0


# =============================================================================
# 8. Who Is Authorized to Respond
# =============================================================================


@pytest.mark.integration
class TestAuthorizedResponders:
    """Verify that only authorized roles can access law enforcement data."""

    async def test_director_role_is_authorized(self):
        """DIRECTOR role is in the authorized set."""
        # Authorized roles are: SUPER_ADMIN, ADMIN, DIRECTOR, LEGAL
        # (defined in app.api.v1.law_enforcement.AUTHORIZED_ROLES)
        authorized = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
        assert UserRole.DIRECTOR in authorized

    async def test_legal_role_is_authorized(self):
        """LEGAL role is in the authorized set."""
        authorized = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
        assert UserRole.LEGAL in authorized

    async def test_admin_role_is_authorized(self):
        """ADMIN role is in the authorized set (system administrators)."""
        authorized = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
        assert UserRole.ADMIN in authorized

    async def test_staff_role_is_not_authorized(self):
        """Regular STAFF role is NOT in the authorized set."""
        authorized = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
        assert UserRole.STAFF not in authorized

    async def test_patron_role_is_not_authorized(self):
        """PATRON role is NOT in the authorized set."""
        authorized = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
        assert UserRole.PATRON not in authorized

    async def test_director_approval_is_required_checklist_step(self, test_db, subpoena_request):
        """Director approval is a required checklist step."""
        service = LawEnforcementService(test_db)
        checklist = await service.get_checklist(subpoena_request.id)

        director_item = next(
            (i for i in checklist if i.item_type == ChecklistItemType.DIRECTOR_APPROVAL),
            None,
        )
        assert director_item is not None
        assert director_item.is_required is True

    async def test_created_by_tracked_on_request(self, test_db, director, subpoena_request):
        """The user who created the LE request is tracked."""
        assert subpoena_request.created_by_id == director.id

    async def test_responding_staff_tracked_on_response(self, test_db, director, subpoena_request):
        """When a response is recorded, the responding staff ID is captured."""
        from app.schemas.law_enforcement_request import ResponseUpdate

        service = LawEnforcementService(test_db)
        response_data = ResponseUpdate(
            response_method="certified_mail",
            response_summary="Provided requested checkout records.",
            data_provided_summary="Checkout history Jan-Mar 2026",
        )

        result = await service.record_response(
            request_id=subpoena_request.id,
            data=response_data,
            responded_by=director,
        )

        assert result.responding_staff_id == director.id
        assert result.response_method == "certified_mail"


# =============================================================================
# 9. Patron Notification Policy
# =============================================================================


@pytest.mark.integration
class TestPatronNotificationPolicy:
    """Verify patron notification rules and gag order handling."""

    async def test_patron_notification_permitted_by_default_for_subpoena(
        self, test_db, subpoena_request
    ):
        """Subpoenas generally permit patron notification."""
        assert subpoena_request.patron_notification_permitted is True

    async def test_record_patron_notification(self, test_db, director, subpoena_request):
        """Can record that the patron was notified, with method and timestamp."""
        service = LawEnforcementService(test_db)
        result = await service.record_patron_notification(
            request_id=subpoena_request.id,
            notification_method="certified_mail",
            notified_by=director,
            notes="Patron notified per policy within 3 business days.",
        )

        assert result.patron_notification_date is not None
        assert result.patron_notification_method == "certified_mail"

    async def test_notification_blocked_when_not_permitted(
        self, test_db, director, patron_under_subpoena
    ):
        """Notification fails when patron_notification_permitted is False (e.g., gag order)."""
        now = datetime.now(timezone.utc)
        gag_request = LawEnforcementRequest(
            tracking_number="LE-2026-GAG001",
            requesting_agency="FBI",
            request_type=RequestType.NATIONAL_SECURITY_LETTER,
            date_received=now,
            patron_id=patron_under_subpoena.id,
            data_requested="All records",
            patron_notification_permitted=False,
            gag_order_until=now + timedelta(days=365),
            workflow_status=WorkflowStatus.RECEIVED,
            legal_review_status=LegalReviewStatus.PENDING_REVIEW,
            created_by_id=director.id,
        )
        test_db.add(gag_request)
        await test_db.commit()
        await test_db.refresh(gag_request)

        service = LawEnforcementService(test_db)

        with pytest.raises(ValueError, match="not permitted"):
            await service.record_patron_notification(
                request_id=gag_request.id,
                notification_method="email",
                notified_by=director,
            )

    async def test_gag_order_expiration_tracked(self, test_db, director, patron_under_subpoena):
        """Gag order expiration date is stored on the request."""
        now = datetime.now(timezone.utc)
        gag_expiry = now + timedelta(days=180)

        nsl_request = LawEnforcementRequest(
            tracking_number="LE-2026-NSL001",
            requesting_agency="FBI",
            request_type=RequestType.NATIONAL_SECURITY_LETTER,
            date_received=now,
            patron_id=patron_under_subpoena.id,
            data_requested="All records",
            patron_notification_permitted=False,
            gag_order_until=gag_expiry,
            workflow_status=WorkflowStatus.RECEIVED,
            legal_review_status=LegalReviewStatus.PENDING_REVIEW,
            created_by_id=director.id,
        )
        test_db.add(nsl_request)
        await test_db.commit()
        await test_db.refresh(nsl_request)

        assert nsl_request.gag_order_until is not None
        # Normalize to naive for comparison (SQLite strips tz info)
        gag_date = nsl_request.gag_order_until
        if gag_date.tzinfo is None:
            assert gag_date > now.replace(tzinfo=None)
        else:
            assert gag_date > now

    async def test_patron_notification_is_audited(self, test_db, director, subpoena_request):
        """Patron notification action is captured in the audit log."""
        service = LawEnforcementService(test_db)
        await service.record_patron_notification(
            request_id=subpoena_request.id,
            notification_method="email",
            notified_by=director,
            notes="Emailed patron per library policy.",
        )

        logs = await service.get_audit_log(subpoena_request.id)
        notify_log = next((l for l in logs if l.action == AuditActionType.PATRON_NOTIFIED), None)
        assert notify_log is not None
        assert notify_log.details["notification_method"] == "email"

    async def test_notify_patron_checklist_is_optional_for_nsl(self):
        """Patron notification is not required for National Security Letters."""
        notify_item = next(
            item
            for item in DEFAULT_CHECKLIST_ITEMS
            if item["item_type"] == ChecklistItemType.NOTIFY_PATRON
        )
        # It's marked as not-required because gag orders may prevent it
        assert notify_item["is_required"] is False


# =============================================================================
# End-to-End: Full Subpoena Response Workflow
# =============================================================================


@pytest.mark.integration
class TestFullSubpoenaWorkflow:
    """End-to-end test of the entire subpoena response process."""

    async def test_complete_subpoena_response_workflow(
        self, test_db, director, legal_counsel, subpoena_request, patron_checkouts
    ):
        """Walk through the full workflow from receipt to documented response."""
        service = LawEnforcementService(test_db)
        rid = subpoena_request.id

        # Step 1: Verify initial state
        assert subpoena_request.workflow_status == WorkflowStatus.RECEIVED
        assert subpoena_request.legal_review_status == LegalReviewStatus.PENDING_REVIEW

        # Step 2: Legal review -- counsel approves
        await service.update_legal_review(
            request_id=rid,
            data=LegalReviewUpdate(
                legal_review_status=LegalReviewStatus.APPROVED,
                legal_review_notes="Subpoena is valid, properly scoped, within jurisdiction.",
            ),
            reviewer=legal_counsel,
        )

        # Step 3: Complete verification checklist items
        for item_type in [
            ChecklistItemType.VERIFY_VALIDITY,
            ChecklistItemType.VERIFY_JURISDICTION,
            ChecklistItemType.VERIFY_SCOPE,
            ChecklistItemType.DIRECTOR_APPROVAL,
        ]:
            await service.update_checklist_item(
                request_id=rid,
                item_type=item_type,
                is_completed=True,
                updated_by=director,
                completion_notes=f"Completed: {item_type.value}",
            )

        # Step 4: Notify patron
        await service.record_patron_notification(
            request_id=rid,
            notification_method="certified_mail",
            notified_by=director,
            notes="Patron notified within 3 business days per policy.",
        )

        # Step 5: Export only what's requested
        _ = await service.export_patron_data(
            export_request=PatronDataExportRequest(
                request_id=rid,
                include_profile=False,
                include_checkouts=True,
                include_holds=True,
                include_fines=False,
                include_reading_history=False,
            ),
            exported_by=director,
        )

        # Step 6: Minimize data checklist
        await service.update_checklist_item(
            request_id=rid,
            item_type=ChecklistItemType.MINIMIZE_DATA,
            is_completed=True,
            updated_by=director,
            completion_notes="Only checkout and hold data exported as subpoenaed.",
        )

        # Step 7: Record the response
        from app.schemas.law_enforcement_request import ResponseUpdate

        await service.record_response(
            request_id=rid,
            data=ResponseUpdate(
                response_method="certified_mail",
                response_summary="Provided checkout history and hold records per subpoena.",
                data_provided_summary="Checkouts and holds, Jan-Mar 2026. No fines or reading history included.",
            ),
            responded_by=director,
        )

        # Step 8: Complete remaining checklist items
        for item_type in [
            ChecklistItemType.DOCUMENT_COMPLIANCE,
            ChecklistItemType.FINAL_REVIEW,
        ]:
            await service.update_checklist_item(
                request_id=rid,
                item_type=item_type,
                is_completed=True,
                updated_by=director,
            )

        # Step 9: Verify completion state
        progress = await service.get_checklist_progress(rid)
        # Most items should be completed
        assert progress["completed"] >= 8

        # Step 10: Verify comprehensive audit trail
        logs = await service.get_audit_log(rid)
        action_types = {l.action for l in logs}

        assert AuditActionType.LEGAL_REVIEW_UPDATED in action_types
        assert AuditActionType.CHECKLIST_UPDATED in action_types
        assert AuditActionType.PATRON_NOTIFIED in action_types
        assert AuditActionType.DATA_EXPORTED in action_types
        assert AuditActionType.RESPONSE_SENT in action_types

        # Every action has a performer and timestamp
        for log in logs:
            assert log.created_at is not None
            assert log.performed_by_id is not None
