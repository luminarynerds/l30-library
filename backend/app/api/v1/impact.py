# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Impact measurement layer — Phase 1 governance endpoints.

Mounted at ``/api/v1/impact``. All endpoints are staff-only.
Approval, review, and promotion endpoints require ``DIRECTOR`` (or
higher) per the spec.

Public dashboard endpoints (``/impact/public/*``) are deferred to
Phase 4. The router intentionally does not expose them in Phase 1.
"""
from __future__ import annotations

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.impact import (
    ClaimCreate,
    ClaimPromote,
    ClaimResponse,
    ClaimReview,
    OutcomeIndicatorApprove,
    OutcomeIndicatorCreate,
    OutcomeIndicatorResponse,
)
from ...services import impact_service
from .dependencies import require_director, require_staff

logger = get_logger(__name__)


router = APIRouter(prefix="/impact", tags=["impact"])


# ---------------------------------------------------------------------
# Outcome indicators
# ---------------------------------------------------------------------


@router.get("/indicators", response_model=list[OutcomeIndicatorResponse])
async def list_outcome_indicators(
    is_active: Optional[bool] = Query(default=None),
    geographic_scope_type: Optional[str] = Query(default=None),
    approved_only: bool = Query(default=False),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[OutcomeIndicatorResponse]:
    rows = await impact_service.list_indicators(
        db,
        is_active=is_active,
        geographic_scope_type=geographic_scope_type,
        approved_only=approved_only,
        limit=limit,
        offset=offset,
    )
    return [OutcomeIndicatorResponse.model_validate(r) for r in rows]


@router.post(
    "/indicators",
    response_model=OutcomeIndicatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_outcome_indicator(
    payload: OutcomeIndicatorCreate,
    actor: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> OutcomeIndicatorResponse:
    indicator = await impact_service.create_indicator(db, actor, payload)
    await db.commit()
    await db.refresh(indicator)
    return OutcomeIndicatorResponse.model_validate(indicator)


@router.get(
    "/indicators/{indicator_id}", response_model=OutcomeIndicatorResponse
)
async def get_outcome_indicator(
    indicator_id: int,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> OutcomeIndicatorResponse:
    indicator = await impact_service.get_indicator(db, indicator_id)
    return OutcomeIndicatorResponse.model_validate(indicator)


@router.post(
    "/indicators/{indicator_id}/approve",
    response_model=OutcomeIndicatorResponse,
)
async def approve_outcome_indicator(
    indicator_id: int,
    payload: OutcomeIndicatorApprove,
    actor: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> OutcomeIndicatorResponse:
    indicator = await impact_service.approve_indicator(
        db, actor, indicator_id, payload
    )
    await db.commit()
    await db.refresh(indicator)
    return OutcomeIndicatorResponse.model_validate(indicator)


# ---------------------------------------------------------------------
# Theory-of-change claims
# ---------------------------------------------------------------------


@router.get("/claims", response_model=list[ClaimResponse])
async def list_claims(
    outcome_indicator_id: Optional[int] = Query(default=None),
    is_active: Optional[bool] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> list[ClaimResponse]:
    rows = await impact_service.list_claims(
        db,
        outcome_indicator_id=outcome_indicator_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )
    return [ClaimResponse.model_validate(r) for r in rows]


@router.post(
    "/claims",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_claim(
    payload: ClaimCreate,
    actor: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ClaimResponse:
    claim = await impact_service.create_claim(db, actor, payload)
    await db.commit()
    await db.refresh(claim)
    return ClaimResponse.model_validate(claim)


@router.get("/claims/{claim_id}", response_model=ClaimResponse)
async def get_claim(
    claim_id: int,
    _: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> ClaimResponse:
    claim = await impact_service.get_claim(db, claim_id)
    return ClaimResponse.model_validate(claim)


@router.post("/claims/{claim_id}/review", response_model=ClaimResponse)
async def review_claim(
    claim_id: int,
    payload: ClaimReview,
    actor: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> ClaimResponse:
    claim = await impact_service.review_claim(db, actor, claim_id, payload)
    await db.commit()
    await db.refresh(claim)
    return ClaimResponse.model_validate(claim)


@router.patch("/claims/{claim_id}/evidence", response_model=ClaimResponse)
async def promote_claim(
    claim_id: int,
    payload: ClaimPromote,
    actor: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
) -> ClaimResponse:
    claim = await impact_service.promote_claim(db, actor, claim_id, payload)
    await db.commit()
    await db.refresh(claim)
    return ClaimResponse.model_validate(claim)
