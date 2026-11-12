# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cover image resizer.

Companion to ``catalog/covers.py``: the cover *proxy* fetches third-party
upstreams and caches the raw bytes. This module takes those bytes (or any
locally-uploaded primary image) and serves a size + format negotiated copy
for the patron page.

- ``w`` ∈ {200, 400, 600}: target width in CSS pixels. Output preserves the
  source aspect ratio; height is derived. The discover/catalog UI renders
  covers at a 2:3 fixed tile, so this is "natural width" not "exact slot".
- ``fmt`` ∈ {auto, avif, webp, jpeg}: ``auto`` negotiates from the
  ``Accept`` header (AVIF preferred, then WebP, JPEG fallback). Explicit
  values let curl/tests/SR users force a format.

Source-of-truth selection mirrors :func:`covers._resolve_cover_source`:
primary uploaded image → first uploaded image → ``cover_url``. Visibility
rules also mirror the catalog item endpoint (cataloged + non-confidential
for anon).

Resized outputs land in an on-disk cache keyed by
``(item_id, width, fmt, source-content-hash)`` so a swapped cover invalidates
the resize automatically.
"""
from __future__ import annotations

import hashlib
import io
from app.core.logging import get_logger
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, Response, StreamingResponse
from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.user import User
from ..auth import get_optional_user
from ..catalog import covers as covers_module
from ..catalog.helpers import _get_catalog_item_with_images

logger = get_logger(__name__)

router = APIRouter(prefix="/images", tags=["images"])

# Resize cache lives alongside the upstream cover cache so a single volume
# survives container rebuilds. Override with COVER_RESIZE_CACHE_DIR if you
# want to evict one without touching the other.
RESIZE_CACHE_DIR = Path(
    os.environ.get("COVER_RESIZE_CACHE_DIR", "/app/uploads/cover_resize_cache")
)

_ALLOWED_WIDTHS = (200, 400, 600)
_ALLOWED_FORMATS = ("auto", "avif", "webp", "jpeg")

# Per-format encoder knobs. Quality is the patron-facing tradeoff knob;
# these are tuned to land a 400w cover ~25-40 KB for AVIF / ~40-60 KB for
# WebP / ~50-80 KB for JPEG. Bumping quality re-runs every resize on next
# request (cache key includes nothing version-y).
_FORMAT_PARAMS = {
    "avif": {"format": "AVIF", "quality": 55, "speed": 6},
    "webp": {"format": "WEBP", "quality": 78, "method": 4},
    "jpeg": {"format": "JPEG", "quality": 82, "optimize": True, "progressive": True},
}

_CONTENT_TYPES = {
    "avif": "image/avif",
    "webp": "image/webp",
    "jpeg": "image/jpeg",
}


def _negotiate_format(accept_header: str | None, requested: str) -> str:
    if requested != "auto":
        return requested
    accept = (accept_header or "").lower()
    if "image/avif" in accept:
        return "avif"
    if "image/webp" in accept:
        return "webp"
    return "jpeg"


def _resize_cache_path(item_id: int, width: int, fmt: str, source_hash: str) -> Path:
    return (
        RESIZE_CACHE_DIR
        / f"{item_id // 1000:04d}"
        / f"{item_id}-{width}-{fmt}-{source_hash[:16]}.{fmt}"
    )


def _hash_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _weak_etag(item_id: int, width: int, fmt: str, source_hash: str) -> str:
    return f'W/"covimg-{item_id}-{width}-{fmt}-{source_hash[:12]}"'


def _read_source_bytes(item, source_url: str) -> bytes | None:
    if covers_module._is_internal_url(source_url):
        return None
    cache_path = covers_module._cache_path_for(source_url)
    if cache_path.exists():
        try:
            return cache_path.read_bytes()
        except OSError as exc:
            logger.warning("Cover resize: failed reading cache %s: %s", cache_path, exc)
            return None
    return None


async def _ensure_source_bytes(item, source_url: str) -> bytes:
    cached = _read_source_bytes(item, source_url)
    if cached is not None:
        return cached
    cache_path = covers_module._cache_path_for(source_url)
    body, _ct = await covers_module._fetch_and_cache(source_url, cache_path)
    return body


def _resize_to_bytes(source: bytes, width: int, fmt: str) -> bytes:
    with Image.open(io.BytesIO(source)) as img:
        img.load()
        src_w, src_h = img.size
        if src_w <= 0 or src_h <= 0:
            raise HTTPException(status_code=502, detail="Source image has zero dimension")
        # Only downscale; if source is already <= target width, keep it.
        if src_w > width:
            new_h = max(1, round(src_h * (width / src_w)))
            img = img.resize((width, new_h), Image.Resampling.LANCZOS)
        params = dict(_FORMAT_PARAMS[fmt])
        save_format = params.pop("format")
        if fmt == "jpeg" and img.mode in ("RGBA", "LA", "P"):
            # JPEG cannot represent alpha. Composite onto white before save
            # so the patron sees the cover, not a black box.
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
            img = background
        elif fmt != "jpeg" and img.mode == "P":
            img = img.convert("RGBA")
        elif fmt == "jpeg" and img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format=save_format, **params)
        return buf.getvalue()


@router.get("/cover/{catalog_id}")
@limiter.limit("600/minute")
async def get_resized_cover(
    request: Request,
    catalog_id: int,
    w: int = Query(400, description="Target width in CSS pixels"),
    fmt: str = Query("auto", description="Output format: auto, avif, webp, jpeg"),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
) -> Response:
    """Return a resized + re-encoded cover image.

    Behavior:
    - ``w`` must be one of {200, 400, 600}. Other values -> 422.
    - ``fmt`` must be one of {auto, avif, webp, jpeg}. Other values -> 422.
    - 404 when item is hidden, has no cover, has no allowlisted source, or
      no cached source bytes are reachable.
    - ``ETag`` includes source content hash so swapping the upstream cover
      invalidates downstream caches automatically.
    - ``Cache-Control: public, max-age=31536000, immutable`` -- the URL
      itself encodes the variant, so the cached value is safe to pin
      forever from the patron's perspective.
    """
    if w not in _ALLOWED_WIDTHS:
        raise HTTPException(
            status_code=422,
            detail=f"width must be one of {_ALLOWED_WIDTHS}",
        )
    if fmt not in _ALLOWED_FORMATS:
        raise HTTPException(
            status_code=422,
            detail=f"fmt must be one of {_ALLOWED_FORMATS}",
        )

    item = await _get_catalog_item_with_images(db, catalog_id)
    if not covers_module._visibility_ok(item, current_user):
        raise HTTPException(status_code=404, detail="Cover not found")

    source_url = covers_module._resolve_cover_source(item)
    if not source_url:
        raise HTTPException(status_code=404, detail="Cover not found")

    if covers_module._is_internal_url(source_url):
        # Local /uploads/ assets: we don't proxy/resize these here yet;
        # the static layer + browser do the cheap thing. Returning 404
        # lets the frontend Cover component fall through to its typographic
        # tile, which is the documented contract for "no resized variant
        # available".
        raise HTTPException(status_code=404, detail="Cover not resizable")

    from urllib.parse import urlparse  # local import keeps top-level slim

    parsed = urlparse(source_url)
    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname not in covers_module._ALLOWED_UPSTREAM_HOSTS
    ):
        logger.warning(
            "Cover resize refusing non-allowlisted upstream for item %d: %s",
            catalog_id,
            parsed.hostname,
        )
        raise HTTPException(status_code=404, detail="Cover not found")

    chosen_fmt = _negotiate_format(request.headers.get("accept"), fmt)

    try:
        source_bytes = await _ensure_source_bytes(item, source_url)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001 - we want this on the 502 path
        logger.warning("Cover resize: source fetch failed for item %d: %s", catalog_id, exc)
        raise HTTPException(status_code=502, detail="Upstream cover unavailable") from exc

    source_hash = _hash_bytes(source_bytes)
    etag = _weak_etag(catalog_id, w, chosen_fmt, source_hash)
    if_none_match = request.headers.get("if-none-match")
    cache_headers = {
        "Cache-Control": "public, max-age=31536000, immutable",
        "ETag": etag,
        "Vary": "Accept",
    }
    if if_none_match == etag:
        return Response(status_code=304, headers=cache_headers)

    cache_path = _resize_cache_path(catalog_id, w, chosen_fmt, source_hash)
    content_type = _CONTENT_TYPES[chosen_fmt]
    if cache_path.exists():
        return FileResponse(
            path=str(cache_path),
            media_type=content_type,
            headers=cache_headers,
        )

    try:
        encoded = _resize_to_bytes(source_bytes, w, chosen_fmt)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Cover resize: encode failed for item %d", catalog_id)
        raise HTTPException(status_code=500, detail="Resize failed") from exc

    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = cache_path.with_suffix(cache_path.suffix + ".part")
    tmp.write_bytes(encoded)
    tmp.replace(cache_path)

    return StreamingResponse(
        io.BytesIO(encoded),
        media_type=content_type,
        headers=cache_headers,
    )
