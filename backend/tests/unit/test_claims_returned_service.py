# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for Claims Returned Dispute Workflow.

Tests the complete workflow for when a patron claims they returned an item:
1. Patron files a claim
2. Staff reviews and flags for search
3. Resolution (approve/deny/item found)

Test coverage includes:
- Filing claims (patron and staff)
- Claim eligibility validation
- Patron claims history tracking
- Review and search workflow
- Resolution with credits
- Patron yearly claim limits
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.models.catalog import CatalogItem, ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.inventory import ItemCopy, ItemCondition
from app.models.lost_damaged import (
    ClaimsReturnedDispute,
    ClaimDisputeStatus,
    LostDamagedSettings,
    LostItemRecord,
    LostItemStatus,
    LostItemType,
)
from app.models.user import User, UserRole
from app.services.claims_returned_service import ClaimsReturnedService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_settings(test_db):
    """Create test lost/damaged settings."""
    settings = LostDamagedSettings(
        branch_location=None,  # System-wide
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
        due_date=datetime.now(timezone.utc) - timedelta(days=7),  # Overdue
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def test_overdue_checkout(test_db, test_patron_for_claim, test_catalog_item_for_claim, test_item_copy_for_claim):
    """Create an overdue checkout."""
    checkout = Checkout(
        user_id=test_patron_for_claim.id,
        item_id=test_catalog_item_for_claim.id,
        item_copy_id=test_item_copy_for_claim.id,
        status=CheckoutStatus.overdue,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=30),
        due_date=datetime.now(timezone.utc) - timedelta(days=14),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def test_returned_checkout(test_db, test_patron_for_claim, test_catalog_item_for_claim, test_item_copy_for_claim):
    """Create a returned checkout (not eligible for claims)."""
    checkout = Checkout(
        user_id=test_patron_for_claim.id,
        item_id=test_catalog_item_for_claim.id,
        item_copy_id=test_item_copy_for_claim.id,
        status=CheckoutStatus.returned,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=14),
        due_date=datetime.now(timezone.utc) - timedelta(days=7),
        returned_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


# ============================================================================
# Test Filing Claims
# ============================================================================


@pytest.mark.unit
class TestFileClaim:
    """Tests for filing claims returned disputes."""

    async def test_file_claim_success(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test successfully filing a claims returned dispute."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book to the Main Branch book drop on Tuesday afternoon around 3pm.",
            claimed_return_date=date.today() - timedelta(days=3),
            claimed_return_location="Main Branch Book Drop",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is True
        assert result.dispute is not None
        assert result.dispute.status == ClaimDisputeStatus.PENDING
        assert result.dispute.patron_id == test_patron_for_claim.id
        assert result.dispute.checkout_id == test_active_checkout.id
        assert "Main Branch Book Drop" in result.dispute.claimed_return_location
        assert result.message == "Claims returned dispute filed successfully"

    async def test_file_claim_updates_checkout_status(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test that filing a claim updates checkout status to claims_returned."""
        service = ClaimsReturnedService(test_db)

        await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I dropped off the book last week at the front desk.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        await test_db.refresh(test_active_checkout)
        assert test_active_checkout.status == CheckoutStatus.claims_returned

    async def test_file_claim_creates_lost_item_record(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test that filing a claim creates a lost item record with correct type."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this item to the library last Monday.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Check lost item record was created. file_claim() doesn't
        # selectinload dispute.lost_item_record (it's created after the
        # dispute in the same call), so a bare attribute access lazy-loads
        # it -- and outside the session's own greenlet that raises
        # MissingGreenlet. Refresh explicitly first.
        await test_db.refresh(result.dispute, attribute_names=["lost_item_record"])
        lost_record = result.dispute.lost_item_record
        assert lost_record is not None
        assert lost_record.lost_type == LostItemType.CLAIMS_RETURNED
        assert lost_record.status == LostItemStatus.DISPUTE_PENDING
        assert lost_record.patron_id == test_patron_for_claim.id

    async def test_file_claim_for_overdue_checkout(
        self, test_db, test_settings, test_patron_for_claim, test_overdue_checkout
    ):
        """Test filing a claim for an overdue checkout."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=test_overdue_checkout.id,
            patron_statement="I definitely returned this book two weeks ago.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is True
        assert result.dispute.status == ClaimDisputeStatus.PENDING

    async def test_file_claim_for_returned_checkout_fails(
        self, test_db, test_settings, test_patron_for_claim, test_returned_checkout
    ):
        """Test that filing a claim for an already returned checkout fails."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=test_returned_checkout.id,
            patron_statement="I need to dispute this return.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is False
        assert "not eligible" in result.message.lower()

    async def test_file_claim_nonexistent_checkout(
        self, test_db, test_settings, test_patron_for_claim
    ):
        """Test filing a claim for a nonexistent checkout fails."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=99999,
            patron_statement="This checkout does not exist.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    async def test_file_claim_records_patron_previous_claims(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test that filing a claim records patron's previous claims count."""
        service = ClaimsReturnedService(test_db)

        result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="This is my first claim for this item.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is True
        assert result.dispute.patron_previous_claims_count == 0


# ============================================================================
# Test Claim Eligibility and Limits
# ============================================================================


@pytest.mark.unit
class TestClaimEligibility:
    """Tests for claim eligibility and yearly limits."""

    async def test_patron_claims_history_empty(
        self, test_db, test_settings, test_patron_for_claim
    ):
        """Test patron claims history for patron with no claims."""
        service = ClaimsReturnedService(test_db)

        history = await service.get_patron_claims_history(test_patron_for_claim.id)

        assert history.total_claims == 0
        assert history.claims_this_year == 0
        assert history.approved_claims == 0
        assert history.denied_claims == 0
        assert history.pending_claims == 0
        assert history.is_at_risk is False
        assert history.max_claims_allowed == 3

    async def test_patron_claims_history_with_claims(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test patron claims history after filing a claim."""
        service = ClaimsReturnedService(test_db)

        # File a claim
        await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Testing claims history tracking.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        history = await service.get_patron_claims_history(test_patron_for_claim.id)

        assert history.total_claims == 1
        assert history.claims_this_year == 1
        assert history.pending_claims == 1
        assert history.approved_claims == 0
        assert history.denied_claims == 0

    async def test_patron_at_risk_near_limit(
        self, test_db, test_settings, test_patron_for_claim
    ):
        """Test is_at_risk flag when patron is near claims limit."""
        # Create 2 existing claims (one less than max of 3)
        for i in range(2):
            dispute = ClaimsReturnedDispute(
                lost_item_record_id=None,
                patron_id=test_patron_for_claim.id,
                checkout_id=None,
                status=ClaimDisputeStatus.APPROVED,
                patron_statement=f"Previous claim {i}",
                filed_at=datetime.now(timezone.utc),
            )
            test_db.add(dispute)

        # Create a placeholder lost item record for the disputes
        lost_record = LostItemRecord(
            patron_id=test_patron_for_claim.id,
            status=LostItemStatus.DISPUTE_PENDING,
            lost_type=LostItemType.CLAIMS_RETURNED,
        )
        test_db.add(lost_record)
        await test_db.commit()

        # Update disputes with lost_item_record_id
        from sqlalchemy import select
        result = await test_db.execute(
            select(ClaimsReturnedDispute).where(
                ClaimsReturnedDispute.patron_id == test_patron_for_claim.id
            )
        )
        disputes = result.scalars().all()
        for d in disputes:
            d.lost_item_record_id = lost_record.id
        await test_db.commit()

        service = ClaimsReturnedService(test_db)
        history = await service.get_patron_claims_history(test_patron_for_claim.id)

        # At 2 claims out of 3 max, patron should be at risk
        assert history.claims_this_year == 2
        assert history.is_at_risk is True

    async def test_exceed_yearly_claims_limit(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test that exceeding yearly claims limit is rejected."""
        # Create max claims (3) for this year
        lost_record = LostItemRecord(
            patron_id=test_patron_for_claim.id,
            status=LostItemStatus.DISPUTE_PENDING,
            lost_type=LostItemType.CLAIMS_RETURNED,
        )
        test_db.add(lost_record)
        await test_db.flush()

        for i in range(3):
            dispute = ClaimsReturnedDispute(
                lost_item_record_id=lost_record.id,
                patron_id=test_patron_for_claim.id,
                checkout_id=None,
                status=ClaimDisputeStatus.PENDING,
                patron_statement=f"Claim {i}",
                filed_at=datetime.now(timezone.utc),
            )
            test_db.add(dispute)
        await test_db.commit()

        # Try to file another claim
        service = ClaimsReturnedService(test_db)
        result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="This should be rejected due to limit.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        assert result.success is False
        assert "maximum claims limit" in result.message.lower()


# ============================================================================
# Test Staff Review Workflow
# ============================================================================


@pytest.mark.unit
class TestReviewWorkflow:
    """Tests for the staff review workflow."""

    async def test_start_review(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test starting a review on a pending claim."""
        service = ClaimsReturnedService(test_db)

        # First file a claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book last week.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Then start review
        review_result = await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
            initial_notes="Starting investigation. Will check book drop logs.",
        )

        assert review_result.success is True
        assert review_result.dispute.status == ClaimDisputeStatus.UNDER_REVIEW
        assert review_result.dispute.reviewed_by_id == test_staff_for_claim.id
        assert review_result.dispute.reviewed_at is not None
        assert "Starting investigation" in review_result.dispute.investigation_notes

    async def test_start_review_on_already_reviewed_fails(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test that starting review on non-pending claim fails."""
        service = ClaimsReturnedService(test_db)

        # File and start review
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book last week.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )
        await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
        )

        # Try to start review again
        result = await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
        )

        assert result.success is False
        assert "not in pending status" in result.message.lower()

    async def test_start_review_nonexistent_dispute(
        self, test_db, test_settings, test_staff_for_claim
    ):
        """Test starting review on nonexistent dispute fails."""
        service = ClaimsReturnedService(test_db)

        result = await service.start_review(
            dispute_id=99999,
            reviewed_by=test_staff_for_claim,
        )

        assert result.success is False
        assert "not found" in result.message.lower()


# ============================================================================
# Test Search Workflow
# ============================================================================


@pytest.mark.unit
class TestSearchWorkflow:
    """Tests for the staff search workflow (flagging for search)."""

    async def test_start_search(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test starting a search for a claimed returned item."""
        service = ClaimsReturnedService(test_db)

        # File a claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this at the Main Branch.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Start search
        search_result = await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Main Branch Book Drop", "Main Branch Shelving Cart", "Main Branch Returns Desk"],
            search_notes="Will search all possible return locations at Main Branch.",
        )

        assert search_result.success is True
        assert search_result.dispute.status == ClaimDisputeStatus.SEARCH_IN_PROGRESS
        assert len(search_result.dispute.search_locations) == 3
        assert "Main Branch Book Drop" in search_result.dispute.search_locations

    async def test_search_updates_investigation_notes(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test that starting a search updates investigation notes."""
        service = ClaimsReturnedService(test_db)

        # File claim and start review
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Returned at drive-through.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )
        await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
            initial_notes="Patron reports drive-through return.",
        )

        # Start search
        search_result = await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Drive-Through Return"],
            search_notes="Checking drive-through area and sorting bins.",
        )

        assert "Search started" in search_result.dispute.investigation_notes


