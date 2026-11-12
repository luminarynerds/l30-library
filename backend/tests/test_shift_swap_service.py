# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for Shift Swap Service

Tests cover:
- Listing creation, retrieval, update, withdrawal
- Claim management and approval/rejection
- Automated matching algorithm
- Reliability scoring (karma system)
- Gaming prevention
- Staff preferences
"""

import pytest
from datetime import datetime, date, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Base, User, UserRole, ShiftSwapListing, ShiftSwapListingType
from app.services.shift_swap_service import ShiftSwapService


# Test fixtures
@pytest.fixture
async def async_db(test_db):
    """Use the standard Postgres test database.

    This file used to spin up its own in-memory sqlite engine and run
    Base.metadata.create_all against the *entire* schema, which fails outright
    on sqlite once any model anywhere uses a Postgres-only column type
    (JSONB, ARRAY, TSVECTOR, ...). Riding the shared postgres test_db fixture
    sidesteps dialect compatibility entirely.
    """
    return test_db


@pytest.fixture
async def test_users(async_db):
    """Create test users"""
    user1 = User(
        id=1,
        email="staff1@example.com",
        password_hash="hashed_password",
        first_name="John",
        last_name="Doe",
        role=UserRole.STAFF,
        is_active=True,
    )
    user2 = User(
        id=2,
        email="staff2@example.com",
        password_hash="hashed_password",
        first_name="Jane",
        last_name="Smith",
        role=UserRole.STAFF,
        is_active=True,
    )
    async_db.add(user1)
    async_db.add(user2)
    await async_db.commit()
    return user1, user2


# ============================================================================
# Listing Tests
# ============================================================================


@pytest.mark.asyncio
async def test_create_listing(async_db, test_users):
    """Test creating a shift swap listing"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
        description="Regular morning shift",
    )

    assert listing.id is not None
    assert listing.user_id == user1.id
    assert listing.branch_id == 1
    assert listing.listing_type == ShiftSwapListingType.giving_away
    assert listing.shift_date == shift_date
    await async_db.commit()


@pytest.mark.asyncio
async def test_get_listing(async_db, test_users):
    """Test retrieving a listing"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    # Create a listing
    shift_date = date.today() + timedelta(days=5)
    created = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    # Retrieve it
    retrieved = await service.get_listing(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id


@pytest.mark.asyncio
async def test_withdraw_listing(async_db, test_users):
    """Test withdrawing a listing"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    # Create and withdraw
    shift_date = date.today() + timedelta(days=5)
    created = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    withdrawn = await service.withdraw_listing(created.id, user1.id)
    # ShiftSwapListingStatus is a StrEnum backed by SQLAlchemy's Enum type
    # with values_callable; the loaded attribute comes back as a plain str,
    # not the enum member, so .value isn't available -- compare directly.
    assert withdrawn.status == "withdrawn"


@pytest.mark.asyncio
async def test_withdraw_listing_not_owner(async_db, test_users):
    """Test that non-owners cannot withdraw listings"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    shift_date = date.today() + timedelta(days=5)
    created = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    # Try to withdraw as different user
    with pytest.raises(ValueError):
        await service.withdraw_listing(created.id, user2.id)


# ============================================================================
# Claim Tests
# ============================================================================


@pytest.mark.asyncio
async def test_claim_listing(async_db, test_users):
    """Test claiming a listing"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    # Create listing
    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    # Claim it
    claim = await service.claim_listing(
        listing_id=listing.id, claimer_id=user2.id, message="I can cover this shift"
    )

    assert claim.id is not None
    assert claim.listing_id == listing.id
    assert claim.claimer_id == user2.id
    await async_db.commit()


@pytest.mark.asyncio
async def test_cannot_claim_own_listing(async_db, test_users):
    """Test that staff cannot claim their own listings"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    with pytest.raises(ValueError):
        await service.claim_listing(listing_id=listing.id, claimer_id=user1.id)


@pytest.mark.asyncio
async def test_cannot_claim_twice(async_db, test_users):
    """Test that a user cannot claim the same listing twice"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    # First claim succeeds
    await service.claim_listing(listing_id=listing.id, claimer_id=user2.id)
    await async_db.commit()

    # Second claim should fail
    with pytest.raises(ValueError):
        await service.claim_listing(listing_id=listing.id, claimer_id=user2.id)


