# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Smart Weeding Recommendations API routes.

Provides CREW method-based weeding analysis, candidate management,
one-click withdraw workflow, and collection health analytics.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.catalog import CatalogItem, ItemStatus
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.inventory import ItemCondition, ItemCopy
from ...models.lifecycle import ItemLifecycleEvent, LifecycleEventType
from ...models.user import User
from ...models.weeding import (
    CREWCategory,
    DisposalMethod,
    WeedingCandidate,
    WeedingReason,
    WeedingRule,
    WeedingStatus,
)
from ...schemas.weeding import (
    DuplicateDetectionResponse,
    OutdatedContentListResponse,
    SectionPressureListResponse,
    SupersededEditionListResponse,
    WeedingAnalysisRequest,
    WeedingCandidateCreate,
    WeedingCandidateListResponse,
    WeedingCandidateResponse,
    WeedingReviewRequest,
    WeedingRuleCreate,
    WeedingRuleListResponse,
    WeedingRuleResponse,
    WeedingSummaryResponse,
    WeedingWithdrawRequest,
)
from ...services.weeding_service import (
    detect_duplicates,
    detect_superseded_editions,
    get_section_pressure,
    get_weeding_summary,
    run_weeding_analysis,
)
from .auth import get_current_user
from .dependencies import require_staff, require_director
from .lifecycle import create_lifecycle_event

router = APIRouter(prefix="/weeding", tags=["weeding"])


def _candidate_to_response(candidate: WeedingCandidate) -> dict:
    item_copy = candidate.item_copy
    catalog_item = item_copy.catalog_item if item_copy else None

    return {
        "id": candidate.id,
        "item_copy_id": candidate.item_copy_id,
        "status": candidate.status,
        "reason": candidate.reason,
        "reason_notes": candidate.reason_notes,
        "item_title": catalog_item.title if catalog_item else None,
        "item_author": catalog_item.author if catalog_item else None,
        "item_barcode": item_copy.barcode if item_copy else None,
        "item_location": item_copy.location if item_copy else None,
        "item_type": str(catalog_item.item_type) if catalog_item and catalog_item.item_type else None,
        "item_condition": item_copy.condition.value if item_copy and hasattr(item_copy.condition, "value") else str(item_copy.condition) if item_copy else None,
        "publication_year": catalog_item.publication_year if catalog_item else None,
        "isbn": catalog_item.isbn if catalog_item else None,
        "last_checkout_date": candidate.last_checkout_date,
        "total_checkouts": candidate.total_checkouts or 0,
        "years_since_acquisition": candidate.years_since_acquisition,
        "condition_score": float(candidate.condition_score) if candidate.condition_score else None,
        "days_since_last_circulation": candidate.days_since_last_circulation,
        "crew_category": candidate.crew_category,
        "crew_score": candidate.crew_score,
        "is_outdated_content": candidate.is_outdated_content or False,
        "outdated_flags": candidate.outdated_flags,
        "is_duplicate": candidate.is_duplicate or False,
        "duplicate_count": candidate.duplicate_count or 0,
        "is_superseded": candidate.is_superseded or False,
        "never_circulated": candidate.never_circulated or False,
        "section_fill_rate": candidate.section_fill_rate,
        "disposition_recommendation": candidate.disposition_recommendation,
        "disposition_rationale": candidate.disposition_rationale,
        "auto_generated": candidate.auto_generated or False,
        "created_at": candidate.created_at,
        "created_by_id": candidate.created_by_id,
        "reviewed_by_id": candidate.reviewed_by_id,
        "reviewed_at": candidate.reviewed_at,
        "approved_by_id": candidate.approved_by_id,
        "approved_at": candidate.approved_at,
    }


# ============ Dashboard & Summary ============


