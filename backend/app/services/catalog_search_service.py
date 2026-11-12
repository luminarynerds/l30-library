# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import String, and_, desc, func, literal_column, not_, or_, select, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.bibframe import BibframeWork
from ..models.catalog import CatalogingStatus, CatalogItem, ItemStatus, ItemType
from ..models.subject import CatalogItemSubject, Subject
from ..schemas.catalog import FacetValue, SearchFacets

logger = get_logger(__name__)


class CatalogSearchService:

    def _escape_like_value(self, value: str) -> str:
        if not value:
            return value
        # Escape backslashes first, then wildcards
        return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

    async def advanced_search(
        self,
        db: AsyncSession,
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        isbn: Optional[str] = None,
        publisher: Optional[str] = None,
        operator: str = "AND",
        exclude_subject: Optional[str] = None,
        item_type: Optional[ItemType] = None,
        status: Optional[ItemStatus] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        location: Optional[str] = None,
        min_lexile: Optional[int] = None,
        max_lexile: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> list[CatalogItem]:
        # Eager load relationships to prevent N+1 queries when callers
        # access checkouts/holds on the returned items.
        # NOTE: checkouts and holds tables don't exist in current schema
        query = select(CatalogItem).options(selectinload(CatalogItem.images))

        # Build search conditions
        search_conditions = []

        # Title search
        if title:
            escaped_title = self._escape_like_value(title)
            search_conditions.append(
                CatalogItem.title.ilike(f"%{escaped_title}%")
            )

        # Author search
        if author:
            escaped_author = self._escape_like_value(author)
            search_conditions.append(
                CatalogItem.author.ilike(f"%{escaped_author}%")
            )

        # Subject search
        if subject:
            escaped_subject = self._escape_like_value(subject)
            search_conditions.append(
                CatalogItem.subjects.ilike(f"%{escaped_subject}%")
            )

        # ISBN search (normalize both search term and database values)
        if isbn:
            # Normalize ISBN by removing hyphens and spaces
            normalized_isbn = isbn.replace("-", "").replace(" ", "") if isbn else isbn
            escaped_isbn = self._escape_like_value(normalized_isbn)
            # Search for ISBN with or without hyphens
            search_conditions.append(
                or_(
                    CatalogItem.isbn.ilike(f"%{escaped_isbn}%"),
                    func.replace(func.replace(CatalogItem.isbn, "-", ""), " ", "").ilike(
                        f"%{escaped_isbn}%"
                    ),
                )
            )

        # Publisher search
        if publisher:
            escaped_publisher = self._escape_like_value(publisher)
            search_conditions.append(
                CatalogItem.publisher.ilike(f"%{escaped_publisher}%")
            )

        # Combine search conditions with operator
        if search_conditions:
            if operator.upper() == "OR":
                combined_search = or_(*search_conditions)
            else:  # Default to AND
                combined_search = and_(*search_conditions)
            query = query.where(combined_search)

        # Apply exclusion filter
        if exclude_subject:
            escaped_exclude = self._escape_like_value(exclude_subject)
            query = query.where(
                not_(CatalogItem.subjects.ilike(f"%{escaped_exclude}%"))
            )

        # Apply type filter
        if item_type:
            query = query.where(CatalogItem.item_type == item_type)

        # Apply status filter
        if status:
            query = query.where(CatalogItem.status == status)

        # Apply publication year range filters
        if year_min is not None:
            query = query.where(CatalogItem.publication_year >= year_min)
        if year_max is not None:
            query = query.where(CatalogItem.publication_year <= year_max)

        # Apply Lexile range filters
        if min_lexile is not None:
            query = query.where(CatalogItem.lexile_number >= min_lexile)
        if max_lexile is not None:
            query = query.where(CatalogItem.lexile_number <= max_lexile)

        # Apply location filter
        if location:
            escaped_location = self._escape_like_value(location)
            query = query.where(
                CatalogItem.location.ilike(f"%{escaped_location}%")
            )

        # Apply pagination. ICU collation keeps non-ASCII titles in locale order
        # instead of byte-order (which sinks Arabic/CJK/accented to the bottom).
        offset = (page - 1) * per_page
        query = query.offset(offset).limit(per_page).order_by(CatalogItem.title.collate("und-x-icu"))

        # Execute query
        result = await db.execute(query)
        return list(result.scalars().all())

    async def advanced_search_with_count(
        self,
        db: AsyncSession,
        title: Optional[str] = None,
        author: Optional[str] = None,
        subject: Optional[str] = None,
        isbn: Optional[str] = None,
        publisher: Optional[str] = None,
        operator: str = "AND",
        exclude_subject: Optional[str] = None,
        item_type: Optional[ItemType] = None,
        status: Optional[ItemStatus] = None,
        year_min: Optional[int] = None,
        year_max: Optional[int] = None,
        location: Optional[str] = None,
        min_lexile: Optional[int] = None,
        max_lexile: Optional[int] = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[list[CatalogItem], int]:
        # Build base query conditions
        conditions = []

        # Build search conditions
        search_conditions = []

        if title:
            escaped_title = self._escape_like_value(title)
            search_conditions.append(
                CatalogItem.title.ilike(f"%{escaped_title}%")
            )

        if author:
            escaped_author = self._escape_like_value(author)
            search_conditions.append(
                CatalogItem.author.ilike(f"%{escaped_author}%")
            )

        if subject:
            escaped_subject = self._escape_like_value(subject)
            search_conditions.append(
                CatalogItem.subjects.ilike(f"%{escaped_subject}%")
            )

        if isbn:
            # Normalize ISBN by removing hyphens and spaces
            normalized_isbn = isbn.replace("-", "").replace(" ", "") if isbn else isbn
            escaped_isbn = self._escape_like_value(normalized_isbn)
            search_conditions.append(
                or_(
                    CatalogItem.isbn.ilike(f"%{escaped_isbn}%"),
                    func.replace(func.replace(CatalogItem.isbn, "-", ""), " ", "").ilike(
                        f"%{escaped_isbn}%"
                    ),
                )
            )

        if publisher:
            escaped_publisher = self._escape_like_value(publisher)
            search_conditions.append(
                CatalogItem.publisher.ilike(f"%{escaped_publisher}%")
            )

        # Combine search conditions
        if search_conditions:
            if operator.upper() == "OR":
                conditions.append(or_(*search_conditions))
            else:
                conditions.append(and_(*search_conditions))

        # Exclusion filter
        if exclude_subject:
            escaped_exclude = self._escape_like_value(exclude_subject)
            conditions.append(
                not_(CatalogItem.subjects.ilike(f"%{escaped_exclude}%"))
            )

        # Type filter
        if item_type:
            conditions.append(CatalogItem.item_type == item_type)

        # Status filter
        if status:
            conditions.append(CatalogItem.status == status)

        # Year range filters
        if year_min is not None:
            conditions.append(CatalogItem.publication_year >= year_min)
        if year_max is not None:
            conditions.append(CatalogItem.publication_year <= year_max)

        # Lexile range filters
        if min_lexile is not None:
            conditions.append(CatalogItem.lexile_number >= min_lexile)
        if max_lexile is not None:
            conditions.append(CatalogItem.lexile_number <= max_lexile)

        # Location filter
        if location:
            escaped_location = self._escape_like_value(location)
            conditions.append(
                CatalogItem.location.ilike(f"%{escaped_location}%")
            )

        # Build base query with conditions
        where_clause = and_(*conditions) if conditions else True

        # Count query
        count_query = select(func.count(CatalogItem.id)).where(where_clause)
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        # Items query with pagination — eager load to prevent N+1.
        # ICU collation for locale-aware title sort across scripts.
        items_query = (
            select(CatalogItem).options(selectinload(CatalogItem.images))
            .where(where_clause)
            .offset((page - 1) * per_page)
            .limit(per_page)
            .order_by(CatalogItem.title.collate("und-x-icu"))
        )

        result = await db.execute(items_query)
        items = list(result.scalars().all())

        return items, total

    async def _compute_facets(
        self,
        db: AsyncSession,
        base_query,
        language_base_query=None,
        author_base_query=None,
        series_base_query=None,
    ) -> SearchFacets:
        base_subquery = base_query.with_only_columns(CatalogItem.id).subquery()
        in_clause = CatalogItem.id.in_(select(base_subquery.c.id))

        # Build sub-selects for each facet dimension with a label column
        item_type_q = (
            select(
                literal_column("'item_type'").label("facet"),
                func.cast(CatalogItem.item_type, String).label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(in_clause)
            .group_by(CatalogItem.item_type)
        )

        status_q = (
            select(
                literal_column("'status'").label("facet"),
                func.cast(CatalogItem.status, String).label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(in_clause)
            .group_by(CatalogItem.status)
        )

        location_q = (
            select(
                literal_column("'location'").label("facet"),
                CatalogItem.location.label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(in_clause, CatalogItem.location.isnot(None))
            .group_by(CatalogItem.location)
        )

        # Year facet has LIMIT, so wrap in subquery before UNION ALL
        year_sub = (
            select(
                literal_column("'year'").label("facet"),
                func.cast(CatalogItem.publication_year, String).label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(in_clause, CatalogItem.publication_year.isnot(None))
            .group_by(CatalogItem.publication_year)
            .order_by(desc(CatalogItem.publication_year))
            .limit(20)
        ).subquery()
        year_q = select(year_sub.c.facet, year_sub.c.val, year_sub.c.cnt)

        # Subject facet -- join through catalog_item_subjects to get exact
        # label counts (replaces the old denormalized-substring approach).
        # Capped at the top 30 subjects within the current result set to
        # keep facet payload bounded for high-cardinality vocabularies.
        subject_sub = (
            select(
                literal_column("'subject'").label("facet"),
                Subject.label.label("val"),
                func.count(CatalogItemSubject.catalog_item_id).label("cnt"),
            )
            .select_from(CatalogItemSubject)
            .join(Subject, Subject.id == CatalogItemSubject.subject_id)
            .where(CatalogItemSubject.catalog_item_id.in_(select(base_subquery.c.id)))
            .group_by(Subject.label)
            .order_by(desc(func.count(CatalogItemSubject.catalog_item_id)))
            .limit(30)
        ).subquery()
        subject_q = select(subject_sub.c.facet, subject_sub.c.val, subject_sub.c.cnt)

        # Language facet -- count distinct catalog_items grouped by the
        # joined bibframe_works language. Uses a separate base set so the
        # facet still shows every language even after the patron has
        # selected one (see docstring).
        lang_source_query = language_base_query if language_base_query is not None else base_query
        lang_id_subq = lang_source_query.with_only_columns(CatalogItem.id).subquery()
        language_sub = (
            select(
                literal_column("'language'").label("facet"),
                BibframeWork.language.label("val"),
                func.count(func.distinct(BibframeWork.catalog_item_id)).label("cnt"),
            )
            .select_from(BibframeWork)
            .where(
                BibframeWork.catalog_item_id.in_(select(lang_id_subq.c.id)),
                BibframeWork.language.isnot(None),
            )
            .group_by(BibframeWork.language)
            .order_by(desc(func.count(func.distinct(BibframeWork.catalog_item_id))))
            .limit(30)
        ).subquery()
        language_q = select(language_sub.c.facet, language_sub.c.val, language_sub.c.cnt)

        # Author facet -- direct column count on catalog_items. Uses the
        # author-free base query (when an author filter was supplied) so the
        # facet output still surfaces other authors the patron could pick.
        # NULL + whitespace-only excluded.
        author_source_query = author_base_query if author_base_query is not None else base_query
        author_id_subq = author_source_query.with_only_columns(CatalogItem.id).subquery()
        author_sub = (
            select(
                literal_column("'author'").label("facet"),
                CatalogItem.author.label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(
                CatalogItem.id.in_(select(author_id_subq.c.id)),
                CatalogItem.author.isnot(None),
                func.trim(CatalogItem.author) != "",
            )
            .group_by(CatalogItem.author)
            .order_by(desc(func.count(CatalogItem.id)))
            .limit(50)
        ).subquery()
        author_q = select(author_sub.c.facet, author_sub.c.val, author_sub.c.cnt)

        # Series facet -- direct column count on catalog_items.series_name.
        # Uses the series-free base query (when a series filter was supplied)
        # so the facet output still surfaces other series the patron could
        # pick. NULL + whitespace-only excluded.
        series_source_query = series_base_query if series_base_query is not None else base_query
        series_id_subq = series_source_query.with_only_columns(CatalogItem.id).subquery()
        series_sub = (
            select(
                literal_column("'series'").label("facet"),
                CatalogItem.series_name.label("val"),
                func.count(CatalogItem.id).label("cnt"),
            )
            .where(
                CatalogItem.id.in_(select(series_id_subq.c.id)),
                CatalogItem.series_name.isnot(None),
                func.trim(CatalogItem.series_name) != "",
            )
            .group_by(CatalogItem.series_name)
            .order_by(desc(func.count(CatalogItem.id)))
            .limit(50)
        ).subquery()
        series_q = select(series_sub.c.facet, series_sub.c.val, series_sub.c.cnt)

        # Single roundtrip for all facets
        combined = union_all(item_type_q, status_q, location_q, year_q, subject_q, language_q, author_q, series_q)
        result = await db.execute(combined)

        # Parse results into facet buckets
        buckets: dict[str, list[FacetValue]] = {
            "item_type": [], "status": [], "location": [], "year": [], "subject": [], "language": [], "author": [], "series": [],
        }
        for row in result.all():
            facet_name = row[0]
            if facet_name in buckets and row[1] is not None:
                buckets[facet_name].append(FacetValue(value=str(row[1]), count=row[2]))

        # Sort by count desc; year already ordered by year desc, subject + language
        # already ordered by count desc inside the limited subqueries.
        for key in ("item_type", "status", "location"):
            buckets[key].sort(key=lambda f: f.count, reverse=True)

        return SearchFacets(
            item_type=buckets["item_type"],
            status=buckets["status"],
            publication_year=buckets["year"],
            location=buckets["location"],
            subject=buckets["subject"],
            language=buckets["language"],
            author=buckets["author"],
            series=buckets["series"],
        )

    async def get_suggestions(
        self,
        db: AsyncSession,
        query: str,
        limit: int = 10,
    ) -> list:
        escaped_query = self._escape_like_value(query)
        pattern = f"{escaped_query}%"

        suggestions = []

        # Query titles matching the prefix (only cataloged items visible to patrons)
        title_query = (
            select(CatalogItem.id, CatalogItem.title)
            .where(
                CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
                CatalogItem.title.ilike(pattern),
            )
            .order_by(CatalogItem.title.collate("und-x-icu"))
            .limit(limit)
        )
        title_result = await db.execute(title_query)
        title_rows = title_result.all()

        for row in title_rows:
            suggestions.append({
                "text": row.title,
                "type": "title",
                "item_id": row.id,
            })

        # Query distinct authors matching the prefix (only from cataloged items)
        remaining = limit - len(suggestions)
        if remaining > 0:
            author_query = (
                select(func.distinct(CatalogItem.author))
                .where(
                    CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
                    CatalogItem.author.ilike(pattern),
                    CatalogItem.author.isnot(None),
                )
                .order_by(CatalogItem.author.collate("und-x-icu"))
                .limit(remaining)
            )
            author_result = await db.execute(author_query)
            author_rows = author_result.scalars().all()

            for author_name in author_rows:
                suggestions.append({
                    "text": author_name,
                    "type": "author",
                    "item_id": None,
                })

        return suggestions


# Singleton instance for convenience
catalog_search_service = CatalogSearchService()
