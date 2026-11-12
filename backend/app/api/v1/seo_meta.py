# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SEO Meta Tag Injection for Dynamic Pages.

Returns the SPA's index.html with page-specific <title>, og:title, og:description
injected for crawlers and social media previews.

Used by nginx: bot user-agents get proxied here instead of the static SPA.
"""
import json
import re
from app.core.logging import get_logger
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.config import get_settings
from ...services.book_challenge_service import BookChallengeService
from ...services.metislib_client import get_metislib_client
from ...services.metislib_errors import MetisLibError
from ...services.organization_features_service import OrganizationFeaturesService
from ...models.board import BoardMeeting
from ...models.blog import BlogPost, BlogPostStatus, BlogTag
from ...models.event import Event
from ...models.learning import Course, CourseLifecycleStage

logger = get_logger(__name__)

router = APIRouter(tags=["seo"])

# Cache the template HTML in memory
_INDEX_HTML: Optional[str] = None

# Structural anchors _inject_meta depends on in the fetched shell. Meta/link
# tags are matched by tag SHAPE (attribute key), not by their current content,
# and are inserted before </head> when absent — so a tenant editing
# frontend/index.html copy cannot silently break SSR injection. Only these
# anchors are load-bearing: ``</head>`` (insertion point for meta/JSON-LD/
# preloads) and ``<div id="root">`` (body_hero_html anchor for e.g. the
# /discover and /banned-books templates). ``<title>`` is checked as an
# early-warning that the fetched document is a real SPA shell.
_REQUIRED_PLACEHOLDERS: tuple[str, ...] = (
    "<title>",
    "</head>",
    '<div id="root">',
)


def _validate_template_placeholders(html: str) -> None:
    missing = [p for p in _REQUIRED_PLACEHOLDERS if p not in html]
    if not missing:
        return
    logger.error(
        "SSR template drift: %d expected placeholder string(s) not found in the served "
        "frontend shell. Head/body injection anchored on these will silently no-op. "
        "Verify the served frontend shell is a real SPA index.html. "
        "Missing: %s",
        len(missing),
        ", ".join(repr(p[:60]) for p in missing),
    )


async def _get_index_html() -> str:
    global _INDEX_HTML
    if _INDEX_HTML is not None:
        return _INDEX_HTML

    # Try local file paths first
    for path in [
        Path("/usr/share/nginx/html/index.html"),
        Path("/app/static/index.html"),
    ]:
        if path.exists():
            _INDEX_HTML = path.read_text()
            _validate_template_placeholders(_INDEX_HTML)
            return _INDEX_HTML

    # Fetch from frontend container via HTTP
    import httpx
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get("http://frontend:80/")
            if resp.status_code == 200 and "<title>" in resp.text:
                _INDEX_HTML = resp.text
                _validate_template_placeholders(_INDEX_HTML)
                return _INDEX_HTML
    except Exception as e:  # noqa: BLE001  # frontend index fetch best-effort — fall back to minimal SEO
        logger.warning("Could not fetch index.html from frontend: %s", e)

    # Minimal SEO-only fallback (crawlers only need meta tags). Derived from
    # settings so a forked deployment never advertises another library's
    # identity when the SPA shell is unreachable.
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    library = _escape(settings.library_name)
    tagline = f"Search the catalog, reserve a room, check your holds, find events at {library}."
    _INDEX_HTML = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{tagline}" />
<title>Library</title>
<meta property="og:site_name" content="{library}">
<meta property="og:type" content="website">
<meta property="og:url" content="{base}/">
<meta property="og:title" content="{library}">
<meta property="og:description" content="{tagline}">
<meta property="og:image" content="{base}/og-image.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{library}">
<meta name="twitter:description" content="{tagline}">
<meta name="twitter:image" content="{base}/og-image.png">
<link rel="alternate" type="text/calendar" title="{library} Events" href="/api/v1/events/calendar.ics" />
<link rel="canonical" href="{base}/" />
<meta name="robots" content="index, follow" />
</head>
<body><div id="root"></div></body>
</html>"""
    _validate_template_placeholders(_INDEX_HTML)
    return _INDEX_HTML


def _set_tag(html: str, pattern: str, replacement_tag: str) -> str:
    """Replace the first tag matching ``pattern`` with ``replacement_tag``,
    inserting the tag before ``</head>`` when the shell has no match.

    Matching is structural (tag shape, not current content), so tenant edits
    to frontend/index.html copy can't silently no-op the injection. The
    lambda replacement avoids re.sub backslash-escape interpretation of the
    injected content.
    """
    new_html, n = re.subn(
        pattern, lambda _m: replacement_tag, html, count=1, flags=re.DOTALL
    )
    if n:
        return new_html
    return html.replace("</head>", f"  {replacement_tag}\n  </head>", 1)


def _meta_pattern(attr: str, key: str) -> str:
    """Pattern for ``<meta {attr}="{key}" content="...">`` in either
    attribute order, single- or double-quoted."""
    key_re = re.escape(key)
    return (
        rf'<meta\s+{attr}=["\']{key_re}["\']\s+content=["\'][^"\']*["\']\s*/?>'
        rf'|<meta\s+content=["\'][^"\']*["\']\s+{attr}=["\']{key_re}["\']\s*/?>'
    )


def _set_meta(html: str, attr: str, key: str, value: str) -> str:
    return _set_tag(
        html,
        _meta_pattern(attr, key),
        f'<meta {attr}="{key}" content="{_escape(value)}" />',
    )


