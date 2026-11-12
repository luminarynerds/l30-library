# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from datetime import datetime, timezone
from typing import Awaitable, Callable, Dict, List

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .organization_features_service import OrganizationFeaturesService


# ---------- Per-hub counter functions ----------


async def front_desk_stats(db: AsyncSession) -> List[dict]:
    from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
    from ..models.panic_alert import PanicAlert, PanicAlertStatus

    holds_ready = (
        await db.execute(
            select(func.count(Hold.id)).where(Hold.status == HoldStatus.ready)
        )
    ).scalar_one()

    now = datetime.now(timezone.utc)
    overdue = (
        await db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.status == CheckoutStatus.active,
                Checkout.due_date < now,
            )
        )
    ).scalar_one()

    panic_active = (
        await db.execute(
            select(func.count(PanicAlert.id)).where(
                PanicAlert.status == PanicAlertStatus.ACTIVE
            )
        )
    ).scalar_one()

    return [
        {
            "key": "holds_ready",
            "value": int(holds_ready or 0),
            "label": "Holds ready for pickup",
            "urgent": False,
        },
        {
            "key": "items_overdue",
            "value": int(overdue or 0),
            "label": "Items overdue",
            "urgent": (overdue or 0) > 0,
        },
        {
            "key": "panic_alerts_active",
            "value": int(panic_active or 0),
            "label": "Panic alerts active",
            "urgent": (panic_active or 0) > 0,
        },
    ]


async def report_hub_stats(db: AsyncSession) -> List[dict]:
    from ..models.report_schedule import UnifiedReportSchedule

    now = datetime.now(timezone.utc)
    overdue = (
        await db.execute(
            select(func.count(UnifiedReportSchedule.id)).where(
                UnifiedReportSchedule.is_active.is_(True),
                UnifiedReportSchedule.next_run_at.is_not(None),
                UnifiedReportSchedule.next_run_at < now,
            )
        )
    ).scalar_one()

    return [
        {
            "key": "scheduled_reports_overdue",
            "value": int(overdue or 0),
            "label": "Scheduled reports overdue",
            "urgent": (overdue or 0) > 0,
        },
    ]


async def collection_hub_stats(db: AsyncSession) -> List[dict]:
    if not await OrganizationFeaturesService.is_feature_enabled(
        db, "processing_queue_enabled"
    ):
        return []

    from ..models.inventory import ItemCopy, ProcessingStep

    active_steps = [
        ProcessingStep.RECEIVED,
        ProcessingStep.LABELING,
        ProcessingStep.RFID_TAGGING,
        ProcessingStep.READY_TO_SHELVE,
    ]
    in_processing = (
        await db.execute(
            select(func.count(ItemCopy.id)).where(
                ItemCopy.processing_step.in_(active_steps)
            )
        )
    ).scalar_one()

    return [
        {
            "key": "items_in_processing",
            "value": int(in_processing or 0),
            "label": "Items in processing queue",
            "urgent": False,
        },
    ]


async def library_hub_stats(db: AsyncSession) -> List[dict]:
    from ..models.emergency_operations import CommunityResourceHub
    from ..models.positivity import PositivityEntry

    hubs_active = (
        await db.execute(
            select(func.count(CommunityResourceHub.id)).where(
                CommunityResourceHub.is_active.is_(True)
            )
        )
    ).scalar_one()

    advocacy_pending = (
        await db.execute(
            select(func.count(PositivityEntry.id)).where(
                PositivityEntry.flagged_for_advocacy.is_(True),
                PositivityEntry.moderation_status == "pending",
            )
        )
    ).scalar_one()

    return [
        {
            "key": "emergency_hubs_active",
            "value": int(hubs_active or 0),
            "label": "Emergency hubs active",
            "urgent": (hubs_active or 0) > 0,
        },
        {
            "key": "advocacy_awaiting_moderation",
            "value": int(advocacy_pending or 0),
            "label": "Advocacy stories awaiting moderation",
            "urgent": False,
        },
    ]


# ---------- Dispatcher ----------

HubStatsFn = Callable[[AsyncSession], Awaitable[List[dict]]]

HUB_STATS_REGISTRY: Dict[str, HubStatsFn] = {
    "front-desk-hub": front_desk_stats,
    "report-hub": report_hub_stats,
    "collection-hub": collection_hub_stats,
    "library-hub": library_hub_stats,
}


async def get_hub_stats(db: AsyncSession, hub_slug: str) -> List[dict]:
    fn = HUB_STATS_REGISTRY.get(hub_slug)
    if fn is None:
        return []
    return await fn(db)
