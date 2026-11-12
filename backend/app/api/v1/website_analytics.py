# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Website Analytics API - Umami proxy endpoints.

Proxies requests to Umami analytics API so the L30 admin dashboard
can display website traffic data without exposing Umami credentials.
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.config import get_settings
from ...models.user import User
from ...services.umami_client import UmamiUnavailable, umami_get
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/website-analytics", tags=["website-analytics"])


async def _umami_get(path: str, params: Optional[dict] = None) -> dict:
    try:
        return await umami_get(path, params)
    except UmamiUnavailable as exc:
        msg = str(exc)
        if "not configured" in msg:
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=502, detail=msg) from exc


@router.get("/stats")
async def get_website_stats(
    days: int = Query(30, ge=1, le=365),
    staff_user: User = Depends(require_staff),
):
    """Overall website stats: pageviews, visitors, visits, bounce rate."""
    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")

    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=days)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)
    return await _umami_get(
        f"/websites/{settings.umami_website_id}/stats",
        {"startAt": start, "endAt": end},
    )


@router.get("/pageviews")
async def get_pageviews(
    days: int = Query(30, ge=1, le=365),
    unit: str = Query("day", pattern="^(hour|day|week|month)$"),
    staff_user: User = Depends(require_staff),
):
    """Pageview and session counts over time."""
    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")

    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=days)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)
    return await _umami_get(
        f"/websites/{settings.umami_website_id}/pageviews",
        {"startAt": start, "endAt": end, "unit": unit},
    )


@router.get("/metrics/{metric_type}")
async def get_metrics(
    metric_type: str,
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(10, ge=1, le=100),
    staff_user: User = Depends(require_staff),
):
    """Top pages, referrers, browsers, OS, devices, countries, etc."""
    allowed = {"path", "entry", "exit", "title", "query", "referrer", "channel", "domain", "country", "region", "city", "browser", "os", "device", "language", "screen", "event", "hostname", "tag", "distinctId", "url"}
    if metric_type not in allowed:
        raise HTTPException(status_code=400, detail=f"Invalid metric type. Allowed: {', '.join(sorted(allowed))}")

    if metric_type == "url":
        metric_type = "path"

    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")

    now = datetime.now(timezone.utc)
    start = int((now - timedelta(days=days)).timestamp() * 1000)
    end = int(now.timestamp() * 1000)
    return await _umami_get(
        f"/websites/{settings.umami_website_id}/metrics",
        {"startAt": start, "endAt": end, "type": metric_type, "limit": limit},
    )


@router.get("/active")
async def get_active_visitors(
    staff_user: User = Depends(require_staff),
):
    """Current active visitors on the site."""
    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")
    return await _umami_get(f"/websites/{settings.umami_website_id}/active")
