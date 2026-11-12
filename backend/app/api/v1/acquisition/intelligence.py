# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition Intelligence API Endpoints

Provides endpoints for:
- Selection enrichment via Open Library / Google Books
- Batch auto-enrichment of pending selections
- Budget intelligence and fund spending analysis
- Vendor performance metrics and comparison
- Auto-generation of purchase orders from approved selections
- Template suggestions based on order history
- Unified acquisition dashboard
"""

from app.core.logging import get_logger
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from collections import defaultdict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.cache import get_cached, set_cached, make_cache_key
from ....core.cache_strategies import CacheTTL
from ....models.acquisition import (
    Fund, FundStatus, PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus,
    SelectionListItem, SelectionPriority, SelectionSource, Vendor, OrderTemplate,
)
from ....models.catalog import CatalogItem
from ....models.circulation import Hold, HoldStatus
from ....models.inventory import ItemCopy, ItemCondition
from ....models.user import User
from ..auth import get_current_user
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/acquisition", tags=["acquisition-intelligence"])


# =============================================================================
# Response Models
# =============================================================================


class EnrichmentData(BaseModel):
    cover_url: str | None = None
    estimated_price: float | None = None
    publisher: str | None = None
    publication_year: int | None = None
    description: str | None = None
    copies_owned: int = 0
    active_holds: int = 0
    previously_ordered: bool = False
    suggested_priority: str = "MEDIUM"
    priority_score: int = 50
    source_api: str | None = None


class EnrichmentResponse(BaseModel):
    item_id: int
    title: str
    author: str | None = None
    isbn: str | None = None
    enrichment: EnrichmentData


class BatchEnrichResponse(BaseModel):
    enriched_count: int
    skipped_count: int
    errors: list[str] = Field(default_factory=list)


class FundIntelligenceItem(BaseModel):
    fund_id: int
    fund_code: str
    fund_name: str
    fiscal_year: int
    allocated_amount: float
    spent_amount: float
    encumbered_amount: float
    available_amount: float
    spending_velocity: float
    projected_exhaustion_date: str | None = None
    months_remaining: float | None = None
    warning_level: str = "ok"
    fy2025_comparison: dict | None = None


class FundIntelligenceResponse(BaseModel):
    funds: list[FundIntelligenceItem]
    alerts: list[str] = Field(default_factory=list)
    total_allocated: float = 0.0
    total_spent: float = 0.0
    total_available: float = 0.0


class OrderHistoryItem(BaseModel):
    po_number: str
    order_date: str
    status: str
    total_amount: float
    items_ordered: int
    items_received: int
    delivery_days: int | None = None


class VendorPerformanceResponse(BaseModel):
    vendor_id: int
    vendor_name: str
    total_orders: int = 0
    total_spent: float = 0.0
    average_delivery_days: float | None = None
    fill_rate: float | None = None
    on_time_rate: float | None = None
    recent_orders: list[OrderHistoryItem] = Field(default_factory=list)


class VendorComparisonResponse(BaseModel):
    vendors: list[VendorPerformanceResponse]


class CreatedPO(BaseModel):
    po_number: str
    vendor_id: int | None = None
    vendor_name: str | None = None
    fund_id: int | None = None
    fund_name: str | None = None
    item_count: int = 0
    total_amount: float = 0.0


class AutoGeneratePOsRequest(BaseModel):
    selection_item_ids: list[int]
    default_vendor_id: int | None = None
    default_fund_id: int | None = None


class AutoGeneratePOsResponse(BaseModel):
    created_pos: list[CreatedPO]
    total_created: int = 0
    errors: list[str] = Field(default_factory=list)


class TemplateItemSuggestion(BaseModel):
    title: str
    author: str | None = None
    isbn: str | None = None
    suggested_quantity: int = 1
    order_count: int = 0


class TemplateSuggestion(BaseModel):
    name: str
    description: str
    items: list[TemplateItemSuggestion] = Field(default_factory=list)


class TemplateSuggestionsResponse(BaseModel):
    suggestions: list[TemplateSuggestion]


class FundSummary(BaseModel):
    total_allocated: float = 0.0
    total_spent: float = 0.0
    total_available: float = 0.0
    funds_with_warnings: int = 0


class SelectionSummary(BaseModel):
    total_pending: int = 0
    total_approved: int = 0
    total_ordered: int = 0


class OrderStatusCount(BaseModel):
    draft: int = 0
    pending_approval: int = 0
    approved: int = 0
    submitted: int = 0
    partially_received: int = 0
    received: int = 0


class TopVendor(BaseModel):
    vendor_id: int
    vendor_name: str
    order_count: int


class VendorSummaryData(BaseModel):
    total_active_vendors: int = 0
    top_vendors: list[TopVendor] = Field(default_factory=list)


class ReleaseSummary(BaseModel):
    upcoming_count: int = 0
    high_demand_count: int = 0


class Bottleneck(BaseModel):
    type: str
    description: str
    count: int = 0
    severity: str = "info"


class RecentAction(BaseModel):
    action: str
    description: str
    timestamp: str
    entity_type: str
    entity_id: int | None = None


class DashboardResponse(BaseModel):
    fund_summary: FundSummary
    selection_summary: SelectionSummary
    order_summary: OrderStatusCount
    vendor_summary: VendorSummaryData
    release_summary: ReleaseSummary
    bottlenecks: list[Bottleneck] = Field(default_factory=list)
    recent_activity: list[RecentAction] = Field(default_factory=list)


# =============================================================================
# Helper Functions
# =============================================================================


async def _fetch_open_library_data(isbn: str | None, title: str | None, author: str | None, client: httpx.AsyncClient | None = None) -> dict | None:
    if not isbn and not title:
        return None

    cache_key = make_cache_key("l30:acq:openlibrary", isbn=isbn or "", title=title or "", author=author or "")
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=10.0)

    try:
            if isbn:
                url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    key = f"ISBN:{isbn}"
                    if key in data:
                        book = data[key]
                        cover_url = None
                        if "cover" in book:
                            cover_url = book["cover"].get("large") or book["cover"].get("medium")
                        publishers = book.get("publishers", [])
                        publisher = publishers[0].get("name") if publishers else None
                        publish_date = book.get("publish_date", "")
                        pub_year = None
                        for part in publish_date.replace(",", " ").split():
                            if part.isdigit() and len(part) == 4:
                                pub_year = int(part)
                                break
                        subjects = book.get("subjects", [])
                        description = ", ".join(s.get("name", "") for s in subjects[:5]) if subjects else None
                        result = {
                            "cover_url": cover_url,
                            "publisher": publisher,
                            "publication_year": pub_year,
                            "description": description,
                            "source_api": "open_library",
                        }
                        await set_cached(cache_key, result, CacheTTL.DAILY)
                        return result

            if title:
                query = title
                if author:
                    query = f"{title} {author}"
                search_url = f"https://openlibrary.org/search.json?q={query}&limit=1"
                resp = await client.get(search_url)
                if resp.status_code == 200:
                    data = resp.json()
                    docs = data.get("docs", [])
                    if docs:
                        doc = docs[0]
                        cover_id = doc.get("cover_i")
                        cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" if cover_id else None
                        publishers = doc.get("publisher", [])
                        publisher = publishers[0] if publishers else None
                        pub_year = doc.get("first_publish_year")
                        result = {
                            "cover_url": cover_url,
                            "publisher": publisher,
                            "publication_year": pub_year,
                            "description": None,
                            "source_api": "open_library",
                        }
                        await set_cached(cache_key, result, CacheTTL.DAILY)
                        return result
    except httpx.TimeoutException:
        logger.warning("Open Library API timeout for isbn=%s title=%s", isbn, title)
    except Exception:
        logger.exception("Open Library API error for isbn=%s title=%s", isbn, title)
    finally:
        if owns_client:
            await client.aclose()

    return None


async def _fetch_google_books_price(isbn: str | None, title: str | None, author: str | None, client: httpx.AsyncClient | None = None) -> float | None:
    if not isbn and not title:
        return None

    cache_key = make_cache_key("l30:acq:googlebooks", isbn=isbn or "", title=title or "", author=author or "")
    cached = await get_cached(cache_key)
    if cached is not None:
        return cached

    owns_client = client is None
    if owns_client:
        client = httpx.AsyncClient(timeout=10.0)

    try:
            if isbn:
                query = f"isbn:{isbn}"
            else:
                query = title or ""
                if author:
                    query = f"{query}+inauthor:{author}"

            url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("items", [])
                if items:
                    sale_info = items[0].get("saleInfo", {})
                    list_price = sale_info.get("listPrice")
                    if list_price:
                        price = float(list_price.get("amount", 0))
                        await set_cached(cache_key, price, CacheTTL.DAILY)
                        return price
                    retail_price = sale_info.get("retailPrice")
                    if retail_price:
                        price = float(retail_price.get("amount", 0))
                        await set_cached(cache_key, price, CacheTTL.DAILY)
                        return price
    except httpx.TimeoutException:
        logger.warning("Google Books API timeout for isbn=%s title=%s", isbn, title)
    except Exception:
        logger.exception("Google Books API error for isbn=%s title=%s", isbn, title)
    finally:
        if owns_client:
            await client.aclose()

    return None


def _calculate_priority_score(
    active_holds: int,
    copies_owned: int,
    source: str | None,
    purchase_request_id: int | None,
) -> tuple[int, str]:
    score = 50

    holds_per_copy = active_holds / max(copies_owned, 1)
    if holds_per_copy >= 3:
        score += 20

    if copies_owned == 0:
        score += 15

    if source == SelectionSource.MANUAL.value or source == SelectionSource.MANUAL:
        if purchase_request_id is not None:
            score += 10

    if copies_owned > 0 and holds_per_copy < 1:
        score -= 10

    score = max(0, min(100, score))

    if score >= 70:
        label = "HIGH"
    elif score >= 40:
        label = "MEDIUM"
    else:
        label = "LOW"

    return score, label


def _generate_po_number() -> str:
    import uuid
    return f"PO-{datetime.now(timezone.utc).strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"


# =============================================================================
# Endpoints
# =============================================================================


@router.post(
    "/selection-list/{item_id}/enrich",
    response_model=EnrichmentResponse,
)
async def enrich_selection_item(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enrich a selection list item with data from Open Library and Google Books.

    Looks up the item by ISBN or title+author, enriches with cover URL,
    estimated price, publisher, publication year, and description.
    Also checks library holdings, hold demand, and prior orders.
    Returns an auto-suggested priority based on demand analysis.
    """
    await require_staff(current_user)

    result = await db.execute(
        select(SelectionListItem).where(SelectionListItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Selection list item not found",
        )

    logger.info("Enriching selection item %s (isbn=%s, title=%s)", item_id, item.isbn, item.title)

    # Fetch enrichment data from external APIs
    ol_data = await _fetch_open_library_data(item.isbn, item.title, item.author)
    estimated_price = await _fetch_google_books_price(item.isbn, item.title, item.author)

    # Count copies owned in catalog
    copies_query = select(func.count(ItemCopy.id)).join(
        CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id
    )
    if item.isbn:
        copies_query = copies_query.where(CatalogItem.isbn == item.isbn)
    else:
        copies_query = copies_query.where(
            and_(
                func.lower(CatalogItem.title) == func.lower(item.title),
                or_(
                    CatalogItem.author.is_(None),
                    func.lower(CatalogItem.author) == func.lower(item.author or ""),
                ),
            )
        )
    copies_query = copies_query.where(
        ItemCopy.condition != ItemCondition.WITHDRAWN
    )
    copies_result = await db.execute(copies_query)
    copies_owned = copies_result.scalar() or 0

    # Count active holds
    holds_query = select(func.count(Hold.id)).join(
        CatalogItem, Hold.item_id == CatalogItem.id
    )
    if item.isbn:
        holds_query = holds_query.where(CatalogItem.isbn == item.isbn)
    else:
        holds_query = holds_query.where(
            func.lower(CatalogItem.title) == func.lower(item.title)
        )
    holds_query = holds_query.where(
        Hold.status.in_([HoldStatus.pending, HoldStatus.ready])
    )
    holds_result = await db.execute(holds_query)
    active_holds = holds_result.scalar() or 0

    # Check if previously ordered
    prev_order_query = select(func.count(PurchaseOrderItem.id))
    if item.isbn:
        prev_order_query = prev_order_query.where(PurchaseOrderItem.isbn == item.isbn)
    else:
        prev_order_query = prev_order_query.where(
            func.lower(PurchaseOrderItem.title) == func.lower(item.title)
        )
    prev_result = await db.execute(prev_order_query)
    previously_ordered = (prev_result.scalar() or 0) > 0

    # Calculate priority
    priority_score, suggested_priority = _calculate_priority_score(
        active_holds=active_holds,
        copies_owned=copies_owned,
        source=item.source,
        purchase_request_id=item.purchase_request_id,
    )

    # Build enrichment data
    enrichment = EnrichmentData(
        cover_url=(ol_data or {}).get("cover_url"),
        estimated_price=estimated_price,
        publisher=(ol_data or {}).get("publisher"),
        publication_year=(ol_data or {}).get("publication_year"),
        description=(ol_data or {}).get("description"),
        copies_owned=copies_owned,
        active_holds=active_holds,
        previously_ordered=previously_ordered,
        suggested_priority=suggested_priority,
        priority_score=priority_score,
        source_api=(ol_data or {}).get("source_api"),
    )

    # Update the selection item with enrichment data
    if enrichment.cover_url and not item.cover_url:
        item.cover_url = enrichment.cover_url
    if enrichment.estimated_price and not item.estimated_price:
        item.estimated_price = Decimal(str(enrichment.estimated_price))

    await db.commit()

    logger.info("Enriched selection item %s with priority_score=%s", item_id, priority_score)

    return EnrichmentResponse(
        item_id=item.id,
        title=item.title,
        author=item.author,
        isbn=item.isbn,
        enrichment=enrichment,
    )


@router.post(
    "/selection-list/auto-enrich",
    response_model=BatchEnrichResponse,
)
async def batch_auto_enrich(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Batch enrich all pending selection items that haven't been enriched yet.

    Processes items where source is 'manual' and cover_url is null,
    up to 20 items at a time.
    """
    await require_staff(current_user)

    result = await db.execute(
        select(SelectionListItem)
        .where(
            SelectionListItem.source == SelectionSource.MANUAL,
            SelectionListItem.cover_url.is_(None),
            SelectionListItem.status == "pending",
        )
        .limit(20)
    )
    items = result.scalars().all()

    if not items:
        return BatchEnrichResponse(enriched_count=0, skipped_count=0)

    logger.info("Auto-enriching %s selection items", len(items))

    enriched_count = 0
    skipped_count = 0
    errors: list[str] = []

    async with httpx.AsyncClient(timeout=10.0) as http_client:
        for item in items:
            if item.cover_url and item.estimated_price:
                skipped_count += 1
                continue
            try:
                ol_data = await _fetch_open_library_data(item.isbn, item.title, item.author, client=http_client)
                estimated_price = await _fetch_google_books_price(item.isbn, item.title, item.author, client=http_client)

                if ol_data or estimated_price:
                    if ol_data:
                        if ol_data.get("cover_url") and not item.cover_url:
                            item.cover_url = ol_data["cover_url"]
                    if estimated_price and not item.estimated_price:
                        item.estimated_price = Decimal(str(estimated_price))
                    enriched_count += 1
                else:
                    skipped_count += 1
            except Exception:
                logger.exception("Failed to enrich item %s", item.id)
                errors.append(f"Failed to enrich item {item.id}: {item.title}")
                skipped_count += 1

    await db.flush()

    logger.info("Auto-enrich complete: enriched=%s skipped=%s errors=%s", enriched_count, skipped_count, len(errors))

    return BatchEnrichResponse(
        enriched_count=enriched_count,
        skipped_count=skipped_count,
        errors=errors,
    )


@router.get(
    "/funds/intelligence",
    response_model=FundIntelligenceResponse,
)
async def fund_intelligence(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Budget intelligence for all active FY2026 funds.

    Calculates spending velocity, projected exhaustion dates, and warning
    levels. Also provides FY2025 vs FY2026 comparison where applicable.
    """
    await require_staff(current_user)

    # FY2026 started Oct 1, 2025
    fy_start = datetime(2025, 10, 1, tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    months_elapsed = (now.year - fy_start.year) * 12 + (now.month - fy_start.month)
    months_elapsed += (now.day - fy_start.day) / 30.0
    months_elapsed = max(months_elapsed, 0.1)  # avoid division by zero

    # Get active FY2026 funds
    result_2026 = await db.execute(
        select(Fund).where(
            Fund.fiscal_year == 2026,
            Fund.status == FundStatus.ACTIVE,
        )
    )
    funds_2026 = result_2026.scalars().all()

    # Get FY2025 funds for comparison
    result_2025 = await db.execute(
        select(Fund).where(Fund.fiscal_year == 2025)
    )
    funds_2025 = result_2025.scalars().all()
    fy2025_by_code = {}
    for f in funds_2025:
        base_code = f.code.split("-FY")[0] if "-FY" in f.code else f.code
        fy2025_by_code[base_code] = f

    fund_items: list[FundIntelligenceItem] = []
    alerts: list[str] = []
    total_allocated = Decimal("0")
    total_spent = Decimal("0")
    total_available = Decimal("0")

    for fund in funds_2026:
        allocated = Decimal(str(fund.allocated_amount or 0))
        spent = Decimal(str(fund.spent_amount or 0))
        encumbered = Decimal(str(fund.encumbered_amount or 0))
        available = allocated - spent - encumbered

        total_allocated += allocated
        total_spent += spent
        total_available += available

        # Spending velocity (per month)
        velocity = float(spent) / months_elapsed if months_elapsed > 0 else 0.0

        # Projected exhaustion
        projected_exhaustion_date = None
        months_remaining = None
        warning_level = "ok"

        if velocity > 0:
            remaining_budget = float(available)
            months_left = remaining_budget / velocity if velocity > 0 else None
            if months_left is not None:
                months_remaining = round(months_left, 1)
                exhaustion_date = now + timedelta(days=months_left * 30.44)
                projected_exhaustion_date = exhaustion_date.strftime("%Y-%m-%d")

                if months_left < 0:
                    warning_level = "critical"
                elif months_left < 1:
                    warning_level = "critical"
                elif months_left < 3:
                    warning_level = "warning"
        elif float(available) <= 0:
            warning_level = "critical"
            months_remaining = 0.0

        # FY2025 comparison
        base_code = fund.code.split("-FY")[0] if "-FY" in fund.code else fund.code
        fy2025_fund = fy2025_by_code.get(base_code)
        fy2025_comparison = None
        if fy2025_fund:
            fy2025_comparison = {
                "fy2025_allocated": float(fy2025_fund.allocated_amount or 0),
                "fy2025_spent": float(fy2025_fund.spent_amount or 0),
                "allocation_change_pct": round(
                    (float(allocated) - float(fy2025_fund.allocated_amount or 1))
                    / float(fy2025_fund.allocated_amount or 1) * 100,
                    1,
                ),
                "spending_change_pct": round(
                    (float(spent) - float(fy2025_fund.spent_amount or 1))
                    / float(fy2025_fund.spent_amount or 1) * 100,
                    1,
                ) if float(fy2025_fund.spent_amount or 0) > 0 else None,
            }

        fund_item = FundIntelligenceItem(
            fund_id=fund.id,
            fund_code=fund.code,
            fund_name=fund.name,
            fiscal_year=fund.fiscal_year,
            allocated_amount=float(allocated),
            spent_amount=float(spent),
            encumbered_amount=float(encumbered),
            available_amount=float(available),
            spending_velocity=round(velocity, 2),
            projected_exhaustion_date=projected_exhaustion_date,
            months_remaining=months_remaining,
            warning_level=warning_level,
            fy2025_comparison=fy2025_comparison,
        )
        fund_items.append(fund_item)

        if warning_level == "critical":
            alerts.append(f"CRITICAL: Fund '{fund.name}' ({fund.code}) is at critical budget level")
        elif warning_level == "warning":
            alerts.append(f"WARNING: Fund '{fund.name}' ({fund.code}) has less than 3 months of budget remaining")

    logger.info("Fund intelligence calculated for %s funds, %s alerts", len(fund_items), len(alerts))

    return FundIntelligenceResponse(
        funds=fund_items,
        alerts=alerts,
        total_allocated=float(total_allocated),
        total_spent=float(total_spent),
        total_available=float(total_available),
    )


async def _compute_vendor_performance(
    vendor: Vendor,
    db: AsyncSession,
) -> VendorPerformanceResponse:
    # Get all POs for this vendor
    po_result = await db.execute(
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.items))
        .where(PurchaseOrder.vendor_id == vendor.id)
        .order_by(PurchaseOrder.order_date.desc())
    )
    all_orders = po_result.scalars().all()

    total_orders = len(all_orders)
    total_spent = sum(float(po.total_amount or 0) for po in all_orders)

    # Delivery days for received orders
    delivery_days_list: list[int] = []
    on_time_count = 0
    received_with_expected = 0

    for po in all_orders:
        if po.actual_delivery and po.order_date:
            delta = po.actual_delivery - po.order_date
            delivery_days_list.append(delta.days)

            if po.expected_delivery:
                received_with_expected += 1
                if po.actual_delivery <= po.expected_delivery:
                    on_time_count += 1

    average_delivery_days = None
    if delivery_days_list:
        average_delivery_days = round(sum(delivery_days_list) / len(delivery_days_list), 1)

    # Fill rate: received items / ordered items across all POs
    total_ordered_qty = 0
    total_received_qty = 0
    for po in all_orders:
        for po_item in (po.items or []):
            total_ordered_qty += po_item.quantity or 0
            total_received_qty += po_item.received_quantity or 0

    fill_rate = None
    if total_ordered_qty > 0:
        fill_rate = round(total_received_qty / total_ordered_qty, 4)

    on_time_rate = None
    if received_with_expected > 0:
        on_time_rate = round(on_time_count / received_with_expected, 4)

    # Recent orders (last 10)
    recent_orders: list[OrderHistoryItem] = []
    for po in all_orders[:10]:
        items_ordered = sum((it.quantity or 0) for it in (po.items or []))
        items_received = sum((it.received_quantity or 0) for it in (po.items or []))
        delivery_days = None
        if po.actual_delivery and po.order_date:
            delivery_days = (po.actual_delivery - po.order_date).days

        recent_orders.append(OrderHistoryItem(
            po_number=po.po_number,
            order_date=po.order_date.isoformat() if po.order_date else "",
            status=str(po.status) if po.status else "",
            total_amount=float(po.total_amount or 0),
            items_ordered=items_ordered,
            items_received=items_received,
            delivery_days=delivery_days,
        ))

    return VendorPerformanceResponse(
        vendor_id=vendor.id,
        vendor_name=vendor.name,
        total_orders=total_orders,
        total_spent=round(total_spent, 2),
        average_delivery_days=average_delivery_days,
        fill_rate=fill_rate,
        on_time_rate=on_time_rate,
        recent_orders=recent_orders,
    )


@router.get(
    "/vendors/{vendor_id}/performance",
    response_model=VendorPerformanceResponse,
)
async def vendor_performance(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get performance metrics for a specific vendor.

    Calculates total orders, total spent, average delivery days, fill rate,
    and on-time delivery rate from PurchaseOrder data.
    """
    await require_staff(current_user)

    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found",
        )

    logger.info("Computing performance metrics for vendor %s", vendor_id)
    return await _compute_vendor_performance(vendor, db)


@router.get(
    "/vendors/compare",
    response_model=VendorComparisonResponse,
)
async def vendor_comparison(
    vendor_ids: str = Query(..., description="Comma-separated list of vendor IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Compare performance metrics for multiple vendors side by side."""
    await require_staff(current_user)

    try:
        id_list = [int(vid.strip()) for vid in vendor_ids.split(",") if vid.strip()]
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vendor_ids must be a comma-separated list of integers",
        ) from None

    if not id_list:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one vendor ID is required",
        )

    if len(id_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot compare more than 10 vendors at once",
        )

    result = await db.execute(
        select(Vendor).where(Vendor.id.in_(id_list))
    )
    vendors = result.scalars().all()

    if not vendors:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No vendors found for the provided IDs",
        )

    logger.info("Comparing %s vendors: %s", len(vendors), id_list)

    performances: list[VendorPerformanceResponse] = []
    for vendor in vendors:
        perf = await _compute_vendor_performance(vendor, db)
        performances.append(perf)

    return VendorComparisonResponse(vendors=performances)


