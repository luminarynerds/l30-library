# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
QR Analytics API.

Aggregates pageviews of URLs that were landed from a staff QR poster
(identified by the `?qr=<slug>` query param the poster always appends).
Source is Umami's existing pageview stream; no new table, no migration,
no patron-facing beacon.

Slug conventions (must stay in sync with frontend/src/pages/_qrSlug.ts):
  /tech                 -> tech-launchpad
  /tech?p=<param>       -> tech-p-<param>
  /guides/<id>          -> guide-<id>
  /legal                -> legal-main
  /legal/calculators    -> legal-calculators

Umami quirk: the `type=url` metric returns 400 on the deployed Umami v3
instance, and `type=path` strips query strings. So we use `type=query`,
which returns a distribution of {x: "<querystring>", y: <count>} rows,
and pluck `qr=<slug>` out of each row.

`y` here represents pageviews. Visitors are not broken out by this
endpoint, so the schema exposes `visitors` as optional.
"""

import asyncio
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import parse_qs

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.config import get_settings
from ...models.user import User
from ...services.umami_client import UmamiUnavailable, umami_get
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/qr-analytics", tags=["qr-analytics"])

# Hard cap on per-row query-string fanout. Umami's `type=query` is already
# capped server-side via the `limit` param we pass; this is a defensive
# bound on parsing in case Umami ever returns a giant row.
_MAX_QUERY_ROW_LEN = 4096


async def _umami_get(path: str, params: Optional[dict] = None) -> list:
    try:
        result = await umami_get(path, params)
    except UmamiUnavailable as exc:
        msg = str(exc)
        if "not configured" in msg:
            raise HTTPException(status_code=503, detail=msg) from exc
        raise HTTPException(status_code=502, detail=msg) from exc
    if not isinstance(result, list):
        # Defensive: Umami's metrics endpoint should always return a list.
        logger.warning("Umami metrics returned non-list: %r", type(result))
        return []
    return result


def _extract_qr_slug(query_string: str) -> Optional[str]:
    if not query_string or len(query_string) > _MAX_QUERY_ROW_LEN:
        return None
    if "qr=" not in query_string:
        return None
    try:
        parsed = parse_qs(query_string, keep_blank_values=False)
    except ValueError:
        return None
    values = parsed.get("qr")
    if not values:
        return None
    slug = values[0].strip()
    return slug or None


def _aggregate_query_rows(rows: list) -> dict[str, int]:
    totals: dict[str, int] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug = _extract_qr_slug(str(row.get("x") or ""))
        if not slug:
            continue
        try:
            count = int(row.get("y") or 0)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        totals[slug] = totals.get(slug, 0) + count
    return totals


def _ms(dt: datetime) -> int:
    return int(dt.timestamp() * 1000)


async def _fetch_query_rows(website_id: str, start_ms: int, end_ms: int) -> list:
    return await _umami_get(
        f"/websites/{website_id}/metrics",
        {
            "startAt": start_ms,
            "endAt": end_ms,
            "type": "query",
            "limit": 500,
        },
    )


@router.get("")
async def get_qr_analytics(
    days: int = Query(30, ge=1, le=365),
    staff_user: User = Depends(require_staff),
) -> list[dict]:
    """
    Per-slug QR-scan counts over the last `days`.

    Returns a list of `{slug, pageviews, visitors?}` ordered by pageviews
    descending. `visitors` is omitted because Umami's `type=query` metric
    does not break visitors out per query string.
    """
    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")

    now = datetime.now(timezone.utc)
    rows = await _fetch_query_rows(
        settings.umami_website_id, _ms(now - timedelta(days=days)), _ms(now)
    )
    totals = _aggregate_query_rows(rows)

    return [
        {"slug": slug, "pageviews": count}
        for slug, count in sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    ]


def _month_windows(now: datetime, months: int) -> list[tuple[str, datetime, datetime]]:
    # Anchor to the first of the current month, UTC.
    anchor = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
    windows: list[tuple[str, datetime, datetime]] = []
    for i in range(months - 1, -1, -1):
        # Walk i months back from the anchor.
        y = anchor.year
        m = anchor.month - i
        while m <= 0:
            m += 12
            y -= 1
        start = datetime(y, m, 1, tzinfo=timezone.utc)
        # Next month start = end exclusive. Clamp the most-recent window's
        # end to `now` so we don't ask Umami for a future range.
        ny = y + (1 if m == 12 else 0)
        nm = 1 if m == 12 else m + 1
        end = datetime(ny, nm, 1, tzinfo=timezone.utc)
        if end > now:
            end = now
        windows.append((f"{y:04d}-{m:02d}", start, end))
    return windows


@router.get("/by-month")
async def get_qr_analytics_by_month(
    months: int = Query(6, ge=1, le=24),
    staff_user: User = Depends(require_staff),
) -> dict:
    """
    Per-slug QR-scan counts grouped by month, for trending.

    Returns:
      {
        "months": ["2026-01", "2026-02", ...],   # oldest -> newest
        "series": [
          {"slug": "tech-p-printer", "counts": [3, 7, 12, ...]},
          ...
        ]
      }

    Issues one Umami metrics call per month window (parallelized with
    asyncio.gather). The `slug` ordering matches the all-time aggregation
    used by GET / (pageviews desc, ties by slug).
    """
    settings = get_settings()
    if not settings.umami_website_id:
        raise HTTPException(status_code=503, detail="Umami website ID not configured")

    now = datetime.now(timezone.utc)
    windows = _month_windows(now, months)

    fetches = [
        _fetch_query_rows(settings.umami_website_id, _ms(start), _ms(end))
        for _label, start, end in windows
    ]
    rows_per_window = await asyncio.gather(*fetches)

    # Aggregate each window, then unify into a slug -> [counts...] series.
    per_window_totals: list[dict[str, int]] = [
        _aggregate_query_rows(rows) for rows in rows_per_window
    ]
    all_slugs: set[str] = set()
    for totals in per_window_totals:
        all_slugs.update(totals.keys())

    grand_totals: dict[str, int] = {}
    for slug in all_slugs:
        grand_totals[slug] = sum(totals.get(slug, 0) for totals in per_window_totals)

    ordered_slugs = sorted(all_slugs, key=lambda s: (-grand_totals[s], s))

    return {
        "months": [label for label, _s, _e in windows],
        "series": [
            {
                "slug": slug,
                "counts": [totals.get(slug, 0) for totals in per_window_totals],
            }
            for slug in ordered_slugs
        ],
    }
