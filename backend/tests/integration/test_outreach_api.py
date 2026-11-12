# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Outreach Program Tracking API endpoints.

Tests cover partner management, deposit collection, visit scheduling,
institutional cards, bulk checkouts, and outreach statistics.
"""

from datetime import date, datetime, timedelta, timezone

import pytest


# ============ Fixtures ============


@pytest.fixture
async def outreach_staff(test_db):
    """Create a staff user for outreach operations."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="outreach_staff@example.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Outreach",
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
async def outreach_patron(test_db):
    """Create a patron user for permission testing."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="outreach_patron@example.com",
        password_hash=hash_password("PatronPassword123!"),
        first_name="Outreach",
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
async def sample_partner(test_db, outreach_staff):
    """Create a sample outreach partner for testing."""
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
        primary_contact_phone="555-1234",
        school_level="elementary",
        school_district="Bébé Memorial USD",
        student_count=450,
        teacher_count=25,
        allows_bulk_checkout=True,
        allows_institutional_card=True,
        requires_deposit=True,
        default_deposit_amount=50.0,
        checkout_limit=100,
        loan_period_days=28,
        created_by_id=outreach_staff.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


@pytest.fixture
async def sample_institutional_card(test_db, sample_partner, outreach_staff):
    """Create a sample institutional card for testing."""
    from app.models.outreach import InstitutionalCard

    card = InstitutionalCard(
        partner_id=sample_partner.id,
        card_number="INST-TEST123456",
        card_name="Lincoln Elementary Library Card",
        status="active",
        authorized_users=["Jane Smith", "John Doe"],
        requires_pin=False,
        checkout_limit=100,
        hold_limit=25,
        loan_period_days=28,
        renewal_limit=2,
        exempt_from_fines=False,
        issued_date=date.today(),
        issued_by_id=outreach_staff.id,
    )
    test_db.add(card)
    await test_db.commit()
    await test_db.refresh(card)
    return card


@pytest.fixture
async def sample_bulk_checkout(test_db, sample_partner, outreach_staff):
    """Create a sample bulk checkout for testing."""
    from app.models.outreach import BulkCheckout

    checkout = BulkCheckout(
        partner_id=sample_partner.id,
        checkout_name="Mrs. Johnson's 3rd Grade Class",
        status="active",
        requestor_name="Mrs. Johnson",
        requestor_email="mjohnson@lincoln.edu",
        classroom_name="Room 201",
        grade_level="3rd",
        checkout_date=date.today(),
        due_date=date.today() + timedelta(days=28),
        total_items=0,
        deposit_required=True,
        deposit_amount=25.0,
        topic_requests=["dinosaurs", "space"],
        processed_by_id=outreach_staff.id,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def sample_visit(test_db, sample_partner, outreach_staff):
    """Create a sample outreach visit for testing."""
    from app.models.outreach import OutreachVisit

    visit = OutreachVisit(
        partner_id=sample_partner.id,
        visit_type="storytime",
        status="scheduled",
        title="Weekly Storytime at Lincoln Elementary",
        description="Read-aloud session for 1st graders",
        scheduled_date=date.today() + timedelta(days=7),
        scheduled_start_time="10:00",
        scheduled_end_time="11:00",
        location_name="Lincoln Elementary",
        location_room="Library",
        expected_attendees=25,
        age_group="children",
        grade_levels=["1"],
        lead_staff_id=outreach_staff.id,
        created_by_id=outreach_staff.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)
    return visit


@pytest.fixture
async def sample_deposit(test_db, sample_partner, outreach_staff):
    """Create a sample deposit for testing."""
    from app.models.outreach import OutreachDeposit

    deposit = OutreachDeposit(
        partner_id=sample_partner.id,
        deposit_type="classroom_checkout",
        status="held",
        amount=50.0,
        payment_method="check",
        payment_reference="CHK-12345",
        receipt_number="DEP-TEST001",
        collected_date=date.today(),
        collected_by_id=outreach_staff.id,
    )
    test_db.add(deposit)
    await test_db.commit()
    await test_db.refresh(deposit)
    return deposit


# ============ Partner Tests ============


@pytest.mark.asyncio
async def test_create_partner(test_db, outreach_staff):
    """Test creating a new outreach partner."""
    from app.models.outreach import OutreachPartner

    partner = OutreachPartner(
        name="Test School",
        partner_type="school",
        status="active",
        city="Test City",
        primary_contact_name="Test Contact",
        school_level="elementary",
        created_by_id=outreach_staff.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)

    assert partner.id is not None
    assert partner.name == "Test School"
    assert partner.partner_type == "school"
    assert partner.status == "active"


@pytest.mark.asyncio
async def test_partner_with_contacts(test_db, sample_partner):
    """Test partner with multiple contacts."""
    from app.models.outreach import OutreachPartnerContact

    contact1 = OutreachPartnerContact(
        partner_id=sample_partner.id,
        name="Contact One",
        email="contact1@test.com",
        is_primary=True,
    )
    contact2 = OutreachPartnerContact(
        partner_id=sample_partner.id,
        name="Contact Two",
        email="contact2@test.com",
        is_primary=False,
    )
    test_db.add_all([contact1, contact2])
    await test_db.commit()

    # A bare refresh() only reloads column attributes; the relationship
    # needs to be named explicitly or accessing it lazily outside an
    # awaited context raises MissingGreenlet.
    await test_db.refresh(sample_partner, attribute_names=["contacts"])
    assert len(sample_partner.contacts) == 2


@pytest.mark.asyncio
async def test_update_partner_status(test_db, sample_partner):
    """Test updating partner status."""
    sample_partner.status = "suspended"
    await test_db.commit()
    await test_db.refresh(sample_partner)

    assert sample_partner.status == "suspended"


# ============ Deposit Tests ============


@pytest.mark.asyncio
async def test_create_deposit(test_db, sample_partner, outreach_staff):
    """Test creating a new deposit."""
    from app.models.outreach import OutreachDeposit

    deposit = OutreachDeposit(
        partner_id=sample_partner.id,
        deposit_type="bulk_checkout",
        status="held",
        amount=100.0,
        payment_method="cash",
        collected_date=date.today(),
        collected_by_id=outreach_staff.id,
    )
    test_db.add(deposit)
    await test_db.commit()
    await test_db.refresh(deposit)

    assert deposit.id is not None
    assert deposit.amount == 100.0
    assert deposit.status == "held"


@pytest.mark.asyncio
async def test_deposit_refund(test_db, sample_deposit, outreach_staff):
    """Test refunding a deposit."""
    sample_deposit.amount_refunded = 25.0
    sample_deposit.refund_reason = "Partial refund for returned items"
    sample_deposit.refund_date = date.today()
    sample_deposit.refunded_by_id = outreach_staff.id
    await test_db.commit()
    await test_db.refresh(sample_deposit)

    remaining = (
        sample_deposit.amount - sample_deposit.amount_applied - sample_deposit.amount_refunded
    )
    assert remaining == 25.0


@pytest.mark.asyncio
async def test_deposit_application(test_db, sample_deposit, outreach_staff):
    """Test applying deposit to fines."""
    from app.models.outreach import DepositApplication

    application = DepositApplication(
        deposit_id=sample_deposit.id,
        amount=10.0,
        reason="Applied to late return fee",
        applied_by_id=outreach_staff.id,
    )
    test_db.add(application)

    sample_deposit.amount_applied += 10.0
    sample_deposit.status = "partially_applied"
    await test_db.commit()

    await test_db.refresh(sample_deposit)
    assert sample_deposit.amount_applied == 10.0
    assert sample_deposit.status == "partially_applied"


# ============ Visit Tests ============


@pytest.mark.asyncio
async def test_create_visit(test_db, sample_partner, outreach_staff):
    """Test creating an outreach visit."""
    from app.models.outreach import OutreachVisit

    visit = OutreachVisit(
        partner_id=sample_partner.id,
        visit_type="book_delivery",
        status="scheduled",
        title="Book Delivery",
        scheduled_date=date.today() + timedelta(days=3),
        items_to_deliver=50,
        created_by_id=outreach_staff.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    assert visit.id is not None
    assert visit.visit_type == "book_delivery"
    assert visit.items_to_deliver == 50


@pytest.mark.asyncio
async def test_complete_visit(test_db, sample_visit):
    """Test completing an outreach visit."""
    sample_visit.status = "completed"
    sample_visit.actual_attendees = 22
    sample_visit.new_cards_issued = 5
    sample_visit.books_checked_out = 15
    sample_visit.outcome_notes = "Great session, kids loved it!"
    sample_visit.actual_end_time = datetime.now(timezone.utc)
    await test_db.commit()
    await test_db.refresh(sample_visit)

    assert sample_visit.status == "completed"
    assert sample_visit.actual_attendees == 22
    assert sample_visit.new_cards_issued == 5


@pytest.mark.asyncio
async def test_cancel_visit(test_db, sample_visit, outreach_staff):
    """Test cancelling an outreach visit."""
    sample_visit.status = "cancelled"
    sample_visit.cancellation_reason = "School closed due to weather"
    sample_visit.cancelled_by_id = outreach_staff.id
    sample_visit.cancelled_at = datetime.now(timezone.utc)
    await test_db.commit()
    await test_db.refresh(sample_visit)

    assert sample_visit.status == "cancelled"
    assert "weather" in sample_visit.cancellation_reason


@pytest.mark.asyncio
async def test_recurring_visit(test_db, sample_visit):
    """Test creating recurring visit chain."""
    from app.models.outreach import OutreachVisit

    sample_visit.is_recurring = True
    sample_visit.recurrence_pattern = "weekly"

    # Create child visit
    child_visit = OutreachVisit(
        partner_id=sample_visit.partner_id,
        visit_type=sample_visit.visit_type,
        status="scheduled",
        title=sample_visit.title,
        scheduled_date=sample_visit.scheduled_date + timedelta(days=7),
        parent_visit_id=sample_visit.id,
        created_by_id=sample_visit.created_by_id,
    )
    test_db.add(child_visit)
    await test_db.commit()
    await test_db.refresh(child_visit)

    assert child_visit.parent_visit_id == sample_visit.id


# ============ Institutional Card Tests ============


@pytest.mark.asyncio
async def test_create_institutional_card(test_db, sample_partner, outreach_staff):
    """Test creating an institutional card."""
    from app.models.outreach import InstitutionalCard

    card = InstitutionalCard(
        partner_id=sample_partner.id,
        card_number="INST-NEW12345",
        card_name="Test Card",
        status="active",
        checkout_limit=50,
        issued_date=date.today(),
        issued_by_id=outreach_staff.id,
    )
    test_db.add(card)
    await test_db.commit()
    await test_db.refresh(card)

    assert card.id is not None
    assert card.card_number == "INST-NEW12345"
    assert card.checkout_limit == 50


@pytest.mark.asyncio
async def test_institutional_checkout(test_db, sample_institutional_card, outreach_staff):
    """Test creating an institutional checkout."""
    from app.models.outreach import InstitutionalCheckout

    checkout = InstitutionalCheckout(
        card_id=sample_institutional_card.id,
        barcode="TEST-BARCODE-001",
        title="Test Book",
        checked_out_by_name="Jane Smith",
        checked_out_by_id=outreach_staff.id,
        due_date=datetime.now(timezone.utc) + timedelta(days=28),
        status="active",
    )
    test_db.add(checkout)

    # Update card statistics
    sample_institutional_card.current_checkouts += 1
    sample_institutional_card.total_checkouts += 1

    await test_db.commit()
    await test_db.refresh(sample_institutional_card)

    assert sample_institutional_card.current_checkouts == 1
    assert sample_institutional_card.total_checkouts == 1


@pytest.mark.asyncio
async def test_institutional_card_suspension(test_db, sample_institutional_card):
    """Test suspending an institutional card."""
    sample_institutional_card.status = "suspended"
    await test_db.commit()
    await test_db.refresh(sample_institutional_card)

    assert sample_institutional_card.status == "suspended"


# ============ Bulk Checkout Tests ============


@pytest.mark.asyncio
async def test_create_bulk_checkout(test_db, sample_partner, outreach_staff):
    """Test creating a bulk checkout."""
    from app.models.outreach import BulkCheckout

    checkout = BulkCheckout(
        partner_id=sample_partner.id,
        checkout_name="Test Bulk Checkout",
        status="active",
        requestor_name="Test Teacher",
        checkout_date=date.today(),
        due_date=date.today() + timedelta(days=14),
        processed_by_id=outreach_staff.id,
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)

    assert checkout.id is not None
    assert checkout.status == "active"


@pytest.mark.asyncio
async def test_add_items_to_bulk_checkout(test_db, sample_bulk_checkout):
    """Test adding items to a bulk checkout."""
    from app.models.outreach import BulkCheckoutItem

    items = [
        BulkCheckoutItem(
            bulk_checkout_id=sample_bulk_checkout.id,
            barcode=f"ITEM-{i:03d}",
            title=f"Book {i}",
            status="checked_out",
        )
        for i in range(5)
    ]
    test_db.add_all(items)

    sample_bulk_checkout.total_items = 5
    await test_db.commit()
    # Name the relationship explicitly -- a bare refresh() only reloads
    # column attributes; lazily accessing .items afterward outside an
    # awaited context raises MissingGreenlet.
    await test_db.refresh(sample_bulk_checkout, attribute_names=["items"])

    assert sample_bulk_checkout.total_items == 5
    assert len(sample_bulk_checkout.items) == 5


@pytest.mark.asyncio
async def test_return_bulk_checkout_items(test_db, sample_bulk_checkout):
    """Test returning items from a bulk checkout."""
    from app.models.outreach import BulkCheckoutItem

    # Add items first
    items = [
        BulkCheckoutItem(
            bulk_checkout_id=sample_bulk_checkout.id,
            barcode=f"RET-{i:03d}",
            title=f"Return Book {i}",
            status="checked_out",
        )
        for i in range(3)
    ]
    test_db.add_all(items)
    sample_bulk_checkout.total_items = 3
    await test_db.commit()

    # Return 2 items
    await test_db.refresh(sample_bulk_checkout, attribute_names=["items"])
    for i, item in enumerate(sample_bulk_checkout.items[:2]):
        item.status = "returned"
        item.returned_at = datetime.now(timezone.utc)
    sample_bulk_checkout.items_returned = 2
    sample_bulk_checkout.status = "partially_returned"
    await test_db.commit()

    await test_db.refresh(sample_bulk_checkout)
    assert sample_bulk_checkout.items_returned == 2
    assert sample_bulk_checkout.status == "partially_returned"


@pytest.mark.asyncio
async def test_bulk_checkout_overdue(test_db, sample_bulk_checkout):
    """Test marking bulk checkout as overdue."""
    # Set due date in the past
    sample_bulk_checkout.due_date = date.today() - timedelta(days=5)
    sample_bulk_checkout.status = "overdue"
    await test_db.commit()
    await test_db.refresh(sample_bulk_checkout)

    assert sample_bulk_checkout.status == "overdue"
    assert sample_bulk_checkout.due_date < date.today()


# ============ Statistics Tests ============


@pytest.mark.asyncio
async def test_create_outreach_statistics(test_db, outreach_staff):
    """Test creating outreach statistics."""
    from app.models.outreach import OutreachStatistics

    stats = OutreachStatistics(
        period_start=date.today().replace(day=1),
        period_end=date.today(),
        total_partners=10,
        active_partners=8,
        new_partners=2,
        partners_by_type={"school": 6, "daycare": 2, "other": 2},
        total_visits=15,
        visits_completed=12,
        visits_cancelled=3,
        total_attendees=350,
        bulk_checkouts_created=5,
        bulk_items_checked_out=150,
        institutional_cards_active=4,
        deposits_collected=200.0,
        new_cards_from_outreach=25,
        generated_by_id=outreach_staff.id,
    )
    test_db.add(stats)
    await test_db.commit()
    await test_db.refresh(stats)

    assert stats.id is not None
    assert stats.total_partners == 10
    assert stats.total_attendees == 350


# ============ Relationship Tests ============


@pytest.mark.asyncio
async def test_partner_cascade_delete(test_db, sample_partner):
    """Test that deleting a partner cascades to related records."""
    from app.models.outreach import OutreachPartnerContact, OutreachVisit, BulkCheckout

    # Add related records
    contact = OutreachPartnerContact(
        partner_id=sample_partner.id,
        name="Delete Test Contact",
    )
    visit = OutreachVisit(
        partner_id=sample_partner.id,
        visit_type="storytime",
        status="scheduled",
        title="Delete Test Visit",
        scheduled_date=date.today(),
    )
    checkout = BulkCheckout(
        partner_id=sample_partner.id,
        checkout_name="Delete Test Checkout",
        status="active",
        requestor_name="Test",
        checkout_date=date.today(),
        due_date=date.today() + timedelta(days=7),
    )
    test_db.add_all([contact, visit, checkout])
    await test_db.commit()

    # Delete the partner
    await test_db.delete(sample_partner)
    await test_db.commit()

    # Verify cascade
    from sqlalchemy import select

    contact_result = await test_db.execute(
        select(OutreachPartnerContact).where(OutreachPartnerContact.partner_id == sample_partner.id)
    )
    assert contact_result.scalar_one_or_none() is None


# ============ Edge Case Tests ============


@pytest.mark.asyncio
async def test_deposit_full_application(test_db, sample_deposit):
    """Test fully applying a deposit."""
    sample_deposit.amount_applied = sample_deposit.amount
    sample_deposit.status = "fully_applied"
    await test_db.commit()
    await test_db.refresh(sample_deposit)

    remaining = (
        sample_deposit.amount - sample_deposit.amount_applied - sample_deposit.amount_refunded
    )
    assert remaining == 0
    assert sample_deposit.status == "fully_applied"


@pytest.mark.asyncio
async def test_institutional_card_expiry(test_db, sample_institutional_card):
    """Test institutional card expiry handling."""
    # Set expiry date in the past
    sample_institutional_card.expiry_date = date.today() - timedelta(days=1)
    sample_institutional_card.status = "expired"
    await test_db.commit()
    await test_db.refresh(sample_institutional_card)

    assert sample_institutional_card.status == "expired"


@pytest.mark.asyncio
async def test_visit_with_follow_up(test_db, sample_visit):
    """Test visit requiring follow-up."""
    sample_visit.status = "completed"
    sample_visit.follow_up_needed = True
    sample_visit.follow_up_notes = "Teacher requested more dinosaur books"
    sample_visit.next_visit_date = date.today() + timedelta(days=14)
    await test_db.commit()
    await test_db.refresh(sample_visit)

    assert sample_visit.follow_up_needed is True
    assert sample_visit.next_visit_date is not None


# ============ Outreach Visit Lifecycle Tests ============


@pytest.mark.asyncio
async def test_outreach_visit_full_lifecycle(test_db, outreach_staff):
    """Test full outreach visit lifecycle: schedule, complete, and cancel.

    Covers:
    1. Schedule a STORYTIME visit for next Tuesday with Somewhere Up North Elementary
    2. Verify OutreachVisit created with status SCHEDULED
    3. Complete the visit with attendance, cards, books, and rating outcomes
    4. Verify visit status changes to COMPLETED with all metrics stored
    5. Cancel a different scheduled visit and verify status changes to CANCELLED
    """
    from app.models.outreach import OutreachPartner, OutreachVisit

    # --- Setup: Create partner "Somewhere Up North Elementary" ---
    partner = OutreachPartner(
        name="Somewhere Up North Elementary",
        partner_type="school",
        status="active",
        address_line1="456 Creek Rd",
        city="Somewhere Up North",
        state="CA",
        zip_code="90211",
        primary_contact_name="Moira Rose",
        primary_contact_email="mrose@schittcreek.edu",
        school_level="elementary",
        school_district="Somewhere Up North USD",
        student_count=300,
        teacher_count=18,
        created_by_id=outreach_staff.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)

    # --- Step 1: Schedule a STORYTIME visit for next Tuesday ---
    today = date.today()
    days_until_tuesday = (1 - today.weekday()) % 7  # Monday=0, Tuesday=1
    if days_until_tuesday == 0:
        days_until_tuesday = 7  # If today is Tuesday, schedule for next Tuesday
    next_tuesday = today + timedelta(days=days_until_tuesday)

    visit = OutreachVisit(
        partner_id=partner.id,
        visit_type="storytime",
        status="scheduled",
        title="Storytime at Somewhere Up North Elementary",
        description="Interactive storytime session for kindergarteners",
        scheduled_date=next_tuesday,
        scheduled_start_time="09:30",
        scheduled_end_time="10:30",
        location_name="Somewhere Up North Elementary",
        location_room="Library",
        expected_attendees=30,
        age_group="children",
        grade_levels=["K", "1"],
        lead_staff_id=outreach_staff.id,
        created_by_id=outreach_staff.id,
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)

    # --- Step 2: Verify OutreachVisit created with status SCHEDULED ---
    assert visit.id is not None
    assert visit.status == "scheduled"
    assert visit.visit_type == "storytime"
    assert visit.partner_id == partner.id
    assert visit.scheduled_date == next_tuesday
    assert visit.title == "Storytime at Somewhere Up North Elementary"
    assert visit.scheduled_start_time == "09:30"
    assert visit.scheduled_end_time == "10:30"
    assert visit.location_name == "Somewhere Up North Elementary"
    assert visit.expected_attendees == 30
    assert visit.grade_levels == ["K", "1"]

    # --- Step 3: Complete the visit with outcomes ---
    visit.status = "completed"
    visit.actual_attendees = 25
    visit.new_cards_issued = 3
    visit.books_checked_out = 45
    visit.partner_rating = 5
    visit.outcome_notes = "Wonderful session! Children were very engaged."
    visit.partner_feedback = "Excellent program, kids loved it."
    visit.staff_notes = "Brought extra picture books which were a big hit."
    visit.actual_start_time = datetime(
        next_tuesday.year,
        next_tuesday.month,
        next_tuesday.day,
        9,
        30,
        tzinfo=timezone.utc,
    )
    visit.actual_end_time = datetime(
        next_tuesday.year,
        next_tuesday.month,
        next_tuesday.day,
        10,
        30,
        tzinfo=timezone.utc,
    )
    await test_db.commit()
    await test_db.refresh(visit)

    # --- Step 4: Verify visit status COMPLETED with all metrics ---
    assert visit.status == "completed"
    assert visit.actual_attendees == 25
    assert visit.new_cards_issued == 3
    assert visit.books_checked_out == 45
    assert visit.partner_rating == 5
    assert visit.outcome_notes == "Wonderful session! Children were very engaged."
    assert visit.partner_feedback == "Excellent program, kids loved it."
    assert visit.staff_notes == "Brought extra picture books which were a big hit."
    assert visit.actual_start_time is not None
    assert visit.actual_end_time is not None

    # --- Step 5: Cancel a different scheduled visit ---
    visit_to_cancel = OutreachVisit(
        partner_id=partner.id,
        visit_type="book_delivery",
        status="scheduled",
        title="Book Delivery to Somewhere Up North Elementary",
        scheduled_date=next_tuesday + timedelta(days=7),
        scheduled_start_time="14:00",
        scheduled_end_time="15:00",
        lead_staff_id=outreach_staff.id,
        created_by_id=outreach_staff.id,
    )
    test_db.add(visit_to_cancel)
    await test_db.commit()
    await test_db.refresh(visit_to_cancel)

    # Verify it starts as scheduled
    assert visit_to_cancel.status == "scheduled"
    assert visit_to_cancel.id != visit.id

    # Cancel it
    visit_to_cancel.status = "cancelled"
    visit_to_cancel.cancellation_reason = "Partner requested postponement due to school event"
    visit_to_cancel.cancelled_by_id = outreach_staff.id
    visit_to_cancel.cancelled_at = datetime.now(timezone.utc)
    await test_db.commit()
    await test_db.refresh(visit_to_cancel)

    # Verify CANCELLED status
    assert visit_to_cancel.status == "cancelled"
    assert (
        visit_to_cancel.cancellation_reason == "Partner requested postponement due to school event"
    )
    assert visit_to_cancel.cancelled_by_id == outreach_staff.id
    assert visit_to_cancel.cancelled_at is not None

    # Verify the original completed visit is unaffected
    await test_db.refresh(visit)
    assert visit.status == "completed"
    assert visit.actual_attendees == 25
