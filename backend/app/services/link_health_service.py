# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
from app.core.logging import get_logger
import ssl
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import AsyncSessionLocal
from ..models.bibframe import BibframeInstance, InstanceType
from ..models.learning import ExternalResource, LessonResource
from ..models.link_health import (
    LinkHealthAlert,
    LinkHealthCheck,
    LinkHealthConfig,
    LinkHealthSummary,
    LinkSource,
    LinkStatus,
)
from ..models.streaming import StreamingCatalogItem

logger = get_logger(__name__)


class LinkHealthService:

    DEFAULT_TIMEOUT = 30.0
    DEFAULT_USER_AGENT = "L30Library-LinkChecker/1.0"
    MAX_REDIRECTS = 10

    def __init__(self, db: AsyncSession):
        self.db = db
        self._config: LinkHealthConfig | None = None

    # =========================================================================
    # Configuration
    # =========================================================================

    async def get_config(self) -> LinkHealthConfig:
        if self._config:
            return self._config

        result = await self.db.execute(select(LinkHealthConfig).limit(1))
        config = result.scalar_one_or_none()

        if not config:
            config = LinkHealthConfig()
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)

        self._config = config
        return config

    async def update_config(self, **kwargs) -> LinkHealthConfig:
        config = await self.get_config()
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
        await self.db.commit()
        await self.db.refresh(config)
        self._config = config
        return config

    # =========================================================================
    # URL Hashing
    # =========================================================================

    @staticmethod
    def hash_url(url: str) -> str:
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    # =========================================================================
    # Single URL Check
    # =========================================================================

    async def check_url(
        self,
        url: str,
        source: LinkSource = LinkSource.other,
        source_id: int | None = None,
        source_name: str | None = None,
        timeout: float | None = None,
    ) -> LinkHealthCheck:
        config = await self.get_config()
        timeout = timeout or config.default_timeout_seconds

        url_hash = self.hash_url(url)
        check = LinkHealthCheck(
            url=url,
            url_hash=url_hash,
            source=source,
            source_id=source_id,
            source_name=source_name,
            status=LinkStatus.unknown,
        )

        start_time = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                max_redirects=config.max_redirects,
                verify=True,
            ) as client:
                # Try HEAD first (faster, less bandwidth)
                try:
                    response = await client.head(
                        url,
                        headers={"User-Agent": config.user_agent or self.DEFAULT_USER_AGENT},
                    )
                except httpx.HTTPStatusError:
                    # Some servers don't support HEAD, fall back to GET
                    response = await client.get(
                        url,
                        headers={"User-Agent": config.user_agent or self.DEFAULT_USER_AGENT},
                    )

                end_time = datetime.now(timezone.utc)
                response_time = (end_time - start_time).total_seconds() * 1000

                check.http_status_code = response.status_code
                check.response_time_ms = response_time
                check.check_duration_ms = response_time
                check.final_url = str(response.url)
                check.redirect_count = len(response.history)
                check.content_type = response.headers.get("content-type")

                content_length = response.headers.get("content-length")
                if content_length:
                    check.content_length = int(content_length)

                # Determine status
                if 200 <= response.status_code < 400:
                    if response_time > config.degraded_response_time_ms:
                        check.status = LinkStatus.degraded
                    else:
                        check.status = LinkStatus.healthy
                elif 400 <= response.status_code < 500:
                    check.status = LinkStatus.broken
                    check.error_message = f"Client error: {response.status_code}"
                else:
                    check.status = LinkStatus.broken
                    check.error_message = f"Server error: {response.status_code}"

                # Check SSL certificate
                if config.ssl_check_enabled and url.startswith("https://"):
                    ssl_info = await self._check_ssl(url)
                    check.ssl_valid = ssl_info.get("valid", False)
                    check.ssl_expires_at = ssl_info.get("expires_at")

        except httpx.TimeoutException:
            check.status = LinkStatus.timeout
            check.error_message = f"Request timed out after {timeout} seconds"

        except httpx.TooManyRedirects:
            check.status = LinkStatus.redirect_loop
            check.error_message = f"Too many redirects (>{config.max_redirects})"

        except httpx.ConnectError as e:
            error_msg = str(e).lower()
            if "dns" in error_msg or "getaddrinfo" in error_msg or "name resolution" in error_msg:
                check.status = LinkStatus.dns_error
                check.error_message = f"DNS resolution failed: {e}"
            else:
                check.status = LinkStatus.broken
                check.error_message = f"Connection error: {e}"

        except ssl.SSLError as e:
            check.status = LinkStatus.ssl_error
            check.error_message = f"SSL error: {e}"
            check.ssl_valid = False

        except Exception as e:
            check.status = LinkStatus.broken
            check.error_message = f"Unexpected error: {e}"
            logger.exception(f"Unexpected error checking URL {url}")

        finally:
            check.checked_at = datetime.now(timezone.utc)
            if not check.check_duration_ms:
                check.check_duration_ms = (
                    datetime.now(timezone.utc) - start_time
                ).total_seconds() * 1000

        # Save check result
        self.db.add(check)
        await self.db.commit()

        # Update summary
        await self._update_summary(check)

        return check

    async def _check_ssl(self, url: str) -> dict[str, Any]:
        try:
            parsed = urlparse(url)
            hostname = parsed.hostname
            port = parsed.port or 443

            # Create SSL context
            context = ssl.create_default_context()

            # Connect and get certificate
            loop = asyncio.get_event_loop()
            cert = await loop.run_in_executor(
                None,
                lambda: self._get_ssl_cert(hostname, port, context),
            )

            if cert:
                expires_str = cert.get("notAfter")
                if expires_str:
                    # Parse SSL date format: 'Mar 15 12:00:00 2025 GMT'
                    expires_at = datetime.strptime(
                        expires_str, "%b %d %H:%M:%S %Y %Z"
                    ).replace(tzinfo=timezone.utc)
                    return {
                        "valid": expires_at > datetime.now(timezone.utc),
                        "expires_at": expires_at,
                    }

            return {"valid": True}

        except (ssl.SSLError, OSError, ValueError) as e:
            logger.debug(f"SSL check failed for {url}: {e}")
            return {"valid": False, "error": str(e)}

    def _get_ssl_cert(self, hostname: str, port: int, context: ssl.SSLContext) -> dict | None:
        import socket

        try:
            with socket.create_connection((hostname, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                    return ssock.getpeercert()
        except (ssl.SSLError, socket.error, OSError):
            return None

    # =========================================================================
    # Summary Management
    # =========================================================================

    async def _update_summary(self, check: LinkHealthCheck) -> LinkHealthSummary:
        result = await self.db.execute(
            select(LinkHealthSummary).where(
                LinkHealthSummary.url_hash == check.url_hash
            )
        )
        summary = result.scalar_one_or_none()

        if not summary:
            summary = LinkHealthSummary(
                url=check.url,
                url_hash=check.url_hash,
                source=check.source,
                source_id=check.source_id,
                source_name=check.source_name,
                first_checked_at=check.checked_at,
            )
            self.db.add(summary)

        # Update metrics
        summary.current_status = check.status
        summary.last_http_status = check.http_status_code
        summary.last_error_message = check.error_message
        summary.last_response_time_ms = check.response_time_ms
        summary.last_checked_at = check.checked_at
        summary.total_checks += 1

        is_success = check.status in (LinkStatus.healthy, LinkStatus.degraded)

        if is_success:
            summary.successful_checks += 1
            summary.consecutive_failures = 0
            summary.last_successful_at = check.checked_at

            # Check if recovered from failure
            if summary.alert_sent and not summary.alert_acknowledged:
                await self._create_recovery_alert(summary)
                summary.alert_sent = False

        else:
            summary.failed_checks += 1
            summary.consecutive_failures += 1
            summary.last_failed_at = check.checked_at

            # Check if alert threshold reached
            config = await self.get_config()
            if (
                summary.consecutive_failures >= config.alert_on_consecutive_failures
                and not summary.alert_sent
                and summary.is_monitored
            ):
                await self._create_broken_alert(summary, check)
                summary.alert_sent = True
                summary.alert_sent_at = datetime.now(timezone.utc)

        # Calculate uptime percentage
        if summary.total_checks > 0:
            summary.uptime_percentage = (
                summary.successful_checks / summary.total_checks
            ) * 100

        # Calculate average response time (moving average)
        if check.response_time_ms:
            if summary.avg_response_time_ms:
                # Exponential moving average
                summary.avg_response_time_ms = (
                    0.9 * summary.avg_response_time_ms + 0.1 * check.response_time_ms
                )
            else:
                summary.avg_response_time_ms = check.response_time_ms

        await self.db.commit()
        return summary

    # =========================================================================
    # Alert Management
    # =========================================================================

    async def _create_broken_alert(
        self, summary: LinkHealthSummary, check: LinkHealthCheck
    ) -> LinkHealthAlert:
        severity = "critical" if summary.source == LinkSource.palace else "warning"

        alert = LinkHealthAlert(
            url_hash=summary.url_hash,
            url=summary.url,
            source=summary.source,
            alert_type="broken",
            severity=severity,
            message=(
                f"Link is broken after {summary.consecutive_failures} consecutive failures. "
                f"Last error: {check.error_message or 'HTTP ' + str(check.http_status_code)}"
            ),
        )
        self.db.add(alert)
        await self.db.commit()

        logger.warning(
            f"Link health alert: {summary.url} is broken "
            f"({summary.consecutive_failures} failures)"
        )

        return alert

    async def _create_recovery_alert(self, summary: LinkHealthSummary) -> LinkHealthAlert:
        alert = LinkHealthAlert(
            url_hash=summary.url_hash,
            url=summary.url,
            source=summary.source,
            alert_type="recovered",
            severity="info",
            message="Link has recovered and is now accessible.",
            status="resolved",
            resolved_at=datetime.now(timezone.utc),
        )
        self.db.add(alert)
        await self.db.commit()

        logger.info(f"Link health recovered: {summary.url}")

        return alert

    async def acknowledge_alert(
        self, alert_id: int, user_id: int, notes: str | None = None
    ) -> LinkHealthAlert | None:
        result = await self.db.execute(
            select(LinkHealthAlert).where(LinkHealthAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = "acknowledged"
            alert.acknowledged_by = user_id
            alert.acknowledged_at = datetime.now(timezone.utc)
            if notes:
                alert.resolution_notes = notes
            await self.db.commit()

        return alert

    async def resolve_alert(
        self, alert_id: int, notes: str | None = None
    ) -> LinkHealthAlert | None:
        result = await self.db.execute(
            select(LinkHealthAlert).where(LinkHealthAlert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if alert:
            alert.status = "resolved"
            alert.resolved_at = datetime.now(timezone.utc)
            if notes:
                alert.resolution_notes = notes
            await self.db.commit()

        return alert

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def _check_one_url_background(
        self,
        db: AsyncSession,
        semaphore: asyncio.Semaphore,
        stats: dict[str, int],
        url: str,
        source: LinkSource,
        source_id: int | None,
        source_name: str | None,
        resource_label: str,
    ) -> None:
        async with semaphore:
            stats["total"] += 1
            try:
                svc = LinkHealthService(db)
                check = await svc.check_url(
                    url=url,
                    source=source,
                    source_id=source_id,
                    source_name=source_name,
                )
                if check.status == LinkStatus.healthy:
                    stats["healthy"] += 1
                elif check.status == LinkStatus.degraded:
                    stats["degraded"] += 1
                else:
                    stats["broken"] += 1
            except Exception as e:  # noqa: BLE001 - per-item boundary: sweep must not abort batch
                logger.error(f"Error checking {resource_label}: {e}")
                stats["errors"] += 1

    async def check_all_external_resources(self) -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(ExternalResource).where(ExternalResource.source_url.isnot(None))
            )
            resources = result.scalars().all()

            stats = {"total": 0, "healthy": 0, "degraded": 0, "broken": 0, "errors": 0}
            config_result = await db.execute(select(LinkHealthConfig).limit(1))
            config = config_result.scalar_one_or_none()
            max_concurrent = config.max_concurrent_checks if config else 10

            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [
                self._check_one_url_background(
                    db=db,
                    semaphore=semaphore,
                    stats=stats,
                    url=resource.source_url,
                    source=LinkSource.external_resource,
                    source_id=resource.id,
                    source_name=resource.title,
                    resource_label=f"external_resource/{resource.id}",
                )
                for resource in resources
            ]
            await asyncio.gather(*tasks)

        return stats

    async def check_all_lesson_resources(self) -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(LessonResource).where(
                    LessonResource.resource_type == "link",
                    LessonResource.url.isnot(None),
                )
            )
            resources = result.scalars().all()

            stats = {"total": 0, "healthy": 0, "degraded": 0, "broken": 0, "errors": 0}
            config_result = await db.execute(select(LinkHealthConfig).limit(1))
            config = config_result.scalar_one_or_none()
            max_concurrent = config.max_concurrent_checks if config else 10

            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [
                self._check_one_url_background(
                    db=db,
                    semaphore=semaphore,
                    stats=stats,
                    url=resource.url,
                    source=LinkSource.lesson_resource,
                    source_id=resource.id,
                    source_name=resource.title,
                    resource_label=f"lesson_resource/{resource.id}",
                )
                for resource in resources
            ]
            await asyncio.gather(*tasks)

        return stats

    async def check_all_catalog_links(self) -> dict[str, int]:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(BibframeInstance).where(
                    BibframeInstance.access_url.isnot(None),
                    BibframeInstance.instance_type == InstanceType.electronic,
                )
            )
            instances = result.scalars().all()

            stats = {"total": 0, "healthy": 0, "degraded": 0, "broken": 0, "errors": 0}
            config_result = await db.execute(select(LinkHealthConfig).limit(1))
            config = config_result.scalar_one_or_none()
            max_concurrent = config.max_concurrent_checks if config else 10

            semaphore = asyncio.Semaphore(max_concurrent)
            tasks = [
                self._check_one_url_background(
                    db=db,
                    semaphore=semaphore,
                    stats=stats,
                    url=instance.access_url,
                    source=LinkSource.catalog_link,
                    source_id=instance.id,
                    source_name=instance.title,
                    resource_label=f"bibframe_instance/{instance.id}",
                )
                for instance in instances
            ]
            await asyncio.gather(*tasks)

        return stats

    async def check_digital_platform_endpoints(self) -> dict[str, Any]:
        endpoints = [
            {
                "url": "https://circulation.thepalaceproject.org/",
                "source": LinkSource.palace,
                "name": "Palace Project API",
            },
        ]

        results = {}
        for endpoint in endpoints:
            try:
                check = await self.check_url(
                    url=endpoint["url"],
                    source=endpoint["source"],
                    source_name=endpoint["name"],
                )
                results[endpoint["name"]] = {
                    "status": str(check.status),
                    "response_time_ms": check.response_time_ms,
                    "http_status": check.http_status_code,
                }
            except Exception as e:  # noqa: BLE001 - per-endpoint boundary: digital-platform sweep must continue past individual failures
                results[endpoint["name"]] = {
                    "status": "error",
                    "error": str(e),
                }

        return results

    # =========================================================================
    # Queries and Reports
    # =========================================================================

    async def get_broken_links(
        self,
        source: LinkSource | None = None,
        limit: int = 100,
        offset: int = 0,
        include_unmonitored: bool = False,
    ) -> list[LinkHealthSummary]:
        query = select(LinkHealthSummary).where(
            LinkHealthSummary.current_status.in_([
                LinkStatus.broken,
                LinkStatus.timeout,
                LinkStatus.dns_error,
                LinkStatus.ssl_error,
            ])
        )

        if not include_unmonitored:
            query = query.where(LinkHealthSummary.is_monitored == True)

        if source:
            query = query.where(LinkHealthSummary.source == source)

        query = query.order_by(
            LinkHealthSummary.consecutive_failures.desc()
        ).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_degraded_links(
        self,
        min_response_time_ms: float | None = None,
        limit: int = 100,
        include_unmonitored: bool = False,
    ) -> list[LinkHealthSummary]:
        config = await self.get_config()
        threshold = min_response_time_ms or config.degraded_response_time_ms

        query = select(LinkHealthSummary).where(
            or_(
                LinkHealthSummary.current_status == LinkStatus.degraded,
                LinkHealthSummary.avg_response_time_ms > threshold,
            )
        )

        if not include_unmonitored:
            query = query.where(LinkHealthSummary.is_monitored == True)

        query = query.order_by(
            LinkHealthSummary.avg_response_time_ms.desc()
        ).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_health_summary_stats(self) -> dict[str, Any]:
        # Count by status
        status_counts = await self.db.execute(
            select(
                LinkHealthSummary.current_status,
                func.count(LinkHealthSummary.id),
            )
            .where(LinkHealthSummary.is_monitored == True)
            .group_by(LinkHealthSummary.current_status)
        )

        stats = {
            "total_monitored": 0,
            "by_status": {},
            "by_source": {},
            "open_alerts": 0,
            "avg_uptime_percentage": 0,
        }

        for status, count in status_counts:
            stats["by_status"][status.value] = count
            stats["total_monitored"] += count

        # Count by source
        source_counts = await self.db.execute(
            select(
                LinkHealthSummary.source,
                func.count(LinkHealthSummary.id),
            )
            .where(LinkHealthSummary.is_monitored == True)
            .group_by(LinkHealthSummary.source)
        )

        for source, count in source_counts:
            stats["by_source"][source.value] = count

        # Open alerts count
        alert_count = await self.db.execute(
            select(func.count(LinkHealthAlert.id)).where(
                LinkHealthAlert.status == "open"
            )
        )
        stats["open_alerts"] = alert_count.scalar() or 0

        # Average uptime
        avg_uptime = await self.db.execute(
            select(func.avg(LinkHealthSummary.uptime_percentage)).where(
                LinkHealthSummary.is_monitored == True,
                LinkHealthSummary.uptime_percentage.isnot(None),
            )
        )
        stats["avg_uptime_percentage"] = round(avg_uptime.scalar() or 0, 2)

        return stats

    async def get_open_alerts(
        self,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[LinkHealthAlert]:
        query = select(LinkHealthAlert).where(LinkHealthAlert.status == "open")

        if severity:
            query = query.where(LinkHealthAlert.severity == severity)

        query = query.order_by(LinkHealthAlert.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_check_history(
        self,
        url: str,
        days: int = 7,
        limit: int = 100,
    ) -> list[LinkHealthCheck]:
        url_hash = self.hash_url(url)
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(LinkHealthCheck)
            .where(
                LinkHealthCheck.url_hash == url_hash,
                LinkHealthCheck.checked_at >= since,
            )
            .order_by(LinkHealthCheck.checked_at.desc())
            .limit(limit)
        )

        return list(result.scalars().all())

    async def set_monitoring(
        self, summary_id: int, is_monitored: bool
    ) -> LinkHealthSummary | None:
        result = await self.db.execute(
            select(LinkHealthSummary).where(LinkHealthSummary.id == summary_id)
        )
        summary = result.scalar_one_or_none()

        if summary:
            summary.is_monitored = is_monitored
            await self.db.commit()
            await self.db.refresh(summary)

        return summary

    # =========================================================================
    # Maintenance
    # =========================================================================

    async def cleanup_old_checks(self, days: int | None = None) -> int:
        config = await self.get_config()
        days = days or config.keep_history_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            delete(LinkHealthCheck).where(LinkHealthCheck.checked_at < cutoff)
        )
        await self.db.commit()

        deleted = result.rowcount
        logger.info(f"Cleaned up {deleted} old link health checks (>{days} days)")
        return deleted

    async def remove_stale_summaries(self, days: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            delete(LinkHealthSummary).where(
                LinkHealthSummary.last_checked_at < cutoff,
            )
        )
        await self.db.commit()

        deleted = result.rowcount
        logger.info(f"Removed {deleted} stale link health summaries")
        return deleted


# Singleton instance
_link_health_service: LinkHealthService | None = None


def get_link_health_service(db: AsyncSession) -> LinkHealthService:
    return LinkHealthService(db)