async def _inject_meta(
    title: str,
    description: str,
    *,
    canonical_url: str,
    og_type: str = "article",
    image: Optional[str] = None,
    json_ld: Optional[dict | list] = None,
    robots: Optional[str] = None,
    preload_images: Optional[list[str]] = None,
    body_hero_html: Optional[str] = None,
    article_meta: Optional[dict] = None,
) -> str:
    html = await _get_index_html()
    html = _set_tag(html, r"<title>.*?</title>", f"<title>{_escape(title)}</title>")
    html = _set_meta(html, "property", "og:title", title)
    html = _set_meta(html, "property", "og:description", description)
    html = _set_meta(html, "name", "twitter:title", title)
    html = _set_meta(html, "name", "twitter:description", description)
    html = _set_meta(html, "name", "description", description)
    html = _set_meta(html, "property", "og:url", canonical_url)
    html = _set_meta(html, "property", "og:type", og_type)
    html = _set_tag(
        html,
        r'<link\s+rel=["\']canonical["\']\s+href=["\'][^"\']*["\']\s*/?>',
        f'<link rel="canonical" href="{_escape(canonical_url)}" />',
    )
    if robots:
        html = _set_meta(html, "name", "robots", robots)
    if image:
        html = _set_meta(html, "property", "og:image", image)
        html = _set_meta(html, "name", "twitter:image", image)
    if json_ld:
        payload = json.dumps(json_ld, ensure_ascii=False).replace("</", "<\\/")
        ld_tag = f'<script type="application/ld+json">{payload}</script>'
        html = html.replace("</head>", f"  {ld_tag}\n  </head>", 1)
    if preload_images:
        # Filter out None/empty so callers can pass cover_url lists without
        # pre-filtering. fetchpriority=high promotes these to the LCP queue.
        tags = "\n  ".join(
            f'<link rel="preload" as="image" fetchpriority="high" href="{_escape(url)}" />'
            for url in preload_images
            if url
        )
        if tags:
            html = html.replace("</head>", f"  {tags}\n  </head>", 1)
    if body_hero_html:
        html = html.replace(
            '<div id="root">',
            f'<div id="root">{body_hero_html}',
            1,
        )
    if article_meta:
        meta_tags: list[str] = []
        for key, value in article_meta.items():
            if value is None:
                continue
            values = value if isinstance(value, (list, tuple)) else [value]
            for v in values:
                if v is None:
                    continue
                meta_tags.append(
                    f'<meta property="article:{_escape(key)}" content="{_escape(str(v))}" />'
                )
        if meta_tags:
            html = html.replace(
                "</head>",
                "  " + "\n  ".join(meta_tags) + "\n  </head>",
                1,
            )
    return html


def _escape(s: str) -> str:
    return s.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")


def _summarize_for_card(meeting: BoardMeeting) -> str:
    raw = (meeting.description or "").strip()
    if not raw:
        date_str = meeting.scheduled_date.strftime("%B %d, %Y") if meeting.scheduled_date else "an upcoming date"
        return f"L30 Board {meeting.meeting_type or 'meeting'} on {date_str}"
    if len(raw) <= 200:
        return raw
    # word-boundary truncate
    cut = raw[:200].rsplit(" ", 1)[0]
    return f"{cut}\u2026"

def _meeting_event_jsonld(meeting: BoardMeeting) -> dict:
    start = meeting.start_time or meeting.scheduled_date
    end = meeting.end_time or meeting.start_time or meeting.scheduled_date

    payload: dict = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": meeting.title,
        "startDate": start.isoformat() if start else None,
        "endDate": end.isoformat() if end else None,
        "eventStatus": (
            "https://schema.org/EventCancelled"
            if meeting.is_cancelled
            else "https://schema.org/EventScheduled"
        ),
        "eventAttendanceMode": (
            "https://schema.org/OnlineEventAttendanceMode"
            if meeting.is_virtual
            else "https://schema.org/OfflineEventAttendanceMode"
        ),
        "organizer": {
            "@type": "GovernmentOrganization",
            "name": "L30 Community Library",
            "url": "https://l30.org",
        },
    }
    if meeting.is_virtual:
        if meeting.virtual_meeting_url:
            payload["location"] = {
                "@type": "VirtualLocation",
                "url": meeting.virtual_meeting_url,
            }
    else:
        if meeting.location:
            payload["location"] = {
                "@type": "Place",
                "name": meeting.location,
                "address": meeting.location,
            }
    if meeting.description:
        payload["description"] = meeting.description
    return payload



@router.get("/seo/ebooks/{ebook_id}", response_class=HTMLResponse)
async def seo_ebook_detail(ebook_id: int, db: AsyncSession = Depends(get_db)):
    """Return index.html with ebook-specific meta tags for crawlers."""
    settings = get_settings()

    # Try MetisLib
    if settings.metislib_enabled:
        try:
            client = get_metislib_client()
            data = await client.get_ebook(ebook_id)
            title = f"{data.get('title', 'Ebook')} by {data.get('author_name', 'Unknown')} | L30 Library"
            desc = (data.get("description") or f"Borrow {data.get('title', 'this ebook')} from L30 Library.")[:200]
            image = data.get("cover_url")
            return HTMLResponse(await _inject_meta(
                title,
                desc,
                canonical_url=f"{settings.frontend_url.rstrip('/')}/ebooks/{ebook_id}",
                og_type="article",
                image=image,
            ))
        except MetisLibError:
            pass

    return HTMLResponse(await _get_index_html())


@router.get("/seo/board/meetings/{meeting_id}", response_class=HTMLResponse)
async def seo_board_meeting_detail(meeting_id: int, db: AsyncSession = Depends(get_db)):
    """Return index.html with board-meeting-specific meta tags for crawlers."""
    settings = get_settings()
    stmt = select(BoardMeeting).where(BoardMeeting.id == meeting_id)
    try:
        result = await db.execute(stmt)
        meeting = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_board_meeting_detail: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    if meeting is None:
        return HTMLResponse(
            await _inject_meta(
                title="Meeting not found \u2014 L30",
                description="This board meeting could not be found.",
                canonical_url=f"{settings.frontend_url.rstrip('/')}/board/meetings",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    title = f"{meeting.title} \u2014 Board meeting \u2014 L30"
    description = _summarize_for_card(meeting)
    canonical_url = f"{settings.frontend_url.rstrip('/')}/board/meetings/{meeting_id}"
    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=description,
            canonical_url=canonical_url,
            og_type="article",
            json_ld=_meeting_event_jsonld(meeting),
        )
    )

def _extract_id_from_slug(slug: str) -> int | None:
    import re
    m = re.search(r"-(\d+)$", slug)
    if m:
        return int(m.group(1))
    # Plain integer slug (e.g. legacy /indie/author/42)
    try:
        return int(slug)
    except ValueError:
        return None


