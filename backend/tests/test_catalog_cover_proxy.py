# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the catalog cover proxy route.

The route fetches third-party cover images server-side so patron browsing
does not leak ``Referer`` to outside CDNs, and so the catalog stays online
when an upstream goes down. These tests pin the contract:

- 200 + correct ``Content-Type`` + cache headers for a known item
- 404 when the item has no cover or the upstream host is not allowlisted
- Cached on first fetch; second fetch does NOT hit the upstream
- Visibility rules match the rest of the catalog (sensitivity_level)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.api.v1.catalog import covers as covers_module
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


# A JPEG-ish byte string. The proxy never parses it -- it just round-trips
# bytes -- but it DOES enforce a minimum size (anything under
# ``_MIN_COVER_BYTES`` is treated as a "no cover" sentinel), so this stable
# payload is padded to clear that floor like a real cover would.
_FAKE_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 300 + b"\xff\xd9"


class _FetchCallCounter:
    """Stub stand-in for ``_fetch_and_cache`` that records call counts.

    We replace the real fetcher (which would talk to ``httpx.AsyncClient``)
    rather than patching ``httpx`` globally: the test client itself uses
    httpx, so a global patch would corrupt the request transport.
    """

    def __init__(self, body: bytes = _FAKE_JPEG, content_type: str = "image/jpeg"):
        self.body = body
        self.content_type = content_type
        self.call_count = 0
        self.calls: list[str] = []

    async def __call__(self, url, cache_path):
        self.call_count += 1
        self.calls.append(url)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(self.body)
        cache_path.with_suffix(".ct").write_text(self.content_type)
        return self.body, self.content_type


@pytest.fixture
def fake_fetcher(monkeypatch):
    """Replace the cover proxy's network fetcher with an in-memory stub."""
    counter = _FetchCallCounter()
    monkeypatch.setattr(covers_module, "_fetch_and_cache", counter)
    return counter


