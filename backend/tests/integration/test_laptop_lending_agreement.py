# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Laptop Lending Agreement workflow.

Tests the full lifecycle of laptop equipment lending agreements:
1. Create an agreement template for laptop lending
2. Have a patron sign the agreement via POST /equipment/agreements/{id}/sign
3. Verify AgreementStatusResponse shows signed=true
4. Check that agreement is required before checkout is allowed
5. Verify visit status changes to COMPLETED with all metrics stored
6. Cancel a different scheduled visit and verify status changes to CANCELLED
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import (
    AgreementStatus,
    DEFAULT_EQUIPMENT_AGREEMENT,
    Equipment,
    EquipmentAgreement,
    EquipmentCheckout,
    EquipmentCondition,
    EquipmentStatus,
    EquipmentType,
    LAPTOP_LENDING_AGREEMENT,
    get_agreement_template,
)
from app.models.outreach import OutreachPartner, OutreachVisit
from app.models.user import User, UserRole
from app.services import equipment_service


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def patron(test_db: AsyncSession) -> User:
    """Create a test patron for agreement signing."""
    from app.core.security import hash_password

    user = User(
        email="patron_laptop@l30.org",
        password_hash=hash_password("PatronPassword123!"),
        first_name="David",
        last_name="Rose",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff(test_db: AsyncSession) -> User:
    """Create a staff member for equipment management."""
    from app.core.security import hash_password

    user = User(
        email="staff_laptop@l30.org",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Stevie",
        last_name="Budd",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def laptop(test_db: AsyncSession, staff: User) -> Equipment:
    """Create a lending laptop that requires an agreement."""
    equipment = Equipment(
        name="Dell Latitude 5540",
        description="14-inch laptop for patron lending",
        equipment_type=EquipmentType.LAPTOP,
        serial_number="DELL-LAT5540-001",
        barcode="EQP-LAPTOP-001",
        asset_tag="LSC-L-001",
        manufacturer="Dell",
        model="Latitude 5540",
        model_year=2024,
        status=EquipmentStatus.AVAILABLE,
        condition=EquipmentCondition.GOOD,
        requires_agreement=True,
        max_checkout_days=7,
        fine_per_day=Decimal("5.00"),
        max_renewals=1,
        deposit_required=False,
        replacement_cost=Decimal("800.00"),
        purchase_price=Decimal("650.00"),
        location="Main Branch - Circulation Desk",
        home_location="Main Branch",
        included_accessories="Power adapter, carrying case",
        created_by_id=staff.id,
    )
    test_db.add(equipment)
    await test_db.commit()
    await test_db.refresh(equipment)
    return equipment


@pytest.fixture
async def laptop_no_agreement(test_db: AsyncSession, staff: User) -> Equipment:
    """Create a lending laptop that does NOT require an agreement."""
    equipment = Equipment(
        name="Chromebook Lenovo 100e",
        description="Basic Chromebook - no agreement needed",
        equipment_type=EquipmentType.LAPTOP,
        serial_number="LEN-CB100E-001",
        barcode="EQP-CB-001",
        manufacturer="Lenovo",
        model="Chromebook 100e",
        model_year=2023,
        status=EquipmentStatus.AVAILABLE,
        condition=EquipmentCondition.GOOD,
        requires_agreement=False,
        max_checkout_days=3,
        fine_per_day=Decimal("2.00"),
        max_renewals=0,
        replacement_cost=Decimal("250.00"),
        location="Main Branch - Quick Lending",
        created_by_id=staff.id,
    )
    test_db.add(equipment)
    await test_db.commit()
    await test_db.refresh(equipment)
    return equipment


@pytest.fixture
async def outreach_partner(test_db: AsyncSession, staff: User) -> OutreachPartner:
    """Create Somewhere Up North Elementary as an outreach partner."""
    partner = OutreachPartner(
        name="Somewhere Up North Elementary",
        partner_type="school",
        status="active",
        address_line1="456 Elm Street",
        city="Somewhere Up North",
        state="CA",
        zip_code="91234",
        primary_contact_name="Jocelyn Schitt",
        primary_contact_email="jschitt@schittcreekelementary.edu",
        primary_contact_phone="555-8765",
        school_level="elementary",
        school_district="Somewhere Up North USD",
        student_count=300,
        teacher_count=18,
        allows_bulk_checkout=True,
        allows_institutional_card=True,
        checkout_limit=150,
        loan_period_days=28,
        created_by_id=staff.id,
    )
    test_db.add(partner)
    await test_db.commit()
    await test_db.refresh(partner)
    return partner


# ============================================================================
# 1. Create an agreement template for laptop lending
# ============================================================================


@pytest.mark.asyncio
class TestLaptopAgreementTemplate:
    """Test that laptop-specific agreement templates exist and are used."""

    async def test_laptop_agreement_template_exists(self):
        """Verify the LAPTOP_LENDING_AGREEMENT template is defined."""
        assert LAPTOP_LENDING_AGREEMENT is not None
        assert len(LAPTOP_LENDING_AGREEMENT) > 0
        assert "LAPTOP LENDING AGREEMENT" in LAPTOP_LENDING_AGREEMENT

    async def test_laptop_template_has_required_sections(self):
        """Verify the laptop agreement covers all required topics."""
        assert "RESPONSIBILITY" in LAPTOP_LENDING_AGREEMENT
        assert "SOFTWARE RESTRICTIONS" in LAPTOP_LENDING_AGREEMENT
        assert "ACCEPTABLE USE" in LAPTOP_LENDING_AGREEMENT
        assert "DATA AND PRIVACY" in LAPTOP_LENDING_AGREEMENT
        assert "REPLACEMENT COST" in LAPTOP_LENDING_AGREEMENT
        assert "TIMELY RETURN" in LAPTOP_LENDING_AGREEMENT
        assert "DAMAGE REPORTING" in LAPTOP_LENDING_AGREEMENT

    async def test_get_agreement_template_returns_laptop_specific(self):
        """get_agreement_template(LAPTOP) returns the laptop-specific template."""
        template = get_agreement_template(EquipmentType.LAPTOP)
        assert template == LAPTOP_LENDING_AGREEMENT
        assert "LAPTOP LENDING AGREEMENT" in template

    async def test_get_agreement_template_fallback_for_other_types(self):
        """get_agreement_template for non-laptop types falls back to default."""
        template = get_agreement_template(EquipmentType.HOTSPOT)
        assert template == DEFAULT_EQUIPMENT_AGREEMENT

    async def test_get_agreement_template_fallback_for_none(self):
        """get_agreement_template(None) returns the default template."""
        template = get_agreement_template(None)
        assert template == DEFAULT_EQUIPMENT_AGREEMENT

    async def test_create_laptop_agreement_uses_laptop_template(
        self, test_db: AsyncSession, patron: User
    ):
        """Creating an agreement for laptop type uses the laptop-specific template."""
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )

        assert agreement.id is not None
        assert agreement.status == AgreementStatus.PENDING
        assert "LAPTOP LENDING AGREEMENT" in agreement.agreement_text
        assert agreement.equipment_types_covered == "laptop"

    async def test_create_generic_agreement_uses_default_template(
        self, test_db: AsyncSession, patron: User
    ):
        """Creating an agreement without specific type uses the default template."""
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=None,
        )

        assert agreement.id is not None
        assert agreement.status == AgreementStatus.PENDING
        assert "EQUIPMENT LENDING AGREEMENT" in agreement.agreement_text