@router.get("/seo/indie/author/{slug}", response_class=HTMLResponse)
async def seo_indie_author_detail(slug: str, db: AsyncSession = Depends(get_db)):
    """Return index.html with indie author-specific meta tags for crawlers.

    Author data lives in local indie_authors table (pen_name, bio).
    The slug is <safe-pen_name>-<indie_authors.id> as generated by the frontend.
    Degrades to unmodified shell on unknown slug to avoid crawler deindex on stale URLs.
    """
    from ...models.indie_author import IndieAuthor
    from ...models.indie_ebook_borrow import IndieEbook

    settings = get_settings()

    def _slug_expr(col):
        return func.btrim(
            func.regexp_replace(func.lower(col), "[^a-z0-9]+", "-", "g"), "-"
        )

    try:
        author = (
            await db.execute(
                select(IndieAuthor).where(_slug_expr(IndieAuthor.pen_name) == slug)
            )
        ).scalar_one_or_none()
        catalog_row = (
            await db.execute(
                select(IndieEbook.author_pen_name, func.count())
                .where(
                    _slug_expr(IndieEbook.author_pen_name) == slug,
                    IndieEbook.title.is_not(None),
                    IndieEbook.copies_owned > 0,
                )
                .group_by(IndieEbook.author_pen_name)
                .order_by(func.count().desc())
                .limit(1)
            )
        ).first()
    except Exception:
        logger.exception("seo_indie_author_detail: DB read failed; returning shell")
        return HTMLResponse(await _get_index_html())

    catalog_name = catalog_row[0] if catalog_row else None
    book_count = catalog_row[1] if catalog_row else 0

    # Legacy <pen_name>-<id> slug: resolve the registered author by id.
    if author is None and book_count == 0:
        author_id = _extract_id_from_slug(slug)
        if author_id is not None:
            author = (
                await db.execute(select(IndieAuthor).where(IndieAuthor.id == author_id))
            ).scalar_one_or_none()

    if author is None and book_count == 0:
        return HTMLResponse(await _get_index_html())

    display_name = (
        (author.pen_name if (author and author.pen_name) else None) or catalog_name or slug
    )
    if author and author.bio:
        description = author.bio[:200]
    elif book_count:
        noun = "title" if book_count == 1 else "titles"
        description = f"Browse {book_count} indie {noun} by {display_name} at L30 Library."
    else:
        description = f"Discover books by {display_name} at L30 Library."
    image = author.profile_image_url if author else None
    return HTMLResponse(await _inject_meta(
        f"{display_name} — Indie Author — L30 Library",
        description,
        canonical_url=f"{settings.frontend_url.rstrip('/')}/indie/author/{slug}",
        og_type="article",
        image=image or None,
    ))


@router.get("/seo/indie/book/{slug}", response_class=HTMLResponse)
async def seo_indie_book_detail(slug: str, db: AsyncSession = Depends(get_db)):
    """Return index.html with indie book-specific meta tags for crawlers.

    Book data is fetched from MetisLib via the same pattern as seo_ebook_detail.
    The slug is <safe-title>-<metislib_ebook_id> as generated by the frontend.
    Degrades to unmodified shell on MetisLib miss or when MetisLib is disabled.
    """
    settings = get_settings()

    if settings.metislib_enabled:
        ebook_id = _extract_id_from_slug(slug)
        if ebook_id is not None:
            try:
                client = get_metislib_client()
                data = await client.get_ebook(ebook_id, entry_type="indie_ebook")
                title = f"{data.get('title', 'Ebook')} by {data.get('author_name') or data.get('author_pen_name', 'Unknown')} | L30 Library"
                desc = (data.get("description") or f"Borrow {data.get('title', 'this ebook')} from L30 Library.")[:200]
                image = data.get("cover_url")
                return HTMLResponse(await _inject_meta(
                    title,
                    desc,
                    canonical_url=f"{settings.frontend_url.rstrip('/')}/indie/book/{slug}",
                    og_type="article",
                    image=image or None,
                ))
            except MetisLibError:
                pass
            except Exception:
                logger.exception("seo_indie_book_detail: unexpected error; returning shell")

    return HTMLResponse(await _get_index_html())


# ---------------------------------------------------------------------------
# Learning Center SSR (Bug §5 + Enhancement §1 of the SEO audit)
#
# Three handlers covering /learn, /learn/catalog, /learn/course/{id}. The
# course detail handler emits both schema.org Course and LearningResource
# JSON-LD so crawlers that index either consume the same data, mirroring the
# board-meeting Event payload pattern (PR #784).
# ---------------------------------------------------------------------------

def _truncate_for_meta(raw: str, limit: int = 160) -> str:
    raw = (raw or "").strip()
    if len(raw) <= limit:
        return raw
    cut = raw[:limit].rsplit(" ", 1)[0]
    return f"{cut}…"


def _iso8601_minutes(minutes: Optional[int]) -> Optional[str]:
    if minutes is None:
        return None
    try:
        m = int(minutes)
    except (TypeError, ValueError):
        return None
    if m <= 0:
        return None
    return f"PT{m}M"


def _organization_jsonld() -> dict:
    settings = get_settings()
    return {
        "@type": "EducationalOrganization",
        "name": settings.library_name,
        "url": settings.frontend_url.rstrip("/"),
    }


def _course_jsonld(course: Course) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "Course",
        "name": course.title,
        "url": f"{base}/learn/course/{course.id}",
        "provider": _organization_jsonld(),
        "courseCode": str(course.id),
    }
    if course.description:
        payload["description"] = course.description
    if course.difficulty:
        payload["educationalLevel"] = course.difficulty
    iso = _iso8601_minutes(course.estimated_minutes)
    if iso:
        payload["timeRequired"] = iso
    if course.thumbnail_url:
        payload["image"] = course.thumbnail_url
    return payload


