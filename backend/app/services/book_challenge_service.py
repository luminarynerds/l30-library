# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import csv
import io
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import extract, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.book_challenge import (
    BookChallenge,
    BookChallengeNote,
    IntellectualFreedomResource,
    ChallengeStatus,
    ChallengeOutcome,
    ChallengeReason,
)
from ..models.user import User
from ..models.catalog import ItemStatus
from ..core.cache import get_cached, set_cached, invalidate_cache
from .state_transition_manager import StateTransitionManager

# Redis cache for the public stats card. Stats are library-scoped and public,
# so a single key is fine. TTL of 1 hour bounds staleness; mutating endpoints
# call _invalidate_stats_cache() to flush sooner.
_STATS_CACHE_KEY = "book_challenges:stats:v1"
_STATS_CACHE_TTL = 3600  # 1 hour


async def _invalidate_stats_cache() -> None:
    try:
        await invalidate_cache("book_challenges:stats*")
    except Exception as exc:  # noqa: BLE001
        logger.warning("book_challenges stats cache invalidation failed: %s", exc)


# Map challenge outcomes that change catalog item status
_OUTCOME_TO_STATUS = {
    ChallengeOutcome.RESTRICTED: ItemStatus.restricted,
    ChallengeOutcome.REMOVED: ItemStatus.withdrawn,
}

logger = get_logger(__name__)


