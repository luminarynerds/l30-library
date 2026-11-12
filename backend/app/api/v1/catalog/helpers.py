# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import re
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import func, literal, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.cache import (
    get_cached,
    invalidate_catalog_cache,
    make_cache_key,
    set_cached,
)
from ....core.config import get_settings
from ....core.database import get_db
from ....core.pagination_config import PaginationDefaults
from ....models.bibframe import BibframeWork
from ....models.catalog import CatalogImage, CatalogItem, ItemStatus, ItemType, CatalogingStatus, SensitivityLevel
from ....models.subject import CatalogItemSubject, Subject
from ....models.user import User, UserRole
from ..dependencies import is_staff_or_admin
from ....schemas.catalog import (
    CatalogItemResponse,
    DuplicateCandidate,
    SearchFacets,
)
from ....services.catalog_query_parser import parse as parse_catalog_query
from ....services.catalog_search_service import catalog_search_service

logger = get_logger(__name__)


_FTS_STOPWORDS: frozenset[str] = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an",
    "and", "any", "are", "as", "at", "be", "because", "been", "before",
    "being", "below", "between", "both", "but", "by", "could", "did", "do",
    "does", "doing", "down", "during", "each", "few", "for", "from",
    "further", "had", "has", "have", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is",
    "it", "its", "itself", "just", "me", "more", "most", "my", "myself", "no",
    "nor", "not", "now", "of", "off", "on", "once", "only", "or", "other",
    "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should",
    "so", "some", "such", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those",
    "through", "to", "too", "under", "until", "up", "very", "was", "we",
    "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "would", "you", "your", "yours", "yourself", "yourselves",
})
"""English FTS stopwords -- common subset of Postgres english snowball list."""


def _is_all_stopwords(q: str) -> bool:
    if not q:
        return False
    cleaned = re.sub(r"[!&|():*<>\\'\"]", " ", q).lower()
    parts = [p for p in cleaned.split() if p]
    if not parts:
        return False
    return all(p in _FTS_STOPWORDS for p in parts)


