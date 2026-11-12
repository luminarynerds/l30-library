# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reports API.
Circulation statistics and analytics.
"""

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

logger = get_logger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.cache import get_cached_with_lock, make_cache_key
from ...core.cache_strategies import CacheTTL
from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.catalog import CatalogItem
from ...models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ...models.fine import Fine, FineStatus
from ...models.inventory import ItemCopy
from ...models.user import User
from ...schemas.analytics import (CirculationTrendsResponse,
                                  DriftingItem,
                                  DriftingItemsResponse,
                                  PopularItem,
                                  PopularItemsResponse,
                                  TopReader, TopReadersResponse,
                                  TrendDataPoint)
from ...middleware.pii_filter import pii_filtered
from ...utils.report_export import make_export_response
from .dependencies import require_staff

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("")
async def reports_index(
    current_user: User = Depends(require_staff),
):
    """List available reports."""
    return {
        "available_reports": [
            {"name": "Daily Circulation", "path": "/reports/circulation/daily"},
            {"name": "Overdue Items", "path": "/reports/overdue-items"},
            {"name": "Popular Items", "path": "/reports/popular-items"},
            {"name": "Hold Queue", "path": "/reports/hold-queue"},
            {"name": "Fine Collection", "path": "/reports/fine-collection"},
            {"name": "Circulation Trends", "path": "/reports/circulation-trends"},
            {"name": "Inventory Summary", "path": "/reports/inventory-summary"},
        ]
    }


@router.get("/circulation/daily")
async def get_daily_stats(
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD). Defaults to today."),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD). Defaults to today."),
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get today's circulation statistics. Add ?format=csv|excel|pdf to download."""

    report_date = start_date or date.today()
    today_start = datetime.combine(report_date, datetime.min.time())
    today_end = datetime.combine(end_date or report_date, datetime.max.time())

    # Checkouts today
    checkouts_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.checked_out_at >= today_start, Checkout.checked_out_at <= today_end
        )
    )
    checkouts_today = checkouts_result.scalar() or 0

    # Returns today
    returns_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.returned_at >= today_start, Checkout.returned_at <= today_end
        )
    )
    returns_today = returns_result.scalar() or 0

    # Active checkouts
    active_result = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.status == CheckoutStatus.active)
    )
    active_checkouts = active_result.scalar() or 0

    # Overdue items
    overdue_result = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.status == CheckoutStatus.active,
            Checkout.due_date < datetime.now(timezone.utc),
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Build data quality warnings
    data_quality = []
    if overdue_count > 0:
        data_quality.append(f"{overdue_count} overdue items need attention.")

    # Get total collection size for ratio check
    collection_result = await db.execute(select(func.count(ItemCopy.id)))
    total_copies = collection_result.scalar() or 0
    if total_copies > 0 and active_checkouts > total_copies * 0.8:
        data_quality.append(
            f"Active checkouts ({active_checkouts}) exceed 80% of collection size ({total_copies}). Verify data accuracy."
        )

    data = {
        "date": date.today().isoformat(),
        "checkouts_today": checkouts_today,
        "returns_today": returns_today,
        "active_checkouts": active_checkouts,
        "overdue_count": overdue_count,
        "data_quality": data_quality,
    }

    if format:
        export = make_export_response(data, format, title="Daily Circulation Statistics", filename_prefix="daily_stats")
        if export:
            return export

    return data


