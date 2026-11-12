# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import (
    Equipment,
    EquipmentAlert,
    EquipmentCheckout,
    EquipmentCondition,
    EquipmentConditionLog,
    EquipmentMaintenance,
    EquipmentReservation,
    EquipmentStatus,
    EquipmentType,
    EquipmentReservationStatus,
)
from app.models.user import User
from app.core.datetime_utils import utc_now


# ============================================================================
# Summary Report
# ============================================================================


async def get_equipment_summary(db: AsyncSession) -> dict:
    # Total equipment counts by status
    status_counts = await db.execute(
        select(
            Equipment.status,
            func.count(Equipment.id).label("count"),
        )
        .where(Equipment.status != EquipmentStatus.RETIRED)
        .group_by(Equipment.status)
    )
    status_dict = {getattr(row.status, "value", row.status): row.count for row in status_counts}

    total = sum(status_dict.values())
    available = status_dict.get("available", 0)
    checked_out = status_dict.get("checked_out", 0)
    reserved = status_dict.get("reserved", 0)
    in_maintenance = status_dict.get("in_maintenance", 0)
    damaged = status_dict.get("damaged", 0)
    lost = status_dict.get("lost", 0)

    # Overdue checkouts
    overdue_result = await db.execute(
        select(func.count()).select_from(EquipmentCheckout).where(
            EquipmentCheckout.status == "overdue",
        )
    )
    overdue_count = overdue_result.scalar() or 0

    # Pending reservations
    reservation_result = await db.execute(
        select(func.count()).select_from(EquipmentReservation).where(
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ])
        )
    )
    pending_reservations = reservation_result.scalar() or 0

    # Maintenance due
    today = date.today()
    maintenance_due_result = await db.execute(
        select(func.count()).select_from(Equipment).where(
            Equipment.status != EquipmentStatus.RETIRED,
            Equipment.next_maintenance_date <= today,
        )
    )
    maintenance_due = maintenance_due_result.scalar() or 0

    # Total replacement value
    replacement_result = await db.execute(
        select(func.sum(Equipment.replacement_cost)).where(
            Equipment.status != EquipmentStatus.RETIRED,
            Equipment.replacement_cost.isnot(None),
        )
    )
    total_replacement_value = replacement_result.scalar() or Decimal("0.00")

    # Calculate utilization rate (checked_out / (available + checked_out + reserved))
    active_equipment = available + checked_out + reserved
    utilization_rate = (checked_out / active_equipment * 100) if active_equipment > 0 else 0.0

    return {
        "total_equipment": total,
        "available_equipment": available,
        "checked_out_equipment": checked_out,
        "reserved_equipment": reserved,
        "in_maintenance": in_maintenance,
        "damaged_or_lost": damaged + lost,
        "overdue_checkouts": overdue_count,
        "pending_reservations": pending_reservations,
        "maintenance_due_count": maintenance_due,
        "total_replacement_value": total_replacement_value,
        "average_utilization_rate": round(utilization_rate, 2),
    }


# ============================================================================
# Utilization Report
# ============================================================================


async def get_utilization_report(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    equipment_type: Optional[EquipmentType] = None,
) -> list[dict]:
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    if not end_date:
        end_date = date.today()

    # Convert to datetime for comparison
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)
    period_days = (end_date - start_date).days + 1

    # Build base query
    equipment_query = select(Equipment).where(Equipment.status != EquipmentStatus.RETIRED)
    if equipment_type:
        equipment_query = equipment_query.where(Equipment.equipment_type == equipment_type)

    equipment_result = await db.execute(equipment_query)
    equipment_list = equipment_result.scalars().all()

    utilization_data = []

    for equipment in equipment_list:
        # Get checkouts for this equipment in the period
        checkouts_result = await db.execute(
            select(EquipmentCheckout).where(
                EquipmentCheckout.equipment_id == equipment.id,
                EquipmentCheckout.checked_out_at >= start_dt,
                EquipmentCheckout.checked_out_at <= end_dt,
            )
        )
        checkouts = checkouts_result.scalars().all()

        total_checkouts = len(checkouts)
        total_days_out = 0
        durations = []

        for checkout in checkouts:
            return_date = checkout.returned_at or utc_now()
            duration = (return_date - checkout.checked_out_at).days
            total_days_out += duration
            durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0
        utilization_rate = (total_days_out / period_days * 100) if period_days > 0 else 0

        # Get last checkout date
        last_checkout = None
        if checkouts:
            last_checkout = max(c.checked_out_at for c in checkouts).date()

        utilization_data.append({
            "equipment_id": equipment.id,
            "equipment_name": equipment.name,
            "equipment_type": equipment.equipment_type,
            "total_checkouts": total_checkouts,
            "total_days_checked_out": total_days_out,
            "average_checkout_duration": round(avg_duration, 1),
            "utilization_rate": round(min(utilization_rate, 100), 2),
            "last_checkout_date": last_checkout,
        })

    # Sort by utilization rate descending
    utilization_data.sort(key=lambda x: x["utilization_rate"], reverse=True)

    return utilization_data