def _escape_ilike(value: str) -> str:
    import re
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", value)
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def _execute_catalog_search(
    db: AsyncSession,
    q: str | None = None,
    title: str | None = None,
    author: str | None = None,
    subject: str | None = None,
    subject_facets: list[str] | None = None,
    author_facets: list[str] | None = None,
    series_facets: list[str] | None = None,
    publication_year: int | None = None,
    item_type: ItemType | None = None,
    item_types: list[ItemType] | None = None,
    status: ItemStatus | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    location: str | None = None,
    publisher: str | None = None,
    min_lexile: int | None = None,
    max_lexile: int | None = None,
    cataloging_status: CatalogingStatus | None = None,
    sensitivity_level: SensitivityLevel | None = None,
    is_new: bool = False,
    is_large_print: bool | None = None,
    available_for_hold: bool | None = None,
    language: list[str] | None = None,
    sort_by: str | None = None,
    sort_direction: str | None = None,
    page: int = 1,
    per_page: int = 20,
    current_user: User | None = None,
    include_facets: bool = False,
    rerank: bool = False,
) -> dict:
    # Sanitize text inputs: strip null bytes and control characters
    def _sanitize(v: str | None) -> str | None:
        if v is None:
            return None
        return v.replace("\x00", "").strip() or None

    q = _sanitize(q)
    title = _sanitize(title)
    author = _sanitize(author)
    subject = _sanitize(subject)
    location = _sanitize(location)
    publisher = _sanitize(publisher)

    # Normalize language: drop empties + sanitize, cap list size to avoid
    # unbounded IN clauses.
    if language:
        language = [
            v.replace("\x00", "").strip().lower()
            for v in language
            if v and v.strip()
        ][:50]
        if not language:
            language = None
    # Dedupe + strip; case preserved (matches stored Subject.label exactly)
    if subject_facets:
        subject_facets = sorted({s.strip() for s in subject_facets if s and s.strip()})
    else:
        subject_facets = []
    if author_facets:
        author_facets = sorted({s.strip() for s in author_facets if s and s.strip()})
    else:
        author_facets = []
    if series_facets:
        series_facets = sorted({s.strip() for s in series_facets if s and s.strip()})
    else:
        series_facets = []

    # Build cache key from all parameters
    cache_key = make_cache_key(
        "catalog:search",
        query=q,
        title=title,
        author=author,
        subject=subject,
        subject_facets=tuple(subject_facets),
        author_facets=tuple(author_facets),
        series_facets=tuple(series_facets),
        publication_year=publication_year,
        item_type=item_type.value if item_type else None,
        item_types=tuple(t.value for t in item_types) if item_types else None,
        status=status.value if status else None,
        year_min=year_min,
        year_max=year_max,
        location=location,
        publisher=publisher,
        min_lexile=min_lexile,
        max_lexile=max_lexile,
        cataloging_status=cataloging_status.value if cataloging_status else None,
        sensitivity_level=sensitivity_level.value if sensitivity_level else None,
        is_new=is_new,
        is_large_print=is_large_print,
        available_for_hold=available_for_hold,
        language=tuple(sorted(language)) if language else None,
        sort_by=sort_by,
        sort_direction=sort_direction,
        page=page,
        per_page=per_page,
        user_role=str(current_user.role) if current_user else None,
        include_facets=include_facets,
        rerank=bool(rerank and get_settings().catalog_rerank_enabled),
    )

    cached_result = await get_cached(cache_key)
    if cached_result:
        return cached_result

    # Use selectinload to eagerly load relationships and prevent N+1
    # queries when serialising CatalogItemResponse (checkouts, holds, etc.)
    # NOTE: checkouts and holds tables don't exist in current schema
    query = select(CatalogItem).options(selectinload(CatalogItem.images))
    count_query = select(func.count(CatalogItem.id))

    # Full-text search across multiple fields.
    # Detect all-stopword queries up front: Postgres english FTS config strips
    # words like the/of/and from to_tsquery, producing an empty tsquery that
    # matches nothing. Without this branch the patron sees a silent
    # zero-results state for queries like ?q=the. We fall through to the
    # unfiltered browse path AND set a flag so the UI can explain.
    query_was_all_stopwords = bool(q and q != "*" and _is_all_stopwords(q))

    # Parse the patron query into ISBN / scoped predicates / FTS residue.
    # ``websearch_to_tsquery`` natively handles "quoted phrases", OR, and
    # -negation, so the residue is passed through untouched. See
    # app.services.catalog_query_parser for the grammar.
    rank_expr = None
    parsed = (
        parse_catalog_query(q)
        if (q and q != "*" and not query_was_all_stopwords)
        else None
    )

    if parsed and not parsed.is_empty:
        fts_predicate = None
        isbn_predicate = None
        scoped_predicates: list = []

        if parsed.residue.strip():
            tsq = func.websearch_to_tsquery("english", parsed.residue)
            fts_predicate = literal_column("search_tsv").op("@@")(tsq)
            rank_expr = func.ts_rank_cd(literal_column("search_tsv"), tsq)

        if parsed.isbn:
            # Preserves the historical ILIKE-with-hyphens-stripped behavior
            # so "978-0-446-31078-9" still finds "9780446310789".
            isbn_predicate = func.replace(
                func.replace(CatalogItem.isbn, "-", ""), " ", ""
            ).ilike(f"%{_escape_ilike(parsed.isbn)}%")

        for field_name, values in parsed.scoped.items():
            for v in values:
                if not v:
                    continue
                if field_name == "title":
                    scoped_predicates.append(
                        CatalogItem.title.ilike(f"%{_escape_ilike(v)}%")
                    )
                elif field_name == "author":
                    scoped_predicates.append(
                        CatalogItem.author.ilike(f"%{_escape_ilike(v)}%")
                    )
                elif field_name == "series":
                    scoped_predicates.append(
                        CatalogItem.series_name.ilike(f"%{_escape_ilike(v)}%")
                    )
                elif field_name == "subject":
                    # Use the same EXISTS predicate the dedicated subject
                    # filter uses (see below). The legacy substring column
                    # is gone; we go through the join table to avoid the
                    # "Cooking" matching "Bookkeeping for Cooks" regression.
                    pattern = f"%{_escape_ilike(v)}%"
                    scoped_predicates.append(
                        select(literal(1))
                        .select_from(CatalogItemSubject)
                        .join(
                            Subject,
                            Subject.id == CatalogItemSubject.subject_id,
                        )
                        .where(
                            CatalogItemSubject.catalog_item_id
                            == CatalogItem.id,
                            Subject.label.ilike(pattern),
                        )
                        .exists()
                    )

        # FTS-or-ISBN forms one combined predicate so a patron typing a
        # mixed query (e.g. "9780446310789 mockingbird") still matches an
        # ISBN row OR a title row. Scoped predicates AND on top.
        fts_or_isbn: list = []
        if fts_predicate is not None:
            fts_or_isbn.append(fts_predicate)
        if isbn_predicate is not None:
            fts_or_isbn.append(isbn_predicate)

        if fts_or_isbn:
            combined = fts_or_isbn[0] if len(fts_or_isbn) == 1 else or_(*fts_or_isbn)
            query = query.where(combined)
            count_query = count_query.where(combined)

        for predicate in scoped_predicates:
            query = query.where(predicate)
            count_query = count_query.where(predicate)

    # Individual field filters
    if title:
        pattern = f"%{_escape_ilike(title)}%"
        query = query.where(CatalogItem.title.ilike(pattern))
        count_query = count_query.where(CatalogItem.title.ilike(pattern))

    if author:
        pattern = f"%{_escape_ilike(author)}%"
        query = query.where(CatalogItem.author.ilike(pattern))
        count_query = count_query.where(CatalogItem.author.ilike(pattern))

    if subject:
        # Subject filter now goes through the normalized catalog_item_subjects
        # join (see migration subjects_join_001). Keep ILIKE on Subject.label
        # for parity with the current partial-browse UX; flip to exact
        # match once a dedicated subject browse UI lands and can pass a
        # canonical label or subject_id.
        pattern = f"%{_escape_ilike(subject)}%"
        subject_exists = (
            select(literal(1))
            .select_from(CatalogItemSubject)
            .join(Subject, Subject.id == CatalogItemSubject.subject_id)
            .where(
                CatalogItemSubject.catalog_item_id == CatalogItem.id,
                Subject.label.ilike(pattern),
            )
            .exists()
        )
        query = query.where(subject_exists)
        count_query = count_query.where(subject_exists)

    if subject_facets:
        # Multi-select exact-match through the same join table. OR within group:
        # an item is included if any of its subjects matches any selected label.
        facets_exists = (
            select(literal(1))
            .select_from(CatalogItemSubject)
            .join(Subject, Subject.id == CatalogItemSubject.subject_id)
            .where(
                CatalogItemSubject.catalog_item_id == CatalogItem.id,
                Subject.label.in_(subject_facets),
            )
            .exists()
        )
        query = query.where(facets_exists)
        count_query = count_query.where(facets_exists)

    # Snapshot before applying the author filter so the author facet output
    # still surfaces other authors the patron could pick instead of (or in
    # addition to) the currently-selected one. Drill-down semantic.
    query_without_author = query
    if author_facets:
        query = query.where(CatalogItem.author.in_(author_facets))
        count_query = count_query.where(CatalogItem.author.in_(author_facets))

    # Same own-predicate-exclusion for series.
    query_without_series = query
    if series_facets:
        query = query.where(CatalogItem.series_name.in_(series_facets))
        count_query = count_query.where(CatalogItem.series_name.in_(series_facets))

    if publication_year is not None:
        query = query.where(CatalogItem.publication_year == publication_year)
        count_query = count_query.where(CatalogItem.publication_year == publication_year)

    if item_type:
        query = query.where(CatalogItem.item_type == item_type)
        count_query = count_query.where(CatalogItem.item_type == item_type)

    if item_types:
        # OR-join multiple item_types. Used by /search/unified to push the
        # formats filter into SQL instead of post-filtering in Python, so
        # paginated requests do not silently drop matches that fall past
        # the per_page window (see PR #936 -- equipment items vanished
        # behind books in default-sorted top-20).
        query = query.where(CatalogItem.item_type.in_(item_types))
        count_query = count_query.where(CatalogItem.item_type.in_(item_types))

    if status:
        query = query.where(CatalogItem.status == status)
        count_query = count_query.where(CatalogItem.status == status)

    if year_min is not None:
        query = query.where(CatalogItem.publication_year >= year_min)
        count_query = count_query.where(CatalogItem.publication_year >= year_min)
    if year_max is not None:
        query = query.where(CatalogItem.publication_year <= year_max)
        count_query = count_query.where(CatalogItem.publication_year <= year_max)

    if min_lexile is not None:
        query = query.where(CatalogItem.lexile_number >= min_lexile)
        count_query = count_query.where(CatalogItem.lexile_number >= min_lexile)
    if max_lexile is not None:
        query = query.where(CatalogItem.lexile_number <= max_lexile)
        count_query = count_query.where(CatalogItem.lexile_number <= max_lexile)

    if location:
        pattern = f"%{_escape_ilike(location)}%"
        query = query.where(CatalogItem.location.ilike(pattern))
        count_query = count_query.where(CatalogItem.location.ilike(pattern))

    if publisher:
        # Mirrors /catalog/search advanced_search publisher field — partial
        # match by design (patrons type "knopf" expecting "Alfred A. Knopf").
        # Added so unified_search_service._search_local_catalog stops 500ing
        # on a TypeError when it forwards the publisher kwarg.
        pattern = f"%{_escape_ilike(publisher)}%"
        query = query.where(CatalogItem.publisher.ilike(pattern))
        count_query = count_query.where(CatalogItem.publisher.ilike(pattern))

    # Large print filter
    if is_large_print is not None:
        query = query.where(CatalogItem.is_large_print == is_large_print)
        count_query = count_query.where(CatalogItem.is_large_print == is_large_print)

    # Holdability filter — derived from ItemStatus (no DB column). Mirrors the
    # CatalogItemResponse.available_for_hold computed field so SQL stays in sync.
    if available_for_hold is not None:
        from ....schemas.catalog import NON_HOLDABLE_STATUSES
        if available_for_hold:
            query = query.where(CatalogItem.status.notin_(NON_HOLDABLE_STATUSES))
            count_query = count_query.where(CatalogItem.status.notin_(NON_HOLDABLE_STATUSES))
        else:
            query = query.where(CatalogItem.status.in_(NON_HOLDABLE_STATUSES))
            count_query = count_query.where(CatalogItem.status.in_(NON_HOLDABLE_STATUSES))

    # Cataloging status filter - role-based visibility
    if cataloging_status:
        query = query.where(CatalogItem.cataloging_status == cataloging_status)
        count_query = count_query.where(CatalogItem.cataloging_status == cataloging_status)
    else:
        if not (current_user is not None and is_staff_or_admin(current_user)):
            query = query.where(CatalogItem.cataloging_status == CatalogingStatus.CATALOGED)
            count_query = count_query.where(CatalogItem.cataloging_status == CatalogingStatus.CATALOGED)

    # Sensitivity level filter - role-based access enforced first, explicit
    # filter narrows within the allowed set. Mirrors browse.py:477-484.
    if not current_user:
        query = query.where(CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC)
        count_query = count_query.where(CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC)
    elif current_user.role == UserRole.PATRON:
        query = query.where(CatalogItem.sensitivity_level != SensitivityLevel.CONFIDENTIAL)
        count_query = count_query.where(CatalogItem.sensitivity_level != SensitivityLevel.CONFIDENTIAL)

    if sensitivity_level:
        query = query.where(CatalogItem.sensitivity_level == sensitivity_level)
        count_query = count_query.where(CatalogItem.sensitivity_level == sensitivity_level)

    # Status visibility: hide withdrawn items from public search
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        query = query.where(CatalogItem.status != ItemStatus.withdrawn)
        count_query = count_query.where(CatalogItem.status != ItemStatus.withdrawn)

    # New arrivals filter
    if is_new:
        from datetime import datetime, timedelta, timezone
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        query = query.where(CatalogItem.created_at >= thirty_days_ago)
        count_query = count_query.where(CatalogItem.created_at >= thirty_days_ago)

    # Snapshot the query BEFORE applying the language filter so the
    # language facet can be computed against the "what if I removed
    # language?" set. This mirrors the standard faceting rule: a facet
    # should still let you discover the other values in its own dimension
    # once you have picked one.
    query_without_language = query

    # Language filter -- joins through bibframe_works. Use EXISTS so the
    # main result row set is not multiplied if an item somehow had multiple
    # bibframe_works rows (defensive: the FK is nullable + non-unique).
    if language:
        language_exists = (
            select(literal(1))
            .select_from(BibframeWork)
            .where(
                BibframeWork.catalog_item_id == CatalogItem.id,
                BibframeWork.language.in_(language),
            )
            .exists()
        )
        query = query.where(language_exists)
        count_query = count_query.where(language_exists)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Compute facets from the base query (before pagination) if requested.
    # Pass query_without_language so the language facet shows all
    # languages even when the patron has narrowed to one.
    facets_data = None
    if include_facets:
        facets = await catalog_search_service._compute_facets(
            db, query,
            language_base_query=query_without_language if language else None,
            author_base_query=query_without_author if author_facets else None,
            series_base_query=query_without_series if series_facets else None,
        )
        facets_data = facets.model_dump()

    offset = (page - 1) * per_page

    # Sorting. String sorts use the ICU "und-x-icu" collation so non-ASCII
    # scripts (Arabic, CJK, accented Latin) sort by locale rules instead of
    # raw byte order — which would otherwise sink them to the bottom of A-Z
    # lists. Numeric sorts (publication_year, id) stay uncollated.
    sort_column = CatalogItem.title.collate("und-x-icu")
    # Secondary key applied after the primary sort_column in the non-relevance
    # branch. Popularity and recently_added both have heavy ties (e.g. ~930
    # items share total_checkouts=0), so a single-column ORDER BY would leave
    # tied rows in nondeterministic order and drift pagination across pages.
    # id breaks the tie deterministically. Title/author/year keep their old
    # single-key behavior (None means "no secondary key").
    secondary_order = None
    if sort_by == "title":
        sort_column = CatalogItem.title.collate("und-x-icu")
    elif sort_by == "author":
        sort_column = CatalogItem.author.collate("und-x-icu")
    elif sort_by == "year":
        sort_column = CatalogItem.publication_year
    elif sort_by == "popularity":
        # Circulation popularity. total_checkouts is maintained per item; this
        # is the patron-facing browse default so the first tiles are titles
        # people actually borrow, not low-id legacy records.
        sort_column = CatalogItem.total_checkouts
        secondary_order = CatalogItem.id.desc()
    elif sort_by == "recently_added":
        sort_column = CatalogItem.created_at
        secondary_order = CatalogItem.id.desc()
    elif sort_by == "relevance":
        # If we built an FTS query, use ts_rank_cd so phrase + field-weighted
        # matches surface above bag-of-words matches. Fall back to id when
        # there's no FTS predicate (e.g. pure ISBN or pure scoped query).
        sort_column = CatalogItem.id

    # Cross-encoder reranker hook. When enabled, we pull a wider top-N
    # candidate window from FTS (sorted by ts_rank_cd) and rerank it with
    # the bge-reranker model so semantically-better matches surface above
    # ones that merely share lexemes. Only fires for genuine FTS queries
    # (we need parsed.residue to feed the model) on the relevance sort.
    # Falls through to plain FTS rank when the candidate pool is too small
    # to be worth a ~600MB model load.
    rerank_settings = get_settings()
    rerank_active = (
        rerank
        and rerank_settings.catalog_rerank_enabled
        and sort_by == "relevance"
        and rank_expr is not None
        and parsed is not None
        and parsed.residue.strip()
    )

    if rerank_active:
        top_n = max(
            rerank_settings.catalog_rerank_top_n_candidates,
            offset + per_page,
        )
        candidate_query = query.order_by(
            rank_expr.desc(), CatalogItem.id
        ).limit(top_n)
        candidate_result = await db.execute(candidate_query)
        candidates = list(candidate_result.scalars().all())

        if len(candidates) > 5:
            # Local import keeps PyTorch out of the cold path for workers
            # that never rerank (and out of test discovery when mocked).
            from ....services.catalog_reranker import rerank as do_rerank

            try:
                ranked = await do_rerank(parsed.residue, candidates)
            except Exception:  # noqa: BLE001 -- degrade to FTS order, never 500
                # Model unavailable (e.g. empty l30_models volume on a fresh
                # deploy). Patron search must not 500 over a ranking nicety:
                # degrade to plain FTS order.
                logger.warning(
                    "catalog.rerank.unavailable -- falling back to FTS order",
                    exc_info=True,
                )
                items = candidates[offset:offset + per_page]
            else:
                ranked_ids = [iid for iid, _ in ranked]
                by_id = {c.id: c for c in candidates}
                ordered = [by_id[iid] for iid in ranked_ids if iid in by_id]
                items = ordered[offset:offset + per_page]
        else:
            # Tiny candidate pool -- skip the model load, use FTS order.
            items = candidates[offset:offset + per_page]
    elif sort_by == "relevance" and rank_expr is not None:
        # ts_rank_cd is always desc -- higher rank is better. The id tie-
        # breaker keeps pagination stable across pages.
        query = (
            query.offset(offset)
            .limit(per_page)
            .order_by(rank_expr.desc(), CatalogItem.id)
        )
        result = await db.execute(query)
        items = result.scalars().all()
    else:
        primary = sort_column.asc() if sort_direction == "asc" else sort_column.desc()
        order_clause = (primary, secondary_order) if secondary_order is not None else (primary,)
        query = query.offset(offset).limit(per_page).order_by(*order_clause)
        result = await db.execute(query)
        items = result.scalars().all()

    response_data = {
        "items": [CatalogItemResponse.model_validate(item).model_dump() for item in items],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
        "facets": facets_data,
        "query_was_all_stopwords": query_was_all_stopwords,
    }

    await set_cached(cache_key, response_data, ttl_seconds=300)
    return response_data