@router.get("/circulation/daily-details")
@pii_filtered
async def get_daily_details(
    request: Request,
    date_param: date = Query(..., alias="date", description="Date (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get detailed checkout/return list for a single day."""
    day_start = datetime.combine(date_param, datetime.min.time())
    day_end = datetime.combine(date_param, datetime.max.time())

    co_query = (
        select(Checkout)
        .where(Checkout.checked_out_at >= day_start, Checkout.checked_out_at <= day_end)
        .options(selectinload(Checkout.user), selectinload(Checkout.item))
    )
    co_result = await db.execute(co_query)
    co_rows = co_result.scalars().all()

    checkouts = [
        {
            "checkout_id": c.id,
            "item_title": c.item.title if c.item else None,
            "item_author": c.item.author if c.item else None,
            "patron_name": c.user.full_name if c.user else None,
            "checked_out_at": c.checked_out_at.isoformat() if c.checked_out_at else None,
        }
        for c in co_rows
    ]

    ret_query = (
        select(Checkout)
        .where(Checkout.returned_at >= day_start, Checkout.returned_at <= day_end)
        .options(selectinload(Checkout.user), selectinload(Checkout.item))
    )
    ret_result = await db.execute(ret_query)
    ret_rows = ret_result.scalars().all()

    returns = [
        {
            "checkout_id": c.id,
            "item_title": c.item.title if c.item else None,
            "item_author": c.item.author if c.item else None,
            "patron_name": c.user.full_name if c.user else None,
            "returned_at": c.returned_at.isoformat() if c.returned_at else None,
        }
        for c in ret_rows
    ]

    patron_ids = {c.user_id for c in co_rows} | {c.user_id for c in ret_rows}

    return {
        "date": date_param.isoformat(),
        "checkouts": checkouts,
        "returns": returns,
        "patron_count": len(patron_ids),
    }


@router.get("/circulation/overdue")
@pii_filtered
async def get_overdue_items(
    request: Request,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    min_days_overdue: int | None = Query(None, ge=0, description="Minimum days overdue filter"),
    max_days_overdue: int | None = Query(None, ge=0, description="Maximum days overdue filter"),
    patron_type: str | None = Query(None, description="Filter by patron type (adult, teen, child)"),
    patron_id: int | None = Query(None, description="Filter by specific patron ID"),
    sort_by: str = Query("due_date", description="Sort field: days_overdue, patron_name, due_date, item_title"),
    sort_order: str = Query("asc", description="Sort order: asc or desc"),
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get list of overdue items with patron contact info, filter and sort options.

    PII fields in the response are automatically scoped by the requesting user's
    role.  Volunteers and patron-level users will see redacted contact details.
    """


    now = datetime.now(timezone.utc)

    # Base query with eager loading of user and item
    query = (
        select(Checkout)
        .where(
            Checkout.status == CheckoutStatus.active,
            Checkout.due_date < now,
        )
        .options(selectinload(Checkout.user), selectinload(Checkout.item))
    )

    # Apply days overdue filters using date math
    if min_days_overdue is not None:
        max_due_date = now - timedelta(days=min_days_overdue)
        query = query.where(Checkout.due_date <= max_due_date)

    if max_days_overdue is not None:
        min_due_date = now - timedelta(days=max_days_overdue)
        query = query.where(Checkout.due_date >= min_due_date)

    # Apply patron type filter
    if patron_type is not None:
        query = query.join(User, Checkout.user_id == User.id).where(User.patron_type == patron_type)

    # Apply patron ID filter
    if patron_id is not None:
        query = query.where(Checkout.user_id == patron_id)

    # Build count query with same filters
    count_query = select(func.count(Checkout.id)).where(
        Checkout.status == CheckoutStatus.active, Checkout.due_date < now
    )
    if min_days_overdue is not None:
        max_due_date = now - timedelta(days=min_days_overdue)
        count_query = count_query.where(Checkout.due_date <= max_due_date)
    if max_days_overdue is not None:
        min_due_date = now - timedelta(days=max_days_overdue)
        count_query = count_query.where(Checkout.due_date >= min_due_date)
    if patron_type is not None:
        count_query = count_query.join(User, Checkout.user_id == User.id).where(User.patron_type == patron_type)
    if patron_id is not None:
        count_query = count_query.where(Checkout.user_id == patron_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply sorting
    # Note: days_overdue sort is equivalent to due_date sort (inversely)
    sort_ascending = sort_order.lower() != "desc"
    if sort_by == "days_overdue":
        # More days overdue = older due_date, so invert the sort
        order_col = Checkout.due_date.asc() if not sort_ascending else Checkout.due_date.desc()
        # Actually: days_overdue asc means least overdue first = newest due_date first = due_date desc
        # days_overdue desc means most overdue first = oldest due_date first = due_date asc
        order_col = Checkout.due_date.desc() if sort_ascending else Checkout.due_date.asc()
    elif sort_by == "due_date":
        order_col = Checkout.due_date.asc() if sort_ascending else Checkout.due_date.desc()
    elif sort_by == "patron_name":
        # Join User if not already joined for patron_type filter
        if patron_type is None:
            query = query.join(User, Checkout.user_id == User.id, isouter=True)
        order_col = User.last_name.asc() if sort_ascending else User.last_name.desc()
    elif sort_by == "item_title":
        query = query.join(CatalogItem, Checkout.item_id == CatalogItem.id, isouter=True)
        order_col = CatalogItem.title.asc() if sort_ascending else CatalogItem.title.desc()
    else:
        # Default to due_date
        order_col = Checkout.due_date.asc()

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(order_col)

    result = await db.execute(query)
    checkouts = result.scalars().all()

    items = []
    for c in checkouts:
        days_overdue = (now - c.due_date).days if c.due_date else 0
        user = c.user

        # Build full address string if available
        address_parts = []
        if user:
            if user.address_line1:
                address_parts.append(user.address_line1)
            if user.address_line2:
                address_parts.append(user.address_line2)
            city_state_zip = []
            if user.city:
                city_state_zip.append(user.city)
            if user.state:
                city_state_zip.append(user.state)
            if user.zip_code:
                city_state_zip.append(user.zip_code)
            if city_state_zip:
                address_parts.append(", ".join(city_state_zip))

        items.append(
            {
                "checkout_id": c.id,
                "patron_id": user.id if user else None,
                "patron_name": user.full_name if user else None,
                "patron_email": user.email if user else None,
                "patron_phone": user.phone if user else None,
                "patron_address": "\n".join(address_parts) if address_parts else None,
                "patron_library_card": user.library_card if user else None,
                "patron_type": user.patron_type if user else None,
                "notice_preference": str(user.notice_preference) if user and user.notice_preference else None,
                "item_title": c.item.title if c.item else None,
                "item_author": c.item.author if c.item else None,
                "due_date": c.due_date.isoformat() if c.due_date else None,
                "days_overdue": days_overdue,
                "checked_out_at": c.checked_out_at.isoformat() if c.checked_out_at else None,
            }
        )

    data = {"items": items, "total": total, "page": page}

    if format:
        # Apply PII filtering before exporting to CSV/Excel/PDF so that
        # downloaded files respect the same role-based scoping as JSON.
        from ...core.pii_scope import filter_report_response as _filter
        filtered_for_export, _ = _filter(data, current_user.role)
        export = make_export_response(
            filtered_for_export, format,
            title="Overdue Items Report", filename_prefix="overdue_items",
        )
        if export:
            return export

    return data


@router.get("/circulation/popular")
async def get_popular_items(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=50),
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD). Overrides days."),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD). Defaults to today."),
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get most popular items by checkout count"""

    async def _fetch_popular():
        if start_date:
            since = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        else:
            since = datetime.now(timezone.utc) - timedelta(days=days)

        until = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc) if end_date else None
        conditions = [Checkout.checked_out_at >= since]
        if until:
            conditions.append(Checkout.checked_out_at <= until)

        query = (
            select(Checkout.item_id, func.count(Checkout.id).label("checkout_count"))
            .where(*conditions)
            .group_by(Checkout.item_id)
            .order_by(func.count(Checkout.id).desc())
            .limit(limit)
        )

        result = await db.execute(query)
        popular = result.all()

        # Collect item IDs and counts
        item_ids = [item_id for item_id, _ in popular if item_id]
        counts = {item_id: count for item_id, count in popular if item_id}

        if not item_ids:
            return {"period_days": days, "items": []}

        # Fetch all catalog items in a single query (fixes N+1)
        cat_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id.in_(item_ids))
        )
        catalog_items = {item.id: item for item in cat_result.scalars().all()}

        # Build response preserving order from checkout counts
        items = []
        for item_id in item_ids:
            if item_id in catalog_items:
                cat_item = catalog_items[item_id]
                items.append(
                    {
                        "catalog_item_id": item_id,
                        "title": cat_item.title,
                        "author": cat_item.author,
                        "item_type": cat_item.item_type,
                        "checkout_count": counts[item_id],
                    }
                )

        return {"period_days": days, "items": items}

    cache_key = make_cache_key("l30:report:popular", days=days, limit=limit, start_date=str(start_date), end_date=str(end_date))
    data = await get_cached_with_lock(cache_key, _fetch_popular, ttl_seconds=CacheTTL.WARM)

    if format:
        export = make_export_response(data, format, title="Popular Items Report", filename_prefix="popular_items")
        if export:
            return export

    return data


