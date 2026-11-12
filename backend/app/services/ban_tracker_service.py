# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.ban_tracker import BanAlertNotification, BanReport, BanSource
from ..models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel
from ..models.user import User, UserRole
from ..core.cache import get_cached, set_cached, invalidate_cache

logger = get_logger(__name__)

# Redis cache for the public ban-tracker stats card. Stats are library-scoped
# and public, single key suffices. TTL of 1 hour bounds staleness; the weekly
# PEN America sync wrapper (see app/core/scheduler.py) invalidates this key
# after each run so fresh totals show up within seconds of a sync completing.
_STATS_CACHE_KEY = "ban_tracker:stats:v1"
_STATS_CACHE_TTL = 3600  # 1 hour


async def _invalidate_stats_cache() -> None:
    try:
        await invalidate_cache("ban_tracker:stats*")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ban_tracker stats cache invalidation failed: %s", exc)


class BanTrackerService:
    @staticmethod
    async def list_reports(
        db: AsyncSession,
        state: Optional[str] = None,
        ban_type: Optional[str] = None,
        source: Optional[str] = None,
        reason_category: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[BanReport], int]:
        base_query = select(BanReport)

        if state:
            base_query = base_query.where(BanReport.state == state)
        if ban_type:
            base_query = base_query.where(BanReport.ban_type == ban_type)
        if source:
            base_query = base_query.where(BanReport.source == source)
        if reason_category:
            base_query = base_query.where(BanReport.reason_category == reason_category)
        if search:
            pattern = f"%{search}%"
            base_query = base_query.where(
                BanReport.title.ilike(pattern) | BanReport.author.ilike(pattern)
            )

        count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * per_page
        rows_result = await db.execute(
            base_query.options(selectinload(BanReport.catalog_match))
            .order_by(BanReport.created_at.desc(), BanReport.id.desc())
            .offset(offset)
            .limit(per_page)
        )
        reports = list(rows_result.scalars().all())

        return reports, total

    @staticmethod
    async def get_report(db: AsyncSession, report_id: int) -> Optional[BanReport]:
        result = await db.execute(
            select(BanReport)
            .options(selectinload(BanReport.alerts))
            .where(BanReport.id == report_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_report(db: AsyncSession, data_dict: dict) -> BanReport:
        report = BanReport(**data_dict)
        db.add(report)
        await db.commit()
        await db.refresh(report)

        await BanTrackerService._check_catalog_match(db, report)
        await _invalidate_stats_cache()
        return report

    @staticmethod
    async def update_report(
        db: AsyncSession, report_id: int, data_dict: dict
    ) -> Optional[BanReport]:
        result = await db.execute(select(BanReport).where(BanReport.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return None

        for key, value in data_dict.items():
            setattr(report, key, value)

        await db.commit()
        await db.refresh(report)
        await _invalidate_stats_cache()
        return report

    @staticmethod
    async def delete_report(db: AsyncSession, report_id: int) -> bool:
        result = await db.execute(select(BanReport).where(BanReport.id == report_id))
        report = result.scalar_one_or_none()
        if report is None:
            return False

        await db.delete(report)
        await db.commit()
        await _invalidate_stats_cache()
        return True

    @staticmethod
    async def get_statistics(db: AsyncSession) -> dict:
        cached = await get_cached(_STATS_CACHE_KEY)
        if cached is not None:
            return cached

        stats = await BanTrackerService._compute_statistics(db)
        await set_cached(_STATS_CACHE_KEY, stats, ttl_seconds=_STATS_CACHE_TTL)
        return stats

    @staticmethod
    async def _compute_statistics(db: AsyncSession) -> dict:
        total_result = await db.execute(select(func.count(BanReport.id)))
        total_reports = total_result.scalar_one()

        states_result = await db.execute(select(func.count(BanReport.state.distinct())))
        total_states = states_result.scalar_one()

        matches_result = await db.execute(
            select(func.count(BanReport.id)).where(BanReport.catalog_match_id.is_not(None))
        )
        total_catalog_matches = matches_result.scalar_one()

        by_state_result = await db.execute(
            select(BanReport.state, func.count(BanReport.id))
            .where(BanReport.state.is_not(None))
            .group_by(BanReport.state)
            .order_by(func.count(BanReport.id).desc())
        )
        by_state = {row[0]: row[1] for row in by_state_result.all()}

        by_type_result = await db.execute(
            select(BanReport.ban_type, func.count(BanReport.id)).group_by(BanReport.ban_type)
        )
        by_type = {
            row[0].value if hasattr(row[0], "value") else str(row[0]): row[1]
            for row in by_type_result.all()
        }

        by_reason_result = await db.execute(
            select(BanReport.reason_category, func.count(BanReport.id))
            .where(BanReport.reason_category.is_not(None))
            .group_by(BanReport.reason_category)
            .order_by(func.count(BanReport.id).desc())
        )
        by_reason = {row[0]: row[1] for row in by_reason_result.all()}

        return {
            "total_reports": total_reports,
            "total_states": total_states,
            "total_catalog_matches": total_catalog_matches,
            "by_state": by_state,
            "by_type": by_type,
            "by_reason": by_reason,
        }

    @staticmethod
    async def get_all_catalog_matches(db: AsyncSession) -> list[BanReport]:
        """Ban reports whose matched catalog item an anonymous visitor can open.

        This feeds a public list of jacket covers that link to /catalog/{id}.
        That route 404s anything not CATALOGED, and anything not PUBLIC, for
        anonymous users (api/v1/catalog/browse.py). Matching those conditions
        here is what keeps the two definitions of "in our catalog" from
        drifting apart: without it the page advertises covers that lead
        nowhere, which is how 38 of 40 links came to be dead in production.
        """
        result = await db.execute(
            select(BanReport)
            .join(CatalogItem, CatalogItem.id == BanReport.catalog_match_id)
            .options(selectinload(BanReport.catalog_match))
            .where(
                BanReport.catalog_match_id.is_not(None),
                CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
                CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
            )
            .order_by(BanReport.title)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_catalog_matches(
        db: AsyncSession, page: int = 1, per_page: int = 20
    ) -> tuple[list[BanReport], int]:
        base_query = select(BanReport).where(BanReport.catalog_match_id.is_not(None))

        count_result = await db.execute(select(func.count()).select_from(base_query.subquery()))
        total = count_result.scalar_one()

        offset = (page - 1) * per_page
        rows_result = await db.execute(
            base_query.order_by(BanReport.matched_at.desc()).offset(offset).limit(per_page)
        )
        reports = list(rows_result.scalars().all())

        return reports, total

    @staticmethod
    async def get_most_banned(db: AsyncSession, limit: int = 10) -> list[dict]:
        result = await db.execute(
            select(
                BanReport.title,
                BanReport.author,
                func.count(BanReport.id).label("report_count"),
                func.count(BanReport.state.distinct()).label("state_count"),
            )
            .group_by(BanReport.title, BanReport.author)
            .order_by(func.count(BanReport.id).desc())
            .limit(limit)
        )
        rows = result.all()
        return [
            {
                "title": row.title,
                "author": row.author,
                "report_count": row.report_count,
                "state_count": row.state_count,
                "states": [],
            }
            for row in rows
        ]

    @staticmethod
    async def _check_catalog_match(db: AsyncSession, report: BanReport) -> None:
        catalog_item: Optional[CatalogItem] = None

        if report.isbn:
            isbn_result = await db.execute(
                select(CatalogItem).where(CatalogItem.isbn == report.isbn)
            )
            catalog_item = isbn_result.scalar_one_or_none()

        if catalog_item is None:
            title_result = await db.execute(
                select(CatalogItem).where(
                    CatalogItem.title.ilike(report.title),
                    CatalogItem.author.ilike(report.author),
                )
            )
            catalog_item = title_result.scalar_one_or_none()

        if catalog_item is None:
            return

        report.catalog_match_id = catalog_item.id
        report.matched_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(report)

        logger.info(
            "Ban report %d matched catalog item %d ('%s')",
            report.id,
            catalog_item.id,
            report.title,
        )

        staff_result = await db.execute(
            select(User).where(
                User.role.in_([UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN])
            )
        )
        staff_users = staff_result.scalars().all()

        for user in staff_users:
            alert = BanAlertNotification(
                ban_report_id=report.id,
                user_id=user.id,
            )
            db.add(alert)

        await db.commit()
        logger.info(
            "Created %d ban alert notifications for report %d",
            len(staff_users),
            report.id,
        )

    @staticmethod
    async def trigger_pen_america_sync(db: AsyncSession) -> dict:
        from .pen_america_sync_service import PenAmericaSyncService

        result = await PenAmericaSyncService.sync(db)
        await _invalidate_stats_cache()
        return result

    @staticmethod
    async def get_sync_status(db: AsyncSession) -> dict:
        from .pen_america_sync_service import PenAmericaSyncService

        return await PenAmericaSyncService.get_sync_status(db)


class BanAlertService:
    @staticmethod
    async def get_unseen_alerts(db: AsyncSession, user_id: int) -> list[BanAlertNotification]:
        result = await db.execute(
            select(BanAlertNotification)
            .options(selectinload(BanAlertNotification.ban_report))
            .where(
                BanAlertNotification.user_id == user_id,
                BanAlertNotification.seen_at.is_(None),
            )
            .order_by(BanAlertNotification.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_unseen_count(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(func.count(BanAlertNotification.id)).where(
                BanAlertNotification.user_id == user_id,
                BanAlertNotification.seen_at.is_(None),
            )
        )
        return result.scalar_one()

    @staticmethod
    async def mark_seen(
        db: AsyncSession, alert_id: int, user_id: int
    ) -> Optional[BanAlertNotification]:
        result = await db.execute(
            select(BanAlertNotification).where(
                BanAlertNotification.id == alert_id,
                BanAlertNotification.user_id == user_id,
            )
        )
        alert = result.scalar_one_or_none()
        if alert is None:
            return None

        alert.seen_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)
        return alert

    @staticmethod
    async def mark_all_seen(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            select(BanAlertNotification).where(
                BanAlertNotification.user_id == user_id,
                BanAlertNotification.seen_at.is_(None),
            )
        )
        alerts = result.scalars().all()

        now = datetime.now(timezone.utc)
        for alert in alerts:
            alert.seen_at = now

        await db.commit()
        return len(alerts)