def _course_learning_resource_jsonld(course: Course) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "learningResourceType": "Course",
        "name": course.title,
        "url": f"{base}/learn/course/{course.id}",
        "provider": _organization_jsonld(),
    }
    if course.description:
        payload["description"] = course.description
    if course.difficulty:
        payload["educationalLevel"] = course.difficulty
    iso = _iso8601_minutes(course.estimated_minutes)
    if iso:
        payload["timeRequired"] = iso
    if course.thumbnail_url:
        payload["image"] = course.thumbnail_url
    return payload


async def _published_patron_courses(
    db: AsyncSession, limit: int = 10
) -> list[Course]:
    stmt = (
        select(Course)
        .where(Course.lifecycle_stage == CourseLifecycleStage.PUBLISHED)
        .where(Course.access_level == "patron")
        .where(Course.deleted_at.is_(None))
        .order_by(Course.created_at.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _learn_home_jsonld(top_courses: list[Course]) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    org = _organization_jsonld()
    org["@context"] = "https://schema.org"
    if top_courses:
        org["hasCourse"] = [
            {
                "@type": "Course",
                "name": c.title,
                "url": f"{base}/learn/course/{c.id}",
                "courseCode": str(c.id),
            }
            for c in top_courses
        ]
    return org


@router.get("/seo/learn", response_class=HTMLResponse)
async def seo_learn_home(db: AsyncSession = Depends(get_db)):
    """Return the Learning Center landing shell with EducationalOrganization JSON-LD."""
    settings = get_settings()
    library = settings.library_name
    title = f"Library Learning Center | {library}"
    description = (
        f"Free online courses from {library}. Browse self-paced learning on "
        "library skills, technology, and community topics — open to all patrons."
    )

    try:
        top_courses = await _published_patron_courses(db, limit=10)
    except Exception:
        logger.exception("seo_learn_home: DB read failed; degrading to landing without hasCourse")
        top_courses = []

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description),
            canonical_url=f"{settings.frontend_url.rstrip('/')}/learn",
            og_type="website",
            json_ld=_learn_home_jsonld(top_courses),
        )
    )


@router.get("/seo/learn/catalog", response_class=HTMLResponse)
async def seo_learn_catalog(db: AsyncSession = Depends(get_db)):
    """Return the course-catalog shell. Emphasizes browsing in copy + JSON-LD."""
    settings = get_settings()
    library = settings.library_name
    title = f"Browse Courses | Learning Center | {library}"
    description = (
        f"Browse the full course catalog at {library}. Filter by topic, "
        "difficulty, and estimated time — every course is free to enroll."
    )

    try:
        top_courses = await _published_patron_courses(db, limit=10)
    except Exception:
        logger.exception("seo_learn_catalog: DB read failed; degrading to landing without hasCourse")
        top_courses = []

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description),
            canonical_url=f"{settings.frontend_url.rstrip('/')}/learn/catalog",
            og_type="website",
            json_ld=_learn_home_jsonld(top_courses),
        )
    )


@router.get("/seo/learn/course/{course_id}", response_class=HTMLResponse)
async def seo_learn_course_detail(course_id: int, db: AsyncSession = Depends(get_db)):
    """Return index.html with course-specific meta tags + schema.org Course JSON-LD.

    Visibility filter mirrors the patron-facing learning routes
    (app/api/v1/learning.py): ``lifecycle_stage == PUBLISHED`` AND
    ``access_level == 'patron'`` AND ``deleted_at IS NULL``. Anything else
    is 404 + ``robots="noindex,follow"`` so crawlers don't index private or
    superseded course IDs.
    """
    settings = get_settings()
    library = settings.library_name
    canonical_base = settings.frontend_url.rstrip("/")

    try:
        result = await db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_learn_course_detail: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    not_findable = (
        course is None
        or course.deleted_at is not None
        or course.access_level != "patron"
        or course.lifecycle_stage != CourseLifecycleStage.PUBLISHED
    )
    if not_findable:
        return HTMLResponse(
            await _inject_meta(
                title=f"Course not found — Learning Center | {library}",
                description="This course could not be found or is not currently available.",
                canonical_url=f"{canonical_base}/learn/catalog",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    title = f"{course.title} | Learning Center | {library}"
    raw_desc = course.description or f"Take {course.title}, a free course from {library}."
    description = _truncate_for_meta(raw_desc, limit=160)
    canonical_url = f"{canonical_base}/learn/course/{course.id}"

    # Emit two JSON-LD blocks (Course + LearningResource) by composing
    # them as a list — schema.org accepts an array payload in one script
    # tag and consumers parse each entry independently.
    json_ld_payload = [
        _course_jsonld(course),
        _course_learning_resource_jsonld(course),
    ]

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=description,
            canonical_url=canonical_url,
            og_type="article",
            image=course.thumbnail_url or None,
            json_ld=json_ld_payload,
        )
    )


# ---------------------------------------------------------------------------
# Events SSR (PR #1 of patron-events SEO sweep)
#
# Two handlers: /seo/events (list) and /seo/events/{event_id} (detail). Both
# emit per-page <title>/og/canonical and schema.org Event JSON-LD so crawlers
# index upcoming programming with rich-result eligibility. The detail handler
# additionally emits a BreadcrumbList block (Home > Events > <title>).
# ---------------------------------------------------------------------------


def _event_jsonld(event: Event, *, canonical_url: str) -> dict:
    settings = get_settings()
    start = event.start_time
    end = event.end_time or event.start_time

    payload: dict = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event.title,
        "startDate": start.isoformat() if start else None,
        "endDate": end.isoformat() if end else None,
        "eventStatus": "https://schema.org/EventScheduled",
        "eventAttendanceMode": (
            "https://schema.org/OnlineEventAttendanceMode"
            if event.is_virtual
            else "https://schema.org/OfflineEventAttendanceMode"
        ),
        "url": canonical_url,
        "organizer": {
            "@type": "Organization",
            "name": settings.library_name,
            "url": settings.frontend_url.rstrip("/"),
        },
        "offers": {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "USD",
            "availability": "https://schema.org/InStock",
            "url": canonical_url,
        },
    }
    if event.is_virtual:
        if event.virtual_link:
            payload["location"] = {
                "@type": "VirtualLocation",
                "url": event.virtual_link,
            }
    elif event.location:
        payload["location"] = {
            "@type": "Place",
            "name": event.location,
            "address": event.location,
        }
    if event.description:
        payload["description"] = event.description
    if event.image_url:
        payload["image"] = event.image_url
    if event.audience:
        payload["typicalAgeRange"] = event.audience
    return payload


