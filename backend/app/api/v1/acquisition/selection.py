# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - Selection List API Endpoints

Provides endpoints for:
- Selection list (wishlist) management
- Converting selection items to purchase orders
- Collection development intelligence report
"""
from app.core.logging import get_logger
import uuid
from collections import defaultdict
from datetime import datetime, timezone

logger = get_logger(__name__)
from decimal import Decimal
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.acquisition import (
    Fund, PurchaseOrder, PurchaseOrderItem,
    SelectionListItem, SelectionPriority, SelectionSource, Vendor
)
from ....models.catalog import CatalogItem
from ....models.circulation import Hold, HoldStatus
from ....models.inventory import ItemCondition, ItemCopy
from ....models.multi_branch import ConsortiumMember, ConsortiumTransaction, LibrarySystem
from ....models.release_tracker import TrackerBook, UserFollow
from ....models.user import User, UserRole
from ....schemas.acquisition import (
    AddInsightToSelectionRequest,
    CollectionInsightItem,
    CollectionIntelligenceReport,
    ConvertToPoRequest,
    PurchaseOrderResponse,
    SelectionItemCreate,
    SelectionItemListResponse,
    SelectionItemResponse,
)
from ..auth import get_current_user
from ..dependencies import require_staff

router = APIRouter(prefix="/acquisition", tags=["acquisition-selection"])


class _InsightActionResponse(BaseModel):
    message: str
    selection_item_id: int



def _norm_key(title: str | None, author: str | None = None) -> str:
    title_clean = (title or "unknown").strip().lower()
    author_clean = (author or "").strip().lower()
    return f"{title_clean}|{author_clean}"


@router.get("/collection-intelligence/report", response_model=CollectionIntelligenceReport)
async def collection_intelligence_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Build collection development intelligence report for staff."""
    await require_staff(current_user)

    # Load only the columns needed for lookup sets (avoid loading full ORM objects)
    isbn_rows = await db.execute(
        select(CatalogItem.isbn).where(CatalogItem.isbn.isnot(None))
    )
    catalog_by_isbn = {row[0] for row in isbn_rows.all()}

    key_rows = await db.execute(
        select(CatalogItem.title, CatalogItem.author)
    )
    catalog_title_keys = {_norm_key(row[0], row[1]) for row in key_rows.all()}

    # 1) Patrons searched for X but we don't have it (proxy: manual selection entries)
    manual_result = await db.execute(
        select(SelectionListItem)
        .where(SelectionListItem.source == SelectionSource.MANUAL)
        .order_by(SelectionListItem.created_at.desc())
        .limit(25)
    )
    patrons_searched_missing: list[CollectionInsightItem] = []
    for row in manual_result.scalars().all():
        if row.isbn and row.isbn in catalog_by_isbn:
            continue
        if _norm_key(row.title, row.author) in catalog_title_keys:
            continue
        patrons_searched_missing.append(
            CollectionInsightItem(
                key=f"manual-{row.id}",
                title=row.title,
                author=row.author,
                isbn=row.isbn,
                reason="Requested manually but not currently in catalog.",
                score=75,
                source="patron_request_proxy",
                metadata={"selection_item_id": row.id, "priority": row.priority},
            )
        )

    # 2) Popular titles we don't own (tracked releases + follower demand)
    follows_count = await db.execute(
        select(UserFollow.author_id, func.count(UserFollow.id)).group_by(UserFollow.author_id)
    )
    follower_map = {row[0]: int(row[1]) for row in follows_count.all()}

    release_rows = await db.execute(
        select(TrackerBook)
        .options(selectinload(TrackerBook.author))
        .order_by(TrackerBook.release_date.desc().nullslast()).limit(150)
    )
    popular_titles_not_owned: list[CollectionInsightItem] = []
    missing_award_winners: list[CollectionInsightItem] = []
    topic_buckets: dict[str, int] = defaultdict(int)

    for book in release_rows.scalars().all():
        if (book.isbn_13 and book.isbn_13 in catalog_by_isbn) or _norm_key(book.title, None) in catalog_title_keys:
            continue

        demand = follower_map.get(book.author_id, 0)
        if demand >= 1:
            popular_titles_not_owned.append(
                CollectionInsightItem(
                    key=f"release-{book.id}",
                    title=book.title,
                    author=book.author_name,
                    isbn=book.isbn_13,
                    reason="Upcoming/recent title has patron follow demand but is not owned.",
                    score=min(100, 50 + demand * 10),
                    source="release_tracker",
                    metadata={"follower_demand": demand},
                )
            )

        categories = [c for c in (book.raw_categories or []) if isinstance(c, str)]
        for cat in categories:
            topic_buckets[cat] += 1
            if "award" in cat.lower() or "prize" in cat.lower() or "medal" in cat.lower():
                missing_award_winners.append(
                    CollectionInsightItem(
                        key=f"award-{book.id}-{cat[:20]}",
                        title=book.title,
                        author=book.author_name,
                        isbn=book.isbn_13,
                        reason=f"Award-related category detected ({cat}) and title is not owned.",
                        score=82,
                        source="release_tracker_categories",
                        metadata={"award_category": cat},
                    )
                )

    popular_titles_not_owned = sorted(popular_titles_not_owned, key=lambda x: x.score, reverse=True)[:20]
    missing_award_winners = missing_award_winners[:20]

    # 3) Series with missing volumes (load only titles)
    volume_pattern = re.compile(r"^(.*?)\s+(?:book|vol(?:ume)?|#)\s*(\d+)\b", re.IGNORECASE)
    series_data: dict[str, set[int]] = defaultdict(set)
    series_titles: dict[str, str] = {}
    title_rows = await db.execute(select(CatalogItem.title).where(CatalogItem.title.isnot(None)))
    for (title,) in title_rows.all():
        m = volume_pattern.match(title)
        if not m:
            continue
        base = m.group(1).strip()
        volume = int(m.group(2))
        series_data[base].add(volume)
        series_titles[base] = base

    series_missing_volumes: list[CollectionInsightItem] = []
    for base, vols in series_data.items():
        if len(vols) < 2:
            continue
        max_vol = max(vols)
        missing = [str(v) for v in range(1, max_vol + 1) if v not in vols]
        if missing:
            series_missing_volumes.append(
                CollectionInsightItem(
                    key=f"series-{base.lower()}",
                    title=series_titles[base],
                    reason=f"Missing volumes: {', '.join(missing[:6])}",
                    score=min(100, 40 + len(missing) * 8),
                    source="catalog_series_gap_scan",
                    metadata={"owned_volumes": len(vols), "missing_count": len(missing)},
                )
            )

    # 4) High-hold-ratio items
    holds_q = await db.execute(
        select(Hold.item_id, func.count(Hold.id))
        .where(Hold.status.in_([HoldStatus.pending, HoldStatus.ready]))
        .group_by(Hold.item_id)
    )
    hold_counts = {int(row[0]): int(row[1]) for row in holds_q.all() if row[0] is not None}

    copies_q = await db.execute(
        select(ItemCopy.catalog_item_id, func.count(ItemCopy.id))
        .where(ItemCopy.condition.notin_([ItemCondition.WITHDRAWN, ItemCondition.DAMAGED]))
        .group_by(ItemCopy.catalog_item_id)
    )
    copy_counts = {int(row[0]): int(row[1]) for row in copies_q.all() if row[0] is not None}

    high_hold_ratio_items: list[CollectionInsightItem] = []
    # Only fetch catalog items that have 3+ holds (avoid full table scan)
    high_hold_ids = [iid for iid, cnt in hold_counts.items() if cnt >= 3]
    if high_hold_ids:
        held_items_rows = await db.execute(
            select(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.isbn)
            .where(CatalogItem.id.in_(high_hold_ids))
        )
        for item_id, title, author, isbn in held_items_rows.all():
            holds = hold_counts.get(item_id, 0)
            copies = copy_counts.get(item_id, 0)
            if copies == 0:
                continue
            ratio = holds / copies
            if ratio < 1.5:
                continue
            high_hold_ratio_items.append(
                CollectionInsightItem(
                    key=f"hold-ratio-{item_id}",
                    title=title,
                    author=author,
                    isbn=isbn,
                    reason=f"High holds-to-copy ratio ({ratio:.2f}); consider buying additional copies.",
                    score=min(100, ratio * 25),
                    source="circulation_holds",
                    metadata={"holds": holds, "copies": copies, "ratio": round(ratio, 2)},
                )
            )

    # 5) Outdated subjects (avg age > 10 years) - load only relevant columns
    current_year = datetime.now(timezone.utc).year
    subject_years: dict[str, list[int]] = defaultdict(list)
    subject_rows = await db.execute(
        select(CatalogItem.publication_year, CatalogItem.subjects)
        .where(CatalogItem.publication_year.isnot(None), CatalogItem.subjects.isnot(None))
    )
    for pub_year, subjects in subject_rows.all():
        age = max(0, current_year - pub_year)
        for subject in [s.strip() for s in subjects.split(",") if s.strip()]:
            subject_years[subject].append(age)

    outdated_subjects: list[CollectionInsightItem] = []
    for subject, ages in subject_years.items():
        if len(ages) < 3:
            continue
        avg_age = sum(ages) / len(ages)
        if avg_age <= 10:
            continue
        outdated_subjects.append(
            CollectionInsightItem(
                key=f"subject-{subject.lower()}",
                title=subject,
                reason=f"Average age is {avg_age:.1f} years; refresh this subject area.",
                score=min(100, avg_age * 4),
                source="subject_age_analysis",
                metadata={"average_age": round(avg_age, 1), "title_count": len(ages)},
            )
        )

    # 6) Peer library comparison (they have it, we don't) via consortium ILL notes
    peer_library_gaps: list[CollectionInsightItem] = []
    peer_q = await db.execute(
        select(ConsortiumTransaction.notes, LibrarySystem.name, func.count(ConsortiumTransaction.id))
        .join(ConsortiumMember, ConsortiumMember.id == ConsortiumTransaction.lending_member_id)
        .join(LibrarySystem, LibrarySystem.id == ConsortiumMember.library_system_id)
        .where(ConsortiumTransaction.notes.isnot(None))
        .group_by(ConsortiumTransaction.notes, LibrarySystem.name)
        .order_by(func.count(ConsortiumTransaction.id).desc())
        .limit(20)
    )
    for note, library_name, tx_count in peer_q.all():
        if not note:
            continue
        if _norm_key(note, None) in catalog_title_keys:
            continue
        peer_library_gaps.append(
            CollectionInsightItem(
                key=f"peer-{library_name}-{note[:20]}",
                title=note[:500],
                reason=f"Requested via consortium from {library_name} {tx_count} time(s), but not found locally.",
                score=min(100, 40 + int(tx_count) * 10),
                source="consortium_transactions",
                metadata={"peer_library": library_name, "request_count": int(tx_count)},
            )
        )

    # 7) & 8) Trending topics without coverage (reuse subject data from section 5)
    trending_topics_without_coverage: list[CollectionInsightItem] = []
    subject_text = " ".join(subject_years.keys()).lower()
    for topic, mentions in sorted(topic_buckets.items(), key=lambda x: x[1], reverse=True)[:30]:
        if mentions < 2:
            continue
        if topic.lower() in subject_text:
            continue
        trending_topics_without_coverage.append(
            CollectionInsightItem(
                key=f"topic-{topic[:20]}",
                title=topic,
                reason="Trending in upcoming titles but weak in local subject coverage.",
                score=min(100, 40 + mentions * 10),
                source="release_tracker_topic_gap",
                metadata={"mentions": mentions},
            )
        )

    return CollectionIntelligenceReport(
        patrons_searched_missing=patrons_searched_missing[:20],
        popular_titles_not_owned=popular_titles_not_owned,
        series_missing_volumes=series_missing_volumes[:20],
        high_hold_ratio_items=sorted(high_hold_ratio_items, key=lambda x: x.score, reverse=True)[:20],
        outdated_subjects=sorted(outdated_subjects, key=lambda x: x.score, reverse=True)[:20],
        peer_library_gaps=peer_library_gaps,
        missing_award_winners=missing_award_winners,
        trending_topics_without_coverage=trending_topics_without_coverage[:20],
    )


