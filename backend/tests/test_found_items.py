# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for found items management.

Tests for:
- Found item creation and management
- Storage location management
- Auto-matching algorithm
- Claim verification workflow
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import select

from app.models.found_items import (
    FoundItem,
    FoundItemStatus,
    FoundItemStorageLocation,
    FoundItemMatch,
    FoundItemClaimVerification,
    ClaimVerificationStatus,
)
from app.models.lost_damaged import LostItemRecord, LostItemStatus, LostItemType
from app.models.user import User, UserRole
from app.services.found_item_service import (
    FoundItemService,
    StorageLocationService,
    ClaimVerificationService,
)
from app.core.datetime_utils import utc_now


@pytest.fixture
async def test_user(test_staff):
    """Alias: the staff fixture user, used as found_by/logged_by across this file."""
    return test_staff


class TestFoundItemService:
    """Tests for FoundItemService."""

    @pytest.mark.asyncio
    async def test_create_found_item(self, test_db, test_staff):
        """Test creating a found item."""
        service = FoundItemService(test_db)

        found_item = await service.create_found_item(
            description="Blue denim jacket",
            category="jacket",
            location_found="circulation desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
            color="blue",
            brand_or_label="Levi's",
            size="medium",
            estimated_value=Decimal("50.00"),
        )

        assert found_item.id is not None
        assert found_item.description == "Blue denim jacket"
        assert found_item.category == "jacket"
        assert found_item.status == FoundItemStatus.LOGGED
        assert found_item.retention_period_days == 30
        assert found_item.found_by_id == test_staff.id

    @pytest.mark.asyncio
    async def test_get_found_item(self, test_db, test_staff):
        """Test getting a found item by ID."""
        service = FoundItemService(test_db)

        # Create an item
        created = await service.create_found_item(
            description="Red glasses",
            category="glasses",
            location_found="study room 3",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Retrieve it
        retrieved = await service.get_found_item_by_id(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.description == "Red glasses"

    @pytest.mark.asyncio
    async def test_update_found_item(self, test_db, test_staff):
        """Test updating a found item."""
        service = FoundItemService(test_db)

        # Create an item
        created = await service.create_found_item(
            description="Brown leather bag",
            category="bag",
            location_found="entrance",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Update it
        updated = await service.update_found_item(
            created.id,
            description="Brown leather messenger bag",
            condition="good",
        )

        assert updated is not None
        assert updated.description == "Brown leather messenger bag"
        assert updated.condition == "good"

    @pytest.mark.asyncio
    async def test_list_found_items(self, test_db, test_staff):
        """Test listing found items."""
        service = FoundItemService(test_db)

        # Create multiple items
        for i in range(5):
            await service.create_found_item(
                description=f"Item {i}",
                category="general",
                location_found=f"location {i}",
                date_found=utc_now(),
                found_by=test_staff,
                logged_by=test_staff,
            )

        # List them
        items, total = await service.list_found_items(limit=10, offset=0)

        assert len(items) == 5
        assert total == 5

    @pytest.mark.asyncio
    async def test_search_found_items(self, test_db, test_staff):
        """Test searching found items."""
        service = FoundItemService(test_db)

        # Create items with different properties
        await service.create_found_item(
            description="Blue jacket",
            category="jacket",
            color="blue",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        await service.create_found_item(
            description="Red scarf",
            category="scarf",
            color="red",
            location_found="shelf",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Search by category
        items, total = await service.search_found_items(category="jacket", limit=10)
        assert len(items) == 1
        assert items[0].description == "Blue jacket"

        # Search by color
        items, total = await service.search_found_items(search_query="red", limit=10)
        assert len(items) == 1
        assert items[0].description == "Red scarf"

    @pytest.mark.asyncio
    async def test_add_photo(self, test_db, test_staff):
        """Test adding photos to a found item."""
        service = FoundItemService(test_db)

        # Create item
        found_item = await service.create_found_item(
            description="Item with photo",
            category="general",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Add photo
        photo = await service.add_photo(
            found_item_id=found_item.id,
            photo_url="https://example.com/photo.jpg",
            photo_key="found-items/123/photo.jpg",
            uploaded_by=test_staff,
            is_primary=True,
        )

        assert photo is not None
        assert photo.is_primary is True
        assert photo.found_item_id == found_item.id

    @pytest.mark.asyncio
    async def test_move_to_storage(self, test_db, test_staff):
        """Test moving item to different storage location."""
        found_service = FoundItemService(test_db)
        storage_service = StorageLocationService(test_db)

        # Create storage location
        location = await storage_service.create_storage_location(
            location_name="Lost & Found Shelf A",
            location_code="LF-A-001",
        )

        # Create found item
        found_item = await found_service.create_found_item(
            description="Item to move",
            category="general",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Move it
        moved = await found_service.move_to_storage(found_item.id, location.id)

        assert moved is not None
        assert moved.storage_location_id == location.id
        assert moved.storage_moved_at is not None

    @pytest.mark.asyncio
    async def test_dispose_found_item(self, test_db, test_staff):
        """Test disposing of a found item."""
        service = FoundItemService(test_db)

        # Create item
        found_item = await service.create_found_item(
            description="Item to dispose",
            category="general",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Dispose it
        disposed = await service.dispose_found_item(
            found_item_id=found_item.id,
            disposal_method="donated_to_charity",
            disposal_notes="Donated to local food bank",
        )

        assert disposed is not None
        assert disposed.disposal_method == "donated_to_charity"
        assert disposed.disposed_at is not None

    @pytest.mark.asyncio
    async def test_retention_period_calculation(self, test_db, test_staff):
        """Test that retention period is correctly calculated."""
        service = FoundItemService(test_db)

        now = utc_now()
        found_item = await service.create_found_item(
            description="Item with retention",
            category="general",
            location_found="desk",
            date_found=now,
            found_by=test_staff,
            logged_by=test_staff,
            retention_period_days=45,
        )

        expected_end = now + timedelta(days=45)
        # Allow 1 minute tolerance for database processing
        assert abs((found_item.retention_end_date - expected_end).total_seconds()) < 60


class TestStorageLocationService:
    """Tests for StorageLocationService."""

    @pytest.mark.asyncio
    async def test_create_storage_location(self, test_db):
        """Test creating a storage location."""
        service = StorageLocationService(test_db)

        location = await service.create_storage_location(
            location_name="Secure Storage Cabinet",
            location_code="LF-SEC-001",
            is_secure_storage=True,
            requires_verification=True,
        )

        assert location.id is not None
        assert location.location_name == "Secure Storage Cabinet"
        assert location.is_secure_storage is True

    @pytest.mark.asyncio
    async def test_list_storage_locations(self, test_db):
        """Test listing storage locations."""
        service = StorageLocationService(test_db)

        # Create multiple locations
        for i in range(3):
            await service.create_storage_location(
                location_name=f"Shelf {i}",
                location_code=f"LF-{i}",
            )

        locations, total = await service.list_storage_locations(limit=10)

        assert len(locations) >= 3
        assert total >= 3

    @pytest.mark.asyncio
    async def test_secure_storage_filtering(self, test_db):
        """Test filtering storage locations by security."""
        service = StorageLocationService(test_db)

        # Create secure and non-secure locations
        await service.create_storage_location(
            location_name="Secure Cabinet",
            location_code="LF-SEC",
            is_secure_storage=True,
        )

        await service.create_storage_location(
            location_name="Open Shelf",
            location_code="LF-OPEN",
            is_secure_storage=False,
        )

        # Get only secure
        secure, _ = await service.list_storage_locations(is_secure_only=True)

        assert all(loc.is_secure_storage for loc in secure)


class TestClaimVerificationService:
    """Tests for ClaimVerificationService."""

    @pytest.mark.asyncio
    async def test_file_claim(self, test_db, test_staff):
        """Test filing a claim for a found item."""
        found_service = FoundItemService(test_db)
        claim_service = ClaimVerificationService(test_db)

        # Create found item
        found_item = await found_service.create_found_item(
            description="Blue jacket",
            category="jacket",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )
        found_item.status = FoundItemStatus.WAITING_CLAIM
        await test_db.commit()

        # File claim
        claim = await claim_service.file_claim(
            found_item_id=found_item.id,
            patron=test_staff,
            claim_statement="This is my blue jacket, I lost it last week",
            distinctive_features={"pattern": "plaid", "size": "M"},
        )

        assert claim is not None
        assert claim.patron_id == test_staff.id
        assert claim.status == ClaimVerificationStatus.PENDING

    @pytest.mark.asyncio
    async def test_verify_identity(self, test_db, test_staff):
        """Test verifying patron identity."""
        found_service = FoundItemService(test_db)
        claim_service = ClaimVerificationService(test_db)

        # Create found item and file claim
        found_item = await found_service.create_found_item(
            description="Glasses",
            category="glasses",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )
        found_item.status = FoundItemStatus.WAITING_CLAIM
        await test_db.commit()

        claim = await claim_service.file_claim(
            found_item_id=found_item.id,
            patron=test_staff,
            claim_statement="My glasses",
        )

        # Verify identity
        verified = await claim_service.verify_identity(
            claim_id=claim.id,
            verification_method="library_card",
        )

        assert verified is not None
        assert verified.identity_verified is True

    @pytest.mark.asyncio
    async def test_review_claim_approval(self, test_db, test_staff):
        """Test approving a claim."""
        found_service = FoundItemService(test_db)
        claim_service = ClaimVerificationService(test_db)

        # Setup
        found_item = await found_service.create_found_item(
            description="Keys",
            category="keys",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )
        found_item.status = FoundItemStatus.WAITING_CLAIM
        await test_db.commit()

        claim = await claim_service.file_claim(
            found_item_id=found_item.id,
            patron=test_staff,
            claim_statement="My keys",
        )

        await claim_service.verify_identity(claim.id, "library_card")
        await claim_service.confirm_item(claim.id)

        # Review and approve
        reviewed = await claim_service.review_claim(
            claim_id=claim.id,
            approval_decision=True,
            reviewer=test_staff,
        )

        assert reviewed is not None
        assert reviewed.approval_decision is True
        assert reviewed.status == ClaimVerificationStatus.APPROVED

    @pytest.mark.asyncio
    async def test_review_claim_rejection(self, test_db, test_staff):
        """Test rejecting a claim."""
        found_service = FoundItemService(test_db)
        claim_service = ClaimVerificationService(test_db)

        # Setup
        found_item = await found_service.create_found_item(
            description="Wallet",
            category="wallet",
            location_found="desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )
        found_item.status = FoundItemStatus.WAITING_CLAIM
        await test_db.commit()

        claim = await claim_service.file_claim(
            found_item_id=found_item.id,
            patron=test_staff,
            claim_statement="My wallet",
        )

        # Review and reject
        reviewed = await claim_service.review_claim(
            claim_id=claim.id,
            approval_decision=False,
            reviewer=test_staff,
            rejection_reason="Description does not match",
        )

        assert reviewed is not None
        assert reviewed.approval_decision is False
        assert reviewed.status == ClaimVerificationStatus.REJECTED


class TestAutoMatching:
    """Tests for auto-matching algorithm."""

    @pytest.mark.asyncio
    async def test_auto_match_found_to_lost(self, test_db, test_staff):
        """Test auto-matching a found item to a lost item report."""
        found_service = FoundItemService(test_db)

        # Create a lost item record
        lost_item = LostItemRecord(
            status=LostItemStatus.REPORTED,
            lost_type=LostItemType.LOST_BY_PATRON,
            patron_id=test_staff.id,
            reported_by_id=test_staff.id,
            report_notes="Blue denim jacket with Levi's tag, size medium",
            last_known_location="circulation desk",
            reported_at=utc_now(),
        )
        test_db.add(lost_item)
        await test_db.flush()

        # Create a matching found item
        found_item = await found_service.create_found_item(
            description="Blue denim jacket",
            category="jacket",
            color="blue",
            brand_or_label="Levi's",
            size="medium",
            location_found="circulation desk",
            date_found=utc_now(),
            found_by=test_staff,
            logged_by=test_staff,
        )

        # Check that matches were created
        matches = await test_db.execute(
            select(FoundItemMatch).where(
                FoundItemMatch.found_item_id == found_item.id
            )
        )
        found_matches = matches.scalars().all()

        assert len(found_matches) > 0
        assert found_matches[0].lost_item_record_id == lost_item.id

    @pytest.mark.asyncio
    async def test_match_score_calculation(self, test_db, test_staff):
        """Test that match scores are calculated correctly."""
        service = FoundItemService(test_db)

        # Create a lost item with detailed description
        lost_item = LostItemRecord(
            status=LostItemStatus.REPORTED,
            lost_type=LostItemType.LOST_BY_PATRON,
            patron_id=test_staff.id,
            reported_by_id=test_staff.id,
            report_notes="Red backpack, small size, leather, near front entrance",
            reported_at=utc_now(),
        )

        # Create a matching found item
        found_item = FoundItem(
            description="Small red leather backpack",
            category="backpack",
            color="red",
            size="small",
            location_found="entrance",
            date_found=utc_now(),
            found_by_id=test_staff.id,
            logged_by_id=test_staff.id,
            retention_period_days=30,
            retention_end_date=utc_now() + timedelta(days=30),
        )

        # Calculate match score
        score = service._calculate_match_score(found_item, lost_item)

        assert score > 0
        assert score <= 100