# ============================================================================
# Condition Trends Report
# ============================================================================


async def get_condition_trends(
    db: AsyncSession,
    months: int = 6,
    equipment_id: Optional[int] = None,
) -> list[dict]:
    start_date = date.today() - timedelta(days=months * 30)
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Query condition logs
    query = select(EquipmentConditionLog).where(
        EquipmentConditionLog.created_at >= start_dt,
    )
    if equipment_id:
        query = query.where(EquipmentConditionLog.equipment_id == equipment_id)

    query = query.order_by(EquipmentConditionLog.created_at)

    result = await db.execute(query)
    logs = result.scalars().all()

    # Group by equipment
    equipment_trends = {}
    for log in logs:
        if log.equipment_id not in equipment_trends:
            equipment_trends[log.equipment_id] = []
        equipment_trends[log.equipment_id].append({
            "date": log.created_at.date().isoformat(),
            "condition": str(log.new_condition),
            "reason": log.change_reason,
        })

    # Build response
    trends_data = []
    for eq_id, history in equipment_trends.items():
        equipment = await db.get(Equipment, eq_id)
        if not equipment:
            continue

        # Calculate degradation rate
        condition_values = {
            "excellent": 5,
            "good": 4,
            "fair": 3,
            "poor": 2,
            "needs_repair": 1,
            "non_functional": 0,
        }

        if len(history) >= 2:
            first_value = condition_values.get(history[0]["condition"], 3)
            last_value = condition_values.get(history[-1]["condition"], 3)
            months_span = len(history) / 4  # Rough estimate
            if months_span > 0:
                degradation_rate = (first_value - last_value) / months_span
            else:
                degradation_rate = 0
        else:
            degradation_rate = None

        trends_data.append({
            "equipment_id": eq_id,
            "equipment_name": equipment.name,
            "current_condition": equipment.condition,
            "condition_history": history,
            "degradation_rate": round(degradation_rate, 2) if degradation_rate else None,
        })

    return trends_data


# ============================================================================
# Popular Equipment Report
# ============================================================================


