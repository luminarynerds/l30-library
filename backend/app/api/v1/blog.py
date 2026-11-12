# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import base64
import hashlib
import hmac
import os
import re
import secrets
import uuid as _uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from xml.etree.ElementTree import Element, SubElement, tostring

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.blog import BlogPost, BlogPostStatus, BlogPostTag, BlogPostVersion, BlogPostView, BlogTag
from app.models.user import User, UserRole
from app.schemas.blog import (
    BlogAuthorSummary,
    BlogPostCreate,
    BlogPostListItem,
    BlogPostListResponse,
    BlogPostResponse,
    BlogPostUpdate,
    BlogPostVersionListItem,
    BlogPostVersionResponse,
    TagResponse,
)
from app.api.v1.auth.helpers import get_optional_user
from app.api.v1.dependencies import require_staff
from app.core.config import get_settings
from app.core.rate_limit import client_ip

router = APIRouter(prefix="/blog", tags=["blog"])


def _extract_client_ip(request: Request) -> str:
    # Shared helper (CF-Connecting-IP -> X-Real-IP -> peer). Keeps the
    # view-count dedup key on the real client instead of a spoofable
    # X-Forwarded-For entry that could be rotated to inflate view counts.
    return client_ip(request)


# ============================================================================
# Preview share-link signing (stdlib HMAC; itsdangerous not a project dep)
# ============================================================================

_PREVIEW_TOKEN_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days
_PREVIEW_TOKEN_PURPOSE = b"blog-preview-v1"


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(token: str) -> bytes:
    padding = "=" * (-len(token) % 4)
    return base64.urlsafe_b64decode(token + padding)


def _sign_preview_token(post_id: int, ttl_seconds: int = _PREVIEW_TOKEN_TTL_SECONDS) -> tuple[str, datetime]:
    settings = get_settings()
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
    exp_unix = int(expires_at.timestamp())
    payload = f"{post_id}.{exp_unix}".encode("ascii")
    sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        _PREVIEW_TOKEN_PURPOSE + b"|" + payload,
        hashlib.sha256,
    ).digest()
    token = f"{_b64url_encode(payload)}.{_b64url_encode(sig)}"
    return token, expires_at


class PreviewTokenError(Exception):
    pass


class PreviewTokenExpired(PreviewTokenError):
    pass


class PreviewTokenInvalid(PreviewTokenError):
    pass


def _verify_preview_token(token: str) -> int:
    settings = get_settings()
    if not token or "." not in token:
        raise PreviewTokenInvalid("malformed token")
    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload = _b64url_decode(payload_b64)
        provided_sig = _b64url_decode(sig_b64)
    except (ValueError, base64.binascii.Error):
        raise PreviewTokenInvalid("malformed token") from None
    expected_sig = hmac.new(
        settings.secret_key.encode("utf-8"),
        _PREVIEW_TOKEN_PURPOSE + b"|" + payload,
        hashlib.sha256,
    ).digest()
    if not secrets.compare_digest(expected_sig, provided_sig):
        raise PreviewTokenInvalid("bad signature")
    try:
        post_id_str, exp_str = payload.decode("ascii").split(".", 1)
        post_id = int(post_id_str)
        exp_unix = int(exp_str)
    except (ValueError, UnicodeDecodeError):
        raise PreviewTokenInvalid("malformed payload") from None
    if datetime.now(timezone.utc).timestamp() > exp_unix:
        raise PreviewTokenExpired("token expired")
    return post_id


