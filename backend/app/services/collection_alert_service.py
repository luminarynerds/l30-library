# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from sqlalchemy import and_, case, func, literal, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.catalog import CatalogItem, ItemStatus
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.inventory import ItemCopy, ItemCondition
from ..models.collection_alert import CollectionAlert, AlertType, CollectionAlertStatus, CollectionAlertSeverity


@dataclass
class ItemMetrics:
    available_copies: int
    available_at_location: int
    total_copies: int
    pending_holds: int
    last_checkout_date: Optional[datetime]


async def get_item_metrics(
    db: AsyncSession,
    catalog_item_id: int,
    location: Optional[str] = None,
) -> ItemMetrics:
    available_filter = ItemCopy.condition.notin_([ItemCondition.WITHDRAWN, ItemCondition.DAMAGED])

    location_case = (
        func.count(
            case(
                (and_(available_filter, ItemCopy.location == location), ItemCopy.id),
            )
        )
        if location
        else literal(0)
    )

    copies_sub = (
        select(
            func.count(case((available_filter, ItemCopy.id))).label("available"),
            location_case.label("available_at_location"),
            func.count(ItemCopy.id).label("total"),
        )
        .where(ItemCopy.catalog_item_id == catalog_item_id)
        .subquery()
    )

    holds_sub = (
        select(func.count(Hold.id).label("pending"))
        .where(Hold.item_id == catalog_item_id, Hold.status == HoldStatus.pending)
        .subquery()
    )

    last_co_sub = (
        select(func.max(Checkout.checked_out_at).label("last_co"))
        .where(
            Checkout.item_id == catalog_item_id,
            Checkout.status.in_([
                CheckoutStatus.returned,
                CheckoutStatus.returned_damaged,
                CheckoutStatus.claims_returned,
            ]),
        )
        .subquery()
    )

    combined = select(
        copies_sub.c.available,
        copies_sub.c.available_at_location,
        copies_sub.c.total,
        holds_sub.c.pending,
        last_co_sub.c.last_co,
    )

    row = (await db.execute(combined)).one()
    return ItemMetrics(
        available_copies=row.available or 0,
        available_at_location=row.available_at_location or 0,
        total_copies=row.total or 0,
        pending_holds=row.pending or 0,
        last_checkout_date=row.last_co,
    )


async def get_existing_alert_types(
    db: AsyncSession,
    catalog_item_id: int,
) -> Dict[tuple, CollectionAlert]:
    result = await db.execute(
        select(CollectionAlert).where(
            CollectionAlert.catalog_item_id == catalog_item_id,
            CollectionAlert.status == CollectionAlertStatus.ACTIVE,
        )
    )
    alerts = result.scalars().all()
    return {(a.alert_type, a.location): a for a in alerts}


# ---------------------------------------------------------------------------
# Standalone metric helpers (backward-compatible, used when called individually)
# ---------------------------------------------------------------------------


async def get_available_copy_count(
    db: AsyncSession,
    catalog_item_id: int,
    location: Optional[str] = None
) -> int:
    query = select(func.count(ItemCopy.id)).where(
        ItemCopy.catalog_item_id == catalog_item_id,
        ItemCopy.condition.notin_([ItemCondition.WITHDRAWN, ItemCondition.DAMAGED])
    )

    if location:
        query = query.where(ItemCopy.location == location)

    result = await db.execute(query)
    return result.scalar() or 0


async def get_total_copy_count(
    db: AsyncSession,
    catalog_item_id: int
) -> int:
    result = await db.execute(
        select(func.count(ItemCopy.id)).where(
            ItemCopy.catalog_item_id == catalog_item_id
        )
    )
    return result.scalar() or 0


async def get_pending_hold_count(
    db: AsyncSession,
    catalog_item_id: int
) -> int:
    result = await db.execute(
        select(func.count(Hold.id)).where(
            Hold.item_id == catalog_item_id,
            Hold.status == HoldStatus.pending
        )
    )
    return result.scalar() or 0


async def get_last_checkout_date(
    db: AsyncSession,
    catalog_item_id: int
) -> Optional[datetime]:
    result = await db.execute(
        select(func.max(Checkout.checked_out_at)).where(
            Checkout.item_id == catalog_item_id,
            Checkout.status.in_([
                CheckoutStatus.returned,
                CheckoutStatus.returned_damaged,
                CheckoutStatus.claims_returned
            ])
        )
    )
    return result.scalar()


# ---------------------------------------------------------------------------
# Individual alert checks -- accept optional pre-computed data
# ---------------------------------------------------------------------------


