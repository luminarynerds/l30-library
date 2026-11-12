# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Learning Center SSR handlers.

/api/v1/seo/learn, /api/v1/seo/learn/catalog, /api/v1/seo/learn/course/{id}
are hit by nginx for crawler user-agents so they get per-page <title>,
og:*, twitter:*, canonical, and schema.org Course/EducationalOrganization
JSON-LD injected into the SPA shell.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.core.config import get_settings
from app.models.learning import Course, CourseLifecycleStage


@pytest.fixture(autouse=True)
def _stub_ssr_index_html(monkeypatch):
    """Make SSR tests use the real frontend/index.html template.

    Production seo_meta.py fetches http://frontend:80/ when running inside
    the backend container; on the host pytest runs from, that URL is not
    the L30 frontend. Monkeypatch the cache + the fetch function so tests
    see the actual source template that production string-replaces against.
    """
    import app.api.v1.seo_meta as seo_meta_module

    template_path = Path(__file__).resolve().parents[4] / "frontend" / "index.html"
    template = template_path.read_text()

    async def _stubbed_get_index_html() -> str:
        return template

    monkeypatch.setattr(seo_meta_module, "_get_index_html", _stubbed_get_index_html)
    monkeypatch.setattr(seo_meta_module, "_INDEX_HTML", None)
    yield


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_jsonld_payloads(body: str) -> list:
    """Pull every <script type='application/ld+json'> body and parse each as JSON.

    Flattens array payloads so callers can match by @type without caring
    whether the SSR handler emitted one script with an array or N scripts
    with a single object each.
    """
    out: list = []
    for m in re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>',
        body,
        re.DOTALL,
    ):
        raw = m.group(1).replace("<\\/", "</")
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            out.extend(parsed)
        else:
            out.append(parsed)
    return out


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def published_course(test_db):
    """A patron-facing published course with full descriptive data."""
    course = Course(
        title="Intro to Library Tech",
        description="A self-paced overview of catalog systems, holds, and patron services.",
        thumbnail_url="https://l30.org/thumbs/courses/intro.png",
        access_level="patron",
        estimated_minutes=240,
        difficulty="beginner",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def draft_course(test_db):
    """Same shape as published_course but lifecycle_stage=draft → must 404 in SSR."""
    course = Course(
        title="Unfinished Draft",
        description="Should not be visible to crawlers.",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def staff_course(test_db):
    """Published but staff-only → must 404 in patron-facing SSR."""
    course = Course(
        title="Staff Onboarding",
        description="Restricted to library employees.",
        access_level="staff",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


@pytest.fixture
async def deleted_course(test_db):
    """Published patron course but soft-deleted → must 404 in SSR."""
    course = Course(
        title="Retired Course",
        description="Soft-deleted, should not be indexed.",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        deleted_at=datetime.now(timezone.utc),
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)
    return course


# ---------------------------------------------------------------------------
# /seo/learn home
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_learn_home_returns_200_with_library_name(client):
    """Home title contains 'Library Learning Center | <library_name>'."""
    settings = get_settings()
    resp = await client.get("/api/v1/seo/learn")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    title = m.group(1)
    assert "Library Learning Center" in title
    assert settings.library_name in title


@pytest.mark.asyncio
async def test_seo_learn_home_emits_educational_organization_jsonld(client):
    """Home page JSON-LD includes EducationalOrganization @type."""
    resp = await client.get("/api/v1/seo/learn")
    assert resp.status_code == 200
    payloads = _extract_jsonld_payloads(resp.text)
    assert any(p.get("@type") == "EducationalOrganization" for p in payloads), (
        f"No EducationalOrganization payload found in: {[p.get('@type') for p in payloads]}"
    )


@pytest.mark.asyncio
async def test_seo_learn_home_hasCourse_links_published_courses(client, published_course):
    """When a published patron course exists, JSON-LD hasCourse lists it."""
    resp = await client.get("/api/v1/seo/learn")
    assert resp.status_code == 200
    payloads = _extract_jsonld_payloads(resp.text)
    org = next(p for p in payloads if p.get("@type") == "EducationalOrganization")
    assert "hasCourse" in org, "EducationalOrganization payload missing hasCourse"
    course_codes = {c.get("courseCode") for c in org["hasCourse"]}
    assert str(published_course.id) in course_codes


@pytest.mark.asyncio
async def test_seo_learn_home_canonical_url_is_learn(client):
    """og:url and canonical point at /learn."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/learn"
    resp = await client.get("/api/v1/seo/learn")
    assert resp.status_code == 200
    assert f'og:url" content="{expected}"' in resp.text
    assert f'canonical" href="{expected}"' in resp.text


# ---------------------------------------------------------------------------
# /seo/learn/catalog
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_learn_catalog_title_emphasizes_browsing(client):
    """Catalog page title contains 'Browse Courses'."""
    resp = await client.get("/api/v1/seo/learn/catalog")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert "Browse Courses" in m.group(1)


@pytest.mark.asyncio
async def test_seo_learn_catalog_canonical_url_is_learn_catalog(client):
    """og:url and canonical point at /learn/catalog (not /learn)."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/learn/catalog"
    resp = await client.get("/api/v1/seo/learn/catalog")
    assert resp.status_code == 200
    assert f'og:url" content="{expected}"' in resp.text
    assert f'canonical" href="{expected}"' in resp.text


# ---------------------------------------------------------------------------
# /seo/learn/course/{id} — published positive path
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_course_detail_title_contains_course_title(client, published_course):
    """<title> contains the course title plus the library suffix."""
    settings = get_settings()
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    title = m.group(1)
    assert published_course.title in title
    assert settings.library_name in title


@pytest.mark.asyncio
async def test_seo_course_detail_description_in_meta(client, published_course):
    """Course description appears in og:description (within 160-char window)."""
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    # First ~50 chars of the description should survive the 160-char truncate
    snippet = published_course.description[:50]
    assert f'og:description" content="{snippet}' in resp.text or snippet in resp.text


@pytest.mark.asyncio
async def test_seo_course_detail_og_image_is_thumbnail(client, published_course):
    """og:image is the course thumbnail_url when present."""
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    assert f'og:image" content="{published_course.thumbnail_url}"' in resp.text


@pytest.mark.asyncio
async def test_seo_course_detail_emits_schema_org_course_jsonld(client, published_course):
    """JSON-LD includes a schema.org Course with timeRequired + courseCode."""
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    payloads = _extract_jsonld_payloads(resp.text)

    course_payload = next((p for p in payloads if p.get("@type") == "Course"), None)
    assert course_payload is not None, (
        f"No Course payload found in: {[p.get('@type') for p in payloads]}"
    )
    assert course_payload["name"] == published_course.title
    assert course_payload["courseCode"] == str(published_course.id)
    assert course_payload["timeRequired"] == "PT240M"
    assert course_payload["educationalLevel"] == "beginner"
    assert course_payload["provider"]["@type"] == "EducationalOrganization"


@pytest.mark.asyncio
async def test_seo_course_detail_emits_learning_resource_jsonld(client, published_course):
    """JSON-LD also includes a LearningResource view for broader indexer compat."""
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    payloads = _extract_jsonld_payloads(resp.text)

    lr = next((p for p in payloads if p.get("@type") == "LearningResource"), None)
    assert lr is not None, (
        f"No LearningResource payload found in: {[p.get('@type') for p in payloads]}"
    )
    assert lr["learningResourceType"] == "Course"
    assert lr["name"] == published_course.title


@pytest.mark.asyncio
async def test_seo_course_detail_canonical_url_is_course_specific(client, published_course):
    """og:url + canonical point at /learn/course/{id}."""
    settings = get_settings()
    expected = f"{settings.frontend_url.rstrip('/')}/learn/course/{published_course.id}"
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    assert f'og:url" content="{expected}"' in resp.text
    assert f'canonical" href="{expected}"' in resp.text


@pytest.mark.asyncio
async def test_seo_course_detail_og_type_is_article(client, published_course):
    """Course detail pages use og:type=article (larger unfurl card)."""
    resp = await client.get(f"/api/v1/seo/learn/course/{published_course.id}")
    assert resp.status_code == 200
    assert 'og:type" content="article"' in resp.text
    assert 'og:type" content="website"' not in resp.text


# ---------------------------------------------------------------------------
# /seo/learn/course/{id} — 404 paths
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_course_detail_missing_id_returns_404_noindex(client):
    """Unknown course ID returns 404 + robots=noindex,follow."""
    resp = await client.get("/api/v1/seo/learn/course/99999999")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text
    m = re.search(r"<title>([^<]+)</title>", resp.text)
    assert m is not None
    assert "Course not found" in m.group(1)


@pytest.mark.asyncio
async def test_seo_course_detail_draft_course_returns_404(client, draft_course):
    """Draft courses must 404 (not 200 with title) to avoid crawler indexing."""
    resp = await client.get(f"/api/v1/seo/learn/course/{draft_course.id}")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text


@pytest.mark.asyncio
async def test_seo_course_detail_staff_course_returns_404(client, staff_course):
    """Staff-only courses must 404 from the patron-facing SSR route."""
    resp = await client.get(f"/api/v1/seo/learn/course/{staff_course.id}")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text


@pytest.mark.asyncio
async def test_seo_course_detail_soft_deleted_course_returns_404(client, deleted_course):
    """Soft-deleted courses must 404 even if lifecycle_stage was published."""
    resp = await client.get(f"/api/v1/seo/learn/course/{deleted_course.id}")
    assert resp.status_code == 404
    assert 'name="robots" content="noindex,follow"' in resp.text


# ---------------------------------------------------------------------------
# XSS safety + edge cases (mirror board-meeting precedent)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_seo_course_detail_jsonld_xss_safe_closing_script_tag(client, test_db):
    """A course title containing </script> must not break out of the JSON-LD block."""
    sneaky = Course(
        title="Evil Course </script><script>alert(1)</script>",
        description="Should be escaped inside JSON-LD.",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
    )
    test_db.add(sneaky)
    await test_db.commit()
    await test_db.refresh(sneaky)

    resp = await client.get(f"/api/v1/seo/learn/course/{sneaky.id}")
    assert resp.status_code == 200

    # Pull every JSON-LD block raw and confirm none contain a literal
    # </script> (the base template's own Organization/WebSite block is also
    # on the page and never contains the escape sequence, so only require
    # it on at least one block -- the Course one).
    blocks = list(re.finditer(
        r'<script type="application/ld\+json">(.*?)</script>',
        resp.text,
        re.DOTALL,
    ))
    assert blocks, "No JSON-LD script tag found"
    escaped_found = False
    for m in blocks:
        assert "</script>" not in m.group(1), (
            "JSON-LD payload contains an unescaped </script>"
        )
        if "<\\/script>" in m.group(1):
            escaped_found = True
    assert escaped_found, "No JSON-LD block contained the escaped </script> sequence"


@pytest.mark.asyncio
async def test_seo_course_detail_long_description_truncated_at_word_boundary(client, test_db):
    """Descriptions over 160 chars are truncated at a word boundary with ellipsis."""
    long_text = (
        "This course covers a wide variety of topics across modern library "
        "operations including circulation, cataloging, patron services, "
        "outreach, and many other important subjects that staff and patrons "
        "alike should know about in detail."
    )
    course = Course(
        title="Long Description Course",
        description=long_text,
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    resp = await client.get(f"/api/v1/seo/learn/course/{course.id}")
    assert resp.status_code == 200
    # og:description content must be <= 160 + 1 (ellipsis) chars
    m = re.search(r'og:description" content="([^"]*)"', resp.text)
    assert m is not None
    desc_text = m.group(1)
    # word-boundary truncate: should end with ellipsis, not a partial word
    assert desc_text.endswith("…")
    assert len(desc_text) <= 161  # 160 char ceiling + ellipsis


@pytest.mark.asyncio
async def test_seo_course_detail_no_estimated_minutes_omits_timerequired(client, test_db):
    """Courses without estimated_minutes omit timeRequired rather than emitting PT0M."""
    course = Course(
        title="No Duration Course",
        description="Self-paced with no fixed time.",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        estimated_minutes=None,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    resp = await client.get(f"/api/v1/seo/learn/course/{course.id}")
    assert resp.status_code == 200
    payloads = _extract_jsonld_payloads(resp.text)
    course_payload = next((p for p in payloads if p.get("@type") == "Course"), None)
    assert course_payload is not None
    assert "timeRequired" not in course_payload