@pytest.mark.asyncio
async def test_approve_claim(async_db, test_users):
    """Test approving a claim"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    claim = await service.claim_listing(listing_id=listing.id, claimer_id=user2.id)
    await async_db.commit()

    approved = await service.approve_claim(claim.id, user1.id, "Approved")

    # ShiftSwapClaimStatus is a StrEnum backed by SQLAlchemy's Enum type
    # with values_callable; the loaded attribute comes back as a plain str,
    # not the enum member, so .value isn't available -- compare directly.
    assert approved.status == "approved"
    assert approved.approved_by_id == user1.id

    # Check that listing is now marked as claimed. Same StrEnum-loads-as-str
    # situation as `approved.status` above -- compare directly, no `.value`.
    listing = await service.get_listing(listing.id)
    assert listing.status == "claimed"
    await async_db.commit()


# ============================================================================
# Reliability Score Tests
# ============================================================================


@pytest.mark.asyncio
async def test_reliability_score_creation(async_db, test_users):
    """Test creating a reliability score record"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    score = await service.get_or_create_reliability_score(user1.id)

    assert score.user_id == user1.id
    assert score.reliability_score == 100.0
    assert score.completion_rate == 100.0
    await async_db.commit()


@pytest.mark.asyncio
async def test_mark_swap_completed(async_db, test_users):
    """Test marking a swap as completed"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    # Setup
    shift_date = date.today() + timedelta(days=5)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    claim = await service.claim_listing(listing_id=listing.id, claimer_id=user2.id)
    await async_db.commit()

    await service.approve_claim(claim.id, user1.id)
    await async_db.commit()

    # Mark as completed
    score = await service.mark_swap_completed(claim.id)

    assert score.total_completed_swaps == 1
    assert score.times_stood_up == 1
    await async_db.commit()


@pytest.mark.asyncio
async def test_gaming_penalty_detection(async_db, test_users):
    """Test that calling out after swap triggers gaming penalty"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    # Setup: complete a swap
    shift_date = date.today() + timedelta(days=1)
    listing = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    claim = await service.claim_listing(listing_id=listing.id, claimer_id=user2.id)
    await async_db.commit()

    await service.approve_claim(claim.id, user1.id)
    await async_db.commit()

    await service.mark_swap_completed(claim.id)
    await async_db.commit()

    # Now detect gaming - user calls out on the swapped shift
    warning = await service.detect_gaming_and_penalize(user2.id, shift_date)

    assert warning is not None

    # Check penalty was applied
    score = await service.get_or_create_reliability_score(user2.id)
    assert score.called_out_after_swap_count == 1
    assert score.reliability_score < 100.0  # Major penalty applied
    await async_db.commit()


# ============================================================================
# Matching Algorithm Tests
# ============================================================================


@pytest.mark.asyncio
async def test_compatibility_score_same_branch(async_db, test_users):
    """Test that same branch increases compatibility score"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    shift_date = date.today() + timedelta(days=5)

    # Both in same branch
    giver = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )

    taker = await service.create_listing(
        user_id=user2.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.looking_for,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    score = await service._calculate_compatibility_score(giver, taker)
    assert score >= 40  # Same branch bonus


@pytest.mark.asyncio
async def test_find_matches(async_db, test_users):
    """Test that the matching algorithm finds compatible shifts"""
    service = ShiftSwapService(async_db)
    user1, user2 = test_users

    shift_date = date.today() + timedelta(days=5)

    # Create compatible listings
    _ = await service.create_listing(
        user_id=user1.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.giving_away,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )

    _ = await service.create_listing(
        user_id=user2.id,
        branch_id=1,
        listing_type=ShiftSwapListingType.looking_for,
        shift_date=shift_date,
        shift_start_time=time(9, 0),
        shift_end_time=time(17, 0),
        shift_type="opening",
    )
    await async_db.commit()

    matches = await service.find_matches()

    # Should find at least one match
    assert len(matches) > 0


# ============================================================================
# Staff Preferences Tests
# ============================================================================


@pytest.mark.asyncio
async def test_preference_profile_creation(async_db, test_users):
    """Test creating a staff preference profile"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    profile = await service.get_or_create_preference_profile(user1.id)

    assert profile.user_id == user1.id
    assert profile.wants_extra_hours == False
    await async_db.commit()


@pytest.mark.asyncio
async def test_update_preference_profile(async_db, test_users):
    """Test updating a staff preference profile"""
    service = ShiftSwapService(async_db)
    user1, _ = test_users

    profile = await service.update_preference_profile(
        user1.id,
        wants_extra_hours=True,
        max_extra_hours_per_week=15,
        preferred_shift_types=["opening", "mid_day"],
    )

    assert profile.wants_extra_hours == True
    assert profile.max_extra_hours_per_week == 15
    await async_db.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