# ============================================================================
# 2. Have a patron sign the agreement via POST /equipment/agreements/{id}/sign
# ============================================================================


@pytest.mark.asyncio
class TestSignAgreement:
    """Test the agreement signing flow through the service layer."""

    async def test_sign_laptop_agreement(self, test_db: AsyncSession, patron: User):
        """Patron signs a laptop lending agreement."""
        # Step 1: Create the agreement
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        assert agreement.status == AgreementStatus.PENDING
        assert agreement.signature is None
        assert agreement.signed_at is None

        # Step 2: Sign the agreement
        signed_agreement = await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
            ip_address="192.168.1.100",
        )

        # Step 3: Verify signed state
        assert signed_agreement.status == AgreementStatus.SIGNED
        assert signed_agreement.signature == "David Rose"
        assert signed_agreement.signed_at is not None
        assert signed_agreement.ip_address == "192.168.1.100"
        assert signed_agreement.valid_from is not None
        assert signed_agreement.valid_until is not None
        # Agreement should be valid for ~1 year
        assert signed_agreement.valid_until > signed_agreement.valid_from

    async def test_sign_agreement_already_signed_raises_error(
        self, test_db: AsyncSession, patron: User
    ):
        """Signing an already-signed agreement raises an error."""
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )

        # Sign it once
        await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        # Try to sign again — should raise 400
        with pytest.raises(Exception) as exc_info:
            await equipment_service.sign_agreement(
                db=test_db,
                agreement_id=agreement.id,
                user_id=patron.id,
                signature="David Rose",
            )
        assert "already signed" in str(exc_info.value.detail).lower()

    async def test_sign_nonexistent_agreement_raises_404(self, test_db: AsyncSession, patron: User):
        """Signing a non-existent agreement raises 404."""
        with pytest.raises(Exception) as exc_info:
            await equipment_service.sign_agreement(
                db=test_db,
                agreement_id=99999,
                user_id=patron.id,
                signature="David Rose",
            )
        assert "not found" in str(exc_info.value.detail).lower()


