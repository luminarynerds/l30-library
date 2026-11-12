# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional, List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, or_

from ..models.work_relationships import (
    WorkRelationship, RelationshipType, RelationshipDirection,
    CrossFormatDiscovery, FormatSuggestion
)
from ..models.bibframe import BibframeWork

logger = get_logger(__name__)


class WorkRelationshipService:

    @staticmethod
    async def create_relationship(
        session: AsyncSession,
        source_work_id: int,
        target_work_id: int,
        relationship_type: RelationshipType,
        direction: RelationshipDirection = RelationshipDirection.forward,
        title: Optional[str] = None,
        description: Optional[str] = None,
        is_official: bool = True,
        adaptation_fidelity: Optional[str] = None,
        created_by_id: Optional[int] = None,
        **kwargs
    ) -> WorkRelationship:
        relationship = WorkRelationship(
            source_work_id=source_work_id,
            target_work_id=target_work_id,
            relationship_type=relationship_type,
            direction=direction,
            title=title,
            description=description,
            is_official=is_official,
            adaptation_fidelity=adaptation_fidelity,
            created_by_id=created_by_id,
            **kwargs
        )
        session.add(relationship)
        await session.flush()
        return relationship

    @staticmethod
    async def find_related_works(
        session: AsyncSession,
        work_id: int,
        relationship_types: Optional[List[RelationshipType]] = None,
        show_discoverable_only: bool = True
    ) -> List[dict]:
        query = select(WorkRelationship).where(
            WorkRelationship.source_work_id == work_id
        )

        if show_discoverable_only:
            query = query.where(WorkRelationship.show_in_discovery == True)

        if relationship_types:
            query = query.where(
                WorkRelationship.relationship_type.in_(relationship_types)
            )

        query = query.options(
            selectinload(WorkRelationship.target_work)
        )

        result = await session.execute(query)
        relationships = result.scalars().all()

        return [
            {
                "target_work_id": rel.target_work_id,
                "target_work": rel.target_work,
                "relationship_type": rel.relationship_type,
                "relationship": rel
            }
            for rel in relationships
        ]

    @staticmethod
    async def find_related_works_bidirectional(
        session: AsyncSession,
        work_id: int,
        relationship_types: Optional[List[RelationshipType]] = None,
        show_discoverable_only: bool = True
    ) -> dict:
        # Forward relationships (this work -> other works)
        forward_query = select(WorkRelationship).where(
            WorkRelationship.source_work_id == work_id
        )

        # Backward relationships (other works -> this work)
        backward_query = select(WorkRelationship).where(
            WorkRelationship.target_work_id == work_id
        )

        if show_discoverable_only:
            forward_query = forward_query.where(
                WorkRelationship.show_in_discovery == True
            )
            backward_query = backward_query.where(
                WorkRelationship.show_in_discovery == True
            )

        if relationship_types:
            forward_query = forward_query.where(
                WorkRelationship.relationship_type.in_(relationship_types)
            )
            backward_query = backward_query.where(
                WorkRelationship.relationship_type.in_(relationship_types)
            )

        forward_query = forward_query.options(
            selectinload(WorkRelationship.target_work)
        )
        backward_query = backward_query.options(
            selectinload(WorkRelationship.source_work)
        )

        forward_result = await session.execute(forward_query)
        backward_result = await session.execute(backward_query)

        forward_rels = forward_result.scalars().all()
        backward_rels = backward_result.scalars().all()

        return {
            "as_source": [
                {
                    "work_id": rel.target_work_id,
                    "work": rel.target_work,
                    "relationship_type": rel.relationship_type,
                    "relationship": rel
                }
                for rel in forward_rels
            ],
            "as_target": [
                {
                    "work_id": rel.source_work_id,
                    "work": rel.source_work,
                    "relationship_type": rel.relationship_type,
                    "relationship": rel
                }
                for rel in backward_rels
            ]
        }

    @staticmethod
    async def find_all_related_by_type(
        session: AsyncSession,
        work_id: int,
        relationship_type: RelationshipType
    ) -> List[BibframeWork]:
        result = await WorkRelationshipService.find_related_works_bidirectional(
            session, work_id, [relationship_type]
        )

        all_works = [item["work"] for item in result["as_source"]]
        all_works.extend([item["work"] for item in result["as_target"]])

        return all_works

    @staticmethod
    async def get_all_formats(
        session: AsyncSession,
        work_id: int
    ) -> dict:
        related = await WorkRelationshipService.find_related_works_bidirectional(
            session, work_id
        )

        formats_by_type = {}

        for item in related["as_source"]:
            rel_type = item["relationship_type"]
            work = item["work"]
            if rel_type not in formats_by_type:
                formats_by_type[rel_type] = []
            formats_by_type[rel_type].append(work)

        for item in related["as_target"]:
            rel_type = item["relationship_type"]
            work = item["work"]
            if rel_type not in formats_by_type:
                formats_by_type[rel_type] = []
            formats_by_type[rel_type].append(work)

        return formats_by_type

    @staticmethod
    async def create_format_suggestion(
        session: AsyncSession,
        source_work_id: int,
        target_work_id: int,
        suggestion_text: str,
        confidence_score: int = 50,
        is_global: bool = True,
        created_by_id: Optional[int] = None,
        **kwargs
    ) -> FormatSuggestion:
        suggestion = FormatSuggestion(
            source_work_id=source_work_id,
            target_work_id=target_work_id,
            suggestion_text=suggestion_text,
            confidence_score=confidence_score,
            is_global=is_global,
            created_by_id=created_by_id,
            **kwargs
        )
        session.add(suggestion)
        await session.flush()
        return suggestion

    @staticmethod
    async def get_suggestions_for_work(
        session: AsyncSession,
        work_id: int,
        is_global: bool = True,
        active_only: bool = True
    ) -> List[FormatSuggestion]:
        query = select(FormatSuggestion).where(
            FormatSuggestion.source_work_id == work_id
        )

        if is_global is not None:
            query = query.where(FormatSuggestion.is_global == is_global)

        if active_only:
            query = query.where(FormatSuggestion.is_active == True)

        query = query.options(
            selectinload(FormatSuggestion.target_work)
        ).order_by(FormatSuggestion.confidence_score.desc())

        result = await session.execute(query)
        return result.scalars().all()

    @staticmethod
    async def update_cross_format_discovery_cache(
        session: AsyncSession,
        primary_work_id: int
    ) -> CrossFormatDiscovery:
        from sqlalchemy import func as sqlalchemy_func

        # Get the primary work
        work_result = await session.execute(
            select(BibframeWork).where(BibframeWork.id == primary_work_id)
        )
        work = work_result.scalar_one_or_none()

        if not work:
            raise ValueError(f"Work {primary_work_id} not found")

        # Get all related works
        related = await WorkRelationshipService.find_related_works_bidirectional(
            session, primary_work_id
        )

        # Compile format counts and lists
        format_counts = {}
        related_work_ids = set()
        relationship_types = {}

        for item in related["as_source"]:
            rel_type = item["relationship_type"].value
            work_id = item["work_id"]
            related_work_ids.add(work_id)

            if rel_type not in format_counts:
                format_counts[rel_type] = 0
            format_counts[rel_type] += 1

            if rel_type not in relationship_types:
                relationship_types[rel_type] = []
            relationship_types[rel_type].append(work_id)

        for item in related["as_target"]:
            rel_type = item["relationship_type"].value
            work_id = item["work_id"]
            related_work_ids.add(work_id)

            if rel_type not in format_counts:
                format_counts[rel_type] = 0
            format_counts[rel_type] += 1

            if rel_type not in relationship_types:
                relationship_types[rel_type] = []
            relationship_types[rel_type].append(work_id)

        # Create or update cache entry
        cache_result = await session.execute(
            select(CrossFormatDiscovery).where(
                CrossFormatDiscovery.primary_work_id == primary_work_id
            )
        )
        cache_entry = cache_result.scalar_one_or_none()

        if cache_entry:
            cache_entry.format_counts = format_counts
            cache_entry.available_formats = list(format_counts.keys())
            cache_entry.related_work_ids = sorted(list(related_work_ids))
            cache_entry.relationship_types = relationship_types
        else:
            cache_entry = CrossFormatDiscovery(
                primary_work_id=primary_work_id,
                series_name=work.title,
                series_slug=work.title.lower().replace(" ", "-"),
                format_counts=format_counts,
                available_formats=list(format_counts.keys()),
                related_work_ids=sorted(list(related_work_ids)),
                relationship_types=relationship_types
            )
            session.add(cache_entry)

        await session.flush()
        return cache_entry

    @staticmethod
    async def search_by_format(
        session: AsyncSession,
        series_name: str
    ) -> Optional[CrossFormatDiscovery]:
        safe_name = series_name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        result = await session.execute(
            select(CrossFormatDiscovery).where(
                CrossFormatDiscovery.series_name.ilike(f"%{safe_name}%")
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def delete_relationship(
        session: AsyncSession,
        relationship_id: int
    ) -> bool:
        result = await session.execute(
            select(WorkRelationship).where(WorkRelationship.id == relationship_id)
        )
        relationship = result.scalar_one_or_none()

        if not relationship:
            return False

        await session.delete(relationship)
        await session.flush()
        return True
