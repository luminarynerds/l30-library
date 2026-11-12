# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Authority-controlled browse endpoints.

Exposes the authority_terms / authority_term_relations vocabulary so that
catalog browse can offer see-also, broader, and narrower navigation across
controlled headings (subjects, authors, series, genres). The schema is
populated by import jobs / catalogers and is read-only here.
"""
from app.core.logging import get_logger
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from ....core.database import get_db
from ....core.rate_limit import limiter
from ....models.catalog_authority import (
    RELATION_TYPES,
    TERM_TYPES,
    AuthorityTerm,
    AuthorityTermRelation,
)

logger = get_logger(__name__)

router = APIRouter()


TermType = Literal["subject", "author", "series", "genre", "geographic"]


class RelatedTerm(BaseModel):
    id: int
    term: str
    relation_type: str
    is_preferred: bool


class AuthorityTermResponse(BaseModel):
    id: int
    term: str
    term_type: str
    scope_note: str | None
    is_preferred: bool
    see_also: list[RelatedTerm]
    broader: list[RelatedTerm]
    narrower: list[RelatedTerm]
    use_for: list[RelatedTerm]


class AuthorityBrowseResponse(BaseModel):
    items: list[AuthorityTermResponse]
    total: int
    prefix: str | None
    term_type: str


def _normalize(term: str) -> str:
    return " ".join(term.lower().split())


async def _load_relations_grouped(
    db: AsyncSession, term_ids: list[int]
) -> dict[int, dict[str, list[RelatedTerm]]]:
    if not term_ids:
        return {}

    related = aliased(AuthorityTerm)
    stmt = (
        select(
            AuthorityTermRelation.term_id,
            AuthorityTermRelation.relation_type,
            related.id,
            related.term,
            related.is_preferred,
        )
        .join(related, related.id == AuthorityTermRelation.related_term_id)
        .where(AuthorityTermRelation.term_id.in_(term_ids))
        .order_by(AuthorityTermRelation.term_id, related.term)
    )
    rows = (await db.execute(stmt)).all()

    grouped: dict[int, dict[str, list[RelatedTerm]]] = {
        tid: {kind: [] for kind in RELATION_TYPES} for tid in term_ids
    }
    for term_id, relation_type, rid, rterm, rpref in rows:
        if relation_type not in RELATION_TYPES:
            continue
        grouped[term_id][relation_type].append(
            RelatedTerm(
                id=rid,
                term=rterm,
                relation_type=relation_type,
                is_preferred=bool(rpref),
            )
        )
    return grouped


@router.get("/authority/browse", response_model=AuthorityBrowseResponse)
@limiter.limit("60/minute")
async def authority_browse(
    request: Request,
    term_type: TermType = Query("subject", description="Authority vocabulary to browse"),
    prefix: str | None = Query(None, description="Match preferred terms starting with this prefix"),
    include_non_preferred: bool = Query(
        False,
        description="Include non-preferred (use-for) terms in the listing",
    ),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Prefix-browse controlled headings with their cross-references.

    Each returned term carries its outbound see-also, broader, narrower, and
    use-for edges. Use the resulting term IDs to filter catalog_items by
    the linked terms in a follow-up search.
    """
    if term_type not in TERM_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported term_type: {term_type}")

    where = [AuthorityTerm.term_type == term_type]
    if not include_non_preferred:
        where.append(AuthorityTerm.is_preferred.is_(True))
    if prefix:
        norm = _normalize(prefix)
        if not norm:
            raise HTTPException(status_code=400, detail="Empty prefix after normalization")
        # Use the (term_type, normalized_term) index for prefix lookup.
        where.append(AuthorityTerm.normalized_term.like(f"{norm}%"))

    base = select(AuthorityTerm).where(and_(*where)).order_by(AuthorityTerm.normalized_term)
    count_stmt = select(func.count(AuthorityTerm.id)).where(and_(*where))

    total = (await db.execute(count_stmt)).scalar() or 0
    offset = (page - 1) * per_page
    rows = (await db.execute(base.offset(offset).limit(per_page))).scalars().all()

    grouped = await _load_relations_grouped(db, [t.id for t in rows])

    items = [
        AuthorityTermResponse(
            id=t.id,
            term=t.term,
            term_type=t.term_type,
            scope_note=t.scope_note,
            is_preferred=bool(t.is_preferred),
            see_also=grouped.get(t.id, {}).get("see_also", []),
            broader=grouped.get(t.id, {}).get("broader", []),
            narrower=grouped.get(t.id, {}).get("narrower", []),
            use_for=grouped.get(t.id, {}).get("use_for", []),
        )
        for t in rows
    ]

    return AuthorityBrowseResponse(
        items=items, total=total, prefix=prefix, term_type=term_type,
    )


@router.get("/authority/{term_id}", response_model=AuthorityTermResponse)
@limiter.limit("120/minute")
async def authority_term_detail(
    request: Request,
    term_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Fetch a single authority term with all of its cross-references."""
    term = (
        await db.execute(select(AuthorityTerm).where(AuthorityTerm.id == term_id))
    ).scalar_one_or_none()
    if term is None:
        raise HTTPException(status_code=404, detail="Authority term not found")

    grouped = await _load_relations_grouped(db, [term.id])
    buckets = grouped.get(term.id, {kind: [] for kind in RELATION_TYPES})

    return AuthorityTermResponse(
        id=term.id,
        term=term.term,
        term_type=term.term_type,
        scope_note=term.scope_note,
        is_preferred=bool(term.is_preferred),
        see_also=buckets.get("see_also", []),
        broader=buckets.get("broader", []),
        narrower=buckets.get("narrower", []),
        use_for=buckets.get("use_for", []),
    )
