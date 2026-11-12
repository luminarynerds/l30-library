# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cover image proxy.

Replaces direct browser fetches to third-party cover CDNs (images.unsplash.com,
placehold.co, covers.openlibrary.org, etc.) with a backend-mediated fetch +
on-disk cache. Two reasons:

1. Patron privacy. Direct CDN fetches leak ``Referer: l30.org/catalog?q=...``
   to third parties, which violates patron-record confidentiality statutes in
   most US jurisdictions (and is just bad practice everywhere else).
2. Reliability. Hotlinked CDNs go away, throttle, or change ToS; caching
   locally means the catalog keeps looking like a catalog even when an
   upstream disappears.

The route is intentionally narrow: it only serves covers that match an
existing :class:`CatalogItem`'s ``cover_url`` (or primary uploaded
:class:`CatalogImage`). It is NOT a generic URL proxy.
"""
from __future__ import annotations

import contextlib
import hashlib
from app.core.logging import get_logger
import mimetypes
import os
from pathlib import Path
from urllib.parse import urljoin, urlparse

import io

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.catalog import CatalogItem, CatalogingStatus, SensitivityLevel
from ....models.user import User, UserRole
from ..auth import get_optional_user
from ..dependencies import is_staff_or_admin
from .helpers import _get_catalog_item_with_images

logger = get_logger(__name__)

router = APIRouter()

# Cache dir. Lives inside the existing l30_uploads volume so it persists
# across container rebuilds without adding a new volume to compose.
# Override with COVER_CACHE_DIR if you need to relocate it.
COVER_CACHE_DIR = Path(os.environ.get("COVER_CACHE_DIR", "/app/uploads/cover_cache"))

# Upstreams we are willing to fetch from. Anything else 404s -- we do not
# want this to become an open proxy.
_ALLOWED_UPSTREAM_HOSTS = {
    "images.unsplash.com",
    "placehold.co",
    "covers.openlibrary.org",
    "openlibrary.org",
    "books.google.com",
    "coverartarchive.org",
    "ia.us.archive.org",
    "archive.org",
}


def _host_allowed(hostname: str | None) -> bool:
    """Allowlist check for a cover upstream host.

    Exact match against ``_ALLOWED_UPSTREAM_HOSTS``, plus any Internet Archive
    CDN node: Open Library ``/b/id/...`` covers 302 through archive.org to a
    numbered node (e.g. ``ia600703.us.archive.org``), which the literal
    ``ia.us.archive.org`` entry can never match.
    """
    if not hostname:
        return False
    if hostname in _ALLOWED_UPSTREAM_HOSTS:
        return True
    return hostname.endswith(".us.archive.org")

# Sniff a content-type if the upstream does not tell us.
_EXT_CONTENT_TYPES = {
    ".jpeg": "image/jpeg",
    ".jpg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".avif": "image/avif",
}

# Reasonable cover ceiling. Real covers are well under this; the cap exists
# so a misconfigured upstream cannot fill the disk.
_MAX_COVER_BYTES = 5 * 1024 * 1024
_FETCH_TIMEOUT_SECONDS = 10.0

# OpenLibrary (and some other CDNs) answer "no cover available" with a tiny
# sentinel image -- historically a 43-byte 1x1 served with HTTP 200. Real book
# covers are always several KB. Anything under this floor is treated as "no
# cover": we 404 (so the frontend shows its generative thumbnail) instead of
# caching a blank 1x1 that renders as an empty box.
_MIN_COVER_BYTES = 256

# Covers are NOT immutable: a bad/sentinel cover_url gets corrected by the
# backfill job, and ``immutable`` would pin the stale image in every client
# for a full day. Allow revalidation (ETag) and keep the fresh window short so
# a corrected cover propagates within the hour.
_COVER_CACHE_CONTROL = "public, max-age=3600, stale-while-revalidate=86400"


def _resolve_cover_source(item: CatalogItem) -> str | None:
    images = getattr(item, "images", None) or []
    primary = next((img for img in images if img.is_primary), None) or (
        images[0] if images else None
    )
    if primary and primary.image_url:
        return primary.image_url
    return item.cover_url or None


def _is_internal_url(url: str) -> bool:
    parsed = urlparse(url)
    if not parsed.scheme and url.startswith("/"):
        return True
    return parsed.scheme == "file"


def _cache_path_for(url: str) -> Path:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return COVER_CACHE_DIR / digest[:2] / digest[2:4] / digest


def _sniff_content_type(url: str, upstream_ct: str | None) -> str:
    if upstream_ct and upstream_ct.startswith("image/"):
        return upstream_ct.split(";", 1)[0].strip()
    parsed = urlparse(url)
    ext = os.path.splitext(parsed.path)[1].lower()
    if ext in _EXT_CONTENT_TYPES:
        return _EXT_CONTENT_TYPES[ext]
    guessed, _ = mimetypes.guess_type(parsed.path)
    if guessed and guessed.startswith("image/"):
        return guessed
    return "application/octet-stream"


async def _fetch_and_cache(url: str, cache_path: Path) -> tuple[bytes, str]:
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(
        timeout=_FETCH_TIMEOUT_SECONDS,
        follow_redirects=False,
        headers={"User-Agent": "L30-CoverProxy/1.0 (+https://l30.org)"},
    ) as client:
        upstream = await client.get(url)
        hops = 0
        while upstream.is_redirect and hops < 3:
            location = upstream.headers.get("location")
            if not location:
                break
            next_url = urljoin(url, location)
            hop = urlparse(next_url)
            if hop.scheme not in ("http", "https") or not _host_allowed(hop.hostname):
                raise HTTPException(
                    status_code=502,
                    detail="Cover upstream redirected to a non-allowlisted host",
                )
            upstream = await client.get(next_url)
            url = next_url
            hops += 1
    if upstream.status_code != 200:
        raise HTTPException(
            status_code=502,
            detail=f"Upstream cover fetch failed: {upstream.status_code}",
        )
    body = upstream.content
    if len(body) > _MAX_COVER_BYTES:
        raise HTTPException(status_code=502, detail="Upstream cover too large")
    if len(body) < _MIN_COVER_BYTES:
        # Upstream "no cover" sentinel -- do not cache it as if it were a cover.
        raise HTTPException(status_code=404, detail="Cover not found")
    content_type = _sniff_content_type(url, upstream.headers.get("content-type"))
    tmp_path = cache_path.with_suffix(".part")
    tmp_path.write_bytes(body)
    tmp_path.replace(cache_path)
    cache_path.with_suffix(".ct").write_text(content_type, encoding="utf-8")
    return body, content_type


def _read_cached_content_type(cache_path: Path, url: str) -> str:
    ct_path = cache_path.with_suffix(".ct")
    if ct_path.exists():
        try:
            return ct_path.read_text(encoding="utf-8").strip() or _sniff_content_type(url, None)
        except OSError:
            pass
    return _sniff_content_type(url, None)


def _weak_etag(item_id: int, url: str) -> str:
    digest = hashlib.sha256(f"{item_id}:{url}".encode("utf-8")).hexdigest()[:16]
    return f'W/"cover-{digest}"'


def _visibility_ok(item: CatalogItem, user: User | None) -> bool:
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        user is not None and is_staff_or_admin(user)
    ):
        return False
    if user is None:
        return item.sensitivity_level == SensitivityLevel.PUBLIC
    if user.role == UserRole.PATRON:
        return item.sensitivity_level != SensitivityLevel.CONFIDENTIAL
    return True


@router.get("/covers/{item_id}")
@limiter.limit("300/minute")
async def get_catalog_cover(
    request: Request,
    item_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> Response:
    """Serve the cover image for a catalog item via the backend.

    First request: fetch from the allowed upstream, write to the cover cache,
    return bytes. Subsequent requests: stream from cache. A cataloged item
    without a usable cover returns 204, allowing the frontend's generated
    thumbnail to take over without recording a noisy failed-resource request.
    Unknown, inaccessible, and disallowed records still return 404.
    """
    item = await _get_catalog_item_with_images(db, item_id)
    if not _visibility_ok(item, current_user):
        raise HTTPException(status_code=404, detail="Cover not found")

    source_url = _resolve_cover_source(item)
    if not source_url:
        return Response(status_code=204)

    if _is_internal_url(source_url):
        return RedirectResponse(url=source_url, status_code=307)

    parsed = urlparse(source_url)
    if parsed.scheme not in ("http", "https") or not _host_allowed(parsed.hostname):
        logger.warning(
            "Cover proxy refusing non-allowlisted upstream for item %d: %s",
            item_id,
            parsed.hostname,
        )
        raise HTTPException(status_code=404, detail="Cover not found")

    etag = _weak_etag(item.id, source_url)
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match == etag:
        return Response(
            status_code=304,
            headers={
                "ETag": etag,
                "Cache-Control": _COVER_CACHE_CONTROL,
            },
        )

    cache_path = _cache_path_for(source_url)
    cache_headers = {
        "Cache-Control": _COVER_CACHE_CONTROL,
        "ETag": etag,
    }

    if cache_path.exists():
        if cache_path.stat().st_size < _MIN_COVER_BYTES:
            # A "no cover" sentinel was cached before the size guard existed.
            # Drop it and fall through to a fresh fetch (which 404s if the
            # upstream is still a sentinel, or caches the real cover if the
            # cover_url has since been corrected).
            with contextlib.suppress(OSError):
                cache_path.unlink()
        else:
            # FileResponse cooperates with starlette's middleware chain (streams
            # the file via async chunks), so headers set via constructor survive
            # the BaseHTTPMiddleware passes that strip them on plain Responses.
            content_type = _read_cached_content_type(cache_path, source_url)
            return FileResponse(path=str(cache_path), media_type=content_type, headers=cache_headers)

    try:
        body, content_type = await _fetch_and_cache(source_url, cache_path)
    except httpx.HTTPError as exc:
        logger.warning("Cover proxy upstream error for item %d: %s", item_id, exc)
        raise HTTPException(status_code=502, detail="Upstream cover fetch failed") from exc

    # Use StreamingResponse: starlette's BaseHTTPMiddleware chain (which the
    # logging/perf/caching layers all rely on) preserves headers on streaming
    # responses, but historically drops custom headers attached to a plain
    # ``Response`` returned from inside the chain.
    return StreamingResponse(
        io.BytesIO(body),
        media_type=content_type,
        headers=cache_headers,
    )