def _event_breadcrumb_jsonld(event: Event, *, canonical_url: str) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Events", "item": f"{base}/events"},
            {"@type": "ListItem", "position": 3, "name": event.title, "item": canonical_url},
        ],
    }


async def _published_upcoming_events(db: AsyncSession, limit: int = 25) -> list[Event]:
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    stmt = (
        select(Event)
        .where(Event.is_published == True)  # noqa: E712
        .where(Event.start_time >= now)
        .where(Event.recurrence_rule.is_(None))
        .where(Event.parent_event_id.is_(None))
        .order_by(Event.start_time)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Discover landing SSR (Improvement #5 + Enhancement #5 of the /discover audit)
#
# Combines per-route meta/canonical with a body-hero injection + LCP-preload
# for the first two carousel cover images. Bot-only — non-bot users get the
# static SPA shell and React-driven render. Cover query mirrors the page's
# carousel: is_new (last 30d) + ICU title sort, limit 2.
# ---------------------------------------------------------------------------


async def _discover_carousel_covers(db: AsyncSession, limit: int = 2) -> list[str]:
    from datetime import datetime, timedelta, timezone
    from ...models.catalog import CatalogItem, CatalogingStatus, ItemStatus, SensitivityLevel

    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    is_postgres = bool(getattr(db, "bind", None)) and db.bind.dialect.name == "postgresql"
    title_order = (
        CatalogItem.title.collate("und-x-icu") if is_postgres else CatalogItem.title
    )
    stmt = (
        select(CatalogItem.cover_url)
        .where(CatalogItem.created_at >= thirty_days_ago)
        .where(CatalogItem.cover_url.isnot(None))
        .where(CatalogItem.cataloging_status == CatalogingStatus.CATALOGED)
        .where(CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC)
        .where(CatalogItem.status != ItemStatus.withdrawn)
        .order_by(title_order)
        .limit(limit)
    )
    result = await db.execute(stmt)
    return [url for url in result.scalars().all() if url]


def _discover_body_hero() -> str:
    return (
        '<h1 style="font-family:Georgia,serif;font-weight:700;font-size:1.875rem;'
        'margin:0 0 0.25rem 0">Discover</h1>'
        '<p style="margin:0 0 1rem 0">Staff picks, new arrivals, and what your '
        "neighbors are reading</p>"
    )


@router.get("/seo/discover", response_class=HTMLResponse)
async def seo_discover(db: AsyncSession = Depends(get_db)):
    """Return the /discover landing shell with route-specific meta + LCP preloads."""
    settings = get_settings()
    library = settings.library_name
    title = f"Discover — Staff picks & new arrivals — L30 — {library}"
    description = (
        f"Browse staff picks, new arrivals, and curated shelves at {library}. "
        "Start your next read on the L30 discovery storefront."
    )
    canonical_url = f"{settings.frontend_url.rstrip('/')}/discover"

    try:
        preload_covers = await _discover_carousel_covers(db, limit=2)
    except Exception:
        logger.exception("seo_discover: cover query failed; degrading to no-preload SSR")
        preload_covers = []

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description),
            canonical_url=canonical_url,
            og_type="website",
            preload_images=preload_covers,
            body_hero_html=_discover_body_hero(),
        )
    )


def _render_banned_books_body(
    library_name: str,
    stats: dict,
    challenges: list,
) -> str:
    """Render the /banned-books SSR body: mission text, stats summary, and
    anonymized public challenge stories, for crawlers and no-JS readers."""
    escaped_library = _escape(library_name or "")
    outcomes = (stats or {}).get("outcomes", {}) or {}
    retained = outcomes.get("RETAINED", 0) + outcomes.get("RETAINED_WITH_CHANGES", 0)
    removed = outcomes.get("REMOVED", 0)
    total = (stats or {}).get("total_challenges", 0)
    pending = (stats or {}).get("pending_challenges", 0)
    resolved_this_year = (stats or {}).get("resolved_this_year", 0)

    if challenges:
        story_parts: list[str] = []
        for c in challenges:
            display_title = _escape(
                getattr(c, "public_title", None) or getattr(c, "title", None) or "Untitled"
            )
            outcome_raw = getattr(c, "outcome", None) or ""
            outcome_label = _escape(str(outcome_raw).replace("_", " ").title())
            author = getattr(c, "author", None)
            public_summary = getattr(c, "public_summary", None)
            lessons_learned = getattr(c, "lessons_learned", None)

            piece = [f'<div class="challenge-story"><h3>{display_title}</h3>']
            if author:
                piece.append(f'<p class="challenge-story-author">by {_escape(author)}</p>')
            piece.append(f'<p class="challenge-story-outcome">{outcome_label}</p>')
            if public_summary:
                piece.append(f'<p class="challenge-story-summary">{_escape(public_summary)}</p>')
            if lessons_learned:
                piece.append(f'<p class="challenge-story-lessons">{_escape(lessons_learned)}</p>')
            piece.append("</div>")
            story_parts.append("".join(piece))
        stories_html = "".join(story_parts)
    else:
        stories_html = (
            '<p class="challenge-story-empty">No public challenge records are '
            "available yet.</p>"
        )

    return (
        '<div class="banned-books-ssr">'
        "<h1>Intellectual Freedom &amp; Banned Books</h1>"
        "<p>Libraries are bastions of intellectual freedom. We believe in the right "
        "to read, the freedom of thought, and access to diverse perspectives. Here "
        "you can learn about our commitment to these values and how we handle "
        "challenges to library materials.</p>"
        "<section>"
        "<h2>Our Commitment</h2>"
        f"<p>{escaped_library} is committed to providing materials that represent "
        "diverse viewpoints on a wide range of topics. We support the freedom to "
        "read and oppose censorship. When materials are challenged, we follow a "
        "fair and transparent review process guided by the American Library "
        "Association's Library Bill of Rights.</p>"
        "</section>"
        '<section class="banned-books-stats">'
        "<h2>Challenge Statistics</h2>"
        f"<div><span>{total}</span> Total Challenges</div>"
        f"<div><span>{pending}</span> Under Review</div>"
        f"<div><span>{retained}</span> Retained</div>"
        f"<div><span>{removed}</span> Removed</div>"
        f"<div><span>{resolved_this_year}</span> Resolved This Year</div>"
        "</section>"
        '<section class="banned-books-stories">'
        "<h2>Public Challenge Records</h2>"
        f"{stories_html}"
        "</section>"
        "</div>"
    )