@router.post(
    "/selection-list/auto-generate-pos",
    response_model=AutoGeneratePOsResponse,
)
async def auto_generate_pos(
    request: AutoGeneratePOsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-generate draft purchase orders from approved selection items.

    Groups approved selection items by suggested vendor (or default vendor
    if provided) and fund, creating one draft PO per vendor+fund combination.
    """
    await require_staff(current_user)

    if not request.selection_item_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No selection item IDs provided",
        )

    # Fetch all requested selection items
    result = await db.execute(
        select(SelectionListItem).where(
            SelectionListItem.id.in_(request.selection_item_ids),
            SelectionListItem.status == "approved",
        )
    )
    items = result.scalars().all()

    if not items:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No approved selection items found for the provided IDs",
        )

    logger.info("Auto-generating POs for %s approved selection items", len(items))

    # Resolve default vendor and fund
    default_vendor = None
    if request.default_vendor_id:
        v_result = await db.execute(
            select(Vendor).where(Vendor.id == request.default_vendor_id)
        )
        default_vendor = v_result.scalar_one_or_none()
        if not default_vendor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default vendor not found",
            )

    default_fund = None
    if request.default_fund_id:
        f_result = await db.execute(
            select(Fund).where(
                Fund.id == request.default_fund_id,
                Fund.status == FundStatus.ACTIVE,
            )
        )
        default_fund = f_result.scalar_one_or_none()
        if not default_fund:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default fund not found or not active",
            )

    # If no default fund, find the first active FY2026 fund
    if not default_fund:
        f_result = await db.execute(
            select(Fund).where(
                Fund.fiscal_year == 2026,
                Fund.status == FundStatus.ACTIVE,
            ).limit(1)
        )
        default_fund = f_result.scalar_one_or_none()

    # Group items by vendor+fund
    # For now, all items go to default vendor + default fund since selection items
    # don't have a vendor field. In a real system, vendor matching could be based
    # on ISBN prefix, publisher, or past order history.
    groups: dict[tuple[int | None, int | None], list[SelectionListItem]] = defaultdict(list)

    vendor_id = default_vendor.id if default_vendor else None
    fund_id = default_fund.id if default_fund else None

    for item in items:
        groups[(vendor_id, fund_id)].append(item)

    created_pos: list[CreatedPO] = []
    errors: list[str] = []

    for (v_id, f_id), group_items in groups.items():
        try:
            po_number = _generate_po_number()

            # Ensure uniqueness by checking the DB
            existing = await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.po_number == po_number)
            )
            if existing.scalar_one_or_none():
                po_number = f"{po_number}-{len(created_pos) + 1}"

            po = PurchaseOrder(
                po_number=po_number,
                vendor_id=v_id,
                fund_id=f_id,
                status=PurchaseOrderStatus.DRAFT,
                created_by_id=current_user.id,
                total_amount=Decimal("0"),
            )
            db.add(po)
            await db.flush()  # Get the PO id

            total_amount = Decimal("0")
            for sel_item in group_items:
                unit_price = sel_item.estimated_price or Decimal("0")
                po_item = PurchaseOrderItem(
                    purchase_order_id=po.id,
                    title=sel_item.title,
                    author=sel_item.author,
                    isbn=sel_item.isbn,
                    quantity=1,
                    unit_price=unit_price,
                )
                db.add(po_item)
                total_amount += unit_price

                # Mark selection item as ordered
                sel_item.status = "ordered"

            po.total_amount = total_amount

            vendor_name = None
            if v_id and default_vendor:
                vendor_name = default_vendor.name
            fund_name = None
            if f_id and default_fund:
                fund_name = default_fund.name

            created_pos.append(CreatedPO(
                po_number=po_number,
                vendor_id=v_id,
                vendor_name=vendor_name,
                fund_id=f_id,
                fund_name=fund_name,
                item_count=len(group_items),
                total_amount=float(total_amount),
            ))

        except Exception:
            logger.exception("Failed to create PO for vendor=%s fund=%s", v_id, f_id)
            errors.append(f"Failed to create PO for vendor_id={v_id}, fund_id={f_id}")

    await db.commit()

    logger.info("Auto-generated %s POs from %s selection items", len(created_pos), len(items))

    return AutoGeneratePOsResponse(
        created_pos=created_pos,
        total_created=len(created_pos),
        errors=errors,
    )


@router.get(
    "/templates/suggestions",
    response_model=TemplateSuggestionsResponse,
)
async def template_suggestions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Suggest order templates based on past order patterns.

    Analyzes the most commonly ordered titles/ISBNs in the last 6 months and
    suggests templates for monthly fiction/non-fiction restocks and seasonal orders.
    """
    await require_staff(current_user)

    six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)

    # Find most commonly ordered items in the last 6 months
    freq_result = await db.execute(
        select(
            PurchaseOrderItem.title,
            PurchaseOrderItem.author,
            PurchaseOrderItem.isbn,
            func.count(PurchaseOrderItem.id).label("order_count"),
            func.sum(PurchaseOrderItem.quantity).label("total_qty"),
        )
        .join(PurchaseOrder, PurchaseOrderItem.purchase_order_id == PurchaseOrder.id)
        .where(PurchaseOrder.order_date >= six_months_ago.date())
        .group_by(
            PurchaseOrderItem.title,
            PurchaseOrderItem.author,
            PurchaseOrderItem.isbn,
        )
        .order_by(func.count(PurchaseOrderItem.id).desc())
        .limit(50)
    )
    frequent_items = freq_result.all()

    if not frequent_items:
        return TemplateSuggestionsResponse(suggestions=[])

    # Categorize items based on catalog data
    fiction_items: list[TemplateItemSuggestion] = []
    non_fiction_items: list[TemplateItemSuggestion] = []
    all_items: list[TemplateItemSuggestion] = []

    for row in frequent_items:
        title = row[0]
        author = row[1]
        isbn = row[2]
        order_count = row[3]
        total_qty = row[4] or 0

        suggestion = TemplateItemSuggestion(
            title=title,
            author=author,
            isbn=isbn,
            suggested_quantity=max(1, int(total_qty / max(order_count, 1))),
            order_count=order_count,
        )
        all_items.append(suggestion)

        # Try to determine fiction vs non-fiction from catalog subjects
        if isbn:
            cat_result = await db.execute(
                select(CatalogItem.subjects).where(CatalogItem.isbn == isbn).limit(1)
            )
            cat_row = cat_result.scalar_one_or_none()
            subjects_lower = (cat_row or "").lower() if cat_row else ""
            if "fiction" in subjects_lower or "novel" in subjects_lower:
                fiction_items.append(suggestion)
            elif subjects_lower:
                non_fiction_items.append(suggestion)
            else:
                fiction_items.append(suggestion)
        else:
            fiction_items.append(suggestion)

    suggestions: list[TemplateSuggestion] = []

    if fiction_items:
        suggestions.append(TemplateSuggestion(
            name="Monthly Fiction Restock",
            description="Frequently ordered fiction titles based on the last 6 months of order history",
            items=fiction_items[:15],
        ))

    if non_fiction_items:
        suggestions.append(TemplateSuggestion(
            name="Monthly Non-Fiction Restock",
            description="Frequently ordered non-fiction titles based on the last 6 months of order history",
            items=non_fiction_items[:15],
        ))

    # Seasonal template: determine current season
    now = datetime.now(timezone.utc)
    month = now.month
    if month in (3, 4, 5):
        season_name = "Spring"
    elif month in (6, 7, 8):
        season_name = "Summer"
    elif month in (9, 10, 11):
        season_name = "Fall"
    else:
        season_name = "Winter"

    if all_items:
        suggestions.append(TemplateSuggestion(
            name=f"{season_name} {now.year} Seasonal Order",
            description=f"Top ordered titles for {season_name} {now.year} based on recent demand patterns",
            items=all_items[:20],
        ))

    logger.info("Generated %s template suggestions from %s frequent items", len(suggestions), len(frequent_items))

    return TemplateSuggestionsResponse(suggestions=suggestions)


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
)
async def acquisition_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Unified acquisition dashboard with summary data across all tabs.

    Returns fund summaries, selection counts, order status breakdown,
    vendor summaries, release info, bottlenecks, and recent activity.
    """
    await require_staff(current_user)

    now = datetime.now(timezone.utc)

    # ---- Fund Summary ----
    fund_result = await db.execute(
        select(
            func.sum(Fund.allocated_amount),
            func.sum(Fund.spent_amount),
            func.sum(Fund.allocated_amount - Fund.spent_amount - Fund.encumbered_amount),
        ).where(
            Fund.fiscal_year == 2026,
            Fund.status == FundStatus.ACTIVE,
        )
    )
    fund_row = fund_result.one()
    total_allocated = float(fund_row[0] or 0)
    total_spent = float(fund_row[1] or 0)
    total_available = float(fund_row[2] or 0)

    # Count funds with warnings (available < 25% of allocated)
    warning_fund_result = await db.execute(
        select(func.count(Fund.id)).where(
            Fund.fiscal_year == 2026,
            Fund.status == FundStatus.ACTIVE,
            (Fund.allocated_amount - Fund.spent_amount - Fund.encumbered_amount)
            < (Fund.allocated_amount * Decimal("0.25")),
            Fund.allocated_amount > 0,
        )
    )
    funds_with_warnings = warning_fund_result.scalar() or 0

    fund_summary = FundSummary(
        total_allocated=total_allocated,
        total_spent=total_spent,
        total_available=total_available,
        funds_with_warnings=funds_with_warnings,
    )

    # ---- Selection Summary ----
    sel_pending_result = await db.execute(
        select(func.count(SelectionListItem.id)).where(
            SelectionListItem.status == "pending"
        )
    )
    sel_approved_result = await db.execute(
        select(func.count(SelectionListItem.id)).where(
            SelectionListItem.status == "approved"
        )
    )
    sel_ordered_result = await db.execute(
        select(func.count(SelectionListItem.id)).where(
            SelectionListItem.status == "ordered"
        )
    )

    selection_summary = SelectionSummary(
        total_pending=sel_pending_result.scalar() or 0,
        total_approved=sel_approved_result.scalar() or 0,
        total_ordered=sel_ordered_result.scalar() or 0,
    )

    # ---- Order Summary ----
    order_counts: dict[str, int] = {}
    for po_status in [
        PurchaseOrderStatus.DRAFT,
        PurchaseOrderStatus.PENDING_APPROVAL,
        PurchaseOrderStatus.APPROVED,
        PurchaseOrderStatus.SUBMITTED,
        PurchaseOrderStatus.PARTIALLY_RECEIVED,
        PurchaseOrderStatus.RECEIVED,
    ]:
        count_result = await db.execute(
            select(func.count(PurchaseOrder.id)).where(
                PurchaseOrder.status == po_status
            )
        )
        order_counts[po_status.value] = count_result.scalar() or 0

    order_summary = OrderStatusCount(
        draft=order_counts.get("draft", 0),
        pending_approval=order_counts.get("pending_approval", 0),
        approved=order_counts.get("approved", 0),
        submitted=order_counts.get("submitted", 0),
        partially_received=order_counts.get("partially_received", 0),
        received=order_counts.get("received", 0),
    )

    # ---- Vendor Summary ----
    active_vendor_result = await db.execute(
        select(func.count(Vendor.id)).where(Vendor.is_active.is_(True))
    )
    total_active_vendors = active_vendor_result.scalar() or 0

    top_vendor_result = await db.execute(
        select(
            Vendor.id,
            Vendor.name,
            func.count(PurchaseOrder.id).label("order_count"),
        )
        .join(PurchaseOrder, PurchaseOrder.vendor_id == Vendor.id)
        .where(Vendor.is_active.is_(True))
        .group_by(Vendor.id, Vendor.name)
        .order_by(func.count(PurchaseOrder.id).desc())
        .limit(5)
    )
    top_vendors = [
        TopVendor(vendor_id=row[0], vendor_name=row[1], order_count=row[2])
        for row in top_vendor_result.all()
    ]

    vendor_summary = VendorSummaryData(
        total_active_vendors=total_active_vendors,
        top_vendors=top_vendors,
    )

    # ---- Release Summary ----
    # Try to import TrackerBook if available; gracefully handle if not
    release_summary = ReleaseSummary(upcoming_count=0, high_demand_count=0)
    try:
        from ....models.release_tracker import TrackerBook, UserFollow

        upcoming_result = await db.execute(
            select(func.count(TrackerBook.id)).where(
                TrackerBook.release_date > now.date(),
                TrackerBook.release_date <= (now + timedelta(days=90)).date(),
            )
        )
        release_summary.upcoming_count = upcoming_result.scalar() or 0

        # High demand: books with >= 3 followers
        high_demand_result = await db.execute(
            select(func.count(func.distinct(TrackerBook.id)))
            .join(UserFollow, UserFollow.tracker_book_id == TrackerBook.id)
            .where(
                TrackerBook.release_date > now.date(),
            )
            .group_by(TrackerBook.id)
            .having(func.count(UserFollow.id) >= 3)
        )
        high_demand_rows = high_demand_result.all()
        release_summary.high_demand_count = len(high_demand_rows)
    except Exception:  # noqa: BLE001  # release tracker models optional — degrade gracefully
        logger.debug("Release tracker models not available for dashboard")

    # ---- Bottlenecks ----
    bottlenecks: list[Bottleneck] = []

    # Orders pending approval > 2 weeks
    two_weeks_ago = now - timedelta(weeks=2)
    stale_approval_result = await db.execute(
        select(func.count(PurchaseOrder.id)).where(
            PurchaseOrder.status == PurchaseOrderStatus.PENDING_APPROVAL,
            PurchaseOrder.created_at < two_weeks_ago,
        )
    )
    stale_approvals = stale_approval_result.scalar() or 0
    if stale_approvals > 0:
        bottlenecks.append(Bottleneck(
            type="stale_approvals",
            description=f"{stale_approvals} purchase order(s) pending approval for over 2 weeks",
            count=stale_approvals,
            severity="warning",
        ))

    # Low-budget funds
    if funds_with_warnings > 0:
        bottlenecks.append(Bottleneck(
            type="low_budget",
            description=f"{funds_with_warnings} fund(s) below 25% of allocated budget",
            count=funds_with_warnings,
            severity="warning" if funds_with_warnings < 3 else "critical",
        ))

    # Stale selections (pending > 30 days)
    thirty_days_ago = now - timedelta(days=30)
    stale_sel_result = await db.execute(
        select(func.count(SelectionListItem.id)).where(
            SelectionListItem.status == "pending",
            SelectionListItem.created_at < thirty_days_ago,
        )
    )
    stale_selections = stale_sel_result.scalar() or 0
    if stale_selections > 0:
        bottlenecks.append(Bottleneck(
            type="stale_selections",
            description=f"{stale_selections} selection item(s) pending for over 30 days",
            count=stale_selections,
            severity="info",
        ))

    # ---- Recent Activity ----
    recent_activity: list[RecentAction] = []

    # Recent POs created
    recent_pos_result = await db.execute(
        select(PurchaseOrder)
        .order_by(PurchaseOrder.created_at.desc())
        .limit(5)
    )
    recent_pos = recent_pos_result.scalars().all()
    for po in recent_pos:
        recent_activity.append(RecentAction(
            action="order_created",
            description=f"PO {po.po_number} created ({po.status})",
            timestamp=po.created_at.isoformat() if po.created_at else "",
            entity_type="purchase_order",
            entity_id=po.id,
        ))

    # Recent items received (POs with actual_delivery in last 30 days)
    recent_received_result = await db.execute(
        select(PurchaseOrder)
        .where(
            PurchaseOrder.actual_delivery.isnot(None),
            PurchaseOrder.status.in_([
                PurchaseOrderStatus.RECEIVED,
                PurchaseOrderStatus.PARTIALLY_RECEIVED,
            ]),
        )
        .order_by(PurchaseOrder.actual_delivery.desc())
        .limit(5)
    )
    recent_received = recent_received_result.scalars().all()
    for po in recent_received:
        recent_activity.append(RecentAction(
            action="items_received",
            description=f"PO {po.po_number} received",
            timestamp=po.actual_delivery.isoformat() if po.actual_delivery else "",
            entity_type="purchase_order",
            entity_id=po.id,
        ))

    # Sort all recent activity by timestamp descending
    recent_activity.sort(key=lambda x: x.timestamp, reverse=True)
    recent_activity = recent_activity[:10]

    logger.info("Dashboard data assembled for user %s", current_user.id)

    return DashboardResponse(
        fund_summary=fund_summary,
        selection_summary=selection_summary,
        order_summary=order_summary,
        vendor_summary=vendor_summary,
        release_summary=release_summary,
        bottlenecks=bottlenecks,
        recent_activity=recent_activity,
    )