@router.get("/circulation/holds")
async def get_hold_stats(
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get hold queue statistics. Add ?format=csv|excel|pdf to download."""


    # Pending holds
    pending_result = await db.execute(
        select(func.count(Hold.id)).where(Hold.status == HoldStatus.pending)
    )
    pending = pending_result.scalar() or 0

    # Ready holds
    ready_result = await db.execute(
        select(func.count(Hold.id)).where(Hold.status == HoldStatus.ready)
    )
    ready = ready_result.scalar() or 0

    # Average wait time - Note: fulfilled_at and placed_at columns don't exist in Hold model
    # Using created_at as a placeholder for now, this needs proper migration to add these fields
    # thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    # Commenting out until fulfilled_at and placed_at columns are added to Hold model
    # avg_wait_result = await db.execute(
    #     select(func.avg(
    #         func.extract('epoch', Hold.fulfilled_at - Hold.created_at) / 86400
    #     )).where(
    #         Hold.status == HoldStatus.fulfilled,
    #         Hold.fulfilled_at >= thirty_days_ago
    #     )
    # )
    # avg_wait_days = avg_wait_result.scalar()
    avg_wait_days = None  # Temporarily disabled until migration adds fulfilled_at field

    data = {
        "pending_holds": pending,
        "ready_for_pickup": ready,
        "avg_wait_days": round(float(avg_wait_days), 1) if avg_wait_days else None,
    }

    if format:
        export = make_export_response(data, format, title="Hold Queue Statistics", filename_prefix="hold_stats")
        if export:
            return export

    return data


@router.get("/circulation/fines")
async def get_fine_stats(
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD). Defaults to first of month."),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD). Defaults to today."),
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get fine collection statistics. Add ?format=csv|excel|pdf to download."""

    period_start = datetime.combine(start_date, datetime.min.time()) if start_date else datetime.combine(date.today().replace(day=1), datetime.min.time())
    period_end = datetime.combine(end_date, datetime.max.time()) if end_date else None

    # Outstanding fines
    outstanding_result = await db.execute(
        select(func.sum(Fine.amount)).where(Fine.status == FineStatus.unpaid)
    )
    outstanding = outstanding_result.scalar() or Decimal("0.00")

    # Paid in period
    paid_q = select(func.sum(Fine.amount)).where(
        Fine.status == FineStatus.paid,
        Fine.paid_at >= period_start,
    )
    if period_end:
        paid_q = paid_q.where(Fine.paid_at <= period_end)
    paid_result = await db.execute(paid_q)
    paid_this_month = paid_result.scalar() or Decimal("0.00")

    # Waived in period
    waived_q = select(func.sum(Fine.amount)).where(
        Fine.status == FineStatus.waived,
        Fine.waived_at >= period_start,
    )
    if period_end:
        waived_q = waived_q.where(Fine.waived_at <= period_end)
    waived_result = await db.execute(waived_q)
    waived_this_month = waived_result.scalar() or Decimal("0.00")

    # Count of patrons with fines
    patrons_with_fines_result = await db.execute(
        select(func.count(func.distinct(Fine.user_id))).where(
            Fine.status == FineStatus.unpaid
        )
    )
    patrons_with_fines = patrons_with_fines_result.scalar() or 0

    data = {
        "outstanding_total": float(outstanding),
        "paid_this_month": float(paid_this_month),
        "waived_this_month": float(waived_this_month),
        "patrons_with_fines": patrons_with_fines,
    }

    if format:
        export = make_export_response(data, format, title="Fine Collection Statistics", filename_prefix="fine_stats")
        if export:
            return export

    return data


@router.get("/circulation/trends")
async def get_circulation_trends(
    days: int = Query(30, ge=7, le=365),
    start_date: date | None = Query(None, description="Start date (YYYY-MM-DD). Overrides days."),
    end_date: date | None = Query(None, description="End date (YYYY-MM-DD). Defaults to today."),
    granularity: str = Query("daily", description="Time granularity: hourly, daily, weekly, monthly"),
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get checkout trends at configurable granularity. Add ?format=csv|excel|pdf to download."""

    if granularity not in ("hourly", "daily", "weekly", "monthly"):
        granularity = "daily"

    since = start_date if start_date else date.today() - timedelta(days=days)
    until = end_date or date.today()
    since_dt = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
    until_dt = datetime.combine(until + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    if granularity == "hourly":
        bucket = func.date_trunc("hour", Checkout.checked_out_at)
    elif granularity == "weekly":
        bucket = func.date_trunc("week", Checkout.checked_out_at)
    elif granularity == "monthly":
        bucket = func.date_trunc("month", Checkout.checked_out_at)
    else:
        bucket = func.date(Checkout.checked_out_at)

    query = (
        select(bucket.label("bucket"), func.count(Checkout.id).label("count"))
        .where(Checkout.checked_out_at >= since_dt, Checkout.checked_out_at < until_dt)
        .group_by(bucket)
        .order_by(bucket)
    )

    result = await db.execute(query)
    rows = result.all()

    data_points = []
    for bucket_val, count in rows:
        label = bucket_val.isoformat() if hasattr(bucket_val, "isoformat") else str(bucket_val)
        data_points.append({"date": label, "checkouts": count})

    data = {"period_days": days, "granularity": granularity, "data": data_points}

    if format:
        export = make_export_response(data, format, title="Circulation Trends", filename_prefix="circulation_trends")
        if export:
            return export

    return data


@router.get("/inventory/summary")
async def get_inventory_summary(
    format: str | None = Query(None, description="Export format: csv, excel, pdf (omit for JSON)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get inventory summary statistics. Add ?format=csv|excel|pdf to download."""


    # Total copies
    total_result = await db.execute(select(func.count(ItemCopy.id)))
    total_copies = total_result.scalar() or 0

    # By condition
    condition_result = await db.execute(
        select(ItemCopy.condition, func.count(ItemCopy.id)).group_by(ItemCopy.condition)
    )
    by_condition = {row[0]: row[1] for row in condition_result.all()}

    # Total catalog items
    catalog_result = await db.execute(select(func.count(CatalogItem.id)))
    total_titles = catalog_result.scalar() or 0

    data = {
        "total_copies": total_copies,
        "total_titles": total_titles,
        "by_condition": by_condition,
    }

    if format:
        export = make_export_response(data, format, title="Inventory Summary", filename_prefix="inventory_summary")
        if export:
            return export

    return data


# ============================================================================
# Analytics Dashboard Endpoints
# ============================================================================



@router.get("/analytics/popular-items", response_model=PopularItemsResponse)
async def get_popular_items(
    days: int = Query(
        30, ge=1, le=365, description="Number of days for popularity metrics"
    ),
    limit: int = Query(10, ge=1, le=50, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get most popular items by checkout count."""


    since = datetime.now(timezone.utc) - timedelta(days=days)

    # Get checkout counts with catalog item details in a single query using JOIN
    query = (
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            CatalogItem.item_type,
            func.count(Checkout.id).label("checkout_count"),
        )
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.checked_out_at >= since)
        .group_by(CatalogItem.id, CatalogItem.title, CatalogItem.author, CatalogItem.item_type)
        .order_by(func.count(Checkout.id).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    popular = result.all()

    items = [
        PopularItem(
            catalog_item_id=item_id,
            title=title,
            author=author,
            checkout_count=checkout_count,
            item_type=item_type,
        )
        for item_id, title, author, item_type, checkout_count in popular
    ]

    # Get total unique items checked out in period
    total_query = select(func.count(func.distinct(Checkout.item_id))).where(
        Checkout.checked_out_at >= since
    )
    total_result = await db.execute(total_query)
    total_unique = total_result.scalar() or 0

    return PopularItemsResponse(
        items=items,
        period_days=days,
        total_unique_items=total_unique,
    )


@router.get("/analytics/circulation-trends", response_model=CirculationTrendsResponse)
async def get_circulation_trends(
    days: int = Query(
        30, ge=7, le=365, description="Number of days for trend analysis"
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get daily circulation trends with checkouts and returns."""


    since = date.today() - timedelta(days=days)

    # Get checkouts by day
    checkout_query = (
        select(
            func.date(Checkout.checked_out_at).label("day"),
            func.count(Checkout.id).label("count"),
        )
        .where(func.date(Checkout.checked_out_at) >= since)
        .group_by(func.date(Checkout.checked_out_at))
    )

    checkout_result = await db.execute(checkout_query)
    checkout_data = {row[0]: row[1] for row in checkout_result.all()}

    # Get returns by day
    return_query = (
        select(
            func.date(Checkout.returned_at).label("day"),
            func.count(Checkout.id).label("count"),
        )
        .where(
            func.date(Checkout.returned_at) >= since, Checkout.returned_at.isnot(None)
        )
        .group_by(func.date(Checkout.returned_at))
    )

    return_result = await db.execute(return_query)
    return_data = {row[0]: row[1] for row in return_result.all()}

    # Combine data
    data_points = []
    current_date = since
    total_checkouts = 0
    peak_day = None
    peak_count = 0

    while current_date <= date.today():
        checkouts = checkout_data.get(current_date, 0)
        returns = return_data.get(current_date, 0)

        data_points.append(
            TrendDataPoint(
                date=current_date.isoformat(),
                checkouts=checkouts,
                returns=returns,
            )
        )

        total_checkouts += checkouts
        if checkouts > peak_count:
            peak_count = checkouts
            peak_day = current_date.isoformat()

        current_date += timedelta(days=1)

    avg_checkouts = total_checkouts / days if days > 0 else 0

    return CirculationTrendsResponse(
        data=data_points,
        period_days=days,
        avg_checkouts=round(avg_checkouts, 2),
        peak_day=peak_day,
        peak_count=peak_count if peak_count > 0 else None,
    )


@router.get("/analytics/top-readers", response_model=TopReadersResponse)
@limiter.limit("15/hour")
async def get_top_readers(
    request: Request,
    days: int = Query(30, ge=0, le=365, description="Number of days (0 = all time)"),
    limit: int = Query(10, ge=1, le=50, description="Number of readers to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get top readers by reading minutes and books completed.

    Rate Limit: 15 requests per hour (complex window function for streak calculation)
    """


    # Import reading models
    from ...models.reading import ReadingLogEntry, ReadingRegistration

    since = datetime.now(timezone.utc) - timedelta(days=days) if days > 0 else None

    # Build query with JOIN to get user info in a single query (eliminates N+1)
    query = (
        select(
            ReadingRegistration.user_id,
            User.first_name,
            User.last_name,
            User.email,
            func.sum(ReadingLogEntry.minutes_read).label("total_minutes"),
            func.sum(ReadingLogEntry.books_read).label("total_books"),
        )
        .join(ReadingLogEntry, ReadingLogEntry.registration_id == ReadingRegistration.id)
        .join(User, ReadingRegistration.user_id == User.id)
    )

    if since:
        query = query.where(ReadingLogEntry.logged_at >= since)

    query = (
        query.group_by(ReadingRegistration.user_id, User.first_name, User.last_name, User.email)
        .order_by(func.sum(ReadingLogEntry.minutes_read).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    reader_stats = result.all()

    # Get user IDs for batch streak calculation
    user_ids = [row[0] for row in reader_stats if row[0]]

    # Batch calculate reading streaks using SQL window functions
    # This calculates the max consecutive day streak for each user in a single query
    streaks_by_user = {}
    if user_ids:
        from sqlalchemy import text

        # Use raw SQL for window function-based streak calculation
        # This identifies gaps between consecutive reading days and groups them
        streak_sql = text("""
            WITH user_dates AS (
                SELECT DISTINCT
                    rr.user_id,
                    DATE(rle.logged_at) as log_date
                FROM reading_log_entries rle
                JOIN reading_registrations rr ON rle.registration_id = rr.id
                WHERE rr.user_id = ANY(:user_ids)
            ),
            date_groups AS (
                SELECT
                    user_id,
                    log_date,
                    log_date - (ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY log_date))::int AS grp
                FROM user_dates
            ),
            streak_lengths AS (
                SELECT
                    user_id,
                    grp,
                    COUNT(*) as streak_length
                FROM date_groups
                GROUP BY user_id, grp
            )
            SELECT user_id, MAX(streak_length) as max_streak
            FROM streak_lengths
            GROUP BY user_id
        """)

        try:
            streak_result = await db.execute(streak_sql, {"user_ids": user_ids})
            for user_id, max_streak in streak_result.all():
                streaks_by_user[user_id] = int(max_streak) if max_streak else 0
        except Exception as e:  # noqa: BLE001  # streak SQL best-effort — fall back to 0
            logger.warning(f"Failed to calculate reading streaks via SQL: {e}")
            # Fallback: all streaks default to 0

    readers = [
        TopReader(
            user_id=user_id,
            user_name=f"{first_name} {last_name}" if first_name and last_name else email,
            total_minutes=int(total_minutes or 0),
            total_books=int(total_books or 0),
            reading_streak=streaks_by_user.get(user_id, 0),
        )
        for user_id, first_name, last_name, email, total_minutes, total_books in reader_stats
        if user_id
    ]

    # Get total number of readers in period
    total_query = (
        select(func.count(func.distinct(ReadingRegistration.user_id)))
        .select_from(ReadingRegistration)
        .join(
            ReadingLogEntry, ReadingLogEntry.registration_id == ReadingRegistration.id
        )
    )
    if since:
        total_query = total_query.where(ReadingLogEntry.logged_at >= since)

    total_result = await db.execute(total_query)
    total_readers = total_result.scalar() or 0

    return TopReadersResponse(
        readers=readers,
        period_days=days,
        total_readers=total_readers,
    )


@router.get("/analytics/drifting-items", response_model=DriftingItemsResponse)
@limiter.limit("15/hour")
async def get_drifting_items(
    request: Request,
    limit: int = Query(20, ge=1, le=100, description="Number of items to return"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get items in the 'drifting' zone (90-180 days since last checkout).

    Rate Limit: 15 requests per hour (multiple subqueries and complex JOIN operations)
    """


    # Calculate date thresholds
    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)
    one_eighty_days_ago = now - timedelta(days=180)

    # Subquery to get last checkout date per item
    last_checkout_subquery = (
        select(
            Checkout.item_id, func.max(Checkout.checked_out_at).label("last_checkout")
        )
        .group_by(Checkout.item_id)
        .subquery()
    )

    # Subquery to get copy counts per catalog item (batch instead of N+1)
    copy_count_subquery = (
        select(
            ItemCopy.catalog_item_id,
            func.count(ItemCopy.id).label("copy_count")
        )
        .group_by(ItemCopy.catalog_item_id)
        .subquery()
    )

    # Main query - join all data in a single query
    query = (
        select(
            CatalogItem.id,
            CatalogItem.title,
            CatalogItem.author,
            last_checkout_subquery.c.last_checkout,
            func.coalesce(copy_count_subquery.c.copy_count, 0).label("copy_count"),
        )
        .join(
            last_checkout_subquery, CatalogItem.id == last_checkout_subquery.c.item_id
        )
        .outerjoin(
            copy_count_subquery, CatalogItem.id == copy_count_subquery.c.catalog_item_id
        )
        .where(
            last_checkout_subquery.c.last_checkout >= one_eighty_days_ago,
            last_checkout_subquery.c.last_checkout < ninety_days_ago,
        )
        .order_by(last_checkout_subquery.c.last_checkout.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    drifting_data = result.all()

    items = [
        DriftingItem(
            catalog_item_id=item_id,
            title=title,
            author=author,
            days_since_checkout=(now - last_checkout).days,
            copy_count=copy_count,
        )
        for item_id, title, author, last_checkout, copy_count in drifting_data
        if last_checkout
    ]

    # Get total drifting count
    total_query = (
        select(func.count(func.distinct(last_checkout_subquery.c.item_id)))
        .select_from(last_checkout_subquery)
        .where(
            last_checkout_subquery.c.last_checkout >= one_eighty_days_ago,
            last_checkout_subquery.c.last_checkout < ninety_days_ago,
        )
    )

    total_result = await db.execute(total_query)
    total_drifting = total_result.scalar() or 0

    return DriftingItemsResponse(
        items=items,
        total_drifting=total_drifting,
    )


# ============================================================================
# Missing Analytics Endpoints
# (consumed by frontend analytics-api.ts)
# ============================================================================


@router.get("/analytics/circulation")
async def get_circulation_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days for stats"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get circulation analytics with trends."""
    from ...schemas.analytics import CirculationStats, StatsMetadata, TrendData

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_start = since - timedelta(days=days)

    # Current period counts
    total_q = select(func.count(Checkout.id)).where(Checkout.checked_out_at >= since)
    total_checkouts = (await db.execute(total_q)).scalar() or 0

    active_q = select(func.count(Checkout.id)).where(Checkout.status == CheckoutStatus.active)
    active_checkouts = (await db.execute(active_q)).scalar() or 0

    today_start = datetime.combine(date.today(), datetime.min.time())
    today_end = datetime.combine(date.today(), datetime.max.time())

    co_today_q = select(func.count(Checkout.id)).where(
        Checkout.checked_out_at >= today_start, Checkout.checked_out_at <= today_end
    )
    checkouts_today = (await db.execute(co_today_q)).scalar() or 0

    ret_today_q = select(func.count(Checkout.id)).where(
        Checkout.returned_at >= today_start, Checkout.returned_at <= today_end
    )
    returns_today = (await db.execute(ret_today_q)).scalar() or 0

    overdue_q = select(func.count(Checkout.id)).where(
        Checkout.status == CheckoutStatus.active,
        Checkout.due_date < now,
    )
    overdue_count = (await db.execute(overdue_q)).scalar() or 0

    unique_q = select(func.count(func.distinct(Checkout.user_id))).where(
        Checkout.checked_out_at >= since
    )
    unique_patrons = (await db.execute(unique_q)).scalar() or 0

    avg_daily = total_checkouts / days if days > 0 else 0

    # Turnover rate
    total_copies_q = select(func.count(ItemCopy.id))
    total_copies = (await db.execute(total_copies_q)).scalar() or 1
    turnover_rate = (total_checkouts / total_copies) * 100

    # Previous period for trends
    prev_total_q = select(func.count(Checkout.id)).where(
        Checkout.checked_out_at >= prev_start, Checkout.checked_out_at < since
    )
    prev_total = (await db.execute(prev_total_q)).scalar() or 0

    prev_overdue_q = select(func.count(Checkout.id)).where(
        Checkout.status == CheckoutStatus.active,
        Checkout.due_date < since,
    )
    prev_overdue = (await db.execute(prev_overdue_q)).scalar() or 0

    return CirculationStats(
        total_checkouts=total_checkouts,
        active_checkouts=active_checkouts,
        checkouts_today=checkouts_today,
        returns_today=returns_today,
        overdue_count=overdue_count,
        checkout_trend=TrendData.calculate(total_checkouts, prev_total),
        overdue_trend=TrendData.calculate(overdue_count, prev_overdue),
        unique_patrons=unique_patrons,
        avg_daily_checkouts=round(avg_daily, 2),
        turnover_rate=round(turnover_rate, 2),
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window=f"{days}d",
        ),
    )


@router.get("/analytics/collection-health")
async def get_collection_health(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get collection health analytics."""
    from ...schemas.analytics import CollectionHealthStats, DormancyBreakdown, StatsMetadata

    now = datetime.now(timezone.utc)
    ninety_days_ago = now - timedelta(days=90)
    one_eighty_days_ago = now - timedelta(days=180)

    # Total items and available
    total_q = select(func.count(ItemCopy.id))
    total_items = (await db.execute(total_q)).scalar() or 0

    from ...models.inventory import ItemCondition
    avail_q = select(func.count(ItemCopy.id)).where(
        ItemCopy.condition.notin_([ItemCondition.WITHDRAWN, ItemCondition.DAMAGED])
    )
    total_available = (await db.execute(avail_q)).scalar() or 0

    # Last checkout per item for dormancy
    last_co = (
        select(Checkout.item_id, func.max(Checkout.checked_out_at).label("last_co"))
        .group_by(Checkout.item_id)
        .subquery()
    )

    # Active: last checkout < 90 days ago
    active_q = (
        select(func.count(func.distinct(last_co.c.item_id)))
        .where(last_co.c.last_co >= ninety_days_ago)
    )
    active_count = (await db.execute(active_q)).scalar() or 0

    # Drifting: 90-180 days
    drifting_q = (
        select(func.count(func.distinct(last_co.c.item_id)))
        .where(last_co.c.last_co >= one_eighty_days_ago, last_co.c.last_co < ninety_days_ago)
    )
    drifting_count = (await db.execute(drifting_q)).scalar() or 0

    # Dormant: 180+ days
    dormant_q = (
        select(func.count(func.distinct(last_co.c.item_id)))
        .where(last_co.c.last_co < one_eighty_days_ago)
    )
    dormant_count = (await db.execute(dormant_q)).scalar() or 0

    total_tracked = active_count + drifting_count + dormant_count or 1

    # Utilization
    active_co_q = select(func.count(Checkout.id)).where(Checkout.status == CheckoutStatus.active)
    active_checkouts = (await db.execute(active_co_q)).scalar() or 0
    utilization = (active_checkouts / total_items * 100) if total_items > 0 else 0

    # Avg checkouts per item
    total_co_q = select(func.count(Checkout.id))
    total_checkouts = (await db.execute(total_co_q)).scalar() or 0
    avg_per_item = total_checkouts / total_items if total_items > 0 else 0

    # Never checked out
    checked_ids = select(func.distinct(Checkout.item_id)).subquery()
    never_q = select(func.count(CatalogItem.id)).where(CatalogItem.id.notin_(select(checked_ids)))
    never_checked = (await db.execute(never_q)).scalar() or 0

    # Damaged and missing
    damaged_q = select(func.count(ItemCopy.id)).where(ItemCopy.condition == ItemCondition.DAMAGED)
    damaged = (await db.execute(damaged_q)).scalar() or 0
    withdrawn_q = select(func.count(ItemCopy.id)).where(ItemCopy.condition == ItemCondition.WITHDRAWN)
    missing = (await db.execute(withdrawn_q)).scalar() or 0

    return CollectionHealthStats(
        total_items=total_items,
        total_available=total_available,
        dormancy=DormancyBreakdown(
            active_count=active_count,
            active_percentage=round(active_count / total_tracked * 100, 1),
            drifting_count=drifting_count,
            drifting_percentage=round(drifting_count / total_tracked * 100, 1),
            dormant_count=dormant_count,
            dormant_percentage=round(dormant_count / total_tracked * 100, 1),
        ),
        utilization_rate=round(utilization, 2),
        avg_checkouts_per_item=round(avg_per_item, 2),
        never_checked_out=never_checked,
        damaged_items=damaged,
        missing_items=missing,
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window="all",
        ),
    )


@router.get("/analytics/patron-engagement")
async def get_patron_engagement(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get patron engagement analytics."""
    from ...schemas.analytics import PatronEngagementStats, StatsMetadata, TrendData

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_start = since - timedelta(days=days)
    dormant_threshold = now - timedelta(days=180)

    total_q = select(func.count(User.id)).where(User.role == "patron")
    total_patrons = (await db.execute(total_q)).scalar() or 0

    active_q = select(func.count(func.distinct(Checkout.user_id))).where(
        Checkout.checked_out_at >= since
    )
    active_patrons = (await db.execute(active_q)).scalar() or 0

    new_q = select(func.count(User.id)).where(User.created_at >= since, User.role == "patron")
    new_patrons = (await db.execute(new_q)).scalar() or 0

    # Dormant: patrons whose last checkout is 180+ days ago
    last_co = (
        select(Checkout.user_id, func.max(Checkout.checked_out_at).label("last_co"))
        .group_by(Checkout.user_id)
        .subquery()
    )
    dormant_q = select(func.count(last_co.c.user_id)).where(last_co.c.last_co < dormant_threshold)
    dormant_patrons = (await db.execute(dormant_q)).scalar() or 0

    engagement_rate = (active_patrons / total_patrons * 100) if total_patrons > 0 else 0

    # Avg checkouts per active patron
    co_count_q = select(func.count(Checkout.id)).where(Checkout.checked_out_at >= since)
    total_co = (await db.execute(co_count_q)).scalar() or 0
    avg_per_patron = total_co / active_patrons if active_patrons > 0 else 0

    # Retention: patrons active in both current and previous period
    prev_active_q = select(func.distinct(Checkout.user_id)).where(
        Checkout.checked_out_at >= prev_start, Checkout.checked_out_at < since
    ).subquery()
    retained_q = select(func.count(func.distinct(Checkout.user_id))).where(
        Checkout.checked_out_at >= since,
        Checkout.user_id.in_(select(prev_active_q)),
    )
    retained = (await db.execute(retained_q)).scalar() or 0
    prev_active_count_q = select(func.count()).select_from(prev_active_q)
    prev_active_count = (await db.execute(prev_active_count_q)).scalar() or 0
    retention_rate = (retained / prev_active_count * 100) if prev_active_count > 0 else 0

    # Trends
    prev_active_total_q = select(func.count(func.distinct(Checkout.user_id))).where(
        Checkout.checked_out_at >= prev_start, Checkout.checked_out_at < since
    )
    prev_active_total = (await db.execute(prev_active_total_q)).scalar() or 0

    prev_new_q = select(func.count(User.id)).where(
        User.created_at >= prev_start, User.created_at < since, User.role == "patron"
    )
    prev_new = (await db.execute(prev_new_q)).scalar() or 0

    return PatronEngagementStats(
        total_patrons=total_patrons,
        active_patrons=active_patrons,
        new_patrons=new_patrons,
        dormant_patrons=dormant_patrons,
        engagement_rate=round(engagement_rate, 2),
        avg_checkouts_per_patron=round(avg_per_patron, 2),
        retention_rate=round(retention_rate, 2),
        engagement_trend=TrendData.calculate(active_patrons, prev_active_total),
        new_patrons_trend=TrendData.calculate(new_patrons, prev_new),
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window=f"{days}d",
        ),
    )


@router.get("/analytics/reading")
async def get_reading_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get reading analytics."""
    from ...models.reading import ReadingLogEntry, ReadingRegistration
    from ...schemas.analytics import ReadingStats, StatsMetadata, TrendData

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_start = since - timedelta(days=days)

    base = (
        select(
            func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0),
            func.coalesce(func.sum(ReadingLogEntry.books_read), 0),
            func.coalesce(func.sum(ReadingLogEntry.pages_read), 0),
            func.count(ReadingLogEntry.id),
            func.avg(ReadingLogEntry.rating),
        )
        .where(ReadingLogEntry.logged_at >= since)
    )
    row = (await db.execute(base)).one()
    total_minutes = int(row[0])
    total_books = int(row[1])
    total_pages = int(row[2])
    entry_count = int(row[3])
    avg_rating = round(float(row[4]), 2) if row[4] else None

    avg_min_session = total_minutes / entry_count if entry_count > 0 else 0
    avg_pages_session = total_pages / entry_count if entry_count > 0 else 0

    participants_q = (
        select(func.count(func.distinct(ReadingRegistration.user_id)))
        .join(ReadingLogEntry, ReadingLogEntry.registration_id == ReadingRegistration.id)
        .where(ReadingLogEntry.logged_at >= since)
    )
    total_participants = (await db.execute(participants_q)).scalar() or 0

    # Previous period for trends
    prev_base = (
        select(
            func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0),
            func.coalesce(func.sum(ReadingLogEntry.books_read), 0),
        )
        .where(ReadingLogEntry.logged_at >= prev_start, ReadingLogEntry.logged_at < since)
    )
    prev_row = (await db.execute(prev_base)).one()
    prev_minutes = int(prev_row[0])
    prev_books = int(prev_row[1])

    return ReadingStats(
        total_minutes_read=total_minutes,
        total_books_completed=total_books,
        total_pages_read=total_pages,
        total_participants=total_participants,
        avg_minutes_per_session=round(avg_min_session, 2),
        avg_pages_per_session=round(avg_pages_session, 2),
        avg_rating=avg_rating,
        minutes_trend=TrendData.calculate(total_minutes, prev_minutes),
        books_trend=TrendData.calculate(total_books, prev_books),
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window=f"{days}d",
        ),
    )


@router.get("/analytics/fines")
async def get_fine_stats(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get fine analytics."""
    from ...schemas.analytics import FineStats, StatsMetadata, TrendData

    now = datetime.now(timezone.utc)
    since = now - timedelta(days=days)
    prev_start = since - timedelta(days=days)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Outstanding
    outstanding_q = select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
        Fine.status == FineStatus.unpaid
    )
    outstanding_total = float((await db.execute(outstanding_q)).scalar() or 0)

    patrons_q = select(func.count(func.distinct(Fine.user_id))).where(
        Fine.status == FineStatus.unpaid
    )
    patrons_with_fines = (await db.execute(patrons_q)).scalar() or 0

    # Paid this month
    paid_q = select(func.coalesce(func.sum(Fine.amount_paid), 0)).where(
        Fine.paid_at >= month_start
    )
    paid_this_month = float((await db.execute(paid_q)).scalar() or 0)

    # Waived this month
    waived_q = select(func.coalesce(func.sum(Fine.amount), 0)).where(
        Fine.status == FineStatus.waived, Fine.waived_at >= month_start
    )
    waived_this_month = float((await db.execute(waived_q)).scalar() or 0)

    # Collection rate
    total_issued_q = select(func.coalesce(func.sum(Fine.amount), 0)).where(
        Fine.created_at >= since
    )
    total_issued = float((await db.execute(total_issued_q)).scalar() or 0)
    total_collected_q = select(func.coalesce(func.sum(Fine.amount_paid), 0)).where(
        Fine.created_at >= since
    )
    total_collected = float((await db.execute(total_collected_q)).scalar() or 0)
    collection_rate = (total_collected / total_issued * 100) if total_issued > 0 else 0

    # Outstanding trend
    prev_outstanding_q = select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0)).where(
        Fine.status == FineStatus.unpaid, Fine.created_at < since
    )
    prev_outstanding = float((await db.execute(prev_outstanding_q)).scalar() or 0)

    return FineStats(
        outstanding_total=round(outstanding_total, 2),
        patrons_with_fines=patrons_with_fines,
        paid_this_month=round(paid_this_month, 2),
        waived_this_month=round(waived_this_month, 2),
        collection_rate=round(collection_rate, 2),
        outstanding_trend=TrendData.calculate(outstanding_total, prev_outstanding),
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window=f"{days}d",
        ),
    )


@router.get("/analytics/dashboard")
async def get_analytics_dashboard(
    request: Request,
    days: int = Query(30, ge=1, le=365, description="Number of days"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get unified analytics dashboard (all stats combined)."""
    from ...schemas.analytics import AnalyticsDashboardResponse, StatsMetadata

    circ = await get_circulation_stats(request, days, db, current_user)
    reading = await get_reading_stats(request, days, db, current_user)
    engagement = await get_patron_engagement(request, days, db, current_user)
    health = await get_collection_health(request, db, current_user)
    fines = await get_fine_stats(request, days, db, current_user)

    now = datetime.now(timezone.utc)
    return AnalyticsDashboardResponse(
        circulation=circ,
        reading=reading,
        patron_engagement=engagement,
        collection_health=health,
        fines=fines,
        metadata=StatsMetadata(
            generated_at=now,
            cached=False,
            cache_ttl=300,
            time_window=f"{days}d",
        ),
    )