class BookChallengeService:
    @staticmethod
    async def create_challenge(
        db: AsyncSession,
        challenge_data: dict[str, Any],
    ) -> BookChallenge:
        challenge = BookChallenge(**challenge_data)
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        logger.info("Created book challenge %s for '%s'", challenge.id, challenge.title)
        await _invalidate_stats_cache()
        return challenge

    @staticmethod
    async def create_from_public_request(
        db: AsyncSession,
        request_data: dict[str, Any],
    ) -> BookChallenge:
        request_data.pop("has_read_material", None)
        request_data.pop("turnstile_token", None)

        challenge = BookChallenge(
            title=request_data["title"],
            author=request_data.get("author"),
            isbn=request_data.get("isbn"),
            primary_reason=request_data["primary_reason"],
            challenger_complaint=request_data["challenger_complaint"],
            challenger_name=request_data["challenger_name"],
            challenger_contact=request_data.get("challenger_contact"),
            challenger_is_patron=True,
            status=ChallengeStatus.RECEIVED,
            outcome=ChallengeOutcome.PENDING,
        )
        db.add(challenge)
        try:
            await db.flush()
            intake_note = BookChallengeNote(
                challenge_id=challenge.id,
                note="Challenge submitted via online reconsideration form by patron.",
                is_internal=True,
                created_by_id=None,
            )
            db.add(intake_note)
            await db.flush()
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        await db.refresh(challenge)

        logger.info(
            "Created book challenge %s for '%s' from public reconsideration request",
            challenge.id,
            challenge.title,
        )
        await _invalidate_stats_cache()
        return challenge

    @staticmethod
    async def get_challenge(
        db: AsyncSession, challenge_id: int, include_notes: bool = False
    ) -> BookChallenge | None:
        query = select(BookChallenge).where(BookChallenge.id == challenge_id)
        if include_notes:
            query = query.options(selectinload(BookChallenge.notes))
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def list_challenges(
        db: AsyncSession,
        status: str | None = None,
        outcome: str | None = None,
        reason: str | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[BookChallenge], int]:
        query = select(BookChallenge)
        count_query = select(func.count(BookChallenge.id))

        if status:
            query = query.where(BookChallenge.status == status)
            count_query = count_query.where(BookChallenge.status == status)

        if outcome:
            query = query.where(BookChallenge.outcome == outcome)
            count_query = count_query.where(BookChallenge.outcome == outcome)

        if reason:
            query = query.where(BookChallenge.primary_reason == reason)
            count_query = count_query.where(BookChallenge.primary_reason == reason)

        if search:
            safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            # challenger_name is deliberately absent. It is encrypted at rest,
            # so an ilike runs against Fernet ciphertext and can never match:
            # the filter would look like a working name search while silently
            # returning nothing. Removed rather than left in place. A blind
            # index can restore the capability if staff ever ask for it.
            search_filter = or_(
                BookChallenge.title.ilike(f"%{safe_search}%"),
                BookChallenge.author.ilike(f"%{safe_search}%"),
                BookChallenge.isbn.ilike(f"%{safe_search}%"),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        # Get total count
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(BookChallenge.date_received.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)

        result = await db.execute(query)
        challenges = list(result.scalars().all())

        return challenges, total

    @staticmethod
    async def list_public_challenges(
        db: AsyncSession,
        limit: int = 50,
        year: int | None = None,
        outcome: str | None = None,
        reason: str | None = None,
        page: int | None = None,
        per_page: int | None = None,
    ) -> list[BookChallenge] | tuple[list[BookChallenge], int]:
        base = select(BookChallenge).where(
            BookChallenge.is_public == True  # noqa: E712
        )
        count_base = select(func.count(BookChallenge.id)).where(
            BookChallenge.is_public == True  # noqa: E712
        )

        if year is not None:
            base = base.where(extract("year", BookChallenge.date_received) == year)
            count_base = count_base.where(extract("year", BookChallenge.date_received) == year)
        if outcome:
            base = base.where(BookChallenge.outcome == outcome)
            count_base = count_base.where(BookChallenge.outcome == outcome)
        if reason:
            base = base.where(BookChallenge.primary_reason == reason)
            count_base = count_base.where(BookChallenge.primary_reason == reason)

        base = base.order_by(
            func.coalesce(BookChallenge.date_resolved, BookChallenge.date_received).desc()
        )

        paginated = page is not None or per_page is not None
        if not paginated:
            # Legacy callers (catalog hooks that read .catalog_item_id off
            # every row) -- preserve list return + ``limit``.
            query = base.limit(limit)
            result = await db.execute(query)
            return list(result.scalars().all())

        # Paginated path: compute total + page slice.
        page = max(1, page or 1)
        per_page = max(1, min(per_page or 20, 100))

        total_result = await db.execute(count_base)
        total = total_result.scalar() or 0

        query = base.offset((page - 1) * per_page).limit(per_page)
        result = await db.execute(query)
        items = list(result.scalars().all())
        return items, total

    @staticmethod
    async def update_challenge(
        db: AsyncSession,
        challenge_id: int,
        update_data: dict[str, Any],
        resolved_by: User | None = None,
    ) -> BookChallenge | None:
        challenge = await BookChallengeService.get_challenge(db, challenge_id)
        if not challenge:
            return None

        old_status = challenge.status
        old_outcome = challenge.outcome

        for key, value in update_data.items():
            if hasattr(challenge, key) and value is not None:
                setattr(challenge, key, value)

        # If resolving, set resolved_by and date
        if update_data.get("outcome") and update_data["outcome"] != ChallengeOutcome.PENDING.value:
            if resolved_by:
                challenge.resolved_by_id = resolved_by.id
            if not challenge.date_resolved:
                challenge.date_resolved = datetime.now(timezone.utc)

        # Trigger catalog item status change for actionable outcomes
        new_outcome = challenge.outcome
        if (
            old_outcome != new_outcome
            and challenge.catalog_item_id
            and new_outcome in _OUTCOME_TO_STATUS
        ):
            await StateTransitionManager.transition(
                db=db,
                catalog_item_id=challenge.catalog_item_id,
                new_status=_OUTCOME_TO_STATUS[new_outcome],
                reason=f"Challenge #{challenge.id} resolved: {new_outcome.value}",
                source_type="challenge_resolution",
                source_id=challenge.id,
                actor_id=resolved_by.id if resolved_by else None,
            )

        await db.commit()
        await db.refresh(challenge)

        # Auto-generate timeline notes for status/outcome changes
        timeline_parts = []
        new_status = challenge.status
        new_outcome = challenge.outcome

        if old_status != new_status:
            old_label = old_status.value if hasattr(old_status, "value") else str(old_status)
            new_label = new_status.value if hasattr(new_status, "value") else str(new_status)
            timeline_parts.append(f"Status changed from {old_label} to {new_label}")

        if old_outcome != new_outcome:
            old_label = old_outcome.value if hasattr(old_outcome, "value") else str(old_outcome)
            new_label = new_outcome.value if hasattr(new_outcome, "value") else str(new_outcome)
            timeline_parts.append(f"Outcome changed from {old_label} to {new_label}")

        if timeline_parts:
            staff_name = ""
            if resolved_by:
                staff_name = (
                    f" by {resolved_by.first_name} {resolved_by.last_name}"
                    if hasattr(resolved_by, "first_name")
                    else ""
                )
            timeline_note = BookChallengeNote(
                challenge_id=challenge_id,
                note=f"{'. '.join(timeline_parts)}{staff_name}.",
                is_internal=True,
                created_by_id=resolved_by.id if resolved_by else None,
            )
            db.add(timeline_note)
            await db.commit()

        logger.info("Updated book challenge %s", challenge_id)
        await _invalidate_stats_cache()
        return challenge

    @staticmethod
    async def delete_challenge(
        db: AsyncSession,
        challenge_id: int,
    ) -> bool:
        challenge = await BookChallengeService.get_challenge(db, challenge_id)
        if not challenge:
            return False

        await db.delete(challenge)
        await db.commit()
        logger.info("Deleted book challenge %s", challenge_id)
        await _invalidate_stats_cache()
        return True

    @staticmethod
    async def add_note(
        db: AsyncSession,
        challenge_id: int,
        note: str,
        is_internal: bool = True,
        created_by: User | None = None,
    ) -> BookChallengeNote:
        note_obj = BookChallengeNote(
            challenge_id=challenge_id,
            note=note,
            is_internal=is_internal,
            created_by_id=created_by.id if created_by else None,
        )
        db.add(note_obj)
        await db.commit()
        await db.refresh(note_obj)
        logger.info("Added note to challenge %s", challenge_id)
        return note_obj

    @staticmethod
    async def get_statistics(db: AsyncSession) -> dict[str, Any]:
        cached = await get_cached(_STATS_CACHE_KEY)
        if cached is not None:
            return cached

        stats = await BookChallengeService._compute_statistics(db)
        await set_cached(_STATS_CACHE_KEY, stats, ttl_seconds=_STATS_CACHE_TTL)
        return stats

    @staticmethod
    async def _compute_statistics(db: AsyncSession) -> dict[str, Any]:
        # Total challenges
        total_result = await db.execute(select(func.count(BookChallenge.id)))
        total = total_result.scalar() or 0

        # Pending challenges
        pending_result = await db.execute(
            select(func.count(BookChallenge.id)).where(
                BookChallenge.outcome == ChallengeOutcome.PENDING
            )
        )
        pending = pending_result.scalar() or 0

        # Resolved this year
        current_year = datetime.now(timezone.utc).year
        year_start = datetime(current_year, 1, 1, tzinfo=timezone.utc)
        resolved_result = await db.execute(
            select(func.count(BookChallenge.id)).where(BookChallenge.date_resolved >= year_start)
        )
        resolved_this_year = resolved_result.scalar() or 0

        # Outcomes breakdown
        outcomes_result = await db.execute(
            select(BookChallenge.outcome, func.count(BookChallenge.id)).group_by(
                BookChallenge.outcome
            )
        )
        outcomes = {
            str(row[0].value if row[0] else "UNKNOWN"): row[1] for row in outcomes_result.all()
        }

        # Reasons breakdown
        reasons_result = await db.execute(
            select(BookChallenge.primary_reason, func.count(BookChallenge.id)).group_by(
                BookChallenge.primary_reason
            )
        )
        reasons = {
            str(row[0].value if row[0] else "UNKNOWN"): row[1] for row in reasons_result.all()
        }

        # Years with at least one is_public challenge -- drives the
        # Transparency Log Year dropdown. Restricted to public rows so the
        # filter never offers a value that returns zero on /public.
        years_result = await db.execute(
            select(extract("year", BookChallenge.date_received))
            .where(BookChallenge.is_public == True)  # noqa: E712
            .distinct()
        )
        available_years = sorted(
            (int(row[0]) for row in years_result.all() if row[0] is not None),
            reverse=True,
        )

        return {
            "total_challenges": total,
            "pending_challenges": pending,
            "resolved_this_year": resolved_this_year,
            "outcomes": outcomes,
            "reasons": reasons,
            "available_years": available_years,
        }

    @staticmethod
    async def export_challenges_csv(
        db: AsyncSession,
        status: str | None = None,
        outcome: str | None = None,
    ) -> str:
        query = select(BookChallenge).order_by(BookChallenge.date_received.desc())

        if status:
            query = query.where(BookChallenge.status == status)
        if outcome:
            query = query.where(BookChallenge.outcome == outcome)

        result = await db.execute(query)
        challenges = list(result.scalars().all())

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Title",
                "Author",
                "ISBN",
                "Status",
                "Primary Reason",
                "Outcome",
                "Date Received",
                "Date Resolved",
                "Challenger Name",
                "Challenger Is Patron",
                "Resolution Summary",
                "Is Public",
            ]
        )

        for c in challenges:
            writer.writerow(
                [
                    c.id,
                    c.title,
                    c.author or "",
                    c.isbn or "",
                    c.status.value if hasattr(c.status, "value") else str(c.status),
                    c.primary_reason.value
                    if hasattr(c.primary_reason, "value")
                    else str(c.primary_reason),
                    c.outcome.value if hasattr(c.outcome, "value") else str(c.outcome),
                    c.date_received.isoformat() if c.date_received else "",
                    c.date_resolved.isoformat() if c.date_resolved else "",
                    c.challenger_name or "",
                    "Yes" if c.challenger_is_patron else "No",
                    c.resolution_summary or "",
                    "Yes" if c.is_public else "No",
                ]
            )

        return output.getvalue()


