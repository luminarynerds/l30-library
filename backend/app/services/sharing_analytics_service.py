# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CatalogItem, Event, ReadingList, User
from ..models.social_sharing import ShareEvent, SharePlatform, ShareableResourceType
from ..schemas.analytics import (
    PlatformBreakdown,
    ShareTrendDataPoint,
    SharedResource,
    SharingDashboardResponse,
    StatsMetadata,
    TopSharer,
    TrendData,
)

logger = get_logger(__name__)


def _apply_resource_type_filter(query, resource_types: Optional[List[str]]):
    if resource_types:
        query = query.where(ShareEvent.resource_type.in_(resource_types))
    return query


class SharingAnalytics:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_dashboard_stats(
        self,
        days: int = 30,
        use_cache: bool = True,
        resource_types: Optional[List[str]] = None,
    ) -> SharingDashboardResponse:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        previous_start = start_date - timedelta(days=days)
        previous_end = start_date

        # Execute queries in parallel
        results = await asyncio.gather(
            self._get_top_shared_resources(start_date, resource_types),
            self._get_platform_breakdown(start_date, resource_types),
            self._get_share_metrics(start_date, resource_types),
            self._get_top_sharers(start_date, resource_types),
            self._get_share_trends(start_date, end_date, days, resource_types),
            self._get_previous_share_count(previous_start, previous_end, resource_types),
        )

        (
            top_resources,
            platforms,
            metrics,
            top_sharers,
            trends,
            previous_count,
        ) = results

        # Calculate trend
        current_count = metrics["total_shares"]
        shares_trend = TrendData.calculate(current_count, previous_count)

        # Determine top platform
        top_platform = platforms[0] if platforms else None
        top_platform_name = top_platform.platform if top_platform else "Unknown"
        top_platform_pct = top_platform.percentage if top_platform else 0.0

        response = SharingDashboardResponse(
            top_shared_resources=top_resources,
            platform_breakdown=platforms,
            total_shares=metrics["total_shares"],
            unique_sharers=metrics["unique_sharers"],
            avg_shares_per_user=metrics["avg_shares_per_user"],
            top_sharers=top_sharers,
            share_trends=trends,
            shares_trend=shares_trend,
            top_platform=top_platform_name,
            top_platform_percentage=top_platform_pct,
            metadata=StatsMetadata(
                generated_at=datetime.now(timezone.utc),
                cached=False,
                cache_ttl=300,
                time_window=f"{days}d",
            ),
        )

        return response

    async def _get_top_shared_resources(
        self, start_date: datetime, resource_types: Optional[List[str]] = None
    ) -> List[SharedResource]:
        try:
            # Build query to get top shared resources with titles
            query = select(
                ShareEvent.resource_type,
                ShareEvent.resource_id,
                func.count(ShareEvent.id).label("share_count"),
            ).where(ShareEvent.shared_at >= start_date)

            query = _apply_resource_type_filter(query, resource_types)

            query = query.group_by(
                ShareEvent.resource_type, ShareEvent.resource_id
            ).order_by(
                func.count(ShareEvent.id).desc()
            ).limit(
                10
            )

            result = await self.db.execute(query)
            share_rows = result.all()

            resources = []
            for resource_type, resource_id, share_count in share_rows:
                title = await self._get_resource_title(resource_type, resource_id)
                author = await self._get_resource_author(resource_type, resource_id)

                resources.append(
                    SharedResource(
                        resource_id=resource_id,
                        resource_type=resource_type,
                        title=title or f"{resource_type.capitalize()} #{resource_id}",
                        author=author,
                        share_count=share_count,
                    )
                )

            return resources
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get top shared resources: {e}")
            return []

    async def _get_resource_title(self, resource_type: str, resource_id: int) -> Optional[str]:
        try:
            if resource_type == ShareableResourceType.book.value:
                result = await self.db.execute(
                    select(CatalogItem.title).where(CatalogItem.id == resource_id)
                )
                return result.scalar()
            elif resource_type == ShareableResourceType.event.value:
                result = await self.db.execute(
                    select(Event.title).where(Event.id == resource_id)
                )
                return result.scalar()
            elif resource_type == ShareableResourceType.reading_list.value:
                result = await self.db.execute(
                    select(ReadingList.name).where(ReadingList.id == resource_id)
                )
                return result.scalar()
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get resource title: {e}")
        return None

    async def _get_resource_author(
        self, resource_type: str, resource_id: int
    ) -> Optional[str]:
        try:
            if resource_type == ShareableResourceType.book.value:
                result = await self.db.execute(
                    select(CatalogItem.author).where(CatalogItem.id == resource_id)
                )
                return result.scalar()
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get resource author: {e}")
        return None

    async def _get_platform_breakdown(
        self, start_date: datetime, resource_types: Optional[List[str]] = None
    ) -> List[PlatformBreakdown]:
        try:
            query = select(
                ShareEvent.platform,
                func.count(ShareEvent.id).label("share_count"),
            ).where(ShareEvent.shared_at >= start_date)

            query = _apply_resource_type_filter(query, resource_types)

            query = query.group_by(
                ShareEvent.platform
            ).order_by(
                func.count(ShareEvent.id).desc()
            )

            result = await self.db.execute(query)
            rows = result.all()

            # Calculate total for percentages
            total_shares = sum(count for _, count in rows)
            if total_shares == 0:
                return []

            platforms = []
            for platform, share_count in rows:
                percentage = (share_count / total_shares) * 100
                platforms.append(
                    PlatformBreakdown(
                        platform=platform,
                        share_count=share_count,
                        percentage=round(percentage, 2),
                    )
                )

            return platforms
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get platform breakdown: {e}")
            return []

    async def _get_share_metrics(
        self, start_date: datetime, resource_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        try:
            # Get total shares
            total_query = select(func.count(ShareEvent.id)).where(
                ShareEvent.shared_at >= start_date
            )
            total_query = _apply_resource_type_filter(total_query, resource_types)
            total_result = await self.db.execute(total_query)
            total_shares = total_result.scalar() or 0

            # Get unique sharers
            unique_query = select(func.count(func.distinct(ShareEvent.user_id))).where(
                ShareEvent.shared_at >= start_date
            )
            unique_query = _apply_resource_type_filter(unique_query, resource_types)
            unique_result = await self.db.execute(unique_query)
            unique_sharers = unique_result.scalar() or 0

            # Calculate average
            avg_shares = total_shares / max(unique_sharers, 1)

            return {
                "total_shares": total_shares,
                "unique_sharers": unique_sharers,
                "avg_shares_per_user": round(avg_shares, 2),
            }
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get share metrics: {e}")
            return {
                "total_shares": 0,
                "unique_sharers": 0,
                "avg_shares_per_user": 0.0,
            }

    async def _get_top_sharers(
        self, start_date: datetime, resource_types: Optional[List[str]] = None
    ) -> List[TopSharer]:
        try:
            query = select(
                ShareEvent.user_id,
                func.count(ShareEvent.id).label("share_count"),
            ).where(
                and_(
                    ShareEvent.shared_at >= start_date,
                    ShareEvent.user_id.isnot(None),
                )
            )

            query = _apply_resource_type_filter(query, resource_types)

            query = query.group_by(
                ShareEvent.user_id
            ).order_by(
                func.count(ShareEvent.id).desc()
            ).limit(
                10
            )

            result = await self.db.execute(query)
            rows = result.all()

            top_sharers = []
            for user_id, share_count in rows:
                user = await self.db.get(User, user_id)
                if user:
                    # Get favorite platform for this user
                    favorite = await self._get_user_favorite_platform(user_id, start_date)
                    top_sharers.append(
                        TopSharer(
                            user_id=user_id,
                            user_name=f"{user.first_name} {user.last_name}",
                            email=user.email,
                            total_shares=share_count,
                            favorite_platform=favorite,
                        )
                    )

            return top_sharers
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get top sharers: {e}")
            return []

    async def _get_user_favorite_platform(
        self, user_id: int, start_date: datetime
    ) -> Optional[str]:
        try:
            query = select(
                ShareEvent.platform,
                func.count(ShareEvent.id).label("count"),
            ).where(
                and_(
                    ShareEvent.user_id == user_id,
                    ShareEvent.shared_at >= start_date,
                )
            ).group_by(
                ShareEvent.platform
            ).order_by(
                func.count(ShareEvent.id).desc()
            ).limit(
                1
            )

            result = await self.db.execute(query)
            row = result.first()
            return row[0] if row else None
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get user favorite platform: {e}")
            return None

    async def _get_share_trends(
        self,
        start_date: datetime,
        end_date: datetime,
        days: int,
        resource_types: Optional[List[str]] = None,
    ) -> List[ShareTrendDataPoint]:
        try:
            # Query shares grouped by date
            query = select(
                func.date(ShareEvent.shared_at).label("date"),
                func.count(ShareEvent.id).label("total_shares"),
                func.count(func.distinct(ShareEvent.user_id)).label("unique_sharers"),
            ).where(
                ShareEvent.shared_at >= start_date
            )

            query = _apply_resource_type_filter(query, resource_types)

            query = query.group_by(
                func.date(ShareEvent.shared_at)
            ).order_by(
                func.date(ShareEvent.shared_at)
            )

            result = await self.db.execute(query)
            rows = result.all()

            trends = []
            for date_obj, total_shares, unique_sharers in rows:
                trends.append(
                    ShareTrendDataPoint(
                        date=str(date_obj),
                        total_shares=total_shares,
                        unique_sharers=unique_sharers,
                    )
                )

            # If no data, return empty list
            if not trends:
                # Generate placeholder data for all days
                current = start_date.date()
                end = end_date.date()
                while current <= end:
                    trends.append(
                        ShareTrendDataPoint(
                            date=str(current),
                            total_shares=0,
                            unique_sharers=0,
                        )
                    )
                    current += timedelta(days=1)

            return trends
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get share trends: {e}")
            return []

    async def _get_previous_share_count(
        self,
        start_date: datetime,
        end_date: datetime,
        resource_types: Optional[List[str]] = None,
    ) -> int:
        try:
            query = select(func.count(ShareEvent.id)).where(
                and_(
                    ShareEvent.shared_at >= start_date,
                    ShareEvent.shared_at < end_date,
                )
            )
            query = _apply_resource_type_filter(query, resource_types)
            result = await self.db.execute(query)
            return result.scalar() or 0
        except Exception as e:  # noqa: BLE001 — analytics — must not block primary flow
            logger.warning(f"Failed to get previous share count: {e}")
            return 0