@router.get("/seo/banned-books", response_class=HTMLResponse)
async def seo_banned_books(db: AsyncSession = Depends(get_db)):
    """Return the /banned-books shell with mission text + stats summary
    injected into <div id="root"> for crawlers and no-JS readers.

    Degrades to the unmodified shell (200, not 404) when the
    banned_books_tracking_enabled feature flag is off -- a 404 would harm
    crawler indexing of any previously-shared link. Degrades to a
    mission-text-only body (zeroed stats, no stories) if the stats or public
    challenges lookup fails, so a transient DB error never surfaces as a
    500 to a crawler.
    """
    try:
        enabled = await OrganizationFeaturesService.is_feature_enabled(
            db, "banned_books_tracking_enabled"
        )
    except Exception:
        logger.exception(
            "seo_banned_books: feature-flag lookup failed; degrading to unmodified shell"
        )
        enabled = False

    if not enabled:
        return HTMLResponse(await _get_index_html())

    settings = get_settings()
    library = settings.library_name
    canonical_url = f"{settings.frontend_url.rstrip('/')}/banned-books"
    title = f"Intellectual Freedom & Banned Books | {library}"
    description = (
        f"Learn how {library} handles challenges to library materials and see "
        "our public transparency log of past book challenges and their outcomes."
    )

    try:
        stats = await BookChallengeService.get_statistics(db)
    except Exception:
        logger.exception(
            "seo_banned_books: stats lookup failed; degrading to zeroed stats"
        )
        stats = {}

    try:
        challenges = await BookChallengeService.list_public_challenges(db, limit=10)
    except Exception:
        logger.exception(
            "seo_banned_books: public challenges lookup failed; degrading to no stories"
        )
        challenges = []

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description),
            canonical_url=canonical_url,
            og_type="website",
            body_hero_html=_render_banned_books_body(
                library_name=library,
                stats=stats,
                challenges=challenges,
            ),
        )
    )


@router.get("/seo/events", response_class=HTMLResponse)
async def seo_events_list(db: AsyncSession = Depends(get_db)):
    """Return the events listing shell with per-event Event JSON-LD.

    Each upcoming event emits its own schema.org Event payload, packaged as a
    JSON array in a single ``<script type="application/ld+json">`` tag
    (consumers parse element-by-element). Degrades to landing page without
    per-event JSON-LD on DB error so the crawler still sees a valid shell.
    """
    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")
    canonical_url = f"{base}/events"
    title = f"Events & Programs | {library}"
    description = (
        f"Browse upcoming events at {library}: story times, workshops, book "
        "clubs, and community programs. All events are free to attend."
    )

    try:
        events = await _published_upcoming_events(db, limit=25)
    except Exception:
        logger.exception("seo_events_list: DB read failed; degrading to landing without per-event JSON-LD")
        events = []

    json_ld_payload: list[dict] = [
        _event_jsonld(e, canonical_url=f"{base}/events/detail/{e.id}") for e in events
    ]

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description, limit=160),
            canonical_url=canonical_url,
            og_type="website",
            json_ld=json_ld_payload if json_ld_payload else None,
        )
    )


@router.get("/seo/events/{event_id}", response_class=HTMLResponse)
async def seo_event_detail(event_id: int, db: AsyncSession = Depends(get_db)):
    """Return index.html with event-specific meta + Event + BreadcrumbList JSON-LD.

    Visibility mirrors the patron-facing list endpoint (is_published==True).
    Unpublished, missing, or deleted events return 404 + robots="noindex,follow"
    so crawlers don't index stale URLs. Canonical matches the actual public
    SPA route ``/events/detail/{id}``.
    """
    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")

    try:
        result = await db.execute(select(Event).where(Event.id == event_id))
        event = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_event_detail: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    if event is None or not event.is_published:
        return HTMLResponse(
            await _inject_meta(
                title=f"Event not found | {library}",
                description="This event could not be found or is no longer available.",
                canonical_url=f"{base}/events",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    canonical_url = f"{base}/events/detail/{event.id}"
    title = f"{event.title} | Events | {library}"
    raw_desc = event.description or f"Join {library} for {event.title}."
    description = _truncate_for_meta(raw_desc, limit=160)

    json_ld_payload: list[dict] = [
        _event_jsonld(event, canonical_url=canonical_url),
        _event_breadcrumb_jsonld(event, canonical_url=canonical_url),
    ]

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=description,
            canonical_url=canonical_url,
            og_type="article",
            image=event.image_url or None,
            json_ld=json_ld_payload,
        )
    )


# ---------------------------------------------------------------------------
# Blog SSR
#
# Three handlers: /seo/blog (list), /seo/blog/{slug} (post detail),
# /seo/blog/tag/{tag_slug} (tag-filtered list). Each emits per-page
# <title>/og/canonical for crawlers and social-share unfurlers; the detail
# handler additionally emits og:type=article + article:published_time +
# article:author + per-tag article:tag (injected before </head>, NOT through
# _REQUIRED_PLACEHOLDERS) plus a schema.org BlogPosting + BreadcrumbList
# JSON-LD payload.
# ---------------------------------------------------------------------------


def _strip_tags(raw: str) -> str:
    import re
    no_tags = re.sub(r"<[^>]+>", " ", raw or "")
    return re.sub(r"\s+", " ", no_tags).strip()