class IntellectualFreedomService:
    @staticmethod
    async def create_resource(
        db: AsyncSession, resource_data: dict[str, Any]
    ) -> IntellectualFreedomResource:
        resource = IntellectualFreedomResource(**resource_data)
        db.add(resource)
        await db.commit()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def get_resource(
        db: AsyncSession, resource_id: int
    ) -> IntellectualFreedomResource | None:
        result = await db.execute(
            select(IntellectualFreedomResource).where(IntellectualFreedomResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_resources(
        db: AsyncSession, active_only: bool = True, resource_type: str | None = None
    ) -> list[IntellectualFreedomResource]:
        query = select(IntellectualFreedomResource)

        if active_only:
            query = query.where(IntellectualFreedomResource.is_active == True)  # noqa: E712

        if resource_type:
            query = query.where(IntellectualFreedomResource.resource_type == resource_type)

        query = query.order_by(IntellectualFreedomResource.display_order)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_resource(
        db: AsyncSession, resource_id: int, update_data: dict[str, Any]
    ) -> IntellectualFreedomResource | None:
        resource = await IntellectualFreedomService.get_resource(db, resource_id)
        if not resource:
            return None

        for key, value in update_data.items():
            if hasattr(resource, key) and value is not None:
                setattr(resource, key, value)

        await db.commit()
        await db.refresh(resource)
        return resource

    @staticmethod
    async def delete_resource(db: AsyncSession, resource_id: int) -> bool:
        resource = await IntellectualFreedomService.get_resource(db, resource_id)
        if not resource:
            return False

        await db.delete(resource)
        await db.commit()
        return True