async def get_popular_equipment(
    db: AsyncSession,
    limit: int = 20,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> list[dict]:
    if not start_date:
        start_date = date.today() - timedelta(days=90)
    if not end_date:
        end_date = date.today()

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Get checkout counts grouped by equipment
    checkout_stats = await db.execute(
        select(
            EquipmentCheckout.equipment_id,
            func.count(EquipmentCheckout.id).label("checkout_count"),
            func.count(func.distinct(EquipmentCheckout.user_id)).label("unique_patrons"),
        )
        .where(
            EquipmentCheckout.checked_out_at >= start_dt,
            EquipmentCheckout.checked_out_at <= end_dt,
        )
        .group_by(EquipmentCheckout.equipment_id)
        .order_by(func.count(EquipmentCheckout.id).desc())
        .limit(limit)
    )

    popular_data = []

    for row in checkout_stats:
        equipment = await db.get(Equipment, row.equipment_id)
        if not equipment:
            continue

        # Get reservation count
        reservation_result = await db.execute(
            select(func.count()).select_from(EquipmentReservation).where(
                EquipmentReservation.equipment_id == row.equipment_id,
                EquipmentReservation.created_at >= start_dt,
                EquipmentReservation.created_at <= end_dt,
            )
        )
        reservation_count = reservation_result.scalar() or 0

        # Calculate average wait time (if there were reservations that became checkouts)
        avg_wait_time = None  # Would need more complex query to calculate

        popular_data.append({
            "equipment_id": equipment.id,
            "equipment_name": equipment.name,
            "equipment_type": equipment.equipment_type,
            "checkout_count": row.checkout_count,
            "unique_patrons": row.unique_patrons,
            "average_wait_time_days": avg_wait_time,
            "reservation_count": reservation_count,
        })

    return popular_data


# ============================================================================
# Equipment by Type Report
# ============================================================================


async def get_equipment_by_type(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(
            Equipment.equipment_type,
            func.count(Equipment.id).label("total_count"),
            func.count(case((Equipment.status == EquipmentStatus.AVAILABLE, 1))).label("available_count"),
            func.count(case((Equipment.status == EquipmentStatus.CHECKED_OUT, 1))).label("checked_out_count"),
            func.sum(Equipment.replacement_cost).label("total_value"),
        )
        .where(Equipment.status != EquipmentStatus.RETIRED)
        .group_by(Equipment.equipment_type)
        .order_by(func.count(Equipment.id).desc())
    )

    type_stats = []
    for row in result:
        utilization = 0
        if row.total_count > 0:
            utilization = (row.checked_out_count / row.total_count) * 100

        type_stats.append({
            "equipment_type": row.equipment_type,
            "total_count": row.total_count,
            "available_count": row.available_count,
            "checked_out_count": row.checked_out_count,
            "total_value": row.total_value or Decimal("0.00"),
            "utilization_rate": round(utilization, 2),
        })

    return type_stats


# ============================================================================
# Overdue Report
# ============================================================================


async def get_overdue_equipment_report(db: AsyncSession) -> list[dict]:
    now = utc_now()

    result = await db.execute(
        select(EquipmentCheckout)
        .where(
            EquipmentCheckout.status.in_(["active", "overdue"]),
            EquipmentCheckout.due_date < now,
        )
        .order_by(EquipmentCheckout.due_date)
    )
    overdue_checkouts = result.scalars().all()

    overdue_data = []

    for checkout in overdue_checkouts:
        equipment = await db.get(Equipment, checkout.equipment_id)
        patron = await db.get(User, checkout.user_id) if checkout.user_id else None

        days_overdue = (now - checkout.due_date).days
        fine_amount = Decimal(days_overdue) * (equipment.fine_per_day if equipment else Decimal("5.00"))

        overdue_data.append({
            "checkout_id": checkout.id,
            "equipment_id": checkout.equipment_id,
            "equipment_name": equipment.name if equipment else "Unknown",
            "equipment_barcode": equipment.barcode if equipment else None,
            "equipment_replacement_cost": equipment.replacement_cost if equipment else None,
            "patron_id": checkout.user_id,
            "patron_name": patron.full_name if patron else "Unknown",
            "patron_email": patron.email if patron else None,
            "patron_phone": patron.phone if patron else None,
            "checked_out_at": checkout.checked_out_at,
            "due_date": checkout.due_date,
            "days_overdue": days_overdue,
            "fine_amount": fine_amount,
            "priority": "urgent" if days_overdue >= 14 else ("high" if days_overdue >= 7 else "medium"),
        })

    return overdue_data


# ============================================================================
# Maintenance Report
# ============================================================================


async def get_maintenance_report(
    db: AsyncSession,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    if not start_date:
        start_date = date.today() - timedelta(days=365)
    if not end_date:
        end_date = date.today()

    start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

    # Total maintenance records
    total_result = await db.execute(
        select(func.count()).select_from(EquipmentMaintenance).where(
            EquipmentMaintenance.created_at >= start_dt,
            EquipmentMaintenance.created_at <= end_dt,
        )
    )
    total_count = total_result.scalar() or 0

    # Completed maintenance
    completed_result = await db.execute(
        select(func.count()).select_from(EquipmentMaintenance).where(
            EquipmentMaintenance.status == "completed",
            EquipmentMaintenance.completed_at >= start_dt,
            EquipmentMaintenance.completed_at <= end_dt,
        )
    )
    completed_count = completed_result.scalar() or 0

    # Total costs
    cost_result = await db.execute(
        select(
            func.sum(EquipmentMaintenance.parts_cost).label("total_parts"),
            func.sum(EquipmentMaintenance.labor_cost).label("total_labor"),
        ).where(
            EquipmentMaintenance.status == "completed",
            EquipmentMaintenance.completed_at >= start_dt,
            EquipmentMaintenance.completed_at <= end_dt,
        )
    )
    cost_row = cost_result.one()
    total_parts_cost = cost_row.total_parts or Decimal("0.00")
    total_labor_cost = cost_row.total_labor or Decimal("0.00")

    # Maintenance by type
    by_type_result = await db.execute(
        select(
            EquipmentMaintenance.maintenance_type,
            func.count(EquipmentMaintenance.id).label("count"),
        )
        .where(
            EquipmentMaintenance.created_at >= start_dt,
            EquipmentMaintenance.created_at <= end_dt,
        )
        .group_by(EquipmentMaintenance.maintenance_type)
    )
    by_type = {getattr(row.maintenance_type, "value", row.maintenance_type): row.count for row in by_type_result}

    # Equipment needing maintenance
    today = date.today()
    due_result = await db.execute(
        select(func.count()).select_from(Equipment).where(
            Equipment.status != EquipmentStatus.RETIRED,
            Equipment.next_maintenance_date <= today,
        )
    )
    maintenance_due = due_result.scalar() or 0

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "total_maintenance_records": total_count,
        "completed_maintenance": completed_count,
        "total_parts_cost": total_parts_cost,
        "total_labor_cost": total_labor_cost,
        "total_maintenance_cost": total_parts_cost + total_labor_cost,
        "maintenance_by_type": by_type,
        "equipment_maintenance_due": maintenance_due,
    }


# ============================================================================
# Patron Equipment History
# ============================================================================


async def get_patron_equipment_history(
    db: AsyncSession,
    patron_id: int,
) -> dict:
    patron = await db.get(User, patron_id)
    if not patron:
        return None

    # Get all checkouts
    checkouts_result = await db.execute(
        select(EquipmentCheckout)
        .where(EquipmentCheckout.user_id == patron_id)
        .order_by(EquipmentCheckout.checked_out_at.desc())
    )
    checkouts = checkouts_result.scalars().all()

    # Count statistics
    total_checkouts = len(checkouts)
    current_checkouts = sum(1 for c in checkouts if c.status in ["active", "overdue"])
    overdue_count = sum(1 for c in checkouts if c.status == "overdue")
    lost_count = sum(1 for c in checkouts if c.status == "lost")

    # Get agreement status
    from app.services.equipment_service import check_patron_agreement
    has_agreement, agreement = await check_patron_agreement(db, patron_id)

    # Format checkout history
    checkout_history = []
    for checkout in checkouts[:50]:  # Limit to 50 most recent
        equipment = await db.get(Equipment, checkout.equipment_id)
        checkout_history.append({
            "id": checkout.id,
            "equipment_id": checkout.equipment_id,
            "equipment_name": equipment.name if equipment else "Unknown",
            "equipment_type": equipment.equipment_type if equipment else None,
            "status": checkout.status,
            "checked_out_at": checkout.checked_out_at,
            "due_date": checkout.due_date,
            "returned_at": checkout.returned_at,
            "condition_at_checkout": checkout.condition_at_checkout,
            "condition_at_return": checkout.condition_at_return,
            "fine_amount": checkout.fine_amount,
        })

    return {
        "patron_id": patron_id,
        "patron_name": patron.full_name,
        "total_checkouts": total_checkouts,
        "current_checkouts": current_checkouts,
        "overdue_count": overdue_count,
        "lost_count": lost_count,
        "has_valid_agreement": has_agreement,
        "agreement_signed_at": agreement.signed_at if agreement else None,
        "checkouts": checkout_history,
    }


# ============================================================================
# Dashboard Metrics
# ============================================================================


async def get_dashboard_metrics(db: AsyncSession) -> dict:
    today = date.today()
    week_ago = today - timedelta(days=7)
    week_ago_dt = datetime.combine(week_ago, datetime.min.time()).replace(tzinfo=timezone.utc)

    # Active alerts by priority
    alerts_result = await db.execute(
        select(
            EquipmentAlert.priority,
            func.count(EquipmentAlert.id).label("count"),
        )
        .where(EquipmentAlert.status == "active")
        .group_by(EquipmentAlert.priority)
    )
    alerts_by_priority = {row.priority: row.count for row in alerts_result}

    # Checkouts this week
    week_checkouts_result = await db.execute(
        select(func.count()).select_from(EquipmentCheckout).where(
            EquipmentCheckout.checked_out_at >= week_ago_dt,
        )
    )
    checkouts_this_week = week_checkouts_result.scalar() or 0

    # Returns this week
    week_returns_result = await db.execute(
        select(func.count()).select_from(EquipmentCheckout).where(
            EquipmentCheckout.returned_at >= week_ago_dt,
        )
    )
    returns_this_week = week_returns_result.scalar() or 0

    # Get summary
    summary = await get_equipment_summary(db)

    return {
        "summary": summary,
        "alerts_by_priority": alerts_by_priority,
        "urgent_alerts": alerts_by_priority.get("urgent", 0),
        "checkouts_this_week": checkouts_this_week,
        "returns_this_week": returns_this_week,
    }


# ============================================================================
# Demand Analytics (Digital Divide Expansion Planning)
# ============================================================================


async def get_demand_analytics(
    db: AsyncSession,
    lookback_days: int = 90,
) -> list[dict]:
    if lookback_days < 7:
        lookback_days = 7

    start_dt = utc_now() - timedelta(days=lookback_days)

    demand_rows = await db.execute(
        select(
            Equipment.equipment_type,
            func.count(func.distinct(Equipment.id)).label("inventory_count"),
            func.count(func.distinct(case((Equipment.status == EquipmentStatus.CHECKED_OUT, Equipment.id)))).label("checked_out_now"),
            func.count(func.distinct(case((EquipmentCheckout.status == "overdue", EquipmentCheckout.id)))).label("overdue_checkouts"),
            func.count(func.distinct(case((EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ]), EquipmentReservation.id)))).label("active_reservations"),
            func.count(func.distinct(case((EquipmentCheckout.checked_out_at >= start_dt, EquipmentCheckout.id)))).label("period_checkouts"),
            func.count(func.distinct(case((EquipmentCheckout.checked_out_at >= start_dt, EquipmentCheckout.user_id)))).label("unique_patrons"),
            func.avg(
                case(
                    (EquipmentCheckout.checked_out_at >= start_dt,
                     extract("epoch", func.coalesce(EquipmentCheckout.returned_at, utc_now()) - EquipmentCheckout.checked_out_at) / 86400.0),
                    else_=None,
                )
            ).label("avg_checkout_days"),
        )
        .outerjoin(EquipmentCheckout, EquipmentCheckout.equipment_id == Equipment.id)
        .outerjoin(EquipmentReservation, EquipmentReservation.equipment_id == Equipment.id)
        .where(Equipment.status != EquipmentStatus.RETIRED)
        .group_by(Equipment.equipment_type)
        .order_by(func.count(func.distinct(EquipmentReservation.id)).desc())
    )

    analytics: list[dict] = []
    for row in demand_rows:
        inventory_count = int(row.inventory_count or 0)
        active_reservations = int(row.active_reservations or 0)
        period_checkouts = int(row.period_checkouts or 0)
        unique_patrons = int(row.unique_patrons or 0)
        checked_out_now = int(row.checked_out_now or 0)
        overdue_checkouts = int(row.overdue_checkouts or 0)

        utilization_pressure = checked_out_now / max(inventory_count, 1)
        reservation_pressure = active_reservations / max(inventory_count, 1)
        circulation_pressure = period_checkouts / max(inventory_count, 1)

        demand_score = round(
            min(
                100.0,
                (utilization_pressure * 40)
                + (reservation_pressure * 35)
                + (circulation_pressure * 5),
            ),
            2,
        )

        recommended_additional_units = max(
            0,
            int(active_reservations + max(0, round((checked_out_now * 0.25) - (inventory_count * 0.1)))),
        )

        analytics.append({
            "equipment_type": row.equipment_type,
            "inventory_count": inventory_count,
            "checked_out_now": checked_out_now,
            "active_reservations": active_reservations,
            "overdue_checkouts": overdue_checkouts,
            "period_checkouts": period_checkouts,
            "unique_patrons": unique_patrons,
            "avg_checkout_days": round(float(row.avg_checkout_days or 0), 2),
            "demand_score": demand_score,
            "recommended_additional_units": recommended_additional_units,
        })

    return analytics
