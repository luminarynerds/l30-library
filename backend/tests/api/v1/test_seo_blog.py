# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for SSR blog endpoints (/api/v1/seo/blog, /seo/blog/{slug}, /seo/blog/tag/{slug}).

These routes are hit by nginx for crawler user-agents to inject per-page
<title>/og/canonical and schema.org BlogPosting + BreadcrumbList JSON-LD into
the SPA shell. Today every social share of /blog or /blog/{slug} shows the
generic site og:image; these routes fix that.
"""
from datetime import datetime, timedelta, timezone
import json
import logging
import re
from pathlib import Path

import pytest

import app.api.v1.seo_meta as seo_meta_module
from app.core.config import get_settings
from app.models.blog import BlogPost, BlogPostStatus, BlogTag


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Make SSR tests use the real frontend/index.html template.

    Same approach as test_seo_events.py / test_seo_board_meetings.py: prod
    seo_meta.py fetches http://frontend:80/ when running inside the backend
    container; the host pytest runs from cannot reach that. Patch the cache
    + the fetch function so tests see the actual source template.
    """
    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta_module, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta_module, "_INDEX_HTML", None)
    yield


def _extract_jsonld_blocks(html: str) -> list:
    """Parse all <script type="application/ld+json"> blocks into Python objects.

    Handles single-object and JSON-array payloads (the detail handler emits
    both BlogPosting and BreadcrumbList in one array).
    """
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
    parsed: list = []
    for raw in blocks:
        unescaped = raw.replace("<\\/", "</")
        obj = json.loads(unescaped)
        if isinstance(obj, list):
            parsed.extend(obj)
        else:
            parsed.append(obj)
    return parsed


# ---------- fixtures ----------

@pytest.fixture
async def sample_post(test_db):
    """Seed one published post with author, tldr, featured_image, tags."""
    now = datetime.now(timezone.utc)
    tag1 = BlogTag(name="Programs", slug="programs")
    tag2 = BlogTag(name="Staff Picks", slug="staff-picks")
    test_db.add_all([tag1, tag2])
    await test_db.commit()

    post = BlogPost(
        title="Summer reading kickoff",
        slug="summer-reading-kickoff",
        body="<p>Join us at the library for our annual summer reading program.</p>",
        tldr="Annual summer reading program kickoff — sign up at the desk.",
        featured_image="/uploads/summer.jpg",
        author_name="Miss Rita",
        author_role="Children's Librarian",
        status=BlogPostStatus.published,
        published_at=now - timedelta(days=1),
    )
    post.tags = [tag1, tag2]
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post, ["tags"])
    return post


@pytest.fixture
async def draft_post(test_db):
    """A draft (non-published) post that must 404 from the SSR detail handler."""
    post = BlogPost(
        title="Internal Draft",
        slug="internal-draft",
        body="<p>Not ready.</p>",
        author_name="Editor",
        status=BlogPostStatus.draft,
    )
    test_db.add(post)
    await test_db.commit()
    await test_db.refresh(post)
    return post


@pytest.fixture
async def sample_tag(test_db):
    """A standalone tag for the tag-list test (no posts attached needed)."""
    tag = BlogTag(name="Library News", slug="library-news")
    test_db.add(tag)
    await test_db.commit()
    await test_db.refresh(tag)
    return tag


# ---------- /seo/blog (list) ----------

@pytest.mark.asyncio
async def test_blog_list_returns_200_with_library_name_in_title(client):
    """The blog list <title> contains the library name and the word Blog."""
    settings = get_settings()
    resp = await client.get("/api/v1/seo/blog")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    title = m.group(1)
    assert settings.library_name in title
    assert "Blog" in title
    # Sanity: default site title got replaced
    assert title != "L30 - Community Library"


@pytest.mark.asyncio
async def test_blog_list_canonical_and_og_url_point_at_blog(client):
    """canonical + og:url point at /blog, not the site root."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/blog"
    resp = await client.get("/api/v1/seo/blog")
    assert resp.status_code == 200
    assert f'canonical" href="{expected}"' in resp.text
    assert f'og:url" content="{expected}"' in resp.text
    assert 'canonical" href="https://l30.org/"' not in resp.text


@pytest.mark.asyncio
async def test_blog_list_emits_blog_jsonld(client):
    """The list page emits a schema.org Blog JSON-LD block."""
    resp = await client.get("/api/v1/seo/blog")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    blogs = [e for e in entries if e.get("@type") == "Blog"]
    assert blogs, f"Expected a Blog JSON-LD entry, got: {[e.get('@type') for e in entries]}"
    assert blogs[0]["@context"] == "https://schema.org"


# ---------- /seo/blog/{slug} (detail) ----------

@pytest.mark.asyncio
async def test_blog_post_detail_title_is_post_title(client, sample_post):
    """The post detail <title> contains the post's own title."""
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert sample_post.title in m.group(1)