# ============================================================================
# Test Resolution Workflow
# ============================================================================


@pytest.mark.unit
class TestResolutionWorkflow:
    """Tests for resolving claims returned disputes."""

    async def test_resolve_claim_approved(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test approving a claims returned dispute."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book on the due date.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Resolve as approved
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="Patron has good standing and no history of disputes. Approved based on benefit of doubt.",
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.APPROVED
        assert resolve_result.dispute.resolved_by_id == test_staff_for_claim.id
        assert resolve_result.dispute.resolved_at is not None
        assert "benefit of doubt" in resolve_result.dispute.resolution_reason

    async def test_resolve_claim_denied(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test denying a claims returned dispute."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I swear I returned it.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Resolve as denied
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=False,
            resolution_reason="Item not found after thorough search of all locations. Security footage does not show patron returning item.",
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.DENIED
        assert "Security footage" in resolve_result.dispute.resolution_reason

    async def test_resolve_claim_item_found(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test resolving a dispute when the item is found."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I definitely returned this book.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Resolve as item found
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="Item found on shelving cart behind circulation desk.",
            item_found=True,
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.ITEM_FOUND
        assert resolve_result.item_found is True

    async def test_resolve_claim_with_credit_for_paid_fine(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test that approving a claim creates credit when fine was paid."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this and paid the fine but want my money back.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Create and attach a paid fine to the lost item record
        fine = Fine(
            user_id=test_patron_for_claim.id,
            checkout_id=test_active_checkout.id,
            fine_type=FineType.lost_item,
            status=FineStatus.paid,
            amount=Decimal("25.00"),
            amount_paid=Decimal("25.00"),
            description="Lost item replacement fee",
        )
        test_db.add(fine)
        await test_db.flush()

        # Update lost item record with fine
        # See test_file_claim_creates_lost_item_record: lost_item_record
        # isn't eager-loaded by file_claim(), so refresh before touching it.
        await test_db.refresh(file_result.dispute, attribute_names=["lost_item_record"])
        file_result.dispute.lost_item_record.fine_id = fine.id
        await test_db.commit()

        # Resolve as approved with credit
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="Claim approved, issuing refund credit.",
            credit_amount=Decimal("25.00"),
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.credit_amount == Decimal("25.00")
        assert resolve_result.credit_fine is not None

    async def test_resolve_claim_waives_unpaid_fine(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test that approving a claim waives unpaid fines."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book, please waive the fine.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Create and attach an unpaid fine
        fine = Fine(
            user_id=test_patron_for_claim.id,
            checkout_id=test_active_checkout.id,
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=Decimal("30.00"),
            amount_paid=Decimal("0.00"),
            description="Lost item replacement fee",
        )
        test_db.add(fine)
        await test_db.flush()

        # See test_file_claim_creates_lost_item_record: lost_item_record
        # isn't eager-loaded by file_claim(), so refresh before touching it.
        await test_db.refresh(file_result.dispute, attribute_names=["lost_item_record"])
        file_result.dispute.lost_item_record.fine_id = fine.id
        await test_db.commit()

        # Resolve as approved
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="Approved - waiving fine.",
            send_notification=False,
        )

        await test_db.refresh(fine)

        assert resolve_result.success is True
        assert fine.status == FineStatus.waived
        assert fine.waived_by_id == test_staff_for_claim.id

    async def test_cannot_resolve_already_resolved_claim(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test that resolving an already resolved claim fails."""
        service = ClaimsReturnedService(test_db)

        # File and resolve claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Test claim.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )
        await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="First resolution.",
            send_notification=False,
        )

        # Try to resolve again
        result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=False,
            resolution_reason="Second resolution attempt.",
            send_notification=False,
        )

        assert result.success is False
        assert "already been resolved" in result.message.lower()


# ============================================================================
# Test Listing and Filtering Claims
# ============================================================================


@pytest.mark.unit
class TestListingClaims:
    """Tests for listing and filtering claims."""

    async def test_get_disputes_all(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test getting all disputes."""
        service = ClaimsReturnedService(test_db)

        # File a claim
        await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Test dispute for listing.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        disputes, total = await service.get_disputes()

        assert total >= 1
        assert len(disputes) >= 1

    async def test_get_disputes_by_status(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test filtering disputes by status."""
        service = ClaimsReturnedService(test_db)

        # File and start review
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Test filtering by status.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )
        await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
        )

        # Filter by under_review status
        disputes, total = await service.get_disputes(status=ClaimDisputeStatus.UNDER_REVIEW)

        assert total >= 1
        for dispute in disputes:
            assert dispute.status == ClaimDisputeStatus.UNDER_REVIEW

    async def test_get_disputes_by_patron(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test filtering disputes by patron."""
        service = ClaimsReturnedService(test_db)

        # File a claim
        await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Test filtering by patron.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        disputes, total = await service.get_disputes(patron_id=test_patron_for_claim.id)

        assert total >= 1
        for dispute in disputes:
            assert dispute.patron_id == test_patron_for_claim.id

    async def test_get_disputes_unresolved_only(
        self, test_db, test_settings, test_patron_for_claim, test_active_checkout
    ):
        """Test getting only unresolved disputes."""
        service = ClaimsReturnedService(test_db)

        # File a claim (pending = unresolved)
        await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="Unresolved dispute test.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        disputes, total = await service.get_disputes(unresolved_only=True)

        assert total >= 1
        for dispute in disputes:
            assert dispute.status in [
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS,
            ]

    async def test_get_overdue_disputes(
        self, test_db, test_settings, test_patron_for_claim
    ):
        """Test getting disputes that exceeded review period."""
        # Create an old dispute
        lost_record = LostItemRecord(
            patron_id=test_patron_for_claim.id,
            status=LostItemStatus.DISPUTE_PENDING,
            lost_type=LostItemType.CLAIMS_RETURNED,
        )
        test_db.add(lost_record)
        await test_db.flush()

        old_dispute = ClaimsReturnedDispute(
            lost_item_record_id=lost_record.id,
            patron_id=test_patron_for_claim.id,
            status=ClaimDisputeStatus.PENDING,
            patron_statement="This is an old dispute.",
            filed_at=datetime.now(timezone.utc) - timedelta(days=60),  # Way past review period
        )
        test_db.add(old_dispute)
        await test_db.commit()

        service = ClaimsReturnedService(test_db)
        overdue_disputes = await service.get_overdue_disputes()

        assert len(overdue_disputes) >= 1
        # All should be pending/under review and filed before cutoff
        for dispute in overdue_disputes:
            assert dispute.status in [
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS,
            ]


# ============================================================================
# Test Complete Workflow Integration
# ============================================================================


@pytest.mark.unit
class TestCompleteWorkflow:
    """Integration tests for the complete claims returned workflow."""

    async def test_full_workflow_patron_claim_approved(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test the complete workflow: file -> review -> search -> approve."""
        service = ClaimsReturnedService(test_db)

        # Step 1: Patron files claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I returned this book to the book drop at Main Branch on December 15th around 2pm.",
            claimed_return_date=date(2024, 12, 15),
            claimed_return_location="Main Branch Book Drop",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )
        assert file_result.success is True
        assert file_result.dispute.status == ClaimDisputeStatus.PENDING

        # Step 2: Staff starts review
        review_result = await service.start_review(
            dispute_id=file_result.dispute.id,
            reviewed_by=test_staff_for_claim,
            initial_notes="Patron has no prior issues. Checking book drop logs for Dec 15.",
        )
        assert review_result.success is True
        assert review_result.dispute.status == ClaimDisputeStatus.UNDER_REVIEW

        # Step 3: Staff initiates search
        search_result = await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Main Branch Book Drop", "Sorting Room", "Shelving Carts", "Returns Processing"],
            search_notes="Searching all return processing areas.",
        )
        assert search_result.success is True
        assert search_result.dispute.status == ClaimDisputeStatus.SEARCH_IN_PROGRESS

        # Step 4: Staff resolves - claim approved
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="After thorough search and review of patron's history, claim approved. Patron has excellent standing.",
            send_notification=False,
        )
        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.APPROVED
        assert resolve_result.dispute.resolved_at is not None

    async def test_full_workflow_item_found_during_search(
        self, test_db, test_settings, test_patron_for_claim, test_staff_for_claim, test_active_checkout
    ):
        """Test workflow where item is found during search."""
        service = ClaimsReturnedService(test_db)

        # File claim
        file_result = await service.file_claim(
            checkout_id=test_active_checkout.id,
            patron_statement="I put it in the night drop.",
            filed_by=test_patron_for_claim,
            send_notification=False,
        )

        # Start search
        await service.start_search(
            dispute_id=file_result.dispute.id,
            search_locations=["Night Drop"],
            search_notes="Checking night drop and processing area.",
        )

        # Item found!
        resolve_result = await service.resolve_claim(
            dispute_id=file_result.dispute.id,
            resolved_by=test_staff_for_claim,
            approved=True,
            resolution_reason="Item found in night drop overflow bin! Was stuck at the bottom.",
            item_found=True,
            send_notification=False,
        )

        assert resolve_result.success is True
        assert resolve_result.dispute.status == ClaimDisputeStatus.ITEM_FOUND
        assert resolve_result.item_found is True

        # Verify patron claims history shows item was found
        history = await service.get_patron_claims_history(test_patron_for_claim.id)
        assert history.items_later_found >= 1