def _absolute_url(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    if url.startswith(("http://", "https://", "//")):
        return url
    base = get_settings().frontend_url.rstrip("/")
    if url.startswith("/"):
        return f"{base}{url}"
    return f"{base}/{url}"


def _blogpost_jsonld(post: BlogPost, *, canonical_url: str) -> dict:
    settings = get_settings()
    image = _absolute_url(post.featured_image)
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "BlogPosting",
        "headline": post.title,
        "url": canonical_url,
        "mainEntityOfPage": canonical_url,
        "author": {
            "@type": "Person",
            "name": post.author_name or settings.library_name,
        },
        "publisher": {
            "@type": "Organization",
            "name": settings.library_name,
            "url": settings.frontend_url.rstrip("/"),
        },
    }
    if post.published_at:
        payload["datePublished"] = post.published_at.isoformat()
    if post.updated_at:
        payload["dateModified"] = post.updated_at.isoformat()
    elif post.published_at:
        payload["dateModified"] = post.published_at.isoformat()
    if image:
        payload["image"] = image
    if post.tldr:
        payload["description"] = post.tldr
    if post.tags:
        payload["keywords"] = ", ".join(t.name for t in post.tags)
    return payload


def _blog_breadcrumb_jsonld(post: BlogPost, *, canonical_url: str) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": f"{base}/"},
            {"@type": "ListItem", "position": 2, "name": "Blog", "item": f"{base}/blog"},
            {"@type": "ListItem", "position": 3, "name": post.title, "item": canonical_url},
        ],
    }


@router.get("/seo/blog", response_class=HTMLResponse)
async def seo_blog_list(db: AsyncSession = Depends(get_db)):
    """Return the blog landing shell with per-page meta + Blog JSON-LD.

    Description is intentionally static rather than derived from the latest
    post: static description is stable across deploys, doesn't churn with
    publishing cadence, and keeps the list-page card consistent in unfurlers.
    """
    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")
    canonical_url = f"{base}/blog"

    title = f"{library} Blog"
    description = (
        f"Stories, updates, and announcements from {library}. Read about new "
        "programs, staff picks, and what's happening at your library."
    )

    json_ld: dict = {
        "@context": "https://schema.org",
        "@type": "Blog",
        "name": title,
        "url": canonical_url,
        "publisher": {
            "@type": "Organization",
            "name": library,
            "url": base,
        },
    }

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description, limit=160),
            canonical_url=canonical_url,
            og_type="website",
            json_ld=json_ld,
        )
    )


@router.get("/seo/blog/tag/{tag_slug}", response_class=HTMLResponse)
async def seo_blog_tag(tag_slug: str, db: AsyncSession = Depends(get_db)):
    """Return the tag-filtered blog list shell.

    404 + ``robots="noindex,follow"`` when the tag slug is unknown so
    crawlers don't index stale or typoed tag URLs. Canonical points at
    ``/blog?tag={slug}`` (the SPA's actual filtered-list URL) so unfurlers
    deep-link correctly.
    """
    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")

    try:
        result = await db.execute(select(BlogTag).where(BlogTag.slug == tag_slug))
        tag = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_blog_tag: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    if tag is None:
        return HTMLResponse(
            await _inject_meta(
                title=f"Tag not found — Blog | {library}",
                description="This blog tag could not be found.",
                canonical_url=f"{base}/blog",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    canonical_url = f"{base}/blog?tag={tag_slug}"
    title = f"{library} Blog — #{tag.name}"
    description = (
        f"Posts tagged #{tag.name} on the {library} blog. Browse stories, "
        "updates, and announcements filtered by topic."
    )

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description, limit=160),
            canonical_url=canonical_url,
            og_type="website",
        )
    )


@router.get("/seo/blog/{slug}", response_class=HTMLResponse)
async def seo_blog_post_detail(slug: str, db: AsyncSession = Depends(get_db)):
    """Return index.html with post-specific meta + BlogPosting JSON-LD.

    Visibility filter: ``status == published``. Anything else (draft,
    scheduled, missing) returns 404 + ``robots="noindex,follow"`` so
    crawlers never index a private slug. Canonical matches the SPA route
    ``/blog/{slug}``. og:image is promoted to absolute via ``_absolute_url``.
    """
    from sqlalchemy.orm import selectinload

    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")

    try:
        result = await db.execute(
            select(BlogPost)
            .options(selectinload(BlogPost.tags))
            .where(BlogPost.slug == slug)
        )
        post = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_blog_post_detail: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    if post is None or post.status != BlogPostStatus.published:
        return HTMLResponse(
            await _inject_meta(
                title=f"Post not found — Blog | {library}",
                description="This blog post could not be found or is not currently available.",
                canonical_url=f"{base}/blog",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    canonical_url = f"{base}/blog/{post.slug}"
    title = post.title or f"Blog post — {library}"

    # Description fallback chain: meta_description -> tldr -> body[:160] stripped.
    raw_desc = post.meta_description or post.tldr or _strip_tags(post.body)
    description = _truncate_for_meta(raw_desc or f"Read this post on the {library} blog.", limit=160)

    image = _absolute_url(post.featured_image)

    article_meta: dict = {}
    if post.published_at:
        article_meta["published_time"] = post.published_at.isoformat()
    if post.updated_at:
        article_meta["modified_time"] = post.updated_at.isoformat()
    if post.author_name:
        article_meta["author"] = post.author_name
    if post.tags:
        article_meta["tag"] = [t.name for t in post.tags]

    json_ld_payload: list[dict] = [
        _blogpost_jsonld(post, canonical_url=canonical_url),
        _blog_breadcrumb_jsonld(post, canonical_url=canonical_url),
    ]

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=description,
            canonical_url=canonical_url,
            og_type="article",
            image=image,
            json_ld=json_ld_payload,
            article_meta=article_meta or None,
        )
    )


