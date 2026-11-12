# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from datetime import datetime, date, timedelta, time
from typing import List, Optional, Tuple
from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    ShiftSwapListing, ShiftSwapListingType, ShiftSwapListingStatus,
    ShiftSwapClaim, ShiftSwapClaimStatus,
    StaffPreferenceProfile,
    SwapperReliabilityScore,
    ShiftSwapMatch, SwapMatchStatus,
    ShiftSwapNotification, NotificationType,
    ShiftSwapAudit,
    User
)


class ShiftSwapService:

    def __init__(self, session: AsyncSession):
        self.session = session

    # ========================================================================
    # Listing Management
    # ========================================================================

    async def create_listing(
        self,
        user_id: int,
        branch_id: int,
        listing_type: ShiftSwapListingType,
        shift_date: date,
        shift_start_time: str,
        shift_end_time: str,
        shift_type: str,
        is_partial: bool = False,
        partial_description: Optional[str] = None,
        description: Optional[str] = None,
        expires_at: datetime = None,
    ) -> ShiftSwapListing:

        # Default expiration: 30 days from now, or if shift is sooner, 2 days before shift
        if expires_at is None:
            shift_datetime = datetime.combine(shift_date, datetime.min.time())
            expires_at = min(
                datetime.now() + timedelta(days=30),
                shift_datetime - timedelta(days=2)
            )

        listing = ShiftSwapListing(
            user_id=user_id,
            branch_id=branch_id,
            listing_type=listing_type,
            shift_date=shift_date,
            shift_start_time=shift_start_time,
            shift_end_time=shift_end_time,
            shift_type=shift_type,
            is_partial=is_partial,
            partial_description=partial_description,
            description=description,
            expires_at=expires_at,
            status=ShiftSwapListingStatus.open,
        )

        self.session.add(listing)
        await self.session.flush()

        # Log audit
        await self._audit_action(
            user_id,
            "created_listing",
            shift_date,
            f"Created {listing_type.value} listing for {shift_date} {shift_start_time}-{shift_end_time}"
        )

        return listing

    async def get_listing(self, listing_id: int) -> Optional[ShiftSwapListing]:
        query = select(ShiftSwapListing).where(
            ShiftSwapListing.id == listing_id
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_listings(
        self,
        branch_id: Optional[int] = None,
        listing_type: Optional[ShiftSwapListingType] = None,
        shift_type: Optional[str] = None,
        status: Optional[ShiftSwapListingStatus] = None,
        shift_date_from: Optional[date] = None,
        shift_date_to: Optional[date] = None,
        user_id: Optional[int] = None,
        limit: int = 50,
        offset: int = 0,
        eager_load_relations: bool = False,
    ) -> Tuple[List[ShiftSwapListing], int]:

        query = select(ShiftSwapListing)
        if eager_load_relations:
            query = query.options(
                selectinload(ShiftSwapListing.user),
            )

        # Build filters
        filters = []
        if branch_id is not None:
            filters.append(ShiftSwapListing.branch_id == branch_id)
        if listing_type is not None:
            filters.append(ShiftSwapListing.listing_type == listing_type)
        if shift_type is not None:
            filters.append(ShiftSwapListing.shift_type == shift_type)
        if status is not None:
            filters.append(ShiftSwapListing.status == status)
        if shift_date_from is not None:
            filters.append(ShiftSwapListing.shift_date >= shift_date_from)
        if shift_date_to is not None:
            filters.append(ShiftSwapListing.shift_date <= shift_date_to)
        if user_id is not None:
            filters.append(ShiftSwapListing.user_id == user_id)

        if filters:
            query = query.where(and_(*filters))

        # Get total count
        count_query = select(func.count()).select_from(ShiftSwapListing)
        if filters:
            count_query = count_query.where(and_(*filters))
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # Apply sorting and pagination
        query = query.order_by(ShiftSwapListing.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        listings = result.scalars().all()

        return listings, total

    async def get_claim_counts(self, listing_ids: List[int]) -> dict:
        if not listing_ids:
            return {}
        result = await self.session.execute(
            select(ShiftSwapClaim.listing_id, func.count(ShiftSwapClaim.id))
            .where(ShiftSwapClaim.listing_id.in_(listing_ids))
            .group_by(ShiftSwapClaim.listing_id)
        )
        return {lid: count for lid, count in result.all()}

    async def get_listings_claimed_by(self, claimer_id: int, listing_ids: List[int]) -> set:
        if not listing_ids:
            return set()
        result = await self.session.execute(
            select(ShiftSwapClaim.listing_id).where(
                and_(
                    ShiftSwapClaim.claimer_id == claimer_id,
                    ShiftSwapClaim.listing_id.in_(listing_ids),
                )
            )
        )
        return {lid for (lid,) in result.all()}

    async def withdraw_listing(self, listing_id: int, user_id: int) -> ShiftSwapListing:
        listing = await self.get_listing(listing_id)
        if not listing:
            raise ValueError("Listing not found")
        if listing.user_id != user_id:
            raise ValueError("Not authorized to withdraw this listing")
        if listing.status not in (ShiftSwapListingStatus.open, ShiftSwapListingStatus.claimed):
            raise ValueError(f"Listing is {listing.status.value}, cannot withdraw")

        now = datetime.now()
        listing.status = ShiftSwapListingStatus.withdrawn
        listing.withdrawn_at = now
        listing.withdrawn_by_id = user_id

        # Cancel any pending or approved claims and notify claimers so they aren't
        # left with stale records pointing at a withdrawn listing.
        claims = await self.get_claims_for_listing(listing_id)
        for claim in claims:
            if claim.status in (ShiftSwapClaimStatus.pending, ShiftSwapClaimStatus.approved):
                # ShiftSwapClaim uses rejected_at/rejected_reason for both rejections
                # and withdrawal-driven cancellations (no separate cancelled_at column).
                claim.status = ShiftSwapClaimStatus.cancelled
                claim.rejected_at = now
                claim.rejected_reason = "Listing withdrawn by owner"
                # Using claim_rejected type for withdrawal-driven cancellations.
                # A dedicated listing_withdrawn type would be more precise.
                await self._create_notification(
                    claim.claimer_id,
                    NotificationType.CLAIM_REJECTED,
                    title="Shift swap listing withdrawn",
                    message=f"The listing for {listing.shift_date} you claimed was withdrawn by the poster.",
                    listing_id=listing_id,
                    claim_id=claim.id,
                )

        await self._audit_action(
            user_id,
            "withdrawn_listing",
            listing.shift_date,
            f"Withdrew listing {listing_id}"
        )

        return listing

    # ========================================================================
    # Claim Management
    # ========================================================================

    async def claim_listing(
        self,
        listing_id: int,
        claimer_id: int,
        swap_shift_date: Optional[date] = None,
        swap_shift_start_time: Optional[str] = None,
        swap_shift_end_time: Optional[str] = None,
        message: Optional[str] = None,
    ) -> ShiftSwapClaim:

        # Check listing exists and is still available
        listing = await self.get_listing(listing_id)
        if not listing:
            raise ValueError("Listing not found")
        if listing.status != ShiftSwapListingStatus.open:
            raise ValueError(f"Listing is {listing.status}, cannot claim")
        if listing.user_id == claimer_id:
            raise ValueError("Cannot claim your own listing")

        # Check for duplicate claim
        existing_claim = await self.session.execute(
            select(ShiftSwapClaim).where(
                and_(
                    ShiftSwapClaim.listing_id == listing_id,
                    ShiftSwapClaim.claimer_id == claimer_id,
                )
            )
        )
        if existing_claim.scalar_one_or_none():
            raise ValueError("You have already claimed this listing")

        # Create claim
        claim = ShiftSwapClaim(
            listing_id=listing_id,
            claimer_id=claimer_id,
            swap_shift_date=swap_shift_date,
            swap_shift_start_time=swap_shift_start_time,
            swap_shift_end_time=swap_shift_end_time,
            message=message,
            status=ShiftSwapClaimStatus.pending,
        )

        self.session.add(claim)
        await self.session.flush()

        # Track total claims for the claimer's reliability denominator.
        claimer_score = await self.get_or_create_reliability_score(claimer_id)
        claimer_score.total_swap_claims += 1

        # Log audit
        await self._audit_action(
            claimer_id,
            "claimed_shift",
            listing.shift_date,
            f"Claimed listing {listing_id}"
        )

        # Send notification to listing owner
        await self._create_notification(
            listing.user_id,
            NotificationType.SWAP_CLAIMED,
            title="Your shift swap was claimed",
            message=f"Someone has claimed your {listing.shift_date} shift",
            listing_id=listing_id,
            claim_id=claim.id,
        )

        return claim

    async def get_claim(self, claim_id: int) -> Optional[ShiftSwapClaim]:
        query = select(ShiftSwapClaim).where(ShiftSwapClaim.id == claim_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_claims_for_listing(self, listing_id: int) -> List[ShiftSwapClaim]:
        query = select(ShiftSwapClaim).where(
            ShiftSwapClaim.listing_id == listing_id
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def approve_claim(
        self,
        claim_id: int,
        approver_id: int,
        approval_notes: Optional[str] = None,
    ) -> ShiftSwapClaim:

        claim = await self.get_claim(claim_id)
        if not claim:
            raise ValueError("Claim not found")

        listing = await self.get_listing(claim.listing_id)
        if not listing:
            raise ValueError("Listing not found")

        if listing.user_id != approver_id:
            raise ValueError("Not authorized to approve this claim")

        if claim.status != ShiftSwapClaimStatus.pending:
            raise ValueError(f"Claim is already {claim.status}")

        # Mark claim as approved
        claim.status = ShiftSwapClaimStatus.approved
        claim.approved_at = datetime.now()
        claim.approved_by_id = approver_id
        claim.approval_notes = approval_notes

        # Mark listing as claimed (no more claims allowed)
        listing.status = ShiftSwapListingStatus.claimed

        await self._audit_action(
            approver_id,
            "approved_claim",
            listing.shift_date,
            f"Approved claim {claim_id}"
        )

        # Notify claimer
        await self._create_notification(
            claim.claimer_id,
            NotificationType.CLAIM_APPROVED,
            title="Your shift swap claim was approved",
            message=f"Your claim for {listing.shift_date} was approved",
            claim_id=claim_id,
        )

        # Reject other pending claims for this listing
        other_claims = await self.get_claims_for_listing(listing.id)
        for other_claim in other_claims:
            if other_claim.id != claim_id and other_claim.status == ShiftSwapClaimStatus.pending:
                other_claim.status = ShiftSwapClaimStatus.rejected
                other_claim.rejected_at = datetime.now()
                other_claim.rejected_reason = "Another claim was approved"

                # Notify rejected claimers
                await self._create_notification(
                    other_claim.claimer_id,
                    NotificationType.CLAIM_REJECTED,
                    title="Your shift swap claim was rejected",
                    message=f"Another claim for {listing.shift_date} was approved",
                    claim_id=other_claim.id,
                )

        return claim

    async def reject_claim(
        self,
        claim_id: int,
        rejector_id: int,
        rejection_reason: str,
    ) -> ShiftSwapClaim:

        claim = await self.get_claim(claim_id)
        if not claim:
            raise ValueError("Claim not found")

        listing = await self.get_listing(claim.listing_id)
        if listing.user_id != rejector_id:
            raise ValueError("Not authorized to reject this claim")

        if claim.status != ShiftSwapClaimStatus.pending:
            raise ValueError(f"Claim is already {claim.status}")

        claim.status = ShiftSwapClaimStatus.rejected
        claim.rejected_at = datetime.now()
        claim.rejected_reason = rejection_reason

        await self._audit_action(
            rejector_id,
            "rejected_claim",
            listing.shift_date,
            f"Rejected claim {claim_id}: {rejection_reason}"
        )

        # Notify claimer
        await self._create_notification(
            claim.claimer_id,
            NotificationType.CLAIM_REJECTED,
            title="Your shift swap claim was rejected",
            message=rejection_reason,
            claim_id=claim_id,
        )

        return claim

    # ========================================================================
    # Shift Matching & Automation
    # ========================================================================

    async def find_matches(self) -> List[ShiftSwapMatch]:

        # Get all open listings
        result = await self.session.execute(
            select(ShiftSwapListing).where(
                ShiftSwapListing.status == ShiftSwapListingStatus.open
            )
        )
        listings = result.scalars().all()

        matches = []

        # For each "giving away", find compatible "looking for"
        for giver_listing in listings:
            if giver_listing.listing_type != ShiftSwapListingType.giving_away:
                continue

            for taker_listing in listings:
                if taker_listing.listing_type != ShiftSwapListingType.looking_for:
                    continue

                if giver_listing.id == taker_listing.id:
                    continue

                # Check if match already exists
                existing_match = await self.session.execute(
                    select(ShiftSwapMatch).where(
                        and_(
                            ShiftSwapMatch.giver_listing_id == giver_listing.id,
                            ShiftSwapMatch.taker_listing_id == taker_listing.id,
                        )
                    )
                )
                if existing_match.scalar_one_or_none():
                    continue

                # Calculate compatibility score
                score = await self._calculate_compatibility_score(giver_listing, taker_listing)

                # Only create match if score is above threshold (60%)
                if score >= 60.0:
                    match = ShiftSwapMatch(
                        giver_listing_id=giver_listing.id,
                        taker_listing_id=taker_listing.id,
                        compatibility_score=score,
                        status=SwapMatchStatus.pending_notification,
                    )
                    self.session.add(match)
                    matches.append(match)

        await self.session.flush()
        return matches

    async def notify_matches(self, matches: List[ShiftSwapMatch] = None) -> List[ShiftSwapMatch]:

        if matches is None:
            # Get all pending notifications with eager-loaded listings
            # to avoid N+1 queries (previously 1 + 2N queries, now 1 query)
            result = await self.session.execute(
                select(ShiftSwapMatch)
                .where(
                    ShiftSwapMatch.status == SwapMatchStatus.pending_notification
                )
                .options(
                    selectinload(ShiftSwapMatch.giver_listing),
                    selectinload(ShiftSwapMatch.taker_listing),
                )
            )
            matches = result.scalars().all()

        # Batch-load listings for any matches that don't have them loaded
        listing_ids = set()
        for match in matches:
            if not hasattr(match, '_sa_instance_state') or 'giver_listing' not in match.__dict__:
                listing_ids.add(match.giver_listing_id)
                listing_ids.add(match.taker_listing_id)

        listings_by_id = {}
        if listing_ids:
            result = await self.session.execute(
                select(ShiftSwapListing).where(
                    ShiftSwapListing.id.in_(listing_ids)
                )
            )
            listings_by_id = {l.id: l for l in result.scalars().all()}

        notified_matches = []

        for match in matches:
            giver_listing = getattr(match, 'giver_listing', None) or listings_by_id.get(match.giver_listing_id)
            taker_listing = getattr(match, 'taker_listing', None) or listings_by_id.get(match.taker_listing_id)

            if not giver_listing or not taker_listing:
                continue

            # Notify both parties
            await self._create_notification(
                giver_listing.user_id,
                NotificationType.NEW_MATCH,
                title="New shift swap match found",
                message=f"Someone is looking for a {taker_listing.shift_date} shift that you're offering",
                match_id=match.id,
            )

            await self._create_notification(
                taker_listing.user_id,
                NotificationType.NEW_MATCH,
                title="New shift swap match found",
                message=f"Someone is offering a {giver_listing.shift_date} shift that you're looking for",
                match_id=match.id,
            )

            match.status = SwapMatchStatus.notified
            match.notified_at = datetime.now()
            notified_matches.append(match)

        await self.session.flush()
        return notified_matches

    async def _calculate_compatibility_score(
        self,
        giver_listing: ShiftSwapListing,
        taker_listing: ShiftSwapListing,
    ) -> float:

        score = 0.0

        # Same branch (most important)
        if giver_listing.branch_id == taker_listing.branch_id:
            score += 40

        # Same shift type
        if giver_listing.shift_type == taker_listing.shift_type:
            score += 30
        # Partial shifts are compatible with anything
        elif giver_listing.shift_type == "partial" or taker_listing.shift_type == "partial":
            score += 15

        # Date proximity (shifts close to each other)
        date_diff = abs((giver_listing.shift_date - taker_listing.shift_date).days)
        if date_diff <= 7:
            score += 15
        elif date_diff <= 30:
            score += 8

        # Reliability (do users have good karma?)
        giver_reliability = await self._get_user_reliability_score(giver_listing.user_id)
        taker_reliability = await self._get_user_reliability_score(taker_listing.user_id)

        avg_reliability = (giver_reliability + taker_reliability) / 2
        if avg_reliability >= 80:
            score += 15
        elif avg_reliability >= 60:
            score += 8

        return min(score, 100.0)

    async def _get_user_reliability_score(self, user_id: int) -> float:
        result = await self.session.execute(
            select(SwapperReliabilityScore).where(
                SwapperReliabilityScore.user_id == user_id
            )
        )
        score_record = result.scalar_one_or_none()
        return score_record.reliability_score if score_record else 100.0

    # ========================================================================
    # Reliability Scoring (Karma System)
    # ========================================================================

    async def get_or_create_reliability_score(self, user_id: int) -> SwapperReliabilityScore:
        result = await self.session.execute(
            select(SwapperReliabilityScore).where(
                SwapperReliabilityScore.user_id == user_id
            )
        )
        score = result.scalar_one_or_none()

        if not score:
            score = SwapperReliabilityScore(user_id=user_id)
            self.session.add(score)
            await self.session.flush()

        return score

    async def mark_swap_completed(self, claim_id: int) -> SwapperReliabilityScore:

        claim = await self.get_claim(claim_id)
        if not claim:
            raise ValueError("Claim not found")

        if claim.status != ShiftSwapClaimStatus.approved:
            raise ValueError("Only approved claims can be marked as completed")

        claim.status = ShiftSwapClaimStatus.completed
        claim.completed_at = datetime.now()

        listing = await self.get_listing(claim.listing_id)
        listing.status = ShiftSwapListingStatus.completed

        # Update reliability scores for both users
        giver_score = await self.get_or_create_reliability_score(listing.user_id)
        taker_score = await self.get_or_create_reliability_score(claim.claimer_id)

        giver_score.total_completed_swaps += 1
        giver_score.last_swap_date = date.today()
        giver_score.times_stood_up += 1
        self._recalculate_reliability_score(giver_score)

        taker_score.total_completed_swaps += 1
        taker_score.last_swap_date = date.today()
        taker_score.times_stood_up += 1
        self._recalculate_reliability_score(taker_score)

        await self.session.flush()
        return giver_score

    async def mark_swap_cancelled(self, claim_id: int) -> SwapperReliabilityScore:

        claim = await self.get_claim(claim_id)
        if not claim:
            raise ValueError("Claim not found")

        if claim.status not in [ShiftSwapClaimStatus.pending, ShiftSwapClaimStatus.approved]:
            raise ValueError("Can only cancel pending or approved claims")

        claim.status = ShiftSwapClaimStatus.cancelled

        # Penalize the claimer for cancelling after claiming
        claimer_score = await self.get_or_create_reliability_score(claim.claimer_id)
        claimer_score.cancelled_after_claiming_count += 1
        claimer_score.times_let_down += 1

        # Reduce score
        claimer_score.reliability_score = max(0, claimer_score.reliability_score - 10)
        self._recalculate_reliability_score(claimer_score)

        await self._audit_action(
            claim.claimer_id,
            "cancelled_claim",
            None,
            f"Cancelled claim {claim_id} - reliability penalized"
        )

        await self.session.flush()
        return claimer_score

    async def detect_gaming_and_penalize(
        self,
        user_id: int,
        check_out_shift_date: date,
    ) -> Optional[str]:

        # Check if user completed a swap for this date in the past 7 days
        cutoff_date = check_out_shift_date - timedelta(days=7)

        # Find swaps this user was involved in for dates near the call-out
        # Eager-load listings to avoid N+1 (previously 1 + N queries, now 1 query)
        result = await self.session.execute(
            select(ShiftSwapClaim)
            .where(
                and_(
                    ShiftSwapClaim.claimer_id == user_id,
                    ShiftSwapClaim.status == ShiftSwapClaimStatus.completed,
                )
            )
            .options(selectinload(ShiftSwapClaim.listing))
        )
        claims = result.scalars().all()

        for claim in claims:
            listing = claim.listing
            if listing and cutoff_date <= listing.shift_date <= check_out_shift_date:
                # Gaming detected!
                score = await self.get_or_create_reliability_score(user_id)
                score.called_out_after_swap_count += 1
                score.times_let_down += 1
                score.reliability_score = max(0, score.reliability_score - 25)
                self._recalculate_reliability_score(score)

                await self._audit_action(
                    user_id,
                    "gaming_detected",
                    check_out_shift_date,
                    "Called out after swapping shift - major reliability penalty"
                )

                await self.session.flush()

                return (
                    f"WARNING: You called out on {check_out_shift_date}, "
                    f"which was a swapped shift. Your reliability score has been "
                    f"reduced significantly. Repeated behavior may result in "
                    f"restrictions on shift swapping."
                )

        return None

    def _recalculate_reliability_score(self, score: SwapperReliabilityScore) -> None:

        if score.total_swap_claims == 0:
            score.completion_rate = 100.0
            score.reliability_score = 100.0
            return

        # Completion rate
        completion_rate = (score.total_completed_swaps / score.total_swap_claims) * 100
        score.completion_rate = completion_rate

        # Base score (100)
        base_score = 100.0

        # Penalties
        penalties = 0.0

        # Cancellations after claiming
        penalties += score.cancelled_after_claiming_count * 5

        # Called out after swap (major penalty)
        penalties += score.called_out_after_swap_count * 25

        # No-shows
        penalties += score.no_show_count * 15

        # Apply penalties
        score.reliability_score = max(0, base_score - penalties)

        score.score_updated_at = datetime.now()

    # ========================================================================
    # Staff Preferences
    # ========================================================================

    async def get_or_create_preference_profile(self, user_id: int) -> StaffPreferenceProfile:
        result = await self.session.execute(
            select(StaffPreferenceProfile).where(
                StaffPreferenceProfile.user_id == user_id
            )
        )
        profile = result.scalar_one_or_none()

        if not profile:
            profile = StaffPreferenceProfile(user_id=user_id)
            self.session.add(profile)
            await self.session.flush()

        return profile

    async def update_preference_profile(
        self,
        user_id: int,
        **kwargs
    ) -> StaffPreferenceProfile:
        profile = await self.get_or_create_preference_profile(user_id)

        for key, value in kwargs.items():
            if hasattr(profile, key) and value is not None:
                setattr(profile, key, value)

        profile.updated_at = datetime.now()
        await self.session.flush()

        return profile

    # ========================================================================
    # Match Management
    # ========================================================================

    async def get_user_matches(self, user_id: int) -> List[ShiftSwapMatch]:
        # Get user's listing IDs
        listing_result = await self.session.execute(
            select(ShiftSwapListing.id).where(
                ShiftSwapListing.user_id == user_id
            )
        )
        user_listing_ids = [lid for lid in listing_result.scalars().all()]

        if not user_listing_ids:
            return []

        # Get matches where user is either giver or taker
        result = await self.session.execute(
            select(ShiftSwapMatch)
            .where(
                or_(
                    ShiftSwapMatch.giver_listing_id.in_(user_listing_ids),
                    ShiftSwapMatch.taker_listing_id.in_(user_listing_ids),
                )
            )
            .options(
                selectinload(ShiftSwapMatch.giver_listing),
                selectinload(ShiftSwapMatch.taker_listing),
            )
            .order_by(ShiftSwapMatch.compatibility_score.desc())
        )
        return list(result.scalars().all())

    async def accept_match(self, match_id: int, user_id: int) -> ShiftSwapMatch:
        result = await self.session.execute(
            select(ShiftSwapMatch)
            .where(ShiftSwapMatch.id == match_id)
            .options(
                selectinload(ShiftSwapMatch.giver_listing),
                selectinload(ShiftSwapMatch.taker_listing),
            )
        )
        match = result.scalar_one_or_none()
        if not match:
            raise ValueError("Match not found")

        # Verify user owns one of the listings
        giver = match.giver_listing
        taker = match.taker_listing
        if not giver or not taker:
            raise ValueError("Match listings not found")
        if giver.user_id != user_id and taker.user_id != user_id:
            raise ValueError("Not authorized to accept this match")

        if match.status not in (SwapMatchStatus.notified, SwapMatchStatus.pending_notification):
            raise ValueError(f"Match cannot be accepted in {match.status} state")

        match.status = SwapMatchStatus.accepted
        match.accepted_at = datetime.now()

        # Notify the other party
        other_user_id = taker.user_id if giver.user_id == user_id else giver.user_id
        await self._create_notification(
            other_user_id,
            NotificationType.MATCH_ACCEPTED,
            title="Match accepted!",
            message="The other party accepted a shift swap match with you",
            match_id=match_id,
        )

        await self._audit_action(
            user_id, "accepted_match", None, f"Accepted match {match_id}"
        )

        await self.session.flush()
        return match

    async def reject_match(self, match_id: int, user_id: int) -> ShiftSwapMatch:
        result = await self.session.execute(
            select(ShiftSwapMatch)
            .where(ShiftSwapMatch.id == match_id)
            .options(
                selectinload(ShiftSwapMatch.giver_listing),
                selectinload(ShiftSwapMatch.taker_listing),
            )
        )
        match = result.scalar_one_or_none()
        if not match:
            raise ValueError("Match not found")

        giver = match.giver_listing
        taker = match.taker_listing
        if not giver or not taker:
            raise ValueError("Match listings not found")
        if giver.user_id != user_id and taker.user_id != user_id:
            raise ValueError("Not authorized to reject this match")

        if match.status not in (SwapMatchStatus.notified, SwapMatchStatus.pending_notification):
            raise ValueError(f"Match cannot be rejected in {match.status} state")

        match.status = SwapMatchStatus.rejected
        match.rejected_at = datetime.now()

        # Notify the other party
        other_user_id = taker.user_id if giver.user_id == user_id else giver.user_id
        await self._create_notification(
            other_user_id,
            NotificationType.MATCH_REJECTED,
            title="Match declined",
            message="The other party declined a shift swap match",
            match_id=match_id,
        )

        await self._audit_action(
            user_id, "rejected_match", None, f"Rejected match {match_id}"
        )

        await self.session.flush()
        return match

    async def mark_notification_read(
        self, notification_id: int, user_id: int
    ) -> ShiftSwapNotification:
        result = await self.session.execute(
            select(ShiftSwapNotification).where(
                and_(
                    ShiftSwapNotification.id == notification_id,
                    ShiftSwapNotification.user_id == user_id,
                )
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            raise ValueError("Notification not found")

        notification.is_read = True
        notification.read_at = datetime.now()
        await self.session.flush()
        return notification

    # ========================================================================
    # Notifications & Audit
    # ========================================================================

    async def _create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        match_id: Optional[int] = None,
        listing_id: Optional[int] = None,
        claim_id: Optional[int] = None,
    ) -> ShiftSwapNotification:

        notification = ShiftSwapNotification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            match_id=match_id,
            listing_id=listing_id,
            claim_id=claim_id,
        )

        self.session.add(notification)
        await self.session.flush()

        return notification

    async def _audit_action(
        self,
        user_id: int,
        action: str,
        shift_date: Optional[date],
        description: str,
    ) -> ShiftSwapAudit:

        audit = ShiftSwapAudit(
            user_id=user_id,
            action=action,
            shift_date=shift_date,
            description=description,
        )

        self.session.add(audit)
        await self.session.flush()

        return audit

    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[ShiftSwapNotification], int]:

        # Count total
        count_query = select(func.count()).select_from(ShiftSwapNotification)
        count_query = count_query.where(ShiftSwapNotification.user_id == user_id)
        count_result = await self.session.execute(count_query)
        total = count_result.scalar()

        # Get notifications
        query = select(ShiftSwapNotification).where(
            ShiftSwapNotification.user_id == user_id
        )
        query = query.order_by(ShiftSwapNotification.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.session.execute(query)
        notifications = result.scalars().all()

        return notifications, total
