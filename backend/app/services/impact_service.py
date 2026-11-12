# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from datetime import date, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import utc_now

from ..models.audit_log import AuditAction, AuditLog
from ..models.impact import OutcomeIndicator, TheoryOfChangeClaim
from ..models.user import User
from ..schemas.impact import (
    ClaimCreate,
    ClaimPromote,
    ClaimReview,
    EvidenceStrength,
    OutcomeIndicatorApprove,
    OutcomeIndicatorCreate,
)

logger = get_logger(__name__)


# Promotion above this rung records a board attestation. Below it,
# director-level promotion is enough.
_BOARD_ATTESTED_LEVELS = {
    EvidenceStrength.quasi_experimental.value,
    EvidenceStrength.experimental.value,
}

_REVIEW_INTERVAL_DAYS = 365


# ---------------------------------------------------------------------
# Audit helpers
# ---------------------------------------------------------------------


def _audit(
    db: AsyncSession,
    actor: User,
    action: AuditAction,
    resource_type: str,
    resource_id: int,
    extra: Optional[dict] = None,
) -> None:
    payload: dict = {"resource_type": resource_type, "resource_id": resource_id}
    if extra:
        payload.update(extra)
    db.add(
        AuditLog(
            admin_id=actor.id,
            target_user_id=None,
            action=action,
            details=payload,
        )
    )


# ---------------------------------------------------------------------
# OutcomeIndicator
# ---------------------------------------------------------------------


async def create_indicator(
    db: AsyncSession,
    actor: User,
    payload: OutcomeIndicatorCreate,
) -> OutcomeIndicator:
    indicator = OutcomeIndicator(
        slug=payload.slug,
        name=payload.name,
        description=payload.description,
        unit=payload.unit,
        direction_better=payload.direction_better.value,
        cadence=payload.cadence.value,
        geographic_scope_type=payload.geographic_scope_type.value,
        primary_source=payload.primary_source,
        source_url=payload.source_url,
        requires_board_approval=payload.requires_board_approval,
        created_by_user_id=actor.id,
    )
    db.add(indicator)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Outcome indicator slug '{payload.slug}' already exists.",
        ) from exc

    _audit(
        db,
        actor,
        AuditAction.OUTCOME_INDICATOR_CREATED,
        "outcome_indicator",
        indicator.id,
        {"slug": indicator.slug, "name": indicator.name},
    )
    await db.flush()
    return indicator


async def approve_indicator(
    db: AsyncSession,
    actor: User,
    indicator_id: int,
    payload: OutcomeIndicatorApprove,
) -> OutcomeIndicator:
    indicator = await _get_indicator_or_404(db, indicator_id)

    if indicator.requires_board_approval and payload.board_decision_link_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                "This indicator requires board approval; "
                "board_decision_link_id is required."
            ),
        )

    indicator.approved_at = utc_now()
    indicator.approved_by_user_id = actor.id
    if payload.board_decision_link_id is not None:
        indicator.board_decision_link_id = payload.board_decision_link_id

    _audit(
        db,
        actor,
        AuditAction.OUTCOME_INDICATOR_APPROVED,
        "outcome_indicator",
        indicator.id,
        {
            "slug": indicator.slug,
            "board_decision_link_id": indicator.board_decision_link_id,
            "requires_board_approval": indicator.requires_board_approval,
        },
    )
    await db.flush()
    return indicator