async def check_last_copy_alert(
    db: AsyncSession,
    catalog_item_id: int,
    metrics: Optional[ItemMetrics] = None,
    existing_alerts: Optional[Dict[tuple, CollectionAlert]] = None,
) -> Optional[CollectionAlert]:
    if metrics is None:
        available = await get_available_copy_count(db, catalog_item_id)
        total = await get_total_copy_count(db, catalog_item_id)
    else:
        available = metrics.available_copies
        total = metrics.total_copies

    if available <= 1 and total > 1:
        if existing_alerts is not None:
            already_exists = (AlertType.LAST_COPY_CHECKOUT, None) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.LAST_COPY_CHECKOUT,
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            context = {
                "available_copies": available,
                "total_copies": total,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.LAST_COPY_CHECKOUT,
                severity=CollectionAlertSeverity.CRITICAL,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            return alert

    return None


async def check_high_demand_hold_alert(
    db: AsyncSession,
    catalog_item_id: int,
    metrics: Optional[ItemMetrics] = None,
    existing_alerts: Optional[Dict[tuple, CollectionAlert]] = None,
) -> Optional[CollectionAlert]:
    if metrics is None:
        hold_count = await get_pending_hold_count(db, catalog_item_id)
        available = await get_available_copy_count(db, catalog_item_id)
    else:
        hold_count = metrics.pending_holds
        available = metrics.available_copies

    if hold_count >= 3:
        if existing_alerts is not None:
            already_exists = (AlertType.HIGH_DEMAND_HOLD, None) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.HIGH_DEMAND_HOLD,
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            context = {
                "pending_holds": hold_count,
                "available_copies": available,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.HIGH_DEMAND_HOLD,
                severity=CollectionAlertSeverity.WARNING,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            return alert

    return None


async def check_long_hold_queue_alert(
    db: AsyncSession,
    catalog_item_id: int,
    metrics: Optional[ItemMetrics] = None,
    existing_alerts: Optional[Dict[tuple, CollectionAlert]] = None,
) -> Optional[CollectionAlert]:
    if metrics is None:
        hold_count = await get_pending_hold_count(db, catalog_item_id)
        available = await get_available_copy_count(db, catalog_item_id)
        total = await get_total_copy_count(db, catalog_item_id)
    else:
        hold_count = metrics.pending_holds
        available = metrics.available_copies
        total = metrics.total_copies

    if hold_count >= 5:
        if existing_alerts is not None:
            already_exists = (AlertType.LONG_HOLD_QUEUE, None) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.LONG_HOLD_QUEUE,
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            context = {
                "pending_holds": hold_count,
                "available_copies": available,
                "total_copies": total,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.LONG_HOLD_QUEUE,
                severity=CollectionAlertSeverity.WARNING,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            return alert

    return None


async def check_low_inventory_alerts(
    db: AsyncSession,
    catalog_item_id: int,
    location: Optional[str] = None,
    metrics: Optional[ItemMetrics] = None,
    existing_alerts: Optional[Dict[tuple, CollectionAlert]] = None,
) -> List[CollectionAlert]:
    alerts = []

    if metrics is None:
        available = await get_available_copy_count(db, catalog_item_id, location)
        total = await get_total_copy_count(db, catalog_item_id)
    else:
        available = metrics.available_at_location if location else metrics.available_copies
        total = metrics.total_copies

    # System-wide low inventory (less than 3 copies)
    if total < 3 and total > 0:
        if existing_alerts is not None:
            already_exists = (AlertType.LOW_INVENTORY, None) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.LOW_INVENTORY,
                    CollectionAlert.location.is_(None),
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            context = {
                "available_copies": available,
                "total_copies": total,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.LOW_INVENTORY,
                severity=CollectionAlertSeverity.WARNING,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            alerts.append(alert)

    # Branch-specific low inventory (0 available at location)
    if location and available == 0 and total > 0:
        if existing_alerts is not None:
            already_exists = (AlertType.LOW_INVENTORY, location) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.LOW_INVENTORY,
                    CollectionAlert.location == location,
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            context = {
                "available_copies": available,
                "total_copies": total,
                "branch": location,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.LOW_INVENTORY,
                severity=CollectionAlertSeverity.CRITICAL,
                location=location,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            alerts.append(alert)

    return alerts


async def check_non_circulating_alert(
    db: AsyncSession,
    catalog_item_id: int,
    months_threshold: int = 12,
    metrics: Optional[ItemMetrics] = None,
    existing_alerts: Optional[Dict[tuple, CollectionAlert]] = None,
) -> Optional[CollectionAlert]:
    if metrics is None:
        last_checkout = await get_last_checkout_date(db, catalog_item_id)
    else:
        last_checkout = metrics.last_checkout_date

    threshold_date = datetime.now(timezone.utc) - timedelta(days=30 * months_threshold)

    if not last_checkout or last_checkout < threshold_date:
        if existing_alerts is not None:
            already_exists = (AlertType.NON_CIRCULATING, None) in existing_alerts
        else:
            existing = await db.execute(
                select(CollectionAlert).where(
                    CollectionAlert.catalog_item_id == catalog_item_id,
                    CollectionAlert.alert_type == AlertType.NON_CIRCULATING,
                    CollectionAlert.status == CollectionAlertStatus.ACTIVE
                )
            )
            already_exists = existing.scalar_one_or_none() is not None

        if not already_exists:
            months_since = None
            if last_checkout:
                delta = datetime.now(timezone.utc) - last_checkout
                months_since = int(delta.days / 30)

            context = {
                "last_checkout_date": last_checkout.isoformat() if last_checkout else None,
                "months_since_checkout": months_since,
                "threshold_months": months_threshold,
                "checked_at": datetime.now(timezone.utc).isoformat()
            }
            alert = CollectionAlert(
                catalog_item_id=catalog_item_id,
                alert_type=AlertType.NON_CIRCULATING,
                severity=CollectionAlertSeverity.INFO,
                context_data=json.dumps(context)
            )
            db.add(alert)
            await db.flush()
            return alert

    return None


# ---------------------------------------------------------------------------
# Batched orchestrators -- single entry point for callers that run multiple checks
# ---------------------------------------------------------------------------


async def check_checkout_alerts(
    db: AsyncSession,
    catalog_item_id: int,
    location: Optional[str] = None,
) -> List[CollectionAlert]:
    metrics = await get_item_metrics(db, catalog_item_id, location)
    existing = await get_existing_alert_types(db, catalog_item_id)
    results: List[CollectionAlert] = []

    alert = await check_last_copy_alert(db, catalog_item_id, metrics=metrics, existing_alerts=existing)
    if alert:
        results.append(alert)

    low_inv = await check_low_inventory_alerts(db, catalog_item_id, location, metrics=metrics, existing_alerts=existing)
    results.extend(low_inv)

    return results


async def check_hold_alerts(
    db: AsyncSession,
    catalog_item_id: int,
) -> List[CollectionAlert]:
    metrics = await get_item_metrics(db, catalog_item_id)
    existing = await get_existing_alert_types(db, catalog_item_id)
    results: List[CollectionAlert] = []

    alert = await check_high_demand_hold_alert(db, catalog_item_id, metrics=metrics, existing_alerts=existing)
    if alert:
        results.append(alert)

    alert = await check_long_hold_queue_alert(db, catalog_item_id, metrics=metrics, existing_alerts=existing)
    if alert:
        results.append(alert)

    return results


# ---------------------------------------------------------------------------
# Alert management helpers (unchanged)
# ---------------------------------------------------------------------------


async def dismiss_alert(
    db: AsyncSession,
    alert_id: int,
    user_id: int
) -> Optional[CollectionAlert]:
    result = await db.execute(
        select(CollectionAlert).where(CollectionAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert and alert.status == CollectionAlertStatus.ACTIVE:
        alert.status = CollectionAlertStatus.DISMISSED
        alert.dismissed_at = datetime.now(timezone.utc)
        alert.dismissed_by_id = user_id
        await db.flush()

    return alert


async def resolve_alert(
    db: AsyncSession,
    alert_id: int
) -> Optional[CollectionAlert]:
    result = await db.execute(
        select(CollectionAlert).where(CollectionAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert and alert.status == CollectionAlertStatus.ACTIVE:
        alert.status = CollectionAlertStatus.RESOLVED
        alert.resolved_at = datetime.now(timezone.utc)
        await db.flush()

    return alert


async def get_active_alerts_for_item(
    db: AsyncSession,
    catalog_item_id: int
) -> List[CollectionAlert]:
    result = await db.execute(
        select(CollectionAlert).where(
            CollectionAlert.catalog_item_id == catalog_item_id,
            CollectionAlert.status == CollectionAlertStatus.ACTIVE
        )
    )
    return result.scalars().all()


async def get_all_active_alerts(
    db: AsyncSession,
    alert_type: Optional[AlertType] = None,
    location: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
) -> List[CollectionAlert]:
    query = select(CollectionAlert).where(
        CollectionAlert.status == CollectionAlertStatus.ACTIVE
    )

    if alert_type:
        query = query.where(CollectionAlert.alert_type == alert_type)

    if location:
        query = query.where(CollectionAlert.location == location)

    query = query.order_by(
        CollectionAlert.severity.desc(),
        CollectionAlert.created_at.desc()
    ).limit(limit).offset(offset)

    result = await db.execute(query)
    return result.scalars().all()


async def get_alert_count_by_type(
    db: AsyncSession
) -> dict:
    result = await db.execute(
        select(
            CollectionAlert.alert_type,
            func.count(CollectionAlert.id).label("count")
        ).where(
            CollectionAlert.status == CollectionAlertStatus.ACTIVE
        ).group_by(CollectionAlert.alert_type)
    )

    counts = {}
    for alert_type, count in result.all():
        counts[alert_type] = count

    return counts
