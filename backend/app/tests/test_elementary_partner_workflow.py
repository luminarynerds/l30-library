# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Test suite for elementary partner management workflow.
Tests the complete workflow: create partner, add contacts, update status, assign liaison, verify data.
"""

import pytest
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.outreach import (
    OutreachPartner, OutreachPartnerContact,
    PartnerType, OutreachPartnerStatus, PartnershipTier, SchoolLevel
)
from app.models.user import User, UserRole


@pytest.fixture
async def staff_user(db: AsyncSession) -> User:
    """Create the staff user who registers partners in these tests.

    outreach_partners.created_by_id is a real FK to users.id; every test
    below used to hardcode created_by_id=1, which only worked when a seed
    user happened to occupy that row. The shared app/tests/conftest.py
    `db` fixture starts from an empty database, so that FK now fails.
    """
    user = User(
        email="staff@example.com",
        password_hash="hashed_password",
        first_name="Library",
        last_name="Staff",
        role=UserRole.STAFF,
    )
    db.add(user)
    await db.flush()
    return user


@pytest.mark.asyncio
class TestElementaryPartnerWorkflow:
    """Test the complete elementary partner management workflow."""

    @pytest.fixture
    async def test_data(self, db: AsyncSession):
        """Fixture to provide test data."""
        return {
            "partner_name": "Somewhere Up North Elementary",
            "school_district": "Somewhere Up North School District",
            "primary_contact": {
                "name": "Principal Jane Doe",
                "title": "Principal",
                "email": "jane@sce.edu",
                "role": "Principal"
            },
            "secondary_contact": {
                "name": "Librarian John Smith",
                "title": "School Librarian",
                "email": "john@sce.edu",
                "role": "Librarian",
                "phone": "+1-555-0123"
            },
            "address": {
                "line1": "123 Main Street",
                "city": "Somewhere Up North",
                "state": "CA",
                "zip": "90210"
            }
        }

    async def test_01_create_elementary_partner_with_prospect_status(self, db: AsyncSession, test_data, staff_user):
        """Test creating a new elementary partner with PROSPECT status."""
        # Create partner
        partner = OutreachPartner(
            name=test_data["partner_name"],
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            partnership_tier=PartnershipTier.BRONZE.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            school_district=test_data["school_district"],
            primary_contact_name=test_data["primary_contact"]["name"],
            primary_contact_title=test_data["primary_contact"]["title"],
            primary_contact_email=test_data["primary_contact"]["email"],
            address_line1=test_data["address"]["line1"],
            city=test_data["address"]["city"],
            state=test_data["address"]["state"],
            zip_code=test_data["address"]["zip"],
            allows_bulk_checkout=True,
            allows_institutional_card=True,
            requires_deposit=False,
            default_deposit_amount=0.0,
            checkout_limit=100,
            loan_period_days=28,
            notes="New elementary school partnership - initial prospect",
            tags=["elementary", "school", "prospect"],
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()

        # Verify partner was created with correct initial values
        assert partner.id is not None
        assert partner.name == test_data["partner_name"]
        assert partner.partner_type == PartnerType.SCHOOL.value
        assert partner.status == OutreachPartnerStatus.PROSPECT.value
        assert partner.partnership_tier == PartnershipTier.BRONZE.value
        assert partner.school_level == SchoolLevel.ELEMENTARY.value
        assert partner.primary_contact_name == test_data["primary_contact"]["name"]
        assert partner.primary_contact_email == test_data["primary_contact"]["email"]

        await db.commit()
        return partner.id

    async def test_02_add_secondary_contact(self, db: AsyncSession, test_data, staff_user):
        """Test adding a secondary contact (Librarian John Smith)."""
        # First create a partner
        partner = OutreachPartner(
            name=test_data["partner_name"],
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            partnership_tier=PartnershipTier.BRONZE.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            school_district=test_data["school_district"],
            primary_contact_name=test_data["primary_contact"]["name"],
            primary_contact_title=test_data["primary_contact"]["title"],
            primary_contact_email=test_data["primary_contact"]["email"],
            address_line1=test_data["address"]["line1"],
            city=test_data["address"]["city"],
            state=test_data["address"]["state"],
            zip_code=test_data["address"]["zip"],
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Add secondary contact
        contact = OutreachPartnerContact(
            partner_id=partner_id,
            name=test_data["secondary_contact"]["name"],
            title=test_data["secondary_contact"]["title"],
            email=test_data["secondary_contact"]["email"],
            phone=test_data["secondary_contact"]["phone"],
            role=test_data["secondary_contact"]["role"],
            is_primary=False,
            receives_notifications=True,
            preferred_contact_method="email",
            notes="School librarian - coordinates book collections"
        )
        db.add(contact)
        await db.flush()

        # Verify contact was added
        assert contact.id is not None
        assert contact.partner_id == partner_id
        assert contact.name == test_data["secondary_contact"]["name"]
        assert contact.email == test_data["secondary_contact"]["email"]
        assert contact.role == test_data["secondary_contact"]["role"]
        assert contact.is_primary is False

        await db.commit()
        return partner_id

    async def test_03_update_partner_status_to_active(self, db: AsyncSession, test_data, staff_user):
        """Test updating partner status from PROSPECT to ACTIVE."""
        # Create partner
        partner = OutreachPartner(
            name=test_data["partner_name"],
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            partnership_tier=PartnershipTier.BRONZE.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            school_district=test_data["school_district"],
            primary_contact_name=test_data["primary_contact"]["name"],
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Verify initial status
        assert partner.status == OutreachPartnerStatus.PROSPECT.value

        # Update status
        partner.status = OutreachPartnerStatus.ACTIVE.value
        await db.flush()

        # Verify status was updated
        assert partner.status == OutreachPartnerStatus.ACTIVE.value

        await db.commit()

        # Verify persistence by querying from database
        query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
        result = await db.execute(query)
        updated_partner = result.scalar_one()
        assert updated_partner.status == OutreachPartnerStatus.ACTIVE.value

    async def test_04_assign_staff_liaison_via_platinum_tier(self, db: AsyncSession, test_data, staff_user):
        """Test assigning staff liaison by upgrading partnership tier to PLATINUM."""
        # Create partner
        partner = OutreachPartner(
            name=test_data["partner_name"],
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            partnership_tier=PartnershipTier.BRONZE.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Verify initial tier
        assert partner.partnership_tier == PartnershipTier.BRONZE.value

        # Upgrade tier to PLATINUM (which includes dedicated staff liaison)
        partner.partnership_tier = PartnershipTier.PLATINUM.value
        await db.flush()

        # Verify tier was updated
        assert partner.partnership_tier == PartnershipTier.PLATINUM.value

        await db.commit()

        # Verify persistence
        query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
        result = await db.execute(query)
        updated_partner = result.scalar_one()
        assert updated_partner.partnership_tier == PartnershipTier.PLATINUM.value

    async def test_05_complete_workflow_end_to_end(self, db: AsyncSession, test_data, staff_user):
        """Test the complete workflow from start to finish."""
        # STEP 1: Create partner with PROSPECT status
        partner = OutreachPartner(
            name=test_data["partner_name"],
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            partnership_tier=PartnershipTier.BRONZE.value,
            school_level=SchoolLevel.ELEMENTARY.value,
            school_district=test_data["school_district"],
            primary_contact_name=test_data["primary_contact"]["name"],
            primary_contact_title=test_data["primary_contact"]["title"],
            primary_contact_email=test_data["primary_contact"]["email"],
            address_line1=test_data["address"]["line1"],
            city=test_data["address"]["city"],
            state=test_data["address"]["state"],
            zip_code=test_data["address"]["zip"],
            allows_bulk_checkout=True,
            allows_institutional_card=True,
            requires_deposit=False,
            checkout_limit=100,
            loan_period_days=28,
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # STEP 2: Add secondary contact
        contact = OutreachPartnerContact(
            partner_id=partner_id,
            name=test_data["secondary_contact"]["name"],
            title=test_data["secondary_contact"]["title"],
            email=test_data["secondary_contact"]["email"],
            phone=test_data["secondary_contact"]["phone"],
            role=test_data["secondary_contact"]["role"],
            is_primary=False,
            receives_notifications=True,
            preferred_contact_method="email"
        )
        db.add(contact)
        await db.flush()

        # STEP 3: Update status to ACTIVE
        partner.status = OutreachPartnerStatus.ACTIVE.value
        await db.flush()

        # STEP 4: Assign staff liaison (upgrade to PLATINUM)
        partner.partnership_tier = PartnershipTier.PLATINUM.value
        await db.flush()

        # Commit all changes
        await db.commit()

        # STEP 5: Verify all data
        # Query partner from database
        query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
        result = await db.execute(query)
        verified_partner = result.scalar_one()

        # Verify partner data
        assert verified_partner.id == partner_id
        assert verified_partner.name == test_data["partner_name"]
        assert verified_partner.partner_type == PartnerType.SCHOOL.value
        assert verified_partner.status == OutreachPartnerStatus.ACTIVE.value
        assert verified_partner.partnership_tier == PartnershipTier.PLATINUM.value
        assert verified_partner.school_level == SchoolLevel.ELEMENTARY.value
        assert verified_partner.school_district == test_data["school_district"]
        assert verified_partner.primary_contact_name == test_data["primary_contact"]["name"]
        assert verified_partner.primary_contact_email == test_data["primary_contact"]["email"]
        assert verified_partner.address_line1 == test_data["address"]["line1"]
        assert verified_partner.city == test_data["address"]["city"]
        assert verified_partner.state == test_data["address"]["state"]
        assert verified_partner.zip_code == test_data["address"]["zip"]

        # Query contacts from database
        contact_query = select(OutreachPartnerContact).where(
            OutreachPartnerContact.partner_id == partner_id
        )
        contact_result = await db.execute(contact_query)
        contacts = contact_result.scalars().all()

        # The "primary contact" (Principal Jane Doe) isn't a row in
        # outreach_partner_contacts at all -- it's the denormalized
        # primary_contact_* columns on outreach_partners itself (already
        # asserted above via verified_partner.primary_contact_*). Only
        # additional contacts, like the secondary one added in STEP 2, live
        # in this table, so exactly 1 row is expected here, not 2.
        assert len(contacts) == 1

        # Find the secondary contact
        secondary = next(c for c in contacts if c.is_primary is False)
        assert secondary.name == test_data["secondary_contact"]["name"]
        assert secondary.email == test_data["secondary_contact"]["email"]
        assert secondary.role == test_data["secondary_contact"]["role"]
        assert secondary.title == test_data["secondary_contact"]["title"]
        assert secondary.phone == test_data["secondary_contact"]["phone"]


@pytest.mark.asyncio
class TestPartnerDataIntegrity:
    """Test data integrity for partner and contact management."""

    async def test_partner_cascade_deletes_contacts_on_delete(self, db: AsyncSession, staff_user):
        """Test that deleting a partner cascades to delete its contacts."""
        # Create partner
        partner = OutreachPartner(
            name="Test Partner",
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.ACTIVE.value,
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Add contact
        contact = OutreachPartnerContact(
            partner_id=partner_id,
            name="Test Contact",
            email="test@example.com"
        )
        db.add(contact)
        await db.flush()

        # Verify contact exists
        query = select(OutreachPartnerContact).where(OutreachPartnerContact.partner_id == partner_id)
        result = await db.execute(query)
        initial_contacts = result.scalars().all()
        assert len(initial_contacts) == 1

        # Delete partner
        await db.delete(partner)
        await db.flush()

        # Verify contacts are also deleted (cascade)
        query = select(OutreachPartnerContact).where(OutreachPartnerContact.partner_id == partner_id)
        result = await db.execute(query)
        remaining_contacts = result.scalars().all()
        assert len(remaining_contacts) == 0

        await db.commit()

    async def test_multiple_contacts_per_partner(self, db: AsyncSession, staff_user):
        """Test that a partner can have multiple contacts with different roles."""
        # Create partner
        partner = OutreachPartner(
            name="Multi-Contact Partner",
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.ACTIVE.value,
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Add multiple contacts
        roles = ["Principal", "Librarian", "Teacher", "Admin"]
        contacts_data = []
        for i, role in enumerate(roles):
            contact = OutreachPartnerContact(
                partner_id=partner_id,
                name=f"Contact {i+1}",
                title=role,
                email=f"contact{i+1}@example.com",
                role=role,
                is_primary=(i == 0)
            )
            db.add(contact)
            contacts_data.append(contact)

        await db.flush()

        # Verify all contacts were created
        query = select(OutreachPartnerContact).where(
            OutreachPartnerContact.partner_id == partner_id
        )
        result = await db.execute(query)
        retrieved_contacts = result.scalars().all()

        assert len(retrieved_contacts) == len(roles)

        # Verify each contact has correct role
        for i, contact in enumerate(sorted(retrieved_contacts, key=lambda c: c.name)):
            assert contact.role in roles

        await db.commit()

    async def test_partner_status_transitions(self, db: AsyncSession, staff_user):
        """Test valid partner status transitions."""
        # Create partner
        partner = OutreachPartner(
            name="Status Test Partner",
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.PROSPECT.value,
            created_by_id=staff_user.id
        )
        db.add(partner)
        await db.flush()
        partner_id = partner.id

        # Test various status transitions
        statuses_to_test = [
            OutreachPartnerStatus.PROSPECT.value,
            OutreachPartnerStatus.ACTIVE.value,
            OutreachPartnerStatus.INACTIVE.value,
            OutreachPartnerStatus.SUSPENDED.value,
            OutreachPartnerStatus.ACTIVE.value,  # Can go back to active
        ]

        for status in statuses_to_test:
            partner.status = status
            await db.flush()

            # Verify status persists
            query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
            result = await db.execute(query)
            updated_partner = result.scalar_one()
            assert updated_partner.status == status

        await db.commit()

    async def test_partnership_tier_levels(self, db: AsyncSession, staff_user):
        """Test that partnership tiers are properly managed."""
        # Create partners with different tiers
        tiers = [
            PartnershipTier.BRONZE.value,
            PartnershipTier.SILVER.value,
            PartnershipTier.GOLD.value,
            PartnershipTier.PLATINUM.value,
        ]

        partner_ids = []
        for i, tier in enumerate(tiers):
            partner = OutreachPartner(
                name=f"Partner {tier.upper()}",
                partner_type=PartnerType.SCHOOL.value,
                status=OutreachPartnerStatus.ACTIVE.value,
                partnership_tier=tier,
                created_by_id=staff_user.id
            )
            db.add(partner)
            await db.flush()
            partner_ids.append((partner.id, tier))

        await db.commit()

        # Verify all tiers were saved correctly
        for partner_id, expected_tier in partner_ids:
            query = select(OutreachPartner).where(OutreachPartner.id == partner_id)
            result = await db.execute(query)
            partner = result.scalar_one()
            assert partner.partnership_tier == expected_tier