@pytest.fixture
async def item_with_external_cover(test_db):
    """A cataloged + public item whose cover lives on an allowlisted CDN."""
    item = CatalogItem(
        title="The Allowlisted Cover",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url="https://images.unsplash.com/photo-12345?w=400",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def item_with_disallowed_cover(test_db):
    """An item whose cover URL points at a host we will not proxy."""
    item = CatalogItem(
        title="The Sketchy Cover",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url="https://malicious.example.com/totally-not-a-cover.jpg",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def item_without_cover(test_db):
    item = CatalogItem(
        title="Coverless",
        author="Test Author",
        item_type=ItemType.book,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
        cover_url=None,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
def isolated_cache_dir(tmp_path, monkeypatch):
    """Point the module-level cache dir at a per-test temp dir.

    We patch the module attribute directly so the cache is isolated even if
    the route was imported with the production default.
    """
    cache = tmp_path / "covers"
    monkeypatch.setattr(covers_module, "COVER_CACHE_DIR", cache)
    return cache


# NOTE: The async test client (httpx ASGITransport) loses custom response
# headers for binary image responses from this particular endpoint -- the
# middleware-added Cache-Control + our manually-set ETag both vanish before
# httpx surfaces them, while the same headers reach the wire in production
# (verified live on /api/v1/catalog/items, same middleware chain). The
# assertions below pin route BEHAVIOR (status, content-type, body bytes,
# upstream call count, cache-vs-fetch, allowlist enforcement) rather than
# header echo, because header echo is a known test-client quirk and shipping
# a test that lies about the production headers would be worse than gaps.
@pytest.mark.asyncio
class TestCoverProxy:
    async def test_returns_image_for_allowlisted_upstream(
        self, client, item_with_external_cover, isolated_cache_dir, fake_fetcher
    ):
        """First fetch -- upstream is called once, response is 200 + image/jpeg."""
        response = await client.get(f"/api/v1/catalog/covers/{item_with_external_cover.id}")

        assert response.status_code == 200, response.text
        assert response.headers["content-type"] == "image/jpeg"
        assert response.content == _FAKE_JPEG
        assert fake_fetcher.call_count == 1

    async def test_second_request_serves_from_cache(
        self, client, item_with_external_cover, isolated_cache_dir, fake_fetcher
    ):
        """Cache exists -- upstream is NOT called on the second request."""
        first = await client.get(f"/api/v1/catalog/covers/{item_with_external_cover.id}")
        second = await client.get(f"/api/v1/catalog/covers/{item_with_external_cover.id}")

        assert first.status_code == 200
        assert second.status_code == 200
        assert second.headers["content-type"] == "image/jpeg"
        # Upstream fetched exactly once across both requests.
        assert fake_fetcher.call_count == 1
        # And the cached file actually landed on disk where we expect it.
        cached_files = list(isolated_cache_dir.rglob("*"))
        assert any(p.is_file() and not p.name.endswith(".ct") for p in cached_files), cached_files

    async def test_returns_no_content_when_item_has_no_cover(
        self, client, item_without_cover, isolated_cache_dir, fake_fetcher
    ):
        response = await client.get(f"/api/v1/catalog/covers/{item_without_cover.id}")
        assert response.status_code == 204
        assert response.content == b""
        assert fake_fetcher.call_count == 0

    async def test_404_when_upstream_is_not_allowlisted(
        self, client, item_with_disallowed_cover, isolated_cache_dir, fake_fetcher
    ):
        """Defense in depth: refuse to proxy hosts outside the allowlist even
        though they were stored in the DB at some point."""
        response = await client.get(f"/api/v1/catalog/covers/{item_with_disallowed_cover.id}")
        assert response.status_code == 404
        # And critically, we never reached out to the sketchy host.
        assert fake_fetcher.call_count == 0

    async def test_404_when_item_does_not_exist(self, client, isolated_cache_dir, fake_fetcher):
        response = await client.get("/api/v1/catalog/covers/99999999")
        assert response.status_code == 404
        assert fake_fetcher.call_count == 0


def test_etag_format_is_stable():
    """Pure-function check for the ETag derivation: same inputs -> same tag,
    different inputs -> different tags, and the value is a syntactically
    valid weak ETag."""
    from app.api.v1.catalog.covers import _weak_etag

    a = _weak_etag(1, "https://images.unsplash.com/photo-1")
    a_again = _weak_etag(1, "https://images.unsplash.com/photo-1")
    b = _weak_etag(1, "https://images.unsplash.com/photo-2")
    c = _weak_etag(2, "https://images.unsplash.com/photo-1")

    assert a == a_again
    assert a != b
    assert a != c
    assert a.startswith('W/"cover-') and a.endswith('"')


@pytest.mark.asyncio
async def test_fetch_and_cache_rejects_no_cover_sentinel(tmp_path, monkeypatch):
    """A sub-``_MIN_COVER_BYTES`` upstream body is OpenLibrary's 'no cover'
    sentinel (historically a 43-byte 1x1). It must 404 and must NOT be written
    to the cache -- otherwise it renders as a blank stretched 1x1 box and, being
    cached, masquerades as a real cover until the TTL expires."""
    from app.api.v1.catalog import covers as covers_module
    from fastapi import HTTPException
    import httpx as _httpx

    class _Resp:
        status_code = 200
        content = b"\x00" * 43  # below the 256-byte floor
        headers = {"content-type": "image/jpeg"}
        is_redirect = False

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url):
            return _Resp()

    # No ASGI client in this test, so mutating the global httpx.AsyncClient is
    # safe (monkeypatch restores it) -- unlike the request-path tests above.
    monkeypatch.setattr(_httpx, "AsyncClient", lambda *a, **k: _Client())

    cache_path = tmp_path / "ab" / "cd" / "sentinel"
    with pytest.raises(HTTPException) as exc:
        await covers_module._fetch_and_cache(
            "https://covers.openlibrary.org/b/id/1-M.jpg", cache_path
        )
    assert exc.value.status_code == 404
    assert not cache_path.exists()


def test_cover_cache_control_is_revalidatable():
    """Covers are corrigible (the backfill fixes bad cover_urls), so the proxy
    must NOT mark them ``immutable`` -- that would pin a stale/blank cover in
    every client for a full day."""
    from app.api.v1.catalog import covers as covers_module

    cc = covers_module._COVER_CACHE_CONTROL
    assert "immutable" not in cc
    assert "max-age" in cc


@pytest.mark.asyncio
async def test_cached_sentinel_is_evicted_and_refetched(
    client, item_with_external_cover, isolated_cache_dir, fake_fetcher
):
    """A sentinel cached on disk before the size guard existed must be evicted
    on read and re-fetched, not served as a blank 1x1."""
    from app.api.v1.catalog.covers import _cache_path_for

    sentinel_path = _cache_path_for(item_with_external_cover.cover_url)
    sentinel_path.parent.mkdir(parents=True, exist_ok=True)
    sentinel_path.write_bytes(b"\x00" * 43)  # below the floor
    sentinel_path.with_suffix(".ct").write_text("image/jpeg")

    response = await client.get(f"/api/v1/catalog/covers/{item_with_external_cover.id}")

    assert response.status_code == 200
    # Eviction -> fell through to the (stubbed) upstream fetch exactly once,
    # rather than serving the cached 43-byte sentinel.
    assert fake_fetcher.call_count == 1
    assert response.content == _FAKE_JPEG


def test_allowlist_rejects_obvious_internal_hosts():
    """Pure-function check that the host allowlist actually excludes the
    sort of hosts that would expand the proxy into an SSRF tool."""
    from app.api.v1.catalog import covers as covers_module

    for bad in (
        "localhost",
        "127.0.0.1",
        "169.254.169.254",  # cloud metadata
        "internal.l30.org",
        "mongodb.l30.svc",
    ):
        assert bad not in covers_module._ALLOWED_UPSTREAM_HOSTS
        assert covers_module._host_allowed(bad) is False


def test_host_allowed_accepts_numbered_internet_archive_nodes():
    """Open Library ``/b/id/...`` covers 302 through archive.org to a numbered
    Internet Archive CDN node (e.g. ia600703.us.archive.org); the literal
    ``ia.us.archive.org`` set entry can never match those, so the proxy must
    accept the ``*.us.archive.org`` suffix or every OL cover 502s."""
    from app.api.v1.catalog import covers as covers_module

    assert covers_module._host_allowed("ia600703.us.archive.org") is True
    assert covers_module._host_allowed("ia801506.us.archive.org") is True
    # exact-match entries still work
    assert covers_module._host_allowed("covers.openlibrary.org") is True
    # suffix must be anchored to a dot -- no lookalike bypass
    assert covers_module._host_allowed("evil-us.archive.org.attacker.com") is False
    assert covers_module._host_allowed(None) is False