# ============================================================================
# 3. Verify AgreementStatusResponse shows signed=true
# ============================================================================


@pytest.mark.asyncio
class TestAgreementStatusAfterSigning:
    """Verify agreement status reflects signed state correctly."""

    async def test_agreement_status_shows_signed_true(self, test_db: AsyncSession, patron: User):
        """After signing, check_patron_agreement returns True."""
        # Create and sign agreement
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        # Check agreement status
        has_valid, found_agreement = await equipment_service.check_patron_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_type=EquipmentType.LAPTOP,
        )

        assert has_valid is True
        assert found_agreement is not None
        assert found_agreement.id == agreement.id
        assert found_agreement.status == AgreementStatus.SIGNED
        assert found_agreement.signed_at is not None

    async def test_agreement_status_shows_false_when_unsigned(
        self, test_db: AsyncSession, patron: User
    ):
        """Before signing, check_patron_agreement returns False."""
        # Create but don't sign
        await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )

        has_valid, found_agreement = await equipment_service.check_patron_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_type=EquipmentType.LAPTOP,
        )

        assert has_valid is False

    async def test_agreement_status_shows_false_when_revoked(
        self, test_db: AsyncSession, patron: User, staff: User
    ):
        """After revocation, check_patron_agreement returns False."""
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        # Revoke
        await equipment_service.revoke_agreement(
            db=test_db,
            agreement_id=agreement.id,
            revoked_by_id=staff.id,
            reason="Patron violated terms",
        )

        has_valid, found_agreement = await equipment_service.check_patron_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_type=EquipmentType.LAPTOP,
        )

        assert has_valid is False

    async def test_agreement_is_valid_property(self, test_db: AsyncSession, patron: User):
        """The is_valid property on the model returns True after signing."""
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )

        # Before signing
        assert agreement.is_valid is False

        # Sign
        signed = await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        assert signed.is_valid is True


# ============================================================================
# 4. Check that agreement is required before checkout is allowed
# ============================================================================