@router.get("/summary", response_model=WeedingSummaryResponse)
async def weeding_summary(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard summary of weeding recommendations and collection health."""
    return await get_weeding_summary(db)


# ============ Analysis Engine ============


@router.post("/analyze", response_model=WeedingCandidateListResponse)
async def run_analysis(
    request: WeedingAnalysisRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Run the smart weeding analysis engine.
    Scans the collection using CREW method criteria and generates weeding candidates.
    """
    candidates = await run_weeding_analysis(
        db=db,
        staff_user_id=current_user.id,
        location_filter=request.location_filter,
        crew_category_filter=request.crew_category,
        min_crew_score=request.min_crew_score,
        include_reasons=request.include_reasons,
        max_results=request.max_results,
    )

    # Reload with relationships
    items = []
    for c in candidates:
        await db.refresh(c, ["item_copy"])
        if c.item_copy:
            await db.refresh(c.item_copy, ["catalog_item"])
        items.append(_candidate_to_response(c))

    return {
        "items": items,
        "total": len(items),
        "page": 1,
        "per_page": request.max_results,
    }


# ============ Candidate CRUD ============


@router.get("/candidates", response_model=WeedingCandidateListResponse)
async def list_candidates(
    status_filter: WeedingStatus | None = Query(None, alias="status"),
    reason_filter: WeedingReason | None = Query(None, alias="reason"),
    location: str | None = None,
    min_score: float | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List weeding candidates with filters."""
    query = (
        select(WeedingCandidate)
        .options(
            selectinload(WeedingCandidate.item_copy).selectinload(ItemCopy.catalog_item)
        )
        .order_by(WeedingCandidate.crew_score.desc().nullslast(), WeedingCandidate.created_at.desc())
    )

    count_query = select(func.count(WeedingCandidate.id))

    if status_filter:
        query = query.where(WeedingCandidate.status == status_filter)
        count_query = count_query.where(WeedingCandidate.status == status_filter)
    if reason_filter:
        query = query.where(WeedingCandidate.reason == reason_filter)
        count_query = count_query.where(WeedingCandidate.reason == reason_filter)
    if location:
        safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.join(ItemCopy, WeedingCandidate.item_copy_id == ItemCopy.id).where(
            ItemCopy.location.ilike(f"%{safe_location}%")
        )
        count_query = count_query.join(ItemCopy, WeedingCandidate.item_copy_id == ItemCopy.id).where(
            ItemCopy.location.ilike(f"%{safe_location}%")
        )
    if min_score is not None:
        query = query.where(WeedingCandidate.crew_score >= min_score)
        count_query = count_query.where(WeedingCandidate.crew_score >= min_score)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    candidates = result.scalars().all()

    items = [_candidate_to_response(c) for c in candidates]

    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get("/candidates/{candidate_id}", response_model=WeedingCandidateResponse)
async def get_candidate(
    candidate_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a single weeding candidate with full details."""
    query = (
        select(WeedingCandidate)
        .options(
            selectinload(WeedingCandidate.item_copy).selectinload(ItemCopy.catalog_item)
        )
        .where(WeedingCandidate.id == candidate_id)
    )
    result = await db.execute(query)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Weeding candidate not found")

    return _candidate_to_response(candidate)


@router.post("/candidates", response_model=WeedingCandidateResponse, status_code=status.HTTP_201_CREATED)
async def create_candidate(
    request: WeedingCandidateCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Manually create a weeding candidate."""
    # Verify item copy exists
    copy_q = select(ItemCopy).where(ItemCopy.id == request.item_copy_id)
    copy_result = await db.execute(copy_q)
    item_copy = copy_result.scalar_one_or_none()
    if not item_copy:
        raise HTTPException(status_code=404, detail="Item copy not found")

    candidate = WeedingCandidate(
        item_copy_id=request.item_copy_id,
        status=WeedingStatus.CANDIDATE,
        reason=request.reason,
        reason_notes=request.reason_notes,
        auto_generated=False,
        created_by_id=current_user.id,
    )
    db.add(candidate)
    await db.commit()
    await db.refresh(candidate, ["item_copy"])
    if candidate.item_copy:
        await db.refresh(candidate.item_copy, ["catalog_item"])

    return _candidate_to_response(candidate)


# ============ Review & Approve Workflow ============


@router.post("/candidates/{candidate_id}/review", response_model=WeedingCandidateResponse)
async def review_candidate(
    candidate_id: int,
    request: WeedingReviewRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Review a weeding candidate - approve or reject."""
    query = (
        select(WeedingCandidate)
        .options(
            selectinload(WeedingCandidate.item_copy).selectinload(ItemCopy.catalog_item)
        )
        .where(WeedingCandidate.id == candidate_id)
    )
    result = await db.execute(query)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Weeding candidate not found")

    if candidate.status not in [WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot review candidate in '{candidate.status}' status",
        )

    now = datetime.now(timezone.utc)

    if request.action == "approve":
        candidate.status = WeedingStatus.APPROVED
        candidate.approved_by_id = current_user.id
        candidate.approved_at = now
        candidate.approval_notes = request.review_notes
        await create_lifecycle_event(
            db=db,
            item_copy_id=candidate.item_copy_id,
            event_type=LifecycleEventType.WEEDING_APPROVED,
            description="Weeding candidate approved",
            performed_by_id=current_user.id,
            related_weeding_id=candidate.id,
        )
    elif request.action == "reject":
        candidate.status = WeedingStatus.REJECTED
        candidate.rejected_by_id = current_user.id
        candidate.rejected_at = now
        candidate.rejection_reason = request.rejection_reason or request.review_notes
        await create_lifecycle_event(
            db=db,
            item_copy_id=candidate.item_copy_id,
            event_type=LifecycleEventType.WEEDING_REJECTED,
            description=request.rejection_reason or request.review_notes or "Weeding candidate rejected",
            performed_by_id=current_user.id,
            related_weeding_id=candidate.id,
        )

    candidate.reviewed_by_id = current_user.id
    candidate.reviewed_at = now
    candidate.review_notes = request.review_notes
    candidate.updated_at = now

    await db.commit()
    await db.refresh(candidate)

    return _candidate_to_response(candidate)


# ============ One-Click Withdraw Workflow ============


@router.post("/candidates/{candidate_id}/withdraw", response_model=WeedingCandidateResponse)
async def withdraw_candidate(
    candidate_id: int,
    request: WeedingWithdrawRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    One-click withdraw workflow: mark candidate as disposed and update item status.
    """
    query = (
        select(WeedingCandidate)
        .options(
            selectinload(WeedingCandidate.item_copy).selectinload(ItemCopy.catalog_item)
        )
        .where(WeedingCandidate.id == candidate_id)
    )
    result = await db.execute(query)
    candidate = result.scalar_one_or_none()

    if not candidate:
        raise HTTPException(status_code=404, detail="Weeding candidate not found")

    if candidate.status != WeedingStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Only approved candidates can be withdrawn. Please approve first.",
        )

    now = datetime.now(timezone.utc)

    # Check for active checkouts on this item copy
    active_checkout_q = select(func.count(Checkout.id)).where(
        Checkout.item_copy_id == candidate.item_copy_id,
        Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
    )
    active_co_result = await db.execute(active_checkout_q)
    if active_co_result.scalar():
        raise HTTPException(
            status_code=409,
            detail="Cannot withdraw - item is currently checked out",
        )

    # Check for pending holds if this is the last non-withdrawn copy
    if candidate.item_copy:
        remaining_q = select(func.count(ItemCopy.id)).where(
            ItemCopy.catalog_item_id == candidate.item_copy.catalog_item_id,
            ItemCopy.id != candidate.item_copy.id,
            ItemCopy.condition != ItemCondition.WITHDRAWN,
        )
        remaining_result = await db.execute(remaining_q)
        remaining_copies = remaining_result.scalar() or 0

        if remaining_copies == 0:
            pending_holds_q = select(func.count(Hold.id)).where(
                Hold.item_id == candidate.item_copy.catalog_item_id,
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
            )
            pending_result = await db.execute(pending_holds_q)
            pending_holds = pending_result.scalar() or 0
            if pending_holds:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot withdraw last copy - item has {pending_holds} pending holds",
                )

    # Update candidate
    candidate.status = WeedingStatus.DISPOSED
    candidate.disposal_method = request.disposal_method
    candidate.disposal_date = now.date()
    candidate.disposal_notes = request.disposal_notes
    candidate.disposal_recipient = request.disposal_recipient
    candidate.updated_at = now

    # Update item copy condition to WITHDRAWN
    if candidate.item_copy:
        candidate.item_copy.condition = ItemCondition.WITHDRAWN

        # If no remaining non-withdrawn copies, mark catalog item as withdrawn
        remaining_after_q = select(func.count(ItemCopy.id)).where(
            ItemCopy.catalog_item_id == candidate.item_copy.catalog_item_id,
            ItemCopy.id != candidate.item_copy.id,
            ItemCopy.condition != ItemCondition.WITHDRAWN,
        )
        remaining_after_result = await db.execute(remaining_after_q)
        if not (remaining_after_result.scalar() or 0):
            catalog_item = candidate.item_copy.catalog_item
            if catalog_item:
                catalog_item.status = ItemStatus.withdrawn

        # Create lifecycle event
        await create_lifecycle_event(
            db=db,
            item_copy_id=candidate.item_copy_id,
            event_type=LifecycleEventType.WEEDED,
            description=f"Item withdrawn via weeding workflow. Disposal: {request.disposal_method}",
            performed_by_id=current_user.id,
            related_weeding_id=candidate.id,
        )

    await db.commit()
    await db.refresh(candidate)

    return _candidate_to_response(candidate)


# ============ Batch Operations ============


@router.post("/candidates/batch-approve")
async def batch_approve(
    candidate_ids: list[int],
    current_user: User = Depends(require_director),
    db: AsyncSession = Depends(get_db),
):
    """Batch approve multiple weeding candidates."""
    now = datetime.now(timezone.utc)
    approved_count = 0

    for cid in candidate_ids:
        q = select(WeedingCandidate).where(WeedingCandidate.id == cid)
        result = await db.execute(q)
        candidate = result.scalar_one_or_none()
        if candidate and candidate.status in [WeedingStatus.CANDIDATE, WeedingStatus.UNDER_REVIEW]:
            candidate.status = WeedingStatus.APPROVED
            candidate.approved_by_id = current_user.id
            candidate.approved_at = now
            candidate.reviewed_by_id = current_user.id
            candidate.reviewed_at = now
            candidate.updated_at = now
            approved_count += 1

    await db.commit()
    return {"approved": approved_count, "total_requested": len(candidate_ids)}


@router.post("/candidates/batch-withdraw")
async def batch_withdraw(
    candidate_ids: list[int],
    disposal_method: DisposalMethod,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Batch withdraw multiple approved candidates."""
    now = datetime.now(timezone.utc)
    withdrawn_count = 0
    skipped = []
    # Track catalog_item_ids already withdrawn in this batch so the
    # last-copy guard accounts for other copies removed in the same request.
    batch_withdrawn_by_catalog: dict[int, int] = {}

    for cid in candidate_ids:
        q = (
            select(WeedingCandidate)
            .options(selectinload(WeedingCandidate.item_copy))
            .where(WeedingCandidate.id == cid)
        )
        result = await db.execute(q)
        candidate = result.scalar_one_or_none()
        if candidate and candidate.status == WeedingStatus.APPROVED:
            # Check for active checkouts
            active_co_q = select(func.count(Checkout.id)).where(
                Checkout.item_copy_id == candidate.item_copy_id,
                Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
            )
            active_co_result = await db.execute(active_co_q)
            if active_co_result.scalar():
                skipped.append({"id": cid, "reason": "Cannot withdraw - item is currently checked out"})
                continue

            if candidate.item_copy:
                cat_id = candidate.item_copy.catalog_item_id
                # Check for pending holds if last copy (accounting for
                # copies already withdrawn earlier in this same batch)
                remaining_q = select(func.count(ItemCopy.id)).where(
                    ItemCopy.catalog_item_id == cat_id,
                    ItemCopy.id != candidate.item_copy.id,
                    ItemCopy.condition != ItemCondition.WITHDRAWN,
                )
                remaining_result = await db.execute(remaining_q)
                remaining_copies = (remaining_result.scalar() or 0) - batch_withdrawn_by_catalog.get(cat_id, 0)

                if remaining_copies <= 0:
                    pending_holds_q = select(func.count(Hold.id)).where(
                        Hold.item_id == cat_id,
                        Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
                    )
                    pending_result = await db.execute(pending_holds_q)
                    pending_holds = pending_result.scalar() or 0
                    if pending_holds:
                        skipped.append({"id": cid, "reason": f"Cannot withdraw last copy - item has {pending_holds} pending holds"})
                        continue

            candidate.status = WeedingStatus.DISPOSED
            candidate.disposal_method = disposal_method
            candidate.disposal_date = now.date()
            candidate.updated_at = now
            if candidate.item_copy:
                candidate.item_copy.condition = ItemCondition.WITHDRAWN

                # Update catalog item status if last copy
                remaining_after_q = select(func.count(ItemCopy.id)).where(
                    ItemCopy.catalog_item_id == candidate.item_copy.catalog_item_id,
                    ItemCopy.id != candidate.item_copy.id,
                    ItemCopy.condition != ItemCondition.WITHDRAWN,
                )
                remaining_after_result = await db.execute(remaining_after_q)
                if not (remaining_after_result.scalar() or 0):
                    catalog_item_q = select(CatalogItem).where(
                        CatalogItem.id == candidate.item_copy.catalog_item_id
                    )
                    cat_result = await db.execute(catalog_item_q)
                    cat_item = cat_result.scalar_one_or_none()
                    if cat_item:
                        cat_item.status = ItemStatus.withdrawn

                # Create lifecycle event
                await create_lifecycle_event(
                    db=db,
                    item_copy_id=candidate.item_copy_id,
                    event_type=LifecycleEventType.WEEDED,
                    description=f"Item withdrawn via batch weeding. Disposal: {disposal_method}",
                    performed_by_id=current_user.id,
                    related_weeding_id=candidate.id,
                )
                batch_withdrawn_by_catalog[cat_id] = batch_withdrawn_by_catalog.get(cat_id, 0) + 1
            withdrawn_count += 1

    await db.commit()
    return {"withdrawn": withdrawn_count, "skipped": skipped, "total_requested": len(candidate_ids)}


# ============ Section Pressure Analysis ============


@router.get("/section-pressure", response_model=SectionPressureListResponse)
async def section_pressure(
    location: str | None = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Analyze space pressure by library section."""
    sections = await get_section_pressure(db, location_filter=location)
    return {"sections": sections}


# ============ Duplicate Detection ============


@router.get("/duplicates", response_model=DuplicateDetectionResponse)
async def duplicate_detection(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Detect items with excessive duplicate copies."""
    groups = await detect_duplicates(db)
    total_excess = sum(g["excess_copies"] for g in groups)
    return {"groups": groups, "total_excess_copies": total_excess}


# ============ Superseded Editions ============


@router.get("/superseded", response_model=SupersededEditionListResponse)
async def superseded_editions(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Find items that have been superseded by newer editions."""
    items = await detect_superseded_editions(db)
    return {"items": items, "total": len(items)}


# ============ Weeding Rules ============


@router.get("/rules", response_model=WeedingRuleListResponse)
async def list_rules(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all configured weeding rules."""
    query = select(WeedingRule).order_by(WeedingRule.name)
    result = await db.execute(query)
    rules = result.scalars().all()
    return {"rules": rules, "total": len(rules)}


@router.post("/rules", response_model=WeedingRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_rule(
    request: WeedingRuleCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new weeding rule."""
    rule = WeedingRule(
        name=request.name,
        description=request.description,
        crew_category=request.crew_category,
        max_age_years=request.max_age_years,
        max_years_no_circulation=request.max_years_no_circulation,
        min_condition_score=request.min_condition_score,
        max_duplicate_copies=request.max_duplicate_copies,
        section_fill_threshold=request.section_fill_threshold,
        subject_keywords=request.subject_keywords,
        location_filter=request.location_filter,
        created_by_id=current_user.id,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    rule_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a weeding rule."""
    query = select(WeedingRule).where(WeedingRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    await db.delete(rule)
    await db.commit()