async def _get_catalog_item_with_images(db: AsyncSession, item_id: int) -> CatalogItem:
    result = await db.execute(
        select(CatalogItem)
        .options(selectinload(CatalogItem.images))
        .where(CatalogItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="We couldn't find that item. It may have been removed from the catalog.")
    return item


async def check_for_duplicates(
    db: AsyncSession,
    isbn: str | None = None,
    title: str | None = None,
    author: str | None = None,
    exclude_id: int | None = None,
) -> list[DuplicateCandidate]:
    duplicates = []

    # 1. ISBN exact match (highest confidence)
    if isbn:
        clean_isbn = isbn.replace("-", "").replace(" ", "").strip()
        if clean_isbn:
            query = select(CatalogItem).where(
                func.replace(func.replace(CatalogItem.isbn, "-", ""), " ", "") == clean_isbn
            )
            if exclude_id:
                query = query.where(CatalogItem.id != exclude_id)

            result = await db.execute(query)
            items = result.scalars().all()

            for item in items:
                duplicates.append(DuplicateCandidate(
                    id=item.id,
                    title=item.title,
                    author=item.author,
                    isbn=item.isbn,
                    item_type=item.item_type,
                    publication_year=item.publication_year,
                    match_type="isbn",
                    match_confidence=1.0,
                ))

    # 2. Title + Author match (high confidence)
    if title and author and not duplicates:
        # Clean and normalize for comparison
        title_clean = title.lower().strip()
        author_clean = author.lower().strip()

        # Escape SQL ILIKE special characters
        title_escaped = title_clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        author_escaped = author_clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        query = select(CatalogItem).where(
            func.lower(CatalogItem.title).ilike(f"%{title_escaped}%"),
            func.lower(CatalogItem.author).ilike(f"%{author_escaped}%"),
        )
        if exclude_id:
            query = query.where(CatalogItem.id != exclude_id)

        result = await db.execute(query)
        items = result.scalars().all()

        for item in items:
            # Calculate similarity (simple approach)
            title_match = title_clean in (item.title or "").lower() or (item.title or "").lower() in title_clean
            author_match = author_clean in (item.author or "").lower() or (item.author or "").lower() in author_clean

            if title_match and author_match:
                # Calculate confidence based on exact vs partial match
                confidence = 0.85
                if title_clean == (item.title or "").lower():
                    confidence += 0.1
                if author_clean == (item.author or "").lower():
                    confidence += 0.05

                duplicates.append(DuplicateCandidate(
                    id=item.id,
                    title=item.title,
                    author=item.author,
                    isbn=item.isbn,
                    item_type=item.item_type,
                    publication_year=item.publication_year,
                    match_type="title_author",
                    match_confidence=min(confidence, 1.0),
                ))

    # 3. Title-only match (lower confidence, only if no other matches)
    elif title and not duplicates:
        title_clean = title.lower().strip()
        title_escaped = title_clean.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

        query = select(CatalogItem).where(
            func.lower(CatalogItem.title) == title_clean
        )
        if exclude_id:
            query = query.where(CatalogItem.id != exclude_id)

        result = await db.execute(query)
        items = result.scalars().all()

        for item in items:
            duplicates.append(DuplicateCandidate(
                id=item.id,
                title=item.title,
                author=item.author,
                isbn=item.isbn,
                item_type=item.item_type,
                publication_year=item.publication_year,
                match_type="title",
                match_confidence=0.6,
            ))

    # Sort by confidence descending
    duplicates.sort(key=lambda x: x.match_confidence, reverse=True)

    return duplicates[:10]  # Limit to top 10


def apply_series_position(payload: dict) -> None:
    """Derive ``series_position`` from ``series_number`` in a create/update payload.

    Mirrors the lexile derivation: only touches the payload when the freeform
    ``series_number`` key is present, so a partial update that doesn't mention
    series leaves the stored position untouched. Setting ``series_number`` to a
    new value (or clearing it) re-derives the numeric position, which may be
    None when the value is unparseable. Keeps the numeric column in sync so it
    never drifts from the freeform source.
    """
    if "series_number" not in payload:
        return
    from ....services.series_position import parse_series_position

    payload["series_position"] = parse_series_position(payload.get("series_number"))


def apply_cataloging_workflow_stamps(
    payload: dict,
    existing_item: CatalogItem | None,
    actor_id: int,
) -> None:
    from datetime import datetime, timezone

    resulting_status = payload.get("cataloging_status")
    if resulting_status is None and existing_item is not None:
        resulting_status = existing_item.cataloging_status

    if resulting_status != CatalogingStatus.CATALOGED and resulting_status != CatalogingStatus.CATALOGED.value:
        return

    already_stamped = existing_item is not None and existing_item.cataloged_at is not None
    if already_stamped:
        return

    payload.setdefault("cataloged_at", datetime.now(timezone.utc))
    payload.setdefault("cataloged_by_id", actor_id)


def raise_for_barcode_conflict(exc: Exception) -> None:
    from sqlalchemy.exc import IntegrityError

    if isinstance(exc, IntegrityError):
        msg = str(getattr(exc, "orig", exc))
        # PG names the constraint catalog_items_barcode_key; SQLite (tests)
        # reports `catalog_items.barcode`. Accept either.
        if "catalog_items_barcode_key" in msg or "catalog_items.barcode" in msg:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Barcode already in use",
            )
    raise exc