# ---------------------------------------------------------------------------
# Learning-paths SSR + learn sitemap
#
# /seo/learning-paths and /seo/learning-paths/{id} mirror the patron-facing
# visibility rules in app/api/v1/learning_paths.py: anonymous users see
# published+draft public paths, but only PUBLISHED public paths are indexable.
# Draft ("Coming Soon") paths render real meta with robots noindex,follow.
#
# /seo/learn/sitemap.xml emits every indexable course and learning-path URL;
# it is referenced from frontend/public/sitemap.xml (the sitemap index).
# ---------------------------------------------------------------------------
from xml.etree.ElementTree import Element, SubElement, tostring  # noqa: E402

from fastapi import Response  # noqa: E402

from ...models.learning_path import LearningPath  # noqa: E402


async def _public_paths(db: AsyncSession, *, statuses: tuple[str, ...]) -> list[LearningPath]:
    stmt = (
        select(LearningPath)
        .where(LearningPath.is_public.is_(True))
        .where(LearningPath.status.in_(statuses))
        .order_by(LearningPath.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


def _path_jsonld(path: LearningPath, courses: list[Course]) -> dict:
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    payload: dict = {
        "@context": "https://schema.org",
        "@type": "LearningResource",
        "learningResourceType": "Learning path",
        "name": path.title,
        "url": f"{base}/learning-paths/{path.id}",
        "provider": _organization_jsonld(),
    }
    if path.description:
        payload["description"] = path.description
    if path.difficulty:
        payload["educationalLevel"] = path.difficulty
    total_minutes = sum(c.estimated_minutes or 0 for c in courses)
    iso = _iso8601_minutes(total_minutes or None)
    if iso:
        payload["timeRequired"] = iso
    if courses:
        payload["hasPart"] = [
            {
                "@type": "Course",
                "name": c.title,
                "url": f"{base}/learn/course/{c.id}",
                "courseCode": str(c.id),
            }
            for c in courses
        ]
    return payload


def _path_indexable_courses(path: LearningPath) -> list[Course]:
    """Published patron courses inside a path, in sort order."""
    courses: list[Course] = []
    for pc in sorted(path.path_courses, key=lambda p: p.sort_order):
        c = pc.course
        if (
            c is not None
            and c.deleted_at is None
            and c.access_level == "patron"
            and c.lifecycle_stage == CourseLifecycleStage.PUBLISHED
        ):
            courses.append(c)
    return courses


@router.get("/seo/learning-paths", response_class=HTMLResponse)
async def seo_learning_paths_list(db: AsyncSession = Depends(get_db)):
    """Return the learning-paths list shell with ItemList JSON-LD."""
    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")
    title = f"Learning Paths | {library}"
    description = (
        f"Guided learning paths from {library}: free course sequences that "
        "take you from first steps to confident skills, at your own pace."
    )

    try:
        paths = await _public_paths(db, statuses=("published",))
    except Exception:
        logger.exception("seo_learning_paths_list: DB read failed; degrading to shell without ItemList")
        paths = []

    json_ld = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": title,
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": f"{base}/learning-paths/{p.id}",
                "name": p.title,
            }
            for i, p in enumerate(paths)
        ],
    }

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(description),
            canonical_url=f"{base}/learning-paths",
            og_type="website",
            json_ld=json_ld,
        )
    )


@router.get("/seo/learning-paths/{path_id}", response_class=HTMLResponse)
async def seo_learning_path_detail(path_id: int, db: AsyncSession = Depends(get_db)):
    """Return index.html with path-specific meta + LearningResource JSON-LD."""
    from sqlalchemy.orm import selectinload
    from ...models.learning_path import PathCourse

    settings = get_settings()
    library = settings.library_name
    base = settings.frontend_url.rstrip("/")

    try:
        result = await db.execute(
            select(LearningPath)
            .where(LearningPath.id == path_id)
            .options(selectinload(LearningPath.path_courses).selectinload(PathCourse.course))
        )
        path = result.scalar_one_or_none()
    except Exception:
        logger.exception("seo_learning_path_detail: DB read failed; returning unmodified shell")
        return HTMLResponse(await _get_index_html())

    not_findable = (
        path is None
        or not path.is_public
        or path.status not in ("published", "draft")
    )
    if not_findable:
        return HTMLResponse(
            await _inject_meta(
                title=f"Learning path not found | {library}",
                description="This learning path could not be found or is not currently available.",
                canonical_url=f"{base}/learning-paths",
                og_type="website",
                robots="noindex,follow",
            ),
            status_code=404,
        )

    courses = _path_indexable_courses(path)
    title = f"{path.title} | Learning Paths | {library}"
    raw_desc = path.description or f"Follow the {path.title} learning path, free from {library}."
    canonical_url = f"{base}/learning-paths/{path.id}"
    # Draft paths render as "Coming Soon" for patrons — visible, not indexable.
    robots = "noindex,follow" if path.status == "draft" else None

    return HTMLResponse(
        await _inject_meta(
            title=title,
            description=_truncate_for_meta(raw_desc, limit=160),
            canonical_url=canonical_url,
            og_type="article",
            image=path.thumbnail_url or None,
            json_ld=_path_jsonld(path, courses),
            robots=robots,
        )
    )


@router.get("/seo/learn/sitemap.xml")
async def seo_learn_sitemap(db: AsyncSession = Depends(get_db)):
    """Sitemap of indexable Learning Center content: published patron courses
    and published public learning paths. Referenced from /sitemap.xml."""
    base = get_settings().frontend_url.rstrip("/")
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    def _add(loc: str, lastmod, changefreq: str, priority: str) -> None:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = loc
        if lastmod is not None:
            SubElement(url, "lastmod").text = lastmod.strftime("%Y-%m-%d")
        SubElement(url, "changefreq").text = changefreq
        SubElement(url, "priority").text = priority

    courses = await _published_patron_courses(db, limit=500)
    for c in courses:
        _add(
            f"{base}/learn/course/{c.id}",
            c.updated_at or c.created_at,
            "monthly",
            "0.7",
        )

    paths = await _public_paths(db, statuses=("published",))
    for p in paths:
        _add(
            f"{base}/learning-paths/{p.id}",
            p.updated_at or p.created_at,
            "monthly",
            "0.6",
        )

    xml_bytes = tostring(urlset, encoding="unicode", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/xml")