@pytest.mark.asyncio
async def test_blog_post_detail_description_uses_tldr(client, sample_post):
    """og:description / meta description use the post's tldr."""
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    expected = sample_post.tldr
    assert f'og:description" content="{expected}"' in resp.text
    assert f'name="description" content="{expected}"' in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_og_image_is_absolute(client, sample_post):
    """og:image must be an absolute URL even when stored as a relative path."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/uploads/summer.jpg"
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    assert f'og:image" content="{expected}"' in resp.text
    assert f'twitter:image" content="{expected}"' in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_og_type_is_article(client, sample_post):
    """og:type=article for post detail (Slack/X show article unfurls)."""
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    assert 'og:type" content="article"' in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_emits_article_meta(client, sample_post):
    """article:published_time and article:author meta tags are present."""
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    assert 'property="article:published_time"' in resp.text
    assert sample_post.published_at.isoformat() in resp.text
    assert 'property="article:author"' in resp.text
    assert sample_post.author_name in resp.text
    # Per-tag article:tag entries
    assert 'property="article:tag"' in resp.text
    assert "Programs" in resp.text
    assert "Staff Picks" in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_emits_blogposting_and_breadcrumb_jsonld(client, sample_post):
    """JSON-LD includes BlogPosting and BreadcrumbList entries for the post."""
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    entries = _extract_jsonld_blocks(resp.text)
    types = {e.get("@type") for e in entries}
    assert "BlogPosting" in types
    assert "BreadcrumbList" in types

    post_ld = next(e for e in entries if e.get("@type") == "BlogPosting")
    assert post_ld["headline"] == sample_post.title
    assert post_ld["author"]["name"] == sample_post.author_name
    assert post_ld["datePublished"] == sample_post.published_at.isoformat()
    # Image absolute-URL promotion
    assert post_ld["image"].startswith("http")


@pytest.mark.asyncio
async def test_blog_post_detail_missing_slug_returns_404(client):
    """Unknown slug returns 404 + robots=noindex,follow so crawlers skip it."""
    resp = await client.get("/api/v1/seo/blog/does-not-exist")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text
    assert "Post not found" in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_draft_post_returns_404(client, draft_post):
    """Draft (unpublished) posts must 404 to crawlers — never leak unpublished content."""
    resp = await client.get(f"/api/v1/seo/blog/{draft_post.slug}")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text


@pytest.mark.asyncio
async def test_blog_post_detail_canonical_matches_spa_route(client, sample_post):
    """Canonical URL must be /blog/{slug}, matching the SPA route."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/blog/{sample_post.slug}"
    resp = await client.get(f"/api/v1/seo/blog/{sample_post.slug}")
    assert resp.status_code == 200
    assert f'canonical" href="{expected}"' in resp.text


# ---------- /seo/blog/tag/{slug} ----------

@pytest.mark.asyncio
async def test_blog_tag_known_returns_200_with_tag_name_in_title(client, sample_tag):
    """A known tag returns 200 with the tag name in the title."""
    resp = await client.get(f"/api/v1/seo/blog/tag/{sample_tag.slug}")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert sample_tag.name in m.group(1)


@pytest.mark.asyncio
async def test_blog_tag_canonical_points_at_query_filtered_blog(client, sample_tag):
    """Tag canonical is /blog?tag={slug}, matching the SPA's filtered-list URL."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/blog?tag={sample_tag.slug}"
    resp = await client.get(f"/api/v1/seo/blog/tag/{sample_tag.slug}")
    assert resp.status_code == 200
    # _escape escapes & for HTML attrs — ?tag= has no ampersand so plain compare is OK
    assert f'canonical" href="{expected}"' in resp.text


@pytest.mark.asyncio
async def test_blog_tag_unknown_returns_404_with_noindex(client):
    """Unknown tag slug returns 404 + robots=noindex,follow."""
    resp = await client.get("/api/v1/seo/blog/tag/totally-fake-tag")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text
    assert "Tag not found" in resp.text


# ---------- _REQUIRED_PLACEHOLDERS coverage ----------

def test_required_placeholders_validator_passes_on_real_index_html(caplog):
    """Sanity: the live frontend/index.html shell contains every placeholder
    the new blog handlers' _inject_meta calls will try to replace. If a future
    Vite/index.html change drops one, this test fires alongside the existing
    drift test in test_seo_meta_drift.py.
    """
    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()
    caplog.set_level(logging.ERROR, logger="app.api.v1.seo_meta")
    seo_meta_module._validate_template_placeholders(template)
    errors = [r for r in caplog.records if r.levelno >= logging.ERROR]
    assert errors == [], (
        "frontend/index.html is missing _REQUIRED_PLACEHOLDERS substrings: "
        f"{[r.getMessage() for r in errors]}"
    )


def test_required_placeholders_unchanged_by_blog_routes():
    """Document that the blog handlers do NOT introduce new structural
    anchors into _inject_meta — article:* meta tags are injected before
    </head> (which IS in _REQUIRED_PLACEHOLDERS already), so the tuple stays
    as-is. Locks the contract: if someone adds a new injection anchor inside
    _inject_meta for a blog field, this test fails and forces them to update
    _REQUIRED_PLACEHOLDERS at the same time. (Meta/link tags are matched by
    tag shape and inserted when absent, so they are NOT anchors.)
    """
    expected = {
        "<title>",
        "</head>",
        '<div id="root">',
    }
    assert set(seo_meta_module._REQUIRED_PLACEHOLDERS) == expected