@router.post("/collection-intelligence/add-to-selection", response_model=_InsightActionResponse, status_code=status.HTTP_201_CREATED)
async def add_insight_to_selection(
    request: AddInsightToSelectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One-click add of any intelligence result to purchase consideration."""
    await require_staff(current_user)

    item = SelectionListItem(
        title=request.title,
        author=request.author,
        isbn=request.isbn,
        estimated_price=request.estimated_price,
        notes=request.notes,
        priority=request.priority,
        source=request.source,
        source_id=request.source_id,
        requested_by_id=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return _InsightActionResponse(
        message="Added to purchase consideration",
        selection_item_id=item.id,
    )


@router.get("/selection-list", response_model=SelectionItemListResponse)
async def list_selection_items(
    priority: SelectionPriority | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List selection list items (wishlist)"""
    await require_staff(current_user)

    query = select(SelectionListItem).options(
        selectinload(SelectionListItem.requested_by)
    )
    count_query = select(func.count(SelectionListItem.id))

    if priority:
        query = query.where(SelectionListItem.priority == priority)
        count_query = count_query.where(SelectionListItem.priority == priority)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.offset(offset)
        .limit(per_page)
        .order_by(SelectionListItem.created_at.desc())
    )

    result = await db.execute(query)
    items = result.scalars().all()

    response_items = []
    for item in items:
        item_response = SelectionItemResponse.model_validate(item)
        item_response.requested_by_name = (
            item.requested_by.full_name if item.requested_by else None
        )
        response_items.append(item_response)

    return SelectionItemListResponse(
        items=response_items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/selection-list", response_model=SelectionItemResponse, status_code=status.HTTP_201_CREATED)
async def add_selection_item(
    item_in: SelectionItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add item to selection list"""
    await require_staff(current_user)

    item = SelectionListItem(
        **item_in.model_dump(),
        requested_by_id=current_user.id,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/selection-list/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_selection_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove item from selection list"""
    await require_staff(current_user)

    item = await get_or_404(db, SelectionListItem, item_id, "Selection item not found")

    await db.delete(item)
    await db.commit()
    return None


@router.post("/selection-list/convert-to-po", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def convert_to_purchase_order(
    request: ConvertToPoRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert selection list items to a purchase order"""
    await require_staff(current_user)

    # Verify vendor and fund exist
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == request.vendor_id, Vendor.is_active == True)
    )
    if not vendor_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found or inactive")

    fund_result = await db.execute(select(Fund).where(Fund.id == request.fund_id))
    if not fund_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fund not found")

    # Get selection items
    result = await db.execute(
        select(SelectionListItem).where(
            SelectionListItem.id.in_(request.selection_item_ids)
        )
    )
    selection_items = result.scalars().all()

    if not selection_items:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid selection items found")

    try:
        # Generate PO number with UUID suffix to avoid race conditions
        po_number = f"PO-{datetime.now().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        # Create purchase order
        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=request.vendor_id,
            fund_id=request.fund_id,
            created_by_id=current_user.id,
        )
        db.add(po)
        await db.flush()

        # Create PO items from selection items
        total = Decimal("0.00")
        for sel_item in selection_items:
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                title=sel_item.title,
                author=sel_item.author,
                isbn=sel_item.isbn,
                quantity=1,
                unit_price=sel_item.estimated_price or Decimal("0.00"),
            )
            db.add(po_item)
            total += sel_item.estimated_price or Decimal("0.00")

            # Mark as ordered instead of deleting
            sel_item.status = "ordered"

        po.total_amount = total
        await db.commit()

        # Re-fetch with relationships for response serialization
        result = await db.execute(
            select(PurchaseOrder)
            .where(PurchaseOrder.id == po.id)
            .options(
                selectinload(PurchaseOrder.items),
                selectinload(PurchaseOrder.vendor),
                selectinload(PurchaseOrder.fund),
            )
        )
        po = result.scalar_one()

        return po
    except Exception:
        await db.rollback()
        logger.exception("Failed to convert to purchase order")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to convert to purchase order"
        ) from None


@router.patch("/selection-list/{item_id}/approve")
async def approve_selection_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a selection list item for ordering."""
    await require_staff(current_user)

    result = await db.execute(select(SelectionListItem).where(SelectionListItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Selection list item not found")
    item.status = "approved"
    await db.commit()
    return {"id": item.id, "status": "approved"}


@router.patch("/selection-list/{item_id}/reject")
async def reject_selection_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reject a selection list item."""
    await require_staff(current_user)

    result = await db.execute(select(SelectionListItem).where(SelectionListItem.id == item_id))
    item = result.scalars().first()
    if not item:
        raise HTTPException(status_code=404, detail="Selection list item not found")
    item.status = "rejected"
    await db.commit()
    return {"id": item.id, "status": "rejected"}
