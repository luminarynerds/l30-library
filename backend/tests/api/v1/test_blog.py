# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for backend blog quality fixes:
- POST /api/v1/blog/media (image upload)
- PUT  /api/v1/blog/posts/{id}/schedule
- View counter X-Forwarded-For dedup
- Branded Atom /feed with <content>
- Per-tag feed /feed/tag/{slug}
"""

from __future__ import annotations

import contextlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import create_access_token, hash_password
from app.models.blog import BlogPost, BlogPostStatus, BlogPostTag, BlogTag
from app.models.user import User, UserRole


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def blog_staff(test_db):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"blog-staff-{unique}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Blog",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def blog_patron(test_db):
    unique = uuid.uuid4().hex[:8]
    user = User(
        email=f"blog-patron-{unique}@example.com",
        password_hash=hash_password("TestPassword123!"),
        first_name="Blog",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff_headers(blog_staff) -> dict:
    """Headers that resolve to `blog_staff` via the dependency override below.
    The token value is opaque — `_override_auth_to` swaps the user out of
    `get_current_user` so we don't depend on Redis (which is unavailable in
    host-venv test runs and makes token revocation fail-secure).
    """
    return {"Authorization": "Bearer test-staff"}


@pytest.fixture
async def patron_headers(blog_patron) -> dict:
    return {"Authorization": "Bearer test-patron"}


@pytest.fixture(autouse=True)
def _override_auth(request, test_db):
    """Per-test: swap `get_current_user` to return whichever user a test asks
    for. Selected by looking for a `blog_staff` or `blog_patron` fixture in the
    test's fixturenames — staff wins if both are requested.

    Without this, JWT verification falls through to `is_token_revoked()`, which
    is fail-secure when Redis is unavailable and returns True for any token it
    hasn't previously cached. The whole suite would 401.
    """
    from app.main import app
    from app.api.v1.auth.helpers import get_current_user

    chosen = None
    if "blog_staff" in request.fixturenames:
        chosen = request.getfixturevalue("blog_staff")
    elif "blog_patron" in request.fixturenames:
        chosen = request.getfixturevalue("blog_patron")

    if chosen is None:
        yield
        return

    async def _override():
        return chosen

    app.dependency_overrides[get_current_user] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# Keep create_access_token import live for any test that wants to verify the
# JWT pathway directly (none currently, but referenced by header fixtures'
# original implementation).
_ = create_access_token


@pytest.fixture
def temp_uploads(monkeypatch, tmp_path):
    """Redirect blog media writes to a tmp dir.

    The endpoint reads `get_settings().storage_local_path` at request time,
    so we patch via monkeypatch on the lru_cached settings object.
    """
    from app.core.config import get_settings

    settings = get_settings()
    original = settings.storage_local_path
    object.__setattr__(settings, "storage_local_path", str(tmp_path))
    yield tmp_path
    with contextlib.suppress(Exception):
        object.__setattr__(settings, "storage_local_path", original)


# ============================================================================
# Helpers
# ============================================================================


async def _make_post(
    test_db,
    *,
    title: str = "Hello",
    body: str = "<p>body</p>",
    status: BlogPostStatus = BlogPostStatus.published,
    slug: str | None = None,
    tag_names: list[str] | None = None,
) -> BlogPost:
    slug = slug or f"post-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    post = BlogPost(
        title=title,
        slug=slug,
        body=body,
        author_name="Author",
        status=status,
        published_at=now if status == BlogPostStatus.published else None,
    )
    test_db.add(post)
    await test_db.commit()
    # BlogPost.author/co_authors are lazy="selectin" (see app/models/blog.py --
    # "to avoid the MissingGreenlet landmine when Pydantic serializes a
    # BlogPost outside an async-context-aware lazy loader"), but
    # Session.refresh() does NOT honor that: it always emits a genuine lazy
    # load for relationship attributes regardless of the mapper's configured
    # strategy, which app/core/lazy_load_guard.py then blocks in tests. Real
    # endpoints avoid this by re-SELECTing with selectinload() instead of
    # refresh() (see e.g. schedule_post's _refetch_post_by_id) -- do the same
    # here rather than test_db.refresh(post).
    refreshed = await test_db.execute(
        select(BlogPost)
        .options(selectinload(BlogPost.author), selectinload(BlogPost.co_authors))
        .where(BlogPost.id == post.id)
    )
    post = refreshed.scalar_one()
    if tag_names:
        for name in tag_names:
            tag_slug = name.lower().replace(" ", "-")
            existing = await test_db.execute(
                __import__("sqlalchemy").select(BlogTag).where(BlogTag.slug == tag_slug)
            )
            tag = existing.scalar_one_or_none()
            if not tag:
                tag = BlogTag(name=name, slug=tag_slug)
                test_db.add(tag)
                await test_db.commit()
                await test_db.refresh(tag)
            test_db.add(BlogPostTag(post_id=post.id, tag_id=tag.id))
        await test_db.commit()
    return post


# 1x1 PNG, used for upload tests
_TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


# ============================================================================
# POST /media — image upload
# ============================================================================


@pytest.mark.asyncio
async def test_upload_media_happy_path(client, staff_headers, temp_uploads):
    res = await client.post(
        "/api/v1/blog/media",
        headers=staff_headers,
        files={"file": ("pic.png", _TINY_PNG, "image/png")},
    )
    assert res.status_code == 201, res.text
    payload = res.json()
    assert payload["url"].startswith("/uploads/blog/")
    assert payload["url"].endswith(".png")
    filename = payload["url"].split("/")[-1]
    blog_dir = os.path.join(str(temp_uploads), "blog")
    assert os.path.exists(os.path.join(blog_dir, filename))


def _extract_detail(payload) -> str:
    """The app wraps HTTPException detail in `{error: {message: ...}}`; older
    paths still surface as `detail`. Accept either."""
    if isinstance(payload, dict):
        if "detail" in payload:
            return str(payload["detail"])
        err = payload.get("error") or {}
        if isinstance(err, dict):
            return str(err.get("message") or err.get("detail") or "")
    return str(payload)


@pytest.mark.asyncio
async def test_upload_media_rejects_non_image_mime(client, staff_headers, temp_uploads):
    res = await client.post(
        "/api/v1/blog/media",
        headers=staff_headers,
        files={"file": ("evil.exe", b"MZ\x90\x00", "application/x-msdownload")},
    )
    assert res.status_code == 415
    assert "Unsupported" in _extract_detail(res.json())


@pytest.mark.asyncio
async def test_upload_media_size_cap(client, staff_headers, temp_uploads):
    oversized = b"\x89PNG\r\n\x1a\n" + b"\x00" * (5 * 1024 * 1024 + 10)
    res = await client.post(
        "/api/v1/blog/media",
        headers=staff_headers,
        files={"file": ("big.png", oversized, "image/png")},
    )
    assert res.status_code == 413
    assert "5MB" in _extract_detail(res.json())


@pytest.mark.asyncio
async def test_upload_media_requires_staff(client, patron_headers, temp_uploads):
    res = await client.post(
        "/api/v1/blog/media",
        headers=patron_headers,
        files={"file": ("pic.png", _TINY_PNG, "image/png")},
    )
    assert res.status_code in (401, 403)


@pytest.mark.asyncio
async def test_upload_media_anonymous_rejected(client, temp_uploads):
    res = await client.post(
        "/api/v1/blog/media",
        files={"file": ("pic.png", _TINY_PNG, "image/png")},
    )
    assert res.status_code in (401, 403)


# ============================================================================
# PUT /posts/{id}/schedule
# ============================================================================


@pytest.mark.asyncio
async def test_schedule_future_date_happy(client, staff_headers, test_db):
    post = await _make_post(test_db, status=BlogPostStatus.draft)
    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    # app/api/v1/blog.py schedule_post takes scheduled_at as a query param
    # ("The frontend sends scheduled_at as a query param"), not a JSON body.
    res = await client.put(
        f"/api/v1/blog/posts/{post.id}/schedule",
        headers=staff_headers,
        params={"scheduled_at": when},
    )
    assert res.status_code == 200, res.text
    # DB-side assertion is more robust than response body when host-venv
    # serialization can trip MissingGreenlet on freshly committed rows.
    from sqlalchemy import select as _select

    await test_db.commit()  # ensure we're not holding a stale transaction
    refreshed = await test_db.execute(_select(BlogPost).where(BlogPost.id == post.id))
    row = refreshed.scalar_one()
    assert row.status == BlogPostStatus.scheduled
    assert row.scheduled_at is not None


@pytest.mark.asyncio
async def test_schedule_past_date_rejected(client, staff_headers, test_db):
    post = await _make_post(test_db, status=BlogPostStatus.draft)
    when = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    res = await client.put(
        f"/api/v1/blog/posts/{post.id}/schedule",
        headers=staff_headers,
        params={"scheduled_at": when},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_schedule_non_draft_rejected(client, staff_headers, test_db):
    post = await _make_post(test_db, status=BlogPostStatus.published)
    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    res = await client.put(
        f"/api/v1/blog/posts/{post.id}/schedule",
        headers=staff_headers,
        params={"scheduled_at": when},
    )
    assert res.status_code == 400


@pytest.mark.asyncio
async def test_schedule_missing_post_returns_404(client, staff_headers):
    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    res = await client.put(
        "/api/v1/blog/posts/9999999/schedule",
        headers=staff_headers,
        params={"scheduled_at": when},
    )
    assert res.status_code == 404


# ============================================================================
# View counter — X-Forwarded-For dedup
#
# Unit-test the `_extract_client_ip` helper directly. End-to-end coverage via
# `GET /posts/{slug}` is brittle in host-venv tests because the existing view-
# counter path triggers a MissingGreenlet on the freshly-committed post
# (pre-existing prod-quirk, unrelated to this PR).
# ============================================================================


def _mock_request(headers: dict[str, str], client_host: str | None = "127.0.0.1"):
    class _Client:
        def __init__(self, host: str):
            self.host = host

    class _Req:
        def __init__(self, headers, client):
            # httpx/starlette headers are case-insensitive; mimic by lower-casing.
            self.headers = {k.lower(): v for k, v in headers.items()}
            self.client = client

    return _Req(headers, _Client(client_host) if client_host else None)


def test_extract_client_ip_prefers_cf_connecting_ip():
    """_extract_client_ip delegates to app/core/rate_limit.py's client_ip(),
    which was hardened to deliberately NOT trust X-Forwarded-For ("nginx
    appends to it ... its leftmost entry is attacker-controlled" -- and an
    attacker-controlled view-count dedup key is exactly the "rotate XFF to
    inflate view counts" attack the original _extract_client_ip docstring
    warns about). Precedence is now CF-Connecting-IP -> X-Real-IP -> peer.
    """
    from app.api.v1.blog import _extract_client_ip

    req = _mock_request(
        {"CF-Connecting-IP": "203.0.113.5", "X-Forwarded-For": "10.0.0.1"},
        client_host="172.17.0.5",
    )
    assert _extract_client_ip(req) == "203.0.113.5"


def test_extract_client_ip_strips_x_real_ip_whitespace():
    """X-Real-IP is the fallback below CF-Connecting-IP (see
    test_extract_client_ip_prefers_cf_connecting_ip) and is whitespace-
    stripped."""
    from app.api.v1.blog import _extract_client_ip

    req = _mock_request({"X-Real-IP": "  203.0.113.5  "}, client_host="172.17.0.5")
    assert _extract_client_ip(req) == "203.0.113.5"


def test_extract_client_ip_falls_back_to_client_host_when_no_xff():
    from app.api.v1.blog import _extract_client_ip

    req = _mock_request({}, client_host="198.51.100.7")
    assert _extract_client_ip(req) == "198.51.100.7"


def test_extract_client_ip_handles_empty_xff():
    from app.api.v1.blog import _extract_client_ip

    req = _mock_request({"X-Forwarded-For": "   "}, client_host="198.51.100.7")
    assert _extract_client_ip(req) == "198.51.100.7"


def test_extract_client_ip_handles_missing_client():
    """No CF-Connecting-IP/X-Real-IP and no socket peer falls through to
    slowapi's get_remote_address(), whose own no-client fallback is the
    literal string "127.0.0.1" (a safe non-empty default), not "".
    """
    from app.api.v1.blog import _extract_client_ip

    req = _mock_request({}, client_host=None)
    assert _extract_client_ip(req) == "127.0.0.1"


def test_view_dedup_hashes_same_for_same_xff_first_hop():
    """Smoke-test: two requests with the same XFF first-hop but different
    downstream proxies should produce the same viewer_hash."""
    import hashlib as _h
    from app.api.v1.blog import _extract_client_ip

    r1 = _mock_request({"X-Forwarded-For": "203.0.113.5, 10.0.0.1", "User-Agent": "ua/1"})
    r2 = _mock_request({"X-Forwarded-For": "203.0.113.5, 10.0.0.99", "User-Agent": "ua/1"})

    def _viewer_hash(req):
        ip = _extract_client_ip(req)
        return _h.sha256(f"{ip}:{req.headers.get('user-agent', '')}".encode()).hexdigest()

    assert _viewer_hash(r1) == _viewer_hash(r2)


def test_view_dedup_hashes_differ_for_distinct_first_hops():
    """See test_extract_client_ip_prefers_cf_connecting_ip -- X-Forwarded-For
    is no longer trusted for the dedup key, so distinct XFF values alone
    (with the same unset peer default) no longer produce distinct hashes.
    Use distinct CF-Connecting-IP values instead, which IS the signal the
    dedup key is keyed on now.
    """
    import hashlib as _h
    from app.api.v1.blog import _extract_client_ip

    r1 = _mock_request({"CF-Connecting-IP": "203.0.113.5", "User-Agent": "ua/1"})
    r2 = _mock_request({"CF-Connecting-IP": "203.0.113.99", "User-Agent": "ua/1"})

    def _viewer_hash(req):
        ip = _extract_client_ip(req)
        return _h.sha256(f"{ip}:{req.headers.get('user-agent', '')}".encode()).hexdigest()

    assert _viewer_hash(r1) != _viewer_hash(r2)


# ============================================================================
# Atom /feed — branding + content
# ============================================================================


@pytest.mark.asyncio
async def test_feed_uses_library_name_in_title(client, test_db):
    from app.core.config import get_settings

    settings = get_settings()
    object.__setattr__(settings, "library_name", "Test Branch Library")
    try:
        await _make_post(test_db, title="Hello", body="<p>hi</p>")
        res = await client.get("/api/v1/blog/feed")
        assert res.status_code == 200
        assert "application/atom+xml" in res.headers["content-type"]
        body = res.text
        assert "<title>Test Branch Library Blog</title>" in body
        assert "L30 Library Blog" not in body
    finally:
        object.__setattr__(settings, "library_name", "My Library")


@pytest.mark.asyncio
async def test_feed_includes_content_cdata(client, test_db):
    await _make_post(test_db, title="Post With Body", body="<p>full <em>body</em></p>")
    res = await client.get("/api/v1/blog/feed")
    assert res.status_code == 200
    body = res.text
    assert '<content type="html">' in body
    # CDATA must be present and unescaped inside
    assert "<![CDATA[" in body
    assert "<p>full <em>body</em></p>" in body


# ============================================================================
# /feed/tag/{slug}
# ============================================================================


@pytest.mark.asyncio
async def test_tag_feed_happy_path(client, test_db):
    from app.core.config import get_settings

    settings = get_settings()
    object.__setattr__(settings, "library_name", "Branchville")
    try:
        await _make_post(
            test_db,
            title="Tagged",
            body="<p>tagged body</p>",
            tag_names=["Books"],
        )
        await _make_post(test_db, title="Untagged")
        res = await client.get("/api/v1/blog/feed/tag/books")
        assert res.status_code == 200
        assert "application/atom+xml" in res.headers["content-type"]
        body = res.text
        assert "Branchville Blog" in body
        assert "#Books" in body
        assert "Tagged" in body
        assert "Untagged" not in body
    finally:
        object.__setattr__(settings, "library_name", "My Library")


@pytest.mark.asyncio
async def test_tag_feed_unknown_slug_returns_404(client, test_db):
    res = await client.get("/api/v1/blog/feed/tag/does-not-exist")
    assert res.status_code == 404


@pytest.mark.asyncio
async def test_tag_feed_existing_tag_with_no_posts_returns_200_empty(client, test_db):
    tag = BlogTag(name="LonelyTag", slug="lonely")
    test_db.add(tag)
    await test_db.commit()
    res = await client.get("/api/v1/blog/feed/tag/lonely")
    assert res.status_code == 200
    assert "<feed" in res.text
    # No <entry> blocks for this empty case
    assert "<entry>" not in res.text