async def list_indicators(
    db: AsyncSession,
    *,
    is_active: Optional[bool] = None,
    geographic_scope_type: Optional[str] = None,
    approved_only: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[OutcomeIndicator]:
    stmt = select(OutcomeIndicator)
    if is_active is not None:
        stmt = stmt.where(OutcomeIndicator.is_active == is_active)
    if geographic_scope_type is not None:
        stmt = stmt.where(
            OutcomeIndicator.geographic_scope_type == geographic_scope_type
        )
    if approved_only:
        stmt = stmt.where(OutcomeIndicator.approved_at.isnot(None))
    stmt = (
        stmt.order_by(OutcomeIndicator.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_indicator_or_404(
    db: AsyncSession, indicator_id: int
) -> OutcomeIndicator:
    result = await db.execute(
        select(OutcomeIndicator).where(OutcomeIndicator.id == indicator_id)
    )
    indicator = result.scalar_one_or_none()
    if indicator is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Outcome indicator {indicator_id} not found.",
        )
    return indicator


async def get_indicator(
    db: AsyncSession, indicator_id: int
) -> OutcomeIndicator:
    return await _get_indicator_or_404(db, indicator_id)


# ---------------------------------------------------------------------
# TheoryOfChangeClaim
# ---------------------------------------------------------------------


def _next_review_date() -> date:
    return (utc_now() + timedelta(days=_REVIEW_INTERVAL_DAYS)).date()


async def create_claim(
    db: AsyncSession,
    actor: User,
    payload: ClaimCreate,
) -> TheoryOfChangeClaim:
    # Verify the referenced indicator exists; surface a clean 422 rather
    # than relying on the FK error path.
    await _get_indicator_or_404(db, payload.outcome_indicator_id)

    claim = TheoryOfChangeClaim(
        outcome_indicator_id=payload.outcome_indicator_id,
        contributing_program_id=payload.contributing_program_id,
        contributing_initiative_id=payload.contributing_initiative_id,
        mechanism_short=payload.mechanism_short,
        mechanism_detail=payload.mechanism_detail,
        evidence_strength=payload.evidence_strength.value,
        evidence_citations=payload.evidence_citations,
        intended_dose=payload.intended_dose,
        expected_lag=payload.expected_lag,
        next_review_due=_next_review_date(),
        created_by_user_id=actor.id,
    )
    db.add(claim)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Claim integrity error: {exc.orig}",
        ) from exc

    _audit(
        db,
        actor,
        AuditAction.CLAIM_CREATED,
        "theory_of_change_claim",
        claim.id,
        {
            "outcome_indicator_id": claim.outcome_indicator_id,
            "evidence_strength": claim.evidence_strength,
            "program_id": claim.contributing_program_id,
            "initiative_id": claim.contributing_initiative_id,
        },
    )
    await db.flush()
    return claim


async def list_claims(
    db: AsyncSession,
    *,
    outcome_indicator_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[TheoryOfChangeClaim]:
    stmt = select(TheoryOfChangeClaim)
    if outcome_indicator_id is not None:
        stmt = stmt.where(
            TheoryOfChangeClaim.outcome_indicator_id == outcome_indicator_id
        )
    if is_active is not None:
        stmt = stmt.where(TheoryOfChangeClaim.is_active == is_active)
    stmt = (
        stmt.order_by(TheoryOfChangeClaim.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _get_claim_or_404(
    db: AsyncSession, claim_id: int
) -> TheoryOfChangeClaim:
    result = await db.execute(
        select(TheoryOfChangeClaim).where(TheoryOfChangeClaim.id == claim_id)
    )
    claim = result.scalar_one_or_none()
    if claim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Theory-of-change claim {claim_id} not found.",
        )
    return claim


async def get_claim(db: AsyncSession, claim_id: int) -> TheoryOfChangeClaim:
    return await _get_claim_or_404(db, claim_id)


async def review_claim(
    db: AsyncSession,
    actor: User,
    claim_id: int,
    payload: ClaimReview,
) -> TheoryOfChangeClaim:
    claim = await _get_claim_or_404(db, claim_id)
    claim.reviewed_at = utc_now()
    claim.reviewed_by_user_id = actor.id
    claim.next_review_due = _next_review_date()

    _audit(
        db,
        actor,
        AuditAction.CLAIM_REVIEWED,
        "theory_of_change_claim",
        claim.id,
        {
            "next_review_due": claim.next_review_due.isoformat(),
            "notes": payload.notes,
        },
    )
    await db.flush()
    return claim


async def promote_claim(
    db: AsyncSession,
    actor: User,
    claim_id: int,
    payload: ClaimPromote,
) -> TheoryOfChangeClaim:
    claim = await _get_claim_or_404(db, claim_id)
    new_level = payload.evidence_strength.value

    if (
        new_level in _BOARD_ATTESTED_LEVELS
        and payload.board_decision_link_id is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Promoting to '{new_level}' requires a "
                "board_decision_link_id."
            ),
        )

    old_level = claim.evidence_strength
    claim.evidence_strength = new_level
    if payload.evidence_citations is not None:
        claim.evidence_citations = payload.evidence_citations
    if payload.board_decision_link_id is not None:
        claim.board_decision_link_id = payload.board_decision_link_id

    _audit(
        db,
        actor,
        AuditAction.CLAIM_PROMOTED,
        "theory_of_change_claim",
        claim.id,
        {
            "old_evidence_strength": old_level,
            "new_evidence_strength": new_level,
            "board_decision_link_id": claim.board_decision_link_id,
        },
    )
    await db.flush()
    return claim


# Convenience: how many claims are reviewed-overdue. Not exposed on the
# router in Phase 1, but useful for ad-hoc checks and Phase 5 plumbing.
async def overdue_claim_count(
    db: AsyncSession, *, grace_days: int = 90
) -> int:
    cutoff = (utc_now().date()) - timedelta(days=grace_days)
    stmt = select(func.count(TheoryOfChangeClaim.id)).where(
        TheoryOfChangeClaim.is_active.is_(True),
        TheoryOfChangeClaim.next_review_due.isnot(None),
        TheoryOfChangeClaim.next_review_due < cutoff,
    )
    result = await db.execute(stmt)
    return int(result.scalar_one())