@pytest.mark.asyncio
class TestAgreementRequiredForCheckout:
    """Verify that laptop checkout is blocked without a signed agreement."""

    async def test_checkout_blocked_without_agreement(
        self, test_db: AsyncSession, patron: User, laptop: Equipment
    ):
        """Attempting checkout without signed agreement raises 403."""
        with pytest.raises(Exception) as exc_info:
            await equipment_service.checkout_equipment(
                db=test_db,
                equipment_id=laptop.id,
                patron_id=patron.id,
            )
        assert exc_info.value.status_code == 403
        assert "agreement" in str(exc_info.value.detail).lower()

    async def test_checkout_blocked_with_pending_agreement(
        self, test_db: AsyncSession, patron: User, laptop: Equipment
    ):
        """Pending (unsigned) agreement still blocks checkout."""
        # Create but don't sign
        await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )

        with pytest.raises(Exception) as exc_info:
            await equipment_service.checkout_equipment(
                db=test_db,
                equipment_id=laptop.id,
                patron_id=patron.id,
            )
        assert exc_info.value.status_code == 403
        assert "agreement" in str(exc_info.value.detail).lower()

    async def test_checkout_succeeds_with_signed_agreement(
        self, test_db: AsyncSession, patron: User, laptop: Equipment
    ):
        """Checkout succeeds after patron signs the agreement."""
        # Create and sign agreement
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        # Now checkout should succeed
        checkout = await equipment_service.checkout_equipment(
            db=test_db,
            equipment_id=laptop.id,
            patron_id=patron.id,
        )

        assert checkout is not None
        assert checkout.equipment_id == laptop.id
        assert checkout.user_id == patron.id
        assert checkout.status.value == "active"
        assert checkout.due_date is not None

    async def test_checkout_allowed_when_no_agreement_required(
        self, test_db: AsyncSession, patron: User, laptop_no_agreement: Equipment
    ):
        """Equipment not requiring agreement can be checked out freely."""
        checkout = await equipment_service.checkout_equipment(
            db=test_db,
            equipment_id=laptop_no_agreement.id,
            patron_id=patron.id,
        )

        assert checkout is not None
        assert checkout.equipment_id == laptop_no_agreement.id
        assert checkout.user_id == patron.id

    async def test_checkout_updates_equipment_status(
        self, test_db: AsyncSession, patron: User, laptop: Equipment
    ):
        """After checkout, equipment status changes to CHECKED_OUT."""
        # Sign agreement first
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
        )

        await equipment_service.checkout_equipment(
            db=test_db,
            equipment_id=laptop.id,
            patron_id=patron.id,
        )

        # Refresh to get updated status
        await test_db.refresh(laptop)
        assert laptop.status == EquipmentStatus.CHECKED_OUT


# ============================================================================
# 5. Verify visit status changes to COMPLETED with all metrics stored
# ============================================================================


def _next_tuesday() -> date:
    """Return the date of next Tuesday from today."""
    today = date.today()
    days_ahead = 1 - today.weekday()  # Monday=0, Tuesday=1
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


