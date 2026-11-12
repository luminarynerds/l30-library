# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.indie_ebook_borrow import BorrowStatus, IndieEbook, IndieEbookBorrow

router = APIRouter(prefix="/indie/catalog", tags=["indie-catalog"])


class IndieCatalogItem(BaseModel):
    # id is the L30 IndieEbook PK -- this is what all lending endpoints expect.
    # Do NOT substitute metislib_ebook_id here; they collide ~1:1 with open-access
    # catalog ids and caused the prior Borrow bug (landed the wrong Gutenberg title).
    id: int
    title: str
    author_pen_name: str
    description: Optional[str]
    cover_url: Optional[str]
    genre: Optional[str]
    language: str
    content_warnings: list[str]
    available_copies: int
    total_copies: int
    publication_year: Optional[int]

    class Config:
        from_attributes = True


class IndieCatalogDetail(IndieCatalogItem):
    subjects: list[str]
    word_count: Optional[int]
    page_count: Optional[int]
    isbn: Optional[str]
    content_rating: str
    author_id: Optional[int]
    average_rating: Optional[float]
    rating_count: int
    total_borrows: int


class IndieCatalogPage(BaseModel):
    items: list[IndieCatalogItem]
    total: int
    page: int
    per_page: int
    pages: int


class IndieGenreCount(BaseModel):
    genre: str
    count: int


class IndieCatalogRails(BaseModel):
    featured: list[IndieCatalogItem]
    popular: list[IndieCatalogItem]
    new: list[IndieCatalogItem]