class PreviewLinkResponse(BaseModel):
    url: str
    expires_at: datetime


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("/posts", response_model=BlogPostListResponse)
async def list_posts(
    tag: str | None = Query(None, description="Filter by tag slug"),
    q: str | None = Query(None, description="Search title and body"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """List published blog posts, newest first.

    Note: scheduled-post promotion (scheduled → published) lives in the
    `publish_scheduled_blog_posts` APScheduler job (runs every minute) — this
    read path no longer writes, removing the prior write-amplification on
    anonymous list traffic.
    """
    base_query = select(BlogPost).where(
        BlogPost.status == BlogPostStatus.published,
        BlogPost.deleted_at.is_(None),
    )
    count_query = select(func.count(BlogPost.id)).where(
        BlogPost.status == BlogPostStatus.published,
        BlogPost.deleted_at.is_(None),
    )

    if tag:
        base_query = base_query.join(BlogPostTag).join(BlogTag).where(BlogTag.slug == tag)
        count_query = count_query.join(BlogPostTag).join(BlogTag).where(BlogTag.slug == tag)

    if q:
        search = f"%{q}%"
        base_query = base_query.where(
            BlogPost.title.ilike(search) | BlogPost.body.ilike(search)
        )
        count_query = count_query.where(
            BlogPost.title.ilike(search) | BlogPost.body.ilike(search)
        )

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        base_query.options(selectinload(BlogPost.tags))
        .order_by(BlogPost.published_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    posts = result.scalars().unique().all()

    return BlogPostListResponse(
        items=[_post_to_list_item(p) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(db: AsyncSession = Depends(get_db)):
    """List all tags with published post counts."""
    query = (
        select(BlogTag, func.count(BlogPost.id).label("post_count"))
        .join(BlogPostTag, BlogTag.id == BlogPostTag.tag_id)
        .join(BlogPost, and_(BlogPostTag.post_id == BlogPost.id, BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None)))
        .group_by(BlogTag.id)
        .order_by(BlogTag.name)
    )
    result = await db.execute(query)
    rows = result.all()
    return [
        TagResponse(id=tag.id, name=tag.name, slug=tag.slug, post_count=count)
        for tag, count in rows
    ]


@router.get("/series/{series_name}", response_model=list[BlogPostListItem])
async def get_series(series_name: str, db: AsyncSession = Depends(get_db)):
    """Get all published posts in a series, ordered."""
    query = (
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(
            and_(
                BlogPost.series_name == series_name,
                BlogPost.status == BlogPostStatus.published,
                BlogPost.deleted_at.is_(None),
            )
        )
        .order_by(BlogPost.series_order.asc())
    )
    result = await db.execute(query)
    posts = result.scalars().unique().all()
    if not posts:
        raise HTTPException(status_code=404, detail="Series not found")
    return [_post_to_list_item(p) for p in posts]


@router.get("/sitemap.xml")
async def get_sitemap(db: AsyncSession = Depends(get_db)):
    site_url = get_settings().frontend_url.rstrip("/")
    query = (
        select(BlogPost)
        .where(BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None))
        .order_by(BlogPost.published_at.desc())
    )
    result = await db.execute(query)
    posts = result.scalars().all()
    urlset = Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")
    url = SubElement(urlset, "url")
    SubElement(url, "loc").text = f"{site_url}/blog"
    SubElement(url, "changefreq").text = "daily"
    SubElement(url, "priority").text = "0.8"
    for post in posts:
        url = SubElement(urlset, "url")
        SubElement(url, "loc").text = f"{site_url}/blog/{post.slug}"
        if post.updated_at or post.published_at:
            SubElement(url, "lastmod").text = (post.updated_at or post.published_at).strftime("%Y-%m-%d")
        SubElement(url, "changefreq").text = "monthly"
        SubElement(url, "priority").text = "0.6"
    xml_bytes = tostring(urlset, encoding="unicode", xml_declaration=True)
    return Response(content=xml_bytes, media_type="application/xml")


@router.get("/feed")
async def get_feed(request: Request, db: AsyncSession = Depends(get_db)):
    """Atom XML feed of 20 most recent published posts."""
    site_url = get_settings().frontend_url.rstrip("/")
    api_url = str(request.base_url).rstrip("/")
    # Scheduled-post promotion lives in publish_scheduled_blog_posts (APScheduler,
    # every minute) — the feed read path no longer writes.
    query = (
        select(BlogPost)
        .where(BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None))
        .order_by(BlogPost.published_at.desc())
        .limit(20)
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    settings = get_settings()
    xml_bytes = _build_atom_feed(
        posts,
        feed_title=f"{settings.library_name} Blog",
        feed_id=f"{site_url}/blog",
        site_link=f"{site_url}/blog",
        self_link=f"{api_url}/api/v1/blog/feed",
        site_url=site_url,
    )
    return Response(content=xml_bytes, media_type="application/atom+xml")


@router.get("/feed/tag/{tag_slug}")
async def get_tag_feed(tag_slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Atom XML feed of 20 most recent published posts for a given tag."""
    tag_result = await db.execute(select(BlogTag).where(BlogTag.slug == tag_slug))
    tag = tag_result.scalar_one_or_none()
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")

    settings = get_settings()
    site_url = settings.frontend_url.rstrip("/")
    api_url = str(request.base_url).rstrip("/")

    # Auto-publish any scheduled posts whose time has arrived
    now = datetime.now(timezone.utc)
    scheduled_result = await db.execute(
        select(BlogPost).where(
            BlogPost.status == BlogPostStatus.scheduled,
            BlogPost.scheduled_at <= now,
        ).with_for_update(skip_locked=True)
    )
    for post in scheduled_result.scalars().all():
        post.status = BlogPostStatus.published
        if not post.published_at:
            post.published_at = post.scheduled_at
    await db.commit()

    query = (
        select(BlogPost)
        .where(
            BlogPost.status == BlogPostStatus.published,
            BlogPost.tags.any(BlogTag.slug == tag_slug),
        )
        .order_by(BlogPost.published_at.desc())
        .limit(20)
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    xml_bytes = _build_atom_feed(
        posts,
        feed_title=f"{settings.library_name} Blog — #{tag.name}",
        feed_id=f"{site_url}/blog?tag={tag.slug}",
        site_link=f"{site_url}/blog?tag={tag.slug}",
        self_link=f"{api_url}/api/v1/blog/feed/tag/{tag.slug}",
        site_url=site_url,
    )
    return Response(content=xml_bytes, media_type="application/atom+xml")


# Sentinel tokens to inject CDATA in entry content. ElementTree escapes any
# raw `<![CDATA[...]]>` placed in element text, so we substitute these tokens
# in the serialized XML string after `tostring()`.
_CDATA_OPEN = "\x00CDATA_OPEN\x00"
_CDATA_CLOSE = "\x00CDATA_CLOSE\x00"


def _build_atom_feed(
    posts,
    *,
    feed_title: str,
    feed_id: str,
    site_link: str,
    self_link: str,
    site_url: str,
) -> str:
    feed = Element("feed", xmlns="http://www.w3.org/2005/Atom")
    SubElement(feed, "title").text = feed_title
    SubElement(feed, "id").text = feed_id
    SubElement(feed, "link", href=site_link)
    SubElement(feed, "link", rel="self", href=self_link)

    if posts:
        SubElement(feed, "updated").text = (
            posts[0].published_at.isoformat() if posts[0].published_at else ""
        )

    for post in posts:
        entry = SubElement(feed, "entry")
        SubElement(entry, "title").text = post.title
        SubElement(entry, "id").text = f"{site_url}/blog/{post.slug}"
        SubElement(entry, "link", href=f"{site_url}/blog/{post.slug}")
        SubElement(entry, "published").text = (
            post.published_at.isoformat() if post.published_at else ""
        )
        SubElement(entry, "updated").text = (
            post.updated_at or post.published_at or post.created_at
        ).isoformat()
        author = SubElement(entry, "author")
        SubElement(author, "name").text = post.author_name
        if post.tldr:
            SubElement(entry, "summary").text = post.tldr
        # type="html" with the body wrapped in CDATA. Sanitization (bleach/nh3)
        # is not yet in place; until it ships, callers should treat content as
        # trusted-staff HTML.
        content = SubElement(entry, "content", type="html")
        content.text = f"{_CDATA_OPEN}{post.body or ''}{_CDATA_CLOSE}"

    xml_str = tostring(feed, encoding="unicode", xml_declaration=True)
    # Substitute sentinel tokens with real CDATA delimiters. ElementTree has
    # escaped any literal `<`/`>`/`&` inside the body, so we restore the body
    # bytes too by unescaping the CDATA-wrapped span.
    return _restore_cdata_sections(xml_str)


def _restore_cdata_sections(xml_str: str) -> str:
    out_parts: list[str] = []
    remaining = xml_str
    while True:
        open_idx = remaining.find(_CDATA_OPEN)
        if open_idx == -1:
            out_parts.append(remaining)
            break
        close_idx = remaining.find(_CDATA_CLOSE, open_idx + len(_CDATA_OPEN))
        if close_idx == -1:
            out_parts.append(remaining)
            break
        out_parts.append(remaining[:open_idx])
        inner_escaped = remaining[open_idx + len(_CDATA_OPEN) : close_idx]
        inner = (
            inner_escaped.replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&apos;", "'")
            .replace("&amp;", "&")
        )
        # Defense in depth: a literal `]]>` inside the body would close the
        # CDATA section early. Split it across two sections.
        inner = inner.replace("]]>", "]]]]><![CDATA[>")
        out_parts.append(f"<![CDATA[{inner}]]>")
        remaining = remaining[close_idx + len(_CDATA_CLOSE) :]
    return "".join(out_parts)


# NOTE: /posts/admin must be registered before /posts/{slug} to avoid
# FastAPI treating "admin" as a slug parameter.


# ============================================================================
# Staff/Admin Endpoints
# ============================================================================


@router.get("/analytics")
async def get_analytics(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Get blog analytics for staff dashboard."""
    now = datetime.now(timezone.utc)

    total_views_result = await db.execute(select(func.count(BlogPostView.id)))
    total_views = total_views_result.scalar() or 0

    total_posts_result = await db.execute(select(func.count(BlogPost.id)))
    total_posts = total_posts_result.scalar() or 0

    published_posts_result = await db.execute(
        select(func.count(BlogPost.id)).where(BlogPost.status == BlogPostStatus.published)
    )
    published_posts = published_posts_result.scalar() or 0

    views_7d_result = await db.execute(
        select(func.count(BlogPostView.id)).where(
            BlogPostView.viewed_at > now - timedelta(days=7)
        )
    )
    views_7d = views_7d_result.scalar() or 0

    views_30d_result = await db.execute(
        select(func.count(BlogPostView.id)).where(
            BlogPostView.viewed_at > now - timedelta(days=30)
        )
    )
    views_30d = views_30d_result.scalar() or 0

    top_posts_result = await db.execute(
        select(BlogPost.id, BlogPost.title, BlogPost.slug, BlogPost.view_count)
        .where(BlogPost.status == BlogPostStatus.published)
        .order_by(BlogPost.view_count.desc())
        .limit(10)
    )
    top_posts = [
        {"id": r.id, "title": r.title, "slug": r.slug, "view_count": r.view_count}
        for r in top_posts_result
    ]

    views_by_day_result = await db.execute(
        select(
            func.date(BlogPostView.viewed_at).label("date"),
            func.count(BlogPostView.id).label("count"),
        )
        .where(BlogPostView.viewed_at > now - timedelta(days=days))
        .group_by(func.date(BlogPostView.viewed_at))
        .order_by(func.date(BlogPostView.viewed_at))
    )
    views_by_day = [
        {"date": str(r.date), "count": r.count}
        for r in views_by_day_result
    ]

    return {
        "total_views": total_views,
        "total_posts": total_posts,
        "published_posts": published_posts,
        "views_last_7_days": views_7d,
        "views_last_30_days": views_30d,
        "top_posts": top_posts,
        "views_by_day": views_by_day,
    }


@router.get("/posts/admin", response_model=BlogPostListResponse)
async def list_posts_admin(
    status_filter: str | None = Query(None, alias="status"),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """List all posts including drafts (staff only)."""
    base_query = select(BlogPost)
    count_query = select(func.count(BlogPost.id))
    order_col = BlogPost.created_at.desc()

    if status_filter == "trash":
        # Trash view: only soft-deleted, ordered by deletion time.
        base_query = base_query.where(BlogPost.deleted_at.is_not(None))
        count_query = count_query.where(BlogPost.deleted_at.is_not(None))
        order_col = BlogPost.deleted_at.desc()
    elif status_filter:
        try:
            status_enum = BlogPostStatus(status_filter)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status_filter}") from None
        base_query = base_query.where(
            BlogPost.status == status_enum, BlogPost.deleted_at.is_(None)
        )
        count_query = count_query.where(
            BlogPost.status == status_enum, BlogPost.deleted_at.is_(None)
        )
    else:
        base_query = base_query.where(BlogPost.deleted_at.is_(None))
        count_query = count_query.where(BlogPost.deleted_at.is_(None))

    if q:
        search = f"%{q}%"
        base_query = base_query.where(BlogPost.title.ilike(search))
        count_query = count_query.where(BlogPost.title.ilike(search))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        base_query.options(selectinload(BlogPost.tags))
        .order_by(order_col)
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    posts = result.scalars().unique().all()

    # Global counts (unaffected by filters) for the staff dashboard header
    draft_result = await db.execute(
        select(func.count(BlogPost.id)).where(
            BlogPost.status == BlogPostStatus.draft, BlogPost.deleted_at.is_(None)
        )
    )
    published_result = await db.execute(
        select(func.count(BlogPost.id)).where(
            BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None)
        )
    )
    scheduled_result = await db.execute(
        select(func.count(BlogPost.id)).where(
            BlogPost.status == BlogPostStatus.scheduled, BlogPost.deleted_at.is_(None)
        )
    )

    return BlogPostListResponse(
        items=[_post_to_list_item(p) for p in posts],
        total=total,
        page=page,
        per_page=per_page,
        draft_count=draft_result.scalar() or 0,
        published_count=published_result.scalar() or 0,
        scheduled_count=scheduled_result.scalar() or 0,
    )


@router.get("/posts/admin/{post_id}", response_model=BlogPostResponse)
async def get_admin_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Get a single post by ID (including drafts) for staff editing."""
    result = await db.execute(
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(BlogPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_to_response(post)


# ============================================================================
# Public Endpoints (slug-based - must come after /posts/admin)
# ============================================================================


def _is_staff_role(user: Optional[User]) -> bool:
    return user is not None and user.role in {
        UserRole.STAFF,
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DIRECTOR,
        UserRole.LEGAL,
    }


@router.get("/posts/preview/{slug}", response_model=BlogPostResponse)
async def preview_post(
    slug: str,
    sig: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """Preview a post.

    Two ways to access:
    - Staff (or higher) bearer token -- existing behavior, any status.
    - Signed share-link `sig` query param -- bypasses auth iff signature
      matches the post resolved by `slug`. Token TTL: 7 days.
    """
    query = select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.slug == slug)
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()

    if sig is not None:
        try:
            signed_post_id = _verify_preview_token(sig)
        except PreviewTokenExpired:
            raise HTTPException(status_code=410, detail="Preview link expired") from None
        except PreviewTokenInvalid:
            raise HTTPException(status_code=401, detail="Invalid preview link") from None
        if not post or signed_post_id != post.id:
            # Don't leak whether post exists when sig doesn't match it.
            raise HTTPException(status_code=401, detail="Invalid preview link")
        return _post_to_response(post)

    # No sig -- fall back to existing staff-auth behavior.
    if not _is_staff_role(current_user):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    return _post_to_response(post)


@router.post("/posts/{post_id}/preview-link", response_model=PreviewLinkResponse)
async def create_preview_link(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Generate a short-lived signed share URL for an unpublished post.

    Lets staff send drafts to external reviewers (board chairs, town counsel)
    without giving them a staff account. Token is HMAC-signed with the app
    secret_key and expires in 7 days.
    """
    result = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.status == BlogPostStatus.published:
        raise HTTPException(
            status_code=400,
            detail="Preview share links are only for unpublished posts",
        )
    token, expires_at = _sign_preview_token(post.id)
    settings = get_settings()
    base = settings.frontend_url.rstrip("/")
    url = f"{base}/blog/preview/{post.slug}?sig={token}"
    return PreviewLinkResponse(url=url, expires_at=expires_at)


@router.get("/posts/{slug}", response_model=BlogPostResponse)
async def get_post(slug: str, request: Request, db: AsyncSession = Depends(get_db)):
    """Get a single published post by slug."""
    query = (
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(and_(BlogPost.slug == slug, BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None)))
    )
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Record view with 1-hour dedup per visitor.
    client_ip = _extract_client_ip(request)
    viewer_hash = hashlib.sha256(
        f"{client_ip}:{request.headers.get('user-agent', '')}".encode()
    ).hexdigest()
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    existing = await db.execute(
        select(BlogPostView).where(
            BlogPostView.post_id == post.id,
            BlogPostView.viewer_hash == viewer_hash,
            BlogPostView.viewed_at > one_hour_ago,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(BlogPostView(post_id=post.id, viewer_hash=viewer_hash))
        post.view_count = (post.view_count or 0) + 1
        await db.commit()
        post = await _refetch_post_by_id(db, post.id)

    return _post_to_response(post)


@router.get("/posts/{slug}/related", response_model=list[BlogPostListItem])
async def get_related_posts(slug: str, db: AsyncSession = Depends(get_db)):
    """Get 3-5 published posts with the most tag overlap."""
    post_query = (
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(and_(BlogPost.slug == slug, BlogPost.status == BlogPostStatus.published, BlogPost.deleted_at.is_(None)))
    )
    result = await db.execute(post_query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    tag_ids = [t.id for t in post.tags]
    if not tag_ids:
        return []

    query = (
        select(BlogPost, func.count(BlogPostTag.tag_id).label("overlap"))
        .join(BlogPostTag)
        .where(
            and_(
                BlogPostTag.tag_id.in_(tag_ids),
                BlogPost.id != post.id,
                BlogPost.status == BlogPostStatus.published,
                BlogPost.deleted_at.is_(None),
            )
        )
        .group_by(BlogPost.id)
        .order_by(func.count(BlogPostTag.tag_id).desc())
        .limit(5)
    )
    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return []
    related_ids = [r[0].id for r in rows]
    reload_query = (
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(BlogPost.id.in_(related_ids))
    )
    reload_result = await db.execute(reload_query)
    related_posts = reload_result.scalars().unique().all()

    id_order = {rid: i for i, rid in enumerate(related_ids)}
    related_posts = sorted(related_posts, key=lambda p: id_order.get(p.id, 0))

    return [_post_to_list_item(p) for p in related_posts]


@router.post("/posts", response_model=BlogPostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    post_in: BlogPostCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Create a new blog post (staff only)."""
    user_provided_slug = bool((post_in.slug or "").strip())
    base_slug = (post_in.slug or "").strip() or slugify(post_in.title) or "post"
    slug = base_slug
    suffix = 2
    while True:
        existing = await db.execute(select(BlogPost).where(BlogPost.slug == slug))
        if not existing.scalar_one_or_none():
            break
        if user_provided_slug:
            raise HTTPException(status_code=400, detail="Slug already exists")
        slug = f"{base_slug}-{suffix}"
        suffix += 1

    # Resolve author_id: explicit > current_user fallback.
    author_id = post_in.author_id if post_in.author_id is not None else current_user.id
    if author_id is not None:
        author_user = await db.get(User, author_id)
        if author_user is None:
            raise HTTPException(status_code=400, detail=f"author_id {author_id} not found")

    post = BlogPost(
        title=post_in.title,
        slug=slug,
        body=post_in.body,
        tldr=post_in.tldr,
        meta_description=post_in.meta_description,
        featured_image=post_in.featured_image,
        author_name=post_in.author_name,
        author_role=post_in.author_role,
        author_id=author_id,
        status=BlogPostStatus(post_in.status),
        series_name=post_in.series_name,
        series_order=post_in.series_order,
    )
    post.read_time_minutes = post.calculate_read_time()

    if post_in.status == "published":
        post.published_at = datetime.now(timezone.utc)
    elif post_in.status == "scheduled" and post_in.scheduled_at:
        post.scheduled_at = post_in.scheduled_at

    await _sync_tags(db, post, post_in.tags)
    await _sync_co_authors(db, post, post_in.co_author_ids, author_id)

    db.add(post)
    await db.commit()

    # Re-SELECT with eager loads so the response doesn't hit the
    # MissingGreenlet trap when serializing onupdate-expired columns
    # (e.g. updated_at) or the just-changed `author` relationship.
    reload = await db.execute(
        select(BlogPost)
        .options(
            selectinload(BlogPost.tags),
            selectinload(BlogPost.author),
            selectinload(BlogPost.co_authors),
        )
        .where(BlogPost.id == post.id)
    )
    fresh = reload.scalar_one()
    return _post_to_response(fresh)


@router.put("/posts/{post_id}", response_model=BlogPostResponse)
async def update_post(
    post_id: int,
    post_in: BlogPostUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Update a blog post (staff only)."""
    query = (
        select(BlogPost)
        .options(
            selectinload(BlogPost.tags),
            selectinload(BlogPost.co_authors),
        )
        .where(BlogPost.id == post_id)
    )
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Save current state as a version before applying changes
    version_count = await db.execute(
        select(func.count()).where(BlogPostVersion.post_id == post_id)
    )
    next_version = version_count.scalar() + 1
    version = BlogPostVersion(
        post_id=post_id,
        title=post.title,
        body=post.body,
        tldr=post.tldr,
        version_number=next_version,
        created_by=current_user.full_name if hasattr(current_user, "full_name") else None,
    )
    db.add(version)

    update_data = post_in.model_dump(exclude_unset=True)
    tags_data = update_data.pop("tags", None)
    co_author_ids = update_data.pop("co_author_ids", None)
    # author_id may legitimately be present-and-None (explicit unset)
    author_id_provided = "author_id" in update_data
    new_author_id = update_data.pop("author_id", None) if author_id_provided else None

    if "slug" in update_data and update_data["slug"] != post.slug:
        existing = await db.execute(select(BlogPost).where(BlogPost.slug == update_data["slug"]))
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Slug already exists")

    if "status" in update_data:
        update_data["status"] = BlogPostStatus(update_data["status"])

    for field, value in update_data.items():
        setattr(post, field, value)

    if author_id_provided:
        if new_author_id is not None:
            author_user = await db.get(User, new_author_id)
            if author_user is None:
                raise HTTPException(status_code=400, detail=f"author_id {new_author_id} not found")
        post.author_id = new_author_id

    if "body" in update_data:
        post.read_time_minutes = post.calculate_read_time()

    if tags_data is not None:
        await _sync_tags(db, post, tags_data)

    if co_author_ids is not None:
        await _sync_co_authors(db, post, co_author_ids, post.author_id)

    await db.commit()

    # Re-SELECT with eager loads — see create_post above.
    # populate_existing() forces the cached instance's relationships to
    # be re-resolved against the eager-load options instead of returning
    # the stale `author` from the identity map.
    reload = await db.execute(
        select(BlogPost)
        .options(
            selectinload(BlogPost.tags),
            selectinload(BlogPost.author),
            selectinload(BlogPost.co_authors),
        )
        .where(BlogPost.id == post.id)
        .execution_options(populate_existing=True)
    )
    fresh = reload.scalar_one()
    return _post_to_response(fresh)


@router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Soft-delete a blog post (staff only). The row stays in the DB with
    `deleted_at` set; all public read paths filter it out. A staff member can
    POST /posts/{id}/restore within the retention window to bring it back."""
    query = select(BlogPost).where(BlogPost.id == post_id, BlogPost.deleted_at.is_(None))
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.deleted_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/posts/{post_id}/restore", response_model=BlogPostResponse)
async def restore_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Restore a soft-deleted blog post (staff only)."""
    query = select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.id == post_id)
    result = await db.execute(query)
    post = result.scalar_one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    if post.deleted_at is None:
        raise HTTPException(status_code=400, detail="Post is not deleted")
    post.deleted_at = None
    await db.commit()
    # Re-fetch fresh -- after commit the post is expired and partial refresh
    # leaves other attrs lazy-loading on access (known L30 async-property landmine).
    result = await db.execute(
        select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.id == post_id)
    )
    post = result.scalar_one()
    return _post_to_response(post)


@router.put("/posts/{post_id}/publish", response_model=BlogPostResponse)
async def publish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Publish a draft post (staff only)."""
    query = select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.id == post_id)
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = BlogPostStatus.published
    if not post.published_at:
        post.published_at = datetime.now(timezone.utc)

    await db.commit()
    post = await _refetch_post_by_id(db, post.id)

    return _post_to_response(post)


@router.put("/posts/{post_id}/unpublish", response_model=BlogPostResponse)
async def unpublish_post(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Unpublish a post back to draft (staff only)."""
    query = select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.id == post_id)
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    post.status = BlogPostStatus.draft
    await db.commit()
    post = await _refetch_post_by_id(db, post.id)

    return _post_to_response(post)


@router.put("/posts/{post_id}/schedule", response_model=BlogPostResponse)
async def schedule_post(
    post_id: int,
    scheduled_at: datetime = Query(..., description="ISO 8601 timestamp"),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    """Schedule a draft post for future publication (staff only).

    The frontend sends scheduled_at as a query param
    (PUT /posts/{id}/schedule?scheduled_at=...), so accept it that way.
    """
    query = (
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(BlogPost.id == post_id)
    )
    result = await db.execute(query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if post.status != BlogPostStatus.draft:
        raise HTTPException(
            status_code=400,
            detail="Only draft posts can be scheduled",
        )

    if scheduled_at.tzinfo is None:
        # Treat naive datetimes as UTC rather than rejecting; clients sending
        # ISO strings without tz are common. Future-dated check below still
        # applies.
        scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)

    if scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400,
            detail="scheduled_at must be in the future",
        )

    post.status = BlogPostStatus.scheduled
    post.scheduled_at = scheduled_at

    await db.commit()
    post = await _refetch_post_by_id(db, post.id)
    return _post_to_response(post)


# ============================================================================
# Version History Endpoints
# ============================================================================


@router.get("/posts/{post_id}/versions", response_model=list[BlogPostVersionListItem])
async def list_versions(
    post_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    post = await db.execute(select(BlogPost).where(BlogPost.id == post_id))
    if not post.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Post not found")

    query = (
        select(BlogPostVersion)
        .where(BlogPostVersion.post_id == post_id)
        .order_by(BlogPostVersion.version_number.desc())
    )
    result = await db.execute(query)
    versions = result.scalars().all()
    return [
        BlogPostVersionListItem(
            id=v.id,
            version_number=v.version_number,
            title=v.title,
            created_at=v.created_at,
            created_by=v.created_by,
        )
        for v in versions
    ]


@router.get("/posts/{post_id}/versions/{version_id}", response_model=BlogPostVersionResponse)
async def get_version(
    post_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    query = select(BlogPostVersion).where(
        BlogPostVersion.id == version_id,
        BlogPostVersion.post_id == post_id,
    )
    result = await db.execute(query)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return BlogPostVersionResponse(
        id=version.id,
        version_number=version.version_number,
        title=version.title,
        body=version.body,
        tldr=version.tldr,
        created_at=version.created_at,
        created_by=version.created_by,
    )


@router.put("/posts/{post_id}/versions/{version_id}/restore", response_model=BlogPostResponse)
async def restore_version(
    post_id: int,
    version_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    post_query = select(BlogPost).options(selectinload(BlogPost.tags)).where(BlogPost.id == post_id)
    result = await db.execute(post_query)
    post = result.scalars().unique().one_or_none()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    version_query = select(BlogPostVersion).where(
        BlogPostVersion.id == version_id,
        BlogPostVersion.post_id == post_id,
    )
    version_result = await db.execute(version_query)
    version = version_result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    # Save current state as a new version before restoring
    version_count = await db.execute(
        select(func.count()).where(BlogPostVersion.post_id == post_id)
    )
    next_version = version_count.scalar() + 1
    snapshot = BlogPostVersion(
        post_id=post_id,
        title=post.title,
        body=post.body,
        tldr=post.tldr,
        version_number=next_version,
        created_by=current_user.full_name if hasattr(current_user, "full_name") else None,
    )
    db.add(snapshot)

    # Restore fields from the selected version
    post.title = version.title
    post.body = version.body
    post.tldr = version.tldr
    post.read_time_minutes = post.calculate_read_time()

    await db.commit()
    post = await _refetch_post_by_id(db, post.id)
    return _post_to_response(post)


# ----------------------------------------------------------------------------
# Media (images for the staff editor)
#
# Storage layout: <STORAGE_LOCAL_PATH>/blog/<uuid>.<ext>
# `STORAGE_LOCAL_PATH` defaults to `/app/uploads`, which is the persistent
# named volume `l30_uploads` declared on the backend service in
# docker-compose.prod.yml. Files are served back through the existing
# `/uploads/...` StaticFiles mount in app.main.
# ----------------------------------------------------------------------------

_BLOG_MEDIA_ALLOWED_MIMES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
_BLOG_MEDIA_MIME_TO_EXT = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}
_BLOG_MEDIA_MAX_BYTES = 5 * 1024 * 1024  # 5 MB; matches BlogFormPage.tsx


def _blog_media_dir() -> str:
    base = get_settings().storage_local_path or "/app/uploads"
    return os.path.join(base, "blog")


@router.post("/media", status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    current_user=Depends(require_staff),
):
    """Upload an image for use in a blog post (staff only).

    - mime must be one of jpeg/png/gif/webp
    - size capped at 5 MB
    - written to the `l30_uploads` named volume at /app/uploads/blog/<uuid>.<ext>
    - returns `{ "url": "/uploads/blog/<filename>" }` for editor insertion
    """
    mime = (file.content_type or "").lower().split(";")[0].strip()
    if mime not in _BLOG_MEDIA_ALLOWED_MIMES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported media type: {mime or 'unknown'}",
        )

    # Read up to limit+1 to detect oversize without buffering arbitrarily.
    data = await file.read(_BLOG_MEDIA_MAX_BYTES + 1)
    if len(data) > _BLOG_MEDIA_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Image must be under 5MB")
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload")

    # Verify the actual bytes match an allowed image type, not just the
    # client-supplied Content-Type header.
    from app.core.file_validation import validate_file_type
    ext = _BLOG_MEDIA_MIME_TO_EXT[mime]
    if validate_file_type(data[:16], f"upload.{ext}") is None:
        raise HTTPException(
            status_code=415,
            detail="File content does not match its declared image type",
        )

    upload_dir = _blog_media_dir()
    os.makedirs(upload_dir, exist_ok=True)
    filename = f"{_uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(upload_dir, filename)
    with open(filepath, "wb") as f:
        f.write(data)

    return {"url": f"/uploads/blog/{filename}"}


@router.get("/media")
async def list_media(current_user=Depends(require_staff)):
    upload_dir = _blog_media_dir()
    if not os.path.exists(upload_dir):
        return []
    files = []
    for f in sorted(
        os.listdir(upload_dir),
        key=lambda x: os.path.getmtime(os.path.join(upload_dir, x)),
        reverse=True,
    ):
        filepath = os.path.join(upload_dir, f)
        if os.path.isfile(filepath):
            stat = os.stat(filepath)
            files.append(
                {
                    "filename": f,
                    "url": f"/uploads/blog/{f}",
                    "size": stat.st_size,
                    "uploaded_at": stat.st_mtime,
                }
            )
    return files


@router.delete("/media/{filename}")
async def delete_media(filename: str, current_user=Depends(require_staff)):
    # Block path traversal — `filename` must be a bare basename.
    if "/" in filename or "\\" in filename or filename in {"", ".", ".."}:
        raise HTTPException(400, "Invalid filename")
    filepath = os.path.join(_blog_media_dir(), filename)
    if not os.path.isfile(filepath):
        raise HTTPException(404, "File not found")
    os.remove(filepath)
    return {"message": "Deleted"}


@router.post("/posts/bulk/publish")
async def bulk_publish(post_ids: list[int], db: AsyncSession = Depends(get_db), current_user=Depends(require_staff)):
    for pid in post_ids:
        result = await db.execute(select(BlogPost).where(BlogPost.id == pid))
        post = result.scalar_one_or_none()
        if post and post.status != BlogPostStatus.published:
            post.status = BlogPostStatus.published
            if not post.published_at:
                post.published_at = datetime.now(timezone.utc)
    await db.commit()
    return {"published": len(post_ids)}


@router.post("/posts/bulk/delete")
async def bulk_delete(post_ids: list[int], db: AsyncSession = Depends(get_db), current_user=Depends(require_staff)):
    """Soft-delete the given post IDs. Returns the actual number of rows that
    transitioned from not-deleted to deleted (silent skips for missing IDs
    or already-deleted rows)."""
    now = datetime.now(timezone.utc)
    deleted = 0
    for pid in post_ids:
        result = await db.execute(select(BlogPost).where(BlogPost.id == pid, BlogPost.deleted_at.is_(None)))
        post = result.scalar_one_or_none()
        if post:
            post.deleted_at = now
            deleted += 1
    await db.commit()
    return {"deleted": deleted, "requested": len(post_ids)}
    return {"deleted": len(post_ids)}


# ============================================================================
# Helpers
# ============================================================================


async def _sync_tags(db: AsyncSession, post: BlogPost, tag_names: list[str]):
    post.tags = []
    for name in tag_names:
        name = name.strip()
        if not name:
            continue
        tag_slug = slugify(name)
        result = await db.execute(select(BlogTag).where(BlogTag.slug == tag_slug))
        tag = result.scalar_one_or_none()
        if not tag:
            tag = BlogTag(name=name, slug=tag_slug)
            db.add(tag)
            await db.flush()
        post.tags.append(tag)


async def _sync_co_authors(
    db: AsyncSession,
    post: BlogPost,
    co_author_ids: list[int] | None,
    primary_author_id: int | None,
) -> None:
    ids = list(dict.fromkeys(co_author_ids or []))  # dedupe, preserve order
    if primary_author_id is not None:
        ids = [i for i in ids if i != primary_author_id]
    if not ids:
        post.co_authors = []
        return
    result = await db.execute(select(User).where(User.id.in_(ids)))
    users = list(result.scalars().all())
    found_ids = {u.id for u in users}
    missing = [i for i in ids if i not in found_ids]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"co_author_ids not found: {missing}",
        )
    # Preserve caller-supplied ordering
    by_id = {u.id: u for u in users}
    post.co_authors = [by_id[i] for i in ids]


async def _cleanup_orphan_tags(db: AsyncSession):
    orphan_query = (
        select(BlogTag)
        .outerjoin(BlogPostTag)
        .group_by(BlogTag.id)
        .having(func.count(BlogPostTag.post_id) == 0)
    )
    result = await db.execute(orphan_query)
    orphans = result.scalars().all()
    for tag in orphans:
        await db.delete(tag)
    if orphans:
        await db.commit()


def _user_to_author_summary(user: User | None) -> BlogAuthorSummary | None:
    if user is None:
        return None
    role = user.staff_role or (user.role.value if hasattr(user.role, "value") else user.role)
    return BlogAuthorSummary(id=user.id, full_name=user.full_name, role=role)


def _compute_byline(post: BlogPost) -> str:
    if post.author is not None:
        name = post.author.full_name
        role = post.author.staff_role or (
            post.author.role.value
            if hasattr(post.author.role, "value")
            else post.author.role
        )
        return f"{name}, {role}" if role else name
    if post.author_name:
        return (
            f"{post.author_name}, {post.author_role}"
            if post.author_role
            else post.author_name
        )
    return ""


async def _refetch_post_by_id(db: AsyncSession, post_id: int) -> BlogPost:
    result = await db.execute(
        select(BlogPost)
        .options(selectinload(BlogPost.tags))
        .where(BlogPost.id == post_id)
    )
    return result.scalars().unique().one()


def _post_to_response(post: BlogPost) -> BlogPostResponse:
    return BlogPostResponse(
        id=post.id,
        title=post.title,
        slug=post.slug,
        body=post.body,
        tldr=post.tldr,
        meta_description=post.meta_description,
        featured_image=post.featured_image,
        author_name=post.author_name,
        author_role=post.author_role,
        author_id=post.author_id,
        author=_user_to_author_summary(post.author),
        co_authors=[
            _user_to_author_summary(u) for u in (post.co_authors or [])
        ],
        byline=_compute_byline(post),
        status=post.status.value if hasattr(post.status, "value") else post.status,
        published_at=post.published_at,
        scheduled_at=post.scheduled_at,
        series_name=post.series_name,
        series_order=post.series_order,
        read_time_minutes=post.read_time_minutes,
        view_count=post.view_count or 0,
        created_at=post.created_at,
        updated_at=post.updated_at,
        tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in post.tags],
    )


def _post_to_list_item(post: BlogPost) -> BlogPostListItem:
    return BlogPostListItem(
        id=post.id,
        title=post.title,
        slug=post.slug,
        tldr=post.tldr,
        meta_description=post.meta_description,
        featured_image=post.featured_image,
        author_name=post.author_name,
        author_role=post.author_role,
        status=post.status.value if hasattr(post.status, "value") else post.status,
        published_at=post.published_at,
        scheduled_at=post.scheduled_at,
        series_name=post.series_name,
        read_time_minutes=post.read_time_minutes,
        view_count=post.view_count or 0,
        created_at=post.created_at,
        deleted_at=post.deleted_at,
        tags=[TagResponse(id=t.id, name=t.name, slug=t.slug) for t in post.tags],
    )