@pytest.mark.asyncio
class TestVisitCompletionWithMetrics:
    """Verify visit status transitions to COMPLETED with all metrics stored."""

    async def test_complete_visit_with_full_metrics(
        self, test_db: AsyncSession, outreach_partner: OutreachPartner, staff: User
    ):
        """Complete a storytime visit and verify all metrics are stored."""
        next_tue = _next_tuesday()

        # Create a scheduled visit
        visit = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="storytime",
            status="scheduled",
            title="Storytime at Somewhere Up North Elementary",
            description="Interactive read-aloud session for K-2 students",
            scheduled_date=next_tue,
            scheduled_start_time="10:00",
            scheduled_end_time="11:00",
            location_name="Somewhere Up North Elementary",
            location_room="Library",
            location_address="456 Elm Street, Somewhere Up North, CA 91234",
            expected_attendees=30,
            age_group="children",
            grade_levels=["K", "1", "2"],
            lead_staff_id=staff.id,
            materials_needed=["Picture books", "Puppets", "Library card applications"],
            items_to_deliver=50,
            created_by_id=staff.id,
        )
        test_db.add(visit)
        await test_db.commit()
        await test_db.refresh(visit)

        assert visit.status == "scheduled"

        # Complete the visit with metrics
        visit.status = "completed"
        visit.actual_attendees = 25
        visit.new_cards_issued = 3
        visit.items_delivered = 45
        visit.books_checked_out = 45
        visit.partner_rating = 5
        visit.outcome_notes = "Wonderful storytime session! Children were very engaged."
        visit.partner_feedback = "The kids absolutely loved the puppet show portion."
        visit.staff_notes = "Strong interest in summer reading program."
        visit.actual_start_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 10, 0, tzinfo=timezone.utc
        )
        visit.actual_end_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 11, 0, tzinfo=timezone.utc
        )
        visit.follow_up_needed = True
        visit.follow_up_notes = "Discuss summer reading program enrollment"
        visit.next_visit_date = next_tue + timedelta(days=14)

        await test_db.commit()
        await test_db.refresh(visit)

        # Verify COMPLETED status and all metrics
        assert visit.status == "completed"
        assert visit.actual_attendees == 25
        assert visit.new_cards_issued == 3
        assert visit.items_delivered == 45
        assert visit.books_checked_out == 45
        assert visit.partner_rating == 5
        assert "engaged" in visit.outcome_notes
        assert "puppet show" in visit.partner_feedback
        assert visit.actual_start_time is not None
        assert visit.actual_end_time is not None
        assert visit.follow_up_needed is True
        assert visit.next_visit_date == next_tue + timedelta(days=14)

    async def test_completed_visit_persists_in_database(
        self, test_db: AsyncSession, outreach_partner: OutreachPartner, staff: User
    ):
        """Verify completed visit can be queried back from the database."""
        next_tue = _next_tuesday()

        visit = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="classroom_visit",
            status="scheduled",
            title="Library Skills Workshop",
            scheduled_date=next_tue,
            scheduled_start_time="13:00",
            scheduled_end_time="14:00",
            location_name="Somewhere Up North Elementary",
            expected_attendees=20,
            lead_staff_id=staff.id,
            created_by_id=staff.id,
        )
        test_db.add(visit)
        await test_db.commit()
        await test_db.refresh(visit)

        visit_id = visit.id

        # Complete it
        visit.status = "completed"
        visit.actual_attendees = 18
        visit.new_cards_issued = 5
        visit.books_checked_out = 30
        visit.partner_rating = 4
        visit.outcome_notes = "Great engagement from 3rd graders"
        visit.actual_start_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 13, 5, tzinfo=timezone.utc
        )
        visit.actual_end_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 13, 55, tzinfo=timezone.utc
        )

        await test_db.commit()

        # Query back from database
        result = await test_db.execute(select(OutreachVisit).where(OutreachVisit.id == visit_id))
        fetched = result.scalar_one()

        assert fetched.status == "completed"
        assert fetched.actual_attendees == 18
        assert fetched.new_cards_issued == 5
        assert fetched.books_checked_out == 30
        assert fetched.partner_rating == 4
        assert fetched.outcome_notes == "Great engagement from 3rd graders"


# ============================================================================
# 6. Cancel a different scheduled visit and verify CANCELLED status
# ============================================================================