def _parse_warnings(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _parse_subjects(raw: Optional[str]) -> list[str]:
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


async def _derived(db: AsyncSession, ebook_ids: list[int]) -> dict:
    """Per-ebook {average_rating, rating_count, total_borrows, active} from borrows.

    Ported from feat/indie-opds-phase2 IndieCatalogService._derived but takes
    a db session directly (no class wrapper) and keys results on local IndieEbook.id.
    """
    if not ebook_ids:
        return {}
    rows = (
        await db.execute(
            select(
                IndieEbookBorrow.ebook_id,
                func.avg(IndieEbookBorrow.rating),
                func.count(IndieEbookBorrow.rating),
                func.count(IndieEbookBorrow.id),
                func.sum(case((IndieEbookBorrow.status == BorrowStatus.active, 1), else_=0)),
            )
            .where(IndieEbookBorrow.ebook_id.in_(ebook_ids))
            .group_by(IndieEbookBorrow.ebook_id)
        )
    ).all()
    out = {}
    for ebook_id, avg, rcount, total, active in rows:
        out[ebook_id] = {
            "average_rating": round(float(avg), 1) if avg is not None else None,
            "rating_count": int(rcount or 0),
            "total_borrows": int(total or 0),
            "active": int(active or 0),
        }
    return out


def _item_from_row(row: IndieEbook, d: dict) -> IndieCatalogItem:
    owned = row.copies_owned or 0
    active = d.get("active", 0)
    avail = max(0, owned - active)
    return IndieCatalogItem(
        id=row.id,
        title=row.title or "",
        author_pen_name=row.author_pen_name or "",
        description=row.description,
        cover_url=row.cover_url,
        genre=row.genre,
        language=row.language or "en",
        content_warnings=_parse_warnings(row.content_warnings),
        available_copies=avail,
        total_copies=owned,
        publication_year=row.publication_year,
    )


# ---------------------------------------------------------------------------
# Literal routes MUST be declared before /{id} to avoid FastAPI shadowing them.
# ---------------------------------------------------------------------------

@router.get("/genres", response_model=list[IndieGenreCount])
async def list_genres(db: AsyncSession = Depends(get_db)):
    """Return genres with at least one owned, titled ebook, descending by count."""
    rows = (
        await db.execute(
            select(IndieEbook.genre, func.count(IndieEbook.id).label("cnt"))
            .where(
                IndieEbook.title.is_not(None),
                IndieEbook.genre.is_not(None),
                IndieEbook.copies_owned > 0,
            )
            .group_by(IndieEbook.genre)
            .order_by(func.count(IndieEbook.id).desc())
        )
    ).all()
    return [IndieGenreCount(genre=g, count=int(c)) for g, c in rows]


@router.get("/rails", response_model=IndieCatalogRails)
async def catalog_rails(
    limit: int = Query(12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """Three discovery rails: featured, popular, new."""
    base_filter = (
        IndieEbook.title.is_not(None),
        IndieEbook.copies_owned > 0,
    )

    # New: imported_at desc nullslast, then id desc
    new_rows = (
        await db.execute(
            select(IndieEbook)
            .where(*base_filter)
            .order_by(IndieEbook.imported_at.desc().nullslast(), IndieEbook.id.desc())
            .limit(limit)
        )
    ).scalars().all()

    # Featured: has a cover, newest first
    featured_rows = (
        await db.execute(
            select(IndieEbook)
            .where(*base_filter, IndieEbook.cover_url.is_not(None))
            .order_by(IndieEbook.imported_at.desc().nullslast(), IndieEbook.id.desc())
            .limit(limit)
        )
    ).scalars().all()

    # Popular: total_borrows desc from aggregation, tie-break title asc.
    # Fetch a wider set so we can sort after hydrating derived stats.
    popular_candidates = (
        await db.execute(
            select(IndieEbook)
            .where(*base_filter)
            .limit(min(limit * 10, 500))
        )
    ).scalars().all()

    all_rows = list({r.id: r for r in [*new_rows, *featured_rows, *popular_candidates]}.values())
    derived = await _derived(db, [r.id for r in all_rows])

    def _item(row: IndieEbook) -> IndieCatalogItem:
        return _item_from_row(row, derived.get(row.id, {}))

    popular_sorted = sorted(
        popular_candidates,
        key=lambda r: (-derived.get(r.id, {}).get("total_borrows", 0), (r.title or "").lower()),
    )[:limit]

    return IndieCatalogRails(
        featured=[_item(r) for r in featured_rows],
        popular=[_item(r) for r in popular_sorted],
        new=[_item(r) for r in new_rows],
    )


class IndieAuthorProfile(BaseModel):
    pen_name: str
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None


@router.get("/author/profile", response_model=Optional[IndieAuthorProfile])
async def get_author_profile(
    slug: str = Query(..., max_length=200),
    db: AsyncSession = Depends(get_db),
):
    """Registered indie-author profile (bio/photo) for an author slug, or null.

    Only authors with an indie_authors row carry a profile; catalog-only authors
    return null and the page falls back to a books-only view.
    """
    from ...models.indie_author import IndieAuthor

    author = (
        await db.execute(
            select(IndieAuthor).where(
                func.btrim(
                    func.regexp_replace(
                        func.lower(IndieAuthor.pen_name), "[^a-z0-9]+", "-", "g"
                    ),
                    "-",
                )
                == slug
            )
        )
    ).scalars().first()
    if author is None:
        return None
    return IndieAuthorProfile(
        pen_name=author.pen_name,
        bio=author.bio,
        profile_image_url=author.profile_image_url,
    )


class IndieCollectionOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    items: list[IndieCatalogItem]


@router.get("/collections", response_model=list[IndieCollectionOut])
async def list_collections(db: AsyncSession = Depends(get_db)):
    """Published curated collections, hydrated from the owned indie_ebooks table.

    Curation rows key on metislib_ebook_id; items without an owned row (e.g.
    open-access titles mixed into a collection) are skipped with a log line
    rather than proxied live -- /indie browse never touches MetisLib.
    """
    from ...core.logging import get_logger
    from ...models.ebook_curation import CollectionStatus, EbookCollection
    from sqlalchemy.orm import selectinload

    logger = get_logger(__name__)
    collections = (
        await db.execute(
            select(EbookCollection)
            .where(EbookCollection.status == CollectionStatus.PUBLISHED)
            .options(selectinload(EbookCollection.items))
            .order_by(EbookCollection.display_order)
            .limit(100)
        )
    ).scalars().unique().all()
    if not collections:
        return []

    metislib_ids = {item.metislib_ebook_id for coll in collections for item in coll.items}
    owned_rows = (
        await db.execute(select(IndieEbook).where(IndieEbook.metislib_ebook_id.in_(metislib_ids)))
    ).scalars().all() if metislib_ids else []
    by_metislib = {r.metislib_ebook_id: r for r in owned_rows}
    d = await _derived(db, [r.id for r in owned_rows])

    out = []
    for coll in collections:
        items = []
        for item in coll.items:
            row = by_metislib.get(item.metislib_ebook_id)
            if row is None:
                logger.warning(
                    f"indie collections: skipping unowned curation item metislib_ebook_id={item.metislib_ebook_id} in collection {coll.id}"
                )
                continue
            items.append(_item_from_row(row, d.get(row.id, {})))
        out.append(IndieCollectionOut(id=coll.id, title=coll.title, description=coll.description, items=items))
    return out


@router.get("/staff-picks", response_model=list[IndieCatalogItem])
async def list_staff_picks(db: AsyncSession = Depends(get_db)):
    """Curated ebook_featured rows (indie entries), hydrated from the owned table."""
    from ...core.logging import get_logger
    from ...models.ebook_curation import EbookFeatured

    logger = get_logger(__name__)
    featured = (
        await db.execute(
            select(EbookFeatured)
            .where(or_(EbookFeatured.entry_type == "indie_ebook", EbookFeatured.entry_type.is_(None)))
            .order_by(EbookFeatured.display_order)
        )
    ).scalars().all()
    if not featured:
        return []

    owned_rows = (
        await db.execute(
            select(IndieEbook).where(
                IndieEbook.metislib_ebook_id.in_([f.metislib_ebook_id for f in featured])
            )
        )
    ).scalars().all()
    by_metislib = {r.metislib_ebook_id: r for r in owned_rows}
    d = await _derived(db, [r.id for r in owned_rows])

    items = []
    for f in featured:
        row = by_metislib.get(f.metislib_ebook_id)
        if row is None:
            logger.warning(
                f"indie staff-picks: skipping unowned featured item metislib_ebook_id={f.metislib_ebook_id}"
            )
            continue
        items.append(_item_from_row(row, d.get(row.id, {})))
    return items


@router.get("/{id}", response_model=IndieCatalogDetail)
async def get_ebook_detail(id: int, db: AsyncSession = Depends(get_db)):
    """Detail page for a single owned indie ebook, keyed on local IndieEbook.id."""
    row = (
        await db.execute(select(IndieEbook).where(IndieEbook.id == id))
    ).scalar_one_or_none()

    if row is None or row.title is None:
        raise HTTPException(status_code=404, detail="Indie ebook not found")

    d = (await _derived(db, [row.id])).get(row.id, {})
    owned = row.copies_owned or 0
    active = d.get("active", 0)

    return IndieCatalogDetail(
        id=row.id,
        title=row.title,
        author_pen_name=row.author_pen_name or "",
        description=row.description,
        cover_url=row.cover_url,
        genre=row.genre,
        language=row.language or "en",
        content_warnings=_parse_warnings(row.content_warnings),
        available_copies=max(0, owned - active),
        total_copies=owned,
        publication_year=row.publication_year,
        subjects=_parse_subjects(row.subjects),
        word_count=row.word_count,
        page_count=row.page_count,
        isbn=row.isbn,
        content_rating=row.content_rating or "unrated",
        author_id=row.author_id,
        average_rating=d.get("average_rating"),
        rating_count=d.get("rating_count", 0),
        total_borrows=d.get("total_borrows", 0),
    )


@router.get("", response_model=IndieCatalogPage)
async def browse_owned_catalog(
    q: Optional[str] = Query(None, max_length=200),
    genre: Optional[str] = Query(None, max_length=100),
    language: Optional[str] = Query(None, max_length=16),
    sort: str = Query("title", pattern="^(title|newest|available)$"),
    page: int = Query(1, ge=1),
    per_page: int = Query(24, ge=1, le=100),
    author: Optional[str] = Query(None, max_length=200),
    author_slug: Optional[str] = Query(None, max_length=200),
    db: AsyncSession = Depends(get_db),
):
    # Returns only rows with a title and at least one owned copy.
    # Rows without a title are import artifacts from Phase 1 that
    # never completed (no usable data) -- exclude them.
    stmt = select(IndieEbook).where(
        IndieEbook.title.is_not(None),
        IndieEbook.copies_owned > 0,
    )

    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                IndieEbook.title.ilike(pattern),
                IndieEbook.author_pen_name.ilike(pattern),
                IndieEbook.description.ilike(pattern),
                IndieEbook.genre.ilike(pattern),
            )
        )

    if genre:
        stmt = stmt.where(IndieEbook.genre.ilike(f"%{genre}%"))

    if author:
        stmt = stmt.where(IndieEbook.author_pen_name == author)
    if author_slug:
        stmt = stmt.where(
            func.btrim(
                func.regexp_replace(
                    func.lower(IndieEbook.author_pen_name), "[^a-z0-9]+", "-", "g"
                ),
                "-",
            )
            == author_slug
        )

    if language:
        stmt = stmt.where(IndieEbook.language == language)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    if sort == "newest":
        stmt = stmt.order_by(IndieEbook.imported_at.desc().nullslast(), IndieEbook.id.desc())
    elif sort == "available":
        stmt = stmt.order_by(IndieEbook.copies_available.desc(), IndieEbook.title.asc())
    else:
        stmt = stmt.order_by(IndieEbook.title.asc())

    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    rows = (await db.execute(stmt)).scalars().all()

    derived_map = await _derived(db, [r.id for r in rows])

    items = [_item_from_row(row, derived_map.get(row.id, {})) for row in rows]

    return IndieCatalogPage(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=max(1, -(-total // per_page)),
    )
