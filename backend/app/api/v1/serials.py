# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Serials management API endpoints."""

from app.core.logging import get_logger
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.serial import (
    SerialTitleCreate, SerialTitleUpdate, SerialTitleResponse, SerialTitleListResponse,
    PredictionPatternCreate, PredictionPatternResponse,
    SerialSubscriptionCreate, SerialSubscriptionUpdate,
    SerialSubscriptionResponse, SerialSubscriptionListResponse,
    SerialIssueCheckinRequest, SerialIssueResponse, SerialIssueListResponse,
    SerialClaimCreate, SerialClaimResponse, SerialClaimUpdateResponse,
    SerialsDashboardResponse,
)
from ...services.serial_service import SerialService
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/serials", tags=["serials"])


def _get_service(db: AsyncSession = Depends(get_db)) -> SerialService:
    return SerialService(db)


# -- Dashboard --------------------------------------------------------------

@router.get("/dashboard", response_model=SerialsDashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
):
    return await service.get_dashboard()


# -- Titles -----------------------------------------------------------------

@router.get("/titles", response_model=SerialTitleListResponse)
async def list_titles(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    frequency: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
):
    items, total = await service.list_titles(
        page=page, per_page=per_page, search=search,
        is_active=is_active, frequency=frequency,
    )
    return SerialTitleListResponse(
        items=[SerialTitleResponse.model_validate(t) for t in items],
        total=total, page=page, per_page=per_page,
    )


@router.post("/titles", response_model=SerialTitleResponse, status_code=status.HTTP_201_CREATED)
async def create_title(
    data: SerialTitleCreate,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    title = await service.create_title(
        **data.model_dump(exclude_unset=True),
        created_by_id=current_user.id,
    )
    await db.commit()
    return SerialTitleResponse.model_validate(title)


@router.get("/titles/{title_id}", response_model=SerialTitleResponse)
async def get_title(
    title_id: int,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
):
    title = await service.get_title(title_id)
    if not title:
        raise HTTPException(status_code=404, detail="Serial title not found")
    return SerialTitleResponse.model_validate(title)


@router.patch("/titles/{title_id}", response_model=SerialTitleResponse)
async def update_title(
    title_id: int,
    data: SerialTitleUpdate,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    title = await service.update_title(title_id, data.model_dump(exclude_unset=True))
    if not title:
        raise HTTPException(status_code=404, detail="Serial title not found")
    await db.commit()
    return SerialTitleResponse.model_validate(title)


# -- Prediction -------------------------------------------------------------

@router.post("/titles/{title_id}/predict", response_model=list[SerialIssueResponse])
async def predict_issues(
    title_id: int,
    subscription_id: int = Query(...),
    months_ahead: int = Query(12, ge=1, le=24),
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    issues = await service.predict_issues(title_id, subscription_id, months_ahead)
    await db.commit()
    return [SerialIssueResponse.model_validate(i) for i in issues]


@router.post("/titles/{title_id}/patterns", response_model=PredictionPatternResponse, status_code=201)
async def create_prediction_pattern(
    title_id: int,
    data: PredictionPatternCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    from app.models.serial import SerialPredictionPattern
    pattern = SerialPredictionPattern(
        serial_title_id=title_id,
        **data.model_dump(exclude_unset=True),
    )
    db.add(pattern)
    await db.commit()
    await db.refresh(pattern)
    return PredictionPatternResponse.model_validate(pattern)


# -- Subscriptions ----------------------------------------------------------

@router.get("/subscriptions", response_model=SerialSubscriptionListResponse)
async def list_subscriptions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    title_id: int | None = Query(None),
    renewal_status: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
):
    rows, total = await service.list_subscriptions(
        page=page, per_page=per_page,
        title_id=title_id, renewal_status=renewal_status,
    )
    items = []
    for row in rows:
        sub = row[0]
        resp = SerialSubscriptionResponse.model_validate(sub)
        resp.serial_title_name = row.serial_title_name
        resp.vendor_name = row.vendor_name
        resp.branch_name = row.branch_name
        items.append(resp)
    return SerialSubscriptionListResponse(
        items=items, total=total, page=page, per_page=per_page,
    )


@router.post("/subscriptions", response_model=SerialSubscriptionResponse, status_code=201)
async def create_subscription(
    data: SerialSubscriptionCreate,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    sub = await service.create_subscription(
        **data.model_dump(exclude_unset=True),
        created_by_id=current_user.id,
    )
    await db.commit()
    return SerialSubscriptionResponse.model_validate(sub)


@router.patch("/subscriptions/{sub_id}", response_model=SerialSubscriptionResponse)
async def update_subscription(
    sub_id: int,
    data: SerialSubscriptionUpdate,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    sub = await service.update_subscription(sub_id, data.model_dump(exclude_unset=True))
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription not found")
    await db.commit()
    return SerialSubscriptionResponse.model_validate(sub)


# -- Issues -----------------------------------------------------------------

@router.get("/issues", response_model=SerialIssueListResponse)
async def list_issues(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    title_id: int | None = Query(None),
    subscription_id: int | None = Query(None),
    issue_status: str | None = Query(None, alias="status"),
    expected_from: date | None = Query(None),
    expected_to: date | None = Query(None),
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
):
    rows, total = await service.list_issues(
        page=page, per_page=per_page, title_id=title_id,
        subscription_id=subscription_id, status=issue_status,
        expected_from=expected_from, expected_to=expected_to,
    )
    items = []
    for row in rows:
        issue = row[0]
        resp = SerialIssueResponse.model_validate(issue)
        resp.serial_title_name = row.serial_title_name
        items.append(resp)
    return SerialIssueListResponse(
        items=items, total=total, page=page, per_page=per_page,
    )


@router.post("/issues/checkin")
async def checkin_issues(
    data: SerialIssueCheckinRequest,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    checked_in = await service.checkin_issues(
        data.issue_ids, current_user.id, data.received_date, data.notes,
    )
    await db.commit()
    return {"checked_in": len(checked_in), "issue_ids": [i.id for i in checked_in]}


# -- Claims -----------------------------------------------------------------

@router.post("/issues/{issue_id}/claim", response_model=SerialClaimResponse, status_code=201)
async def create_claim(
    issue_id: int,
    data: SerialClaimCreate,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    claim = await service.create_claim(
        issue_id, current_user.id,
        claim_type=data.claim_type, claim_number=data.claim_number, notes=data.notes,
    )
    await db.commit()
    return SerialClaimResponse.model_validate(claim)


@router.post("/subscriptions/{sub_id}/generate-renewal-po", status_code=201)
async def generate_renewal_po(
    sub_id: int,
    current_user: User = Depends(require_staff),
    service: SerialService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    """Generate a draft PO for subscription renewal."""
    try:
        po = await service.generate_renewal_po(sub_id, current_user.id)
        await db.commit()
        return {
            "id": po.id,
            "po_number": po.po_number,
            "total_amount": float(po.total_amount or 0),
            "message": f"Draft PO {po.po_number} created for renewal",
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