@pytest.mark.asyncio
class TestVisitCancellation:
    """Verify visit cancellation updates status and stores reason."""

    async def test_cancel_scheduled_visit(
        self, test_db: AsyncSession, outreach_partner: OutreachPartner, staff: User
    ):
        """Cancel a scheduled visit and verify CANCELLED status."""
        visit = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="book_delivery",
            status="scheduled",
            title="Book Delivery to Somewhere Up North Elementary",
            description="Delivering new collection of chapter books for 3rd-5th graders",
            scheduled_date=_next_tuesday() + timedelta(days=7),
            scheduled_start_time="14:00",
            scheduled_end_time="14:30",
            location_name="Somewhere Up North Elementary",
            location_room="Front Office",
            expected_attendees=2,
            items_to_deliver=30,
            lead_staff_id=staff.id,
            created_by_id=staff.id,
        )
        test_db.add(visit)
        await test_db.commit()
        await test_db.refresh(visit)

        assert visit.status == "scheduled"

        # Cancel the visit
        visit.status = "cancelled"
        visit.cancellation_reason = "School closed for teacher professional development day"
        visit.cancelled_by_id = staff.id
        visit.cancelled_at = datetime.now(timezone.utc)

        await test_db.commit()
        await test_db.refresh(visit)

        # Verify CANCELLED status
        assert visit.status == "cancelled"
        assert visit.cancellation_reason == "School closed for teacher professional development day"
        assert visit.cancelled_by_id == staff.id
        assert visit.cancelled_at is not None

    async def test_cancelled_visit_persists_in_database(
        self, test_db: AsyncSession, outreach_partner: OutreachPartner, staff: User
    ):
        """Verify cancelled visit can be queried back from the database."""
        visit = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="workshop",
            status="scheduled",
            title="Library Skills Workshop",
            scheduled_date=_next_tuesday() + timedelta(days=14),
            scheduled_start_time="09:00",
            scheduled_end_time="10:00",
            location_name="Somewhere Up North Elementary",
            location_room="Computer Lab",
            expected_attendees=20,
            lead_staff_id=staff.id,
            created_by_id=staff.id,
        )
        test_db.add(visit)
        await test_db.commit()
        await test_db.refresh(visit)

        visit_id = visit.id

        # Cancel
        visit.status = "cancelled"
        visit.cancellation_reason = "Computer lab unavailable due to maintenance"
        visit.cancelled_by_id = staff.id
        visit.cancelled_at = datetime.now(timezone.utc)

        await test_db.commit()

        # Query back
        result = await test_db.execute(select(OutreachVisit).where(OutreachVisit.id == visit_id))
        fetched = result.scalar_one()

        assert fetched.status == "cancelled"
        assert fetched.cancellation_reason == "Computer lab unavailable due to maintenance"
        assert fetched.cancelled_by_id == staff.id
        assert fetched.cancelled_at is not None


# ============================================================================
# End-to-end: Full laptop lending agreement + visit lifecycle
# ============================================================================


