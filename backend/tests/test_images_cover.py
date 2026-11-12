# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the cover resizer (/api/v1/images/cover/{id}).

Companion to test_catalog_cover_proxy.py; pins the contract for the size +
format negotiated layer that sits on top of the existing cover cache:

- 200 + correct ``Content-Type`` for AVIF / WebP / JPEG via ``Accept``
- 200 + correct ``Content-Type`` for explicit ``fmt=avif|webp|jpeg``
- 304 on ETag match
- 422 on invalid ``w`` / ``fmt``
- 404 on missing item, no-cover item, non-allowlisted upstream
"""
from __future__ import annotations

import io
from pathlib import Path

import pytest
from PIL import Image

from app.api.v1.catalog import covers as covers_module
from app.api.v1.images import cover as cover_module
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


def _make_source_png(width: int = 800, height: int = 1200) -> bytes:
    """A real 2:3 PNG so Pillow has something to decode + resize."""
    buf = io.BytesIO()
    Image.new("RGB", (width, height), (139, 94, 94)).save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture
def isolated_caches(tmp_path, monkeypatch):
    """Point both source-cover cache and resize cache at per-test temp dirs."""
    src = tmp_path / "src_covers"
    resized = tmp_path / "resized_covers"
    monkeypatch.setattr(covers_module, "COVER_CACHE_DIR", src)
    monkeypatch.setattr(cover_module, "RESIZE_CACHE_DIR", resized)
    return src, resized


@pytest.fixture
def primed_source(isolated_caches):
    """Seed the source-cover cache for the test item's cover_url so the
    resizer route doesn't need to hit the network."""
    src_cache_dir, _ = isolated_caches
    source_url = "https://images.unsplash.com/photo-12345?w=400"
    cache_path = covers_module._cache_path_for(source_url)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(_make_source_png())
    cache_path.with_suffix(".ct").write_text("image/png")
    return source_url


@pytest.fixture
async def item(test_db, primed_source):
    obj = CatalogItem(
        title="Resizable Cover",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url=primed_source,
    )
    test_db.add(obj)
    await test_db.commit()
    await test_db.refresh(obj)
    return obj


@pytest.fixture
async def coverless_item(test_db, isolated_caches):
    obj = CatalogItem(
        title="No Cover",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url=None,
    )
    test_db.add(obj)
    await test_db.commit()
    await test_db.refresh(obj)
    return obj


@pytest.fixture
async def disallowed_item(test_db, isolated_caches):
    obj = CatalogItem(
        title="Sketchy Cover",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url="https://malicious.example.com/cover.jpg",
    )
    test_db.add(obj)
    await test_db.commit()
    await test_db.refresh(obj)
    return obj


@pytest.mark.asyncio
class TestCoverResizer:
    async def test_avif_when_accept_header_prefers_avif(self, client, item):
        response = await client.get(
            f"/api/v1/images/cover/{item.id}?w=200",
            headers={"Accept": "image/avif,image/webp,*/*"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/avif"
        # AVIF starts with an ftyp box; just check non-empty image bytes.
        assert len(response.content) > 32

    async def test_webp_when_accept_lacks_avif(self, client, item):
        response = await client.get(
            f"/api/v1/images/cover/{item.id}?w=200",
            headers={"Accept": "image/webp,*/*"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/webp"
        assert response.content[:4] == b"RIFF"  # WebP container magic

    async def test_jpeg_fallback_when_accept_is_plain(self, client, item):
        response = await client.get(
            f"/api/v1/images/cover/{item.id}?w=200",
            headers={"Accept": "*/*"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content[:3] == b"\xff\xd8\xff"  # JPEG SOI

    async def test_explicit_fmt_overrides_accept(self, client, item):
        response = await client.get(
            f"/api/v1/images/cover/{item.id}?w=400&fmt=jpeg",
            headers={"Accept": "image/avif"},
        )
        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/jpeg"

    async def test_etag_match_returns_304(self, client, item):
        first = await client.get(
            f"/api/v1/images/cover/{item.id}?w=200&fmt=webp",
        )
        assert first.status_code == 200
        etag = first.headers.get("etag")
        assert etag and etag.startswith('W/"covimg-')

        second = await client.get(
            f"/api/v1/images/cover/{item.id}?w=200&fmt=webp",
            headers={"If-None-Match": etag},
        )
        assert second.status_code == 304

    async def test_invalid_width_is_422(self, client, item):
        response = await client.get(f"/api/v1/images/cover/{item.id}?w=137")
        assert response.status_code == 422

    async def test_invalid_format_is_422(self, client, item):
        response = await client.get(f"/api/v1/images/cover/{item.id}?w=200&fmt=heic")
        assert response.status_code == 422

    async def test_missing_item_is_404(self, client, isolated_caches):
        response = await client.get("/api/v1/images/cover/99999999?w=200")
        assert response.status_code == 404

    async def test_item_without_cover_is_404(self, client, coverless_item):
        response = await client.get(f"/api/v1/images/cover/{coverless_item.id}?w=200")
        assert response.status_code == 404

    async def test_non_allowlisted_upstream_is_404(self, client, disallowed_item):
        response = await client.get(f"/api/v1/images/cover/{disallowed_item.id}?w=200")
        assert response.status_code == 404


def test_negotiate_format_table():
    """Pure-function check on the Accept negotiation."""
    from app.api.v1.images.cover import _negotiate_format

    assert _negotiate_format("image/avif,image/webp", "auto") == "avif"
    assert _negotiate_format("image/webp,*/*", "auto") == "webp"
    assert _negotiate_format("*/*", "auto") == "jpeg"
    assert _negotiate_format(None, "auto") == "jpeg"
    # Explicit fmt always wins.
    assert _negotiate_format("image/avif", "jpeg") == "jpeg"
    assert _negotiate_format("*/*", "webp") == "webp"


def test_etag_is_stable_and_input_sensitive():
    from app.api.v1.images.cover import _weak_etag

    a = _weak_etag(1, 200, "avif", "abc123" * 6)
    a_again = _weak_etag(1, 200, "avif", "abc123" * 6)
    b = _weak_etag(1, 400, "avif", "abc123" * 6)
    c = _weak_etag(1, 200, "webp", "abc123" * 6)
    d = _weak_etag(2, 200, "avif", "abc123" * 6)
    e = _weak_etag(1, 200, "avif", "def456" * 6)

    assert a == a_again
    assert len({a, b, c, d, e}) == 5
    assert a.startswith('W/"covimg-') and a.endswith('"')


def test_resize_preserves_aspect_ratio_when_downscaling():
    from app.api.v1.images.cover import _resize_to_bytes

    source = _make_source_png(800, 1200)  # 2:3
    out = _resize_to_bytes(source, 200, "jpeg")
    with Image.open(io.BytesIO(out)) as img:
        # Aspect should match: 200 wide → ~300 tall
        assert img.size == (200, 300)


def test_resize_does_not_upscale():
    """If source is already smaller than target, leave it alone."""
    from app.api.v1.images.cover import _resize_to_bytes

    source = _make_source_png(150, 225)  # 2:3, smaller than any allowed w
    out = _resize_to_bytes(source, 600, "jpeg")
    with Image.open(io.BytesIO(out)) as img:
        assert img.size == (150, 225)