@pytest.mark.asyncio
class TestFullLaptopLendingLifecycle:
    """End-to-end test combining agreement, checkout, and visit workflows."""

    async def test_full_lifecycle(
        self,
        test_db: AsyncSession,
        patron: User,
        staff: User,
        laptop: Equipment,
        outreach_partner: OutreachPartner,
    ):
        """
        Full lifecycle:
        1. Create laptop agreement with laptop-specific template
        2. Verify checkout blocked without signing
        3. Sign the agreement
        4. Verify agreement status shows signed=True
        5. Successfully checkout laptop
        6. Complete an outreach visit with metrics
        7. Cancel a different visit
        """
        # --- Step 1: Create laptop agreement ---
        agreement = await equipment_service.get_or_create_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_types=[EquipmentType.LAPTOP],
        )
        assert agreement.status == AgreementStatus.PENDING
        assert "LAPTOP LENDING AGREEMENT" in agreement.agreement_text

        # --- Step 2: Verify checkout is blocked ---
        with pytest.raises(Exception) as exc_info:
            await equipment_service.checkout_equipment(
                db=test_db,
                equipment_id=laptop.id,
                patron_id=patron.id,
            )
        assert exc_info.value.status_code == 403

        # --- Step 3: Sign the agreement ---
        signed = await equipment_service.sign_agreement(
            db=test_db,
            agreement_id=agreement.id,
            user_id=patron.id,
            signature="David Rose",
            ip_address="10.0.0.42",
        )
        assert signed.status == AgreementStatus.SIGNED
        assert signed.signature == "David Rose"

        # --- Step 4: Verify agreement status ---
        has_valid, valid_agreement = await equipment_service.check_patron_agreement(
            db=test_db,
            user_id=patron.id,
            equipment_type=EquipmentType.LAPTOP,
        )
        assert has_valid is True
        assert valid_agreement.signed_at is not None

        # --- Step 5: Successfully checkout laptop ---
        checkout = await equipment_service.checkout_equipment(
            db=test_db,
            equipment_id=laptop.id,
            patron_id=patron.id,
        )
        assert checkout.equipment_id == laptop.id
        assert checkout.user_id == patron.id
        assert checkout.status.value == "active"

        # --- Step 6: Complete a visit with full metrics ---
        next_tue = _next_tuesday()
        storytime = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="storytime",
            status="scheduled",
            title="Storytime at Somewhere Up North Elementary",
            scheduled_date=next_tue,
            scheduled_start_time="10:00",
            scheduled_end_time="11:00",
            location_name="Somewhere Up North Elementary",
            location_room="Library",
            expected_attendees=30,
            age_group="children",
            grade_levels=["K", "1", "2"],
            lead_staff_id=staff.id,
            items_to_deliver=50,
            created_by_id=staff.id,
        )
        test_db.add(storytime)
        await test_db.commit()
        await test_db.refresh(storytime)

        assert storytime.status == "scheduled"

        storytime.status = "completed"
        storytime.actual_attendees = 25
        storytime.new_cards_issued = 3
        storytime.items_delivered = 45
        storytime.books_checked_out = 45
        storytime.partner_rating = 5
        storytime.outcome_notes = "Excellent session with 25 enthusiastic children"
        storytime.actual_start_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 10, 0, tzinfo=timezone.utc
        )
        storytime.actual_end_time = datetime(
            next_tue.year, next_tue.month, next_tue.day, 11, 0, tzinfo=timezone.utc
        )

        await test_db.commit()
        await test_db.refresh(storytime)

        assert storytime.status == "completed"
        assert storytime.actual_attendees == 25
        assert storytime.new_cards_issued == 3
        assert storytime.books_checked_out == 45
        assert storytime.partner_rating == 5

        # --- Step 7: Cancel a different scheduled visit ---
        workshop = OutreachVisit(
            partner_id=outreach_partner.id,
            visit_type="workshop",
            status="scheduled",
            title="Digital Literacy Workshop",
            scheduled_date=next_tue + timedelta(days=7),
            scheduled_start_time="13:00",
            scheduled_end_time="14:00",
            location_name="Somewhere Up North Elementary",
            location_room="Computer Lab",
            expected_attendees=20,
            lead_staff_id=staff.id,
            created_by_id=staff.id,
        )
        test_db.add(workshop)
        await test_db.commit()
        await test_db.refresh(workshop)

        assert workshop.status == "scheduled"

        workshop.status = "cancelled"
        workshop.cancellation_reason = "Computer lab unavailable due to maintenance"
        workshop.cancelled_by_id = staff.id
        workshop.cancelled_at = datetime.now(timezone.utc)

        await test_db.commit()
        await test_db.refresh(workshop)

        assert workshop.status == "cancelled"
        assert workshop.cancellation_reason is not None
        assert workshop.cancelled_at is not None

        # --- Final verification: query all visits from DB ---
        result = await test_db.execute(
            select(OutreachVisit)
            .where(OutreachVisit.partner_id == outreach_partner.id)
            .order_by(OutreachVisit.scheduled_date)
        )
        all_visits = result.scalars().all()
        assert len(all_visits) == 2

        completed_visit = next(v for v in all_visits if v.status == "completed")
        cancelled_visit = next(v for v in all_visits if v.status == "cancelled")

        assert completed_visit.actual_attendees == 25
        assert completed_visit.partner_rating == 5
        assert cancelled_visit.cancellation_reason is not None
