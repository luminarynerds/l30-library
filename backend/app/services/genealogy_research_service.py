# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz
from sqlalchemy import and_, delete, desc, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.genealogy_research import (
    DNAMatch,
    DNAMatchStatus,
    DNAProfile,
    ExternalDatabaseSource,
    ExternalRecordReference,
    FamilyRelationship,
    GenealogyDocument,
    GenealogyPerson,
    GenealogyResearchProject,
    PersonDocumentLink,
    ProjectCollaborator,
    ProjectRole,
    RecordLink,
    RecordLinkStatus,
    RelationshipType,
    ResearchGuidanceSuggestion,
    ResearchGuidanceType,
    ResearchNote,
    TimelineEvent,
)
from ..models.user import User


class GenealogyResearchService:

    # ========================================================================
    # PROJECT MANAGEMENT
    # ========================================================================

    @staticmethod
    async def create_project(
        db: AsyncSession,
        owner_id: int,
        name: str,
        description: Optional[str] = None,
        is_public: bool = False,
        allow_join_requests: bool = True,
        default_license: str = "CC-BY-4.0",
    ) -> GenealogyResearchProject:
        project = GenealogyResearchProject(
            name=name,
            description=description,
            owner_id=owner_id,
            is_public=is_public,
            allow_join_requests=allow_join_requests,
            default_license=default_license,
        )
        db.add(project)
        await db.flush()

        # Add owner as OWNER collaborator
        collaborator = ProjectCollaborator(
            project_id=project.id,
            user_id=owner_id,
            role=ProjectRole.OWNER,
            accepted_at=datetime.now(timezone.utc),
            is_active=True,
        )
        db.add(collaborator)
        await db.commit()
        await db.refresh(project)
        return project

    @staticmethod
    async def get_project(
        db: AsyncSession, project_id: int
    ) -> Optional[GenealogyResearchProject]:
        result = await db.execute(
            select(GenealogyResearchProject).where(
                GenealogyResearchProject.id == project_id
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_user_projects(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 50
    ) -> List[GenealogyResearchProject]:
        result = await db.execute(
            select(GenealogyResearchProject)
            .join(
                ProjectCollaborator,
                and_(
                    ProjectCollaborator.project_id == GenealogyResearchProject.id,
                    ProjectCollaborator.user_id == user_id,
                    ProjectCollaborator.is_active == True,
                ),
            )
            .order_by(desc(GenealogyResearchProject.updated_at))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def check_project_access(
        db: AsyncSession,
        project_id: int,
        user_id: int,
        required_role: Optional[ProjectRole] = None,
    ) -> Optional[ProjectCollaborator]:
        query = select(ProjectCollaborator).where(
            and_(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == user_id,
                ProjectCollaborator.is_active == True,
            )
        )
        result = await db.execute(query)
        collaborator = result.scalar_one_or_none()

        if not collaborator:
            return None

        if required_role:
            role_hierarchy = {
                ProjectRole.VIEWER: 0,
                ProjectRole.EDITOR: 1,
                ProjectRole.ADMIN: 2,
                ProjectRole.OWNER: 3,
            }
            if role_hierarchy.get(collaborator.role, 0) < role_hierarchy.get(
                required_role, 0
            ):
                return None

        return collaborator

    @staticmethod
    async def invite_collaborator(
        db: AsyncSession,
        project_id: int,
        user_id: int,
        role: ProjectRole,
        invited_by: int,
    ) -> ProjectCollaborator:
        collaborator = ProjectCollaborator(
            project_id=project_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
            is_active=True,
            accepted_at=datetime.now(timezone.utc),
        )
        db.add(collaborator)
        await db.commit()
        await db.refresh(collaborator)
        return collaborator

    @staticmethod
    async def get_project_collaborators(
        db: AsyncSession, project_id: int
    ) -> List[ProjectCollaborator]:
        result = await db.execute(
            select(ProjectCollaborator)
            .where(
                and_(
                    ProjectCollaborator.project_id == project_id,
                    ProjectCollaborator.is_active == True,
                )
            )
            .order_by(ProjectCollaborator.role)
        )
        return list(result.scalars().all())

    # ========================================================================
    # PERSON MANAGEMENT
    # ========================================================================

    @staticmethod
    async def create_person(
        db: AsyncSession,
        project_id: int,
        created_by: int,
        **person_data: Any,
    ) -> GenealogyPerson:
        person = GenealogyPerson(
            project_id=project_id, created_by=created_by, **person_data
        )
        db.add(person)

        # Update project person count
        await db.execute(
            update(GenealogyResearchProject)
            .where(GenealogyResearchProject.id == project_id)
            .values(person_count=GenealogyResearchProject.person_count + 1)
        )

        await db.commit()
        await db.refresh(person)
        return person

    @staticmethod
    async def get_person(
        db: AsyncSession, person_id: int
    ) -> Optional[GenealogyPerson]:
        result = await db.execute(
            select(GenealogyPerson).where(GenealogyPerson.id == person_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_project_persons(
        db: AsyncSession,
        project_id: int,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[GenealogyPerson]:
        query = select(GenealogyPerson).where(
            GenealogyPerson.project_id == project_id
        )

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    GenealogyPerson.given_names.ilike(search_pattern),
                    GenealogyPerson.surname.ilike(search_pattern),
                    GenealogyPerson.maiden_name.ilike(search_pattern),
                    GenealogyPerson.nickname.ilike(search_pattern),
                )
            )

        query = query.order_by(
            GenealogyPerson.surname, GenealogyPerson.given_names
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_person(
        db: AsyncSession, person_id: int, **update_data: Any
    ) -> Optional[GenealogyPerson]:
        result = await db.execute(
            select(GenealogyPerson).where(GenealogyPerson.id == person_id)
        )
        person = result.scalar_one_or_none()
        if not person:
            return None

        for field, value in update_data.items():
            if value is not None:
                setattr(person, field, value)

        await db.commit()
        await db.refresh(person)
        return person

    # ========================================================================
    # FAMILY RELATIONSHIPS
    # ========================================================================

    @staticmethod
    async def create_relationship(
        db: AsyncSession,
        project_id: int,
        created_by: int,
        **rel_data: Any,
    ) -> FamilyRelationship:
        relationship = FamilyRelationship(
            project_id=project_id, created_by=created_by, **rel_data
        )
        db.add(relationship)
        await db.commit()
        await db.refresh(relationship)
        return relationship

    @staticmethod
    async def get_person_relationships(
        db: AsyncSession, person_id: int
    ) -> List[FamilyRelationship]:
        result = await db.execute(
            select(FamilyRelationship).where(
                or_(
                    FamilyRelationship.person1_id == person_id,
                    FamilyRelationship.person2_id == person_id,
                )
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def build_family_tree(
        db: AsyncSession, project_id: int, root_person_id: Optional[int] = None
    ) -> Dict[str, Any]:
        # Get all persons in the project
        persons_result = await db.execute(
            select(GenealogyPerson).where(
                GenealogyPerson.project_id == project_id
            )
        )
        persons = list(persons_result.scalars().all())

        # Get all relationships
        rels_result = await db.execute(
            select(FamilyRelationship).where(
                FamilyRelationship.project_id == project_id
            )
        )
        relationships = list(rels_result.scalars().all())

        # Build adjacency data
        nodes = {}
        for person in persons:
            nodes[person.id] = {
                "person": person,
                "parents": [],
                "children": [],
                "spouses": [],
                "siblings": [],
            }

        for rel in relationships:
            p1 = rel.person1_id
            p2 = rel.person2_id

            if rel.relationship_type == RelationshipType.PARENT_CHILD:
                if p1 in nodes:
                    nodes[p1]["children"].append(p2)
                if p2 in nodes:
                    nodes[p2]["parents"].append(p1)
            elif rel.relationship_type == RelationshipType.SPOUSE:
                if p1 in nodes:
                    nodes[p1]["spouses"].append(p2)
                if p2 in nodes:
                    nodes[p2]["spouses"].append(p1)
            elif rel.relationship_type == RelationshipType.SIBLING:
                if p1 in nodes:
                    nodes[p1]["siblings"].append(p2)
                if p2 in nodes:
                    nodes[p2]["siblings"].append(p1)

        # Calculate generation count
        generation_count = GenealogyResearchService._calculate_generations(
            nodes, root_person_id
        )

        return {
            "project_id": project_id,
            "root_person_id": root_person_id,
            "nodes": nodes,
            "relationships": relationships,
            "generation_count": generation_count,
            "person_count": len(persons),
        }

    @staticmethod
    def _calculate_generations(
        nodes: Dict[int, Dict], root_id: Optional[int]
    ) -> int:
        if not nodes or not root_id or root_id not in nodes:
            return 0

        visited = set()
        max_depth = 0

        def dfs(person_id: int, depth: int, direction: str) -> None:
            nonlocal max_depth
            if person_id in visited:
                return
            visited.add(person_id)
            max_depth = max(max_depth, depth)

            node = nodes.get(person_id, {})
            if direction in ("up", "both"):
                for parent_id in node.get("parents", []):
                    dfs(parent_id, depth + 1, "up")
            if direction in ("down", "both"):
                for child_id in node.get("children", []):
                    dfs(child_id, depth + 1, "down")

        dfs(root_id, 0, "up")
        up_depth = max_depth

        visited.clear()
        max_depth = 0
        dfs(root_id, 0, "down")

        return up_depth + max_depth + 1

    # ========================================================================
    # DOCUMENT MANAGEMENT
    # ========================================================================

    @staticmethod
    async def create_document(
        db: AsyncSession,
        project_id: int,
        uploaded_by: int,
        **doc_data: Any,
    ) -> GenealogyDocument:
        document = GenealogyDocument(
            project_id=project_id, uploaded_by=uploaded_by, **doc_data
        )
        db.add(document)

        await db.execute(
            update(GenealogyResearchProject)
            .where(GenealogyResearchProject.id == project_id)
            .values(document_count=GenealogyResearchProject.document_count + 1)
        )

        await db.commit()
        await db.refresh(document)
        return document

    @staticmethod
    async def list_project_documents(
        db: AsyncSession,
        project_id: int,
        document_type: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[GenealogyDocument]:
        query = select(GenealogyDocument).where(
            GenealogyDocument.project_id == project_id
        )

        if document_type:
            query = query.where(GenealogyDocument.document_type == document_type)

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    GenealogyDocument.title.ilike(search_pattern),
                    GenealogyDocument.ocr_text.ilike(search_pattern),
                    GenealogyDocument.description.ilike(search_pattern),
                )
            )

        query = query.order_by(desc(GenealogyDocument.created_at)).offset(skip).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def update_document_ocr(
        db: AsyncSession,
        document_id: int,
        ocr_text: str,
        ocr_confidence: float,
        ocr_language: str = "en",
    ) -> Optional[GenealogyDocument]:
        result = await db.execute(
            select(GenealogyDocument).where(GenealogyDocument.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if not doc:
            return None

        doc.ocr_text = ocr_text
        doc.ocr_confidence = ocr_confidence
        doc.ocr_language = ocr_language
        doc.ocr_processed_at = datetime.now(timezone.utc)
        doc.status = "ocr_complete"

        await db.commit()
        await db.refresh(doc)
        return doc

    @staticmethod
    async def link_person_to_document(
        db: AsyncSession,
        person_id: int,
        document_id: int,
        created_by: int,
        role_in_document: Optional[str] = None,
        page_number: Optional[int] = None,
        excerpt: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> PersonDocumentLink:
        link = PersonDocumentLink(
            person_id=person_id,
            document_id=document_id,
            created_by=created_by,
            role_in_document=role_in_document,
            page_number=page_number,
            excerpt=excerpt,
            notes=notes,
        )
        db.add(link)
        await db.commit()
        await db.refresh(link)
        return link

    # ========================================================================
    # TIMELINE EVENTS
    # ========================================================================

    @staticmethod
    async def create_timeline_event(
        db: AsyncSession,
        project_id: int,
        created_by: int,
        **event_data: Any,
    ) -> TimelineEvent:
        event = TimelineEvent(
            project_id=project_id, created_by=created_by, **event_data
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)
        return event

    @staticmethod
    async def get_person_timeline(
        db: AsyncSession, person_id: int
    ) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent)
            .where(TimelineEvent.person_id == person_id)
            .order_by(TimelineEvent.event_date_normalized)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_family_timeline(
        db: AsyncSession, project_id: int, person_ids: List[int]
    ) -> List[TimelineEvent]:
        result = await db.execute(
            select(TimelineEvent)
            .where(
                and_(
                    TimelineEvent.project_id == project_id,
                    TimelineEvent.person_id.in_(person_ids),
                )
            )
            .order_by(TimelineEvent.event_date_normalized)
        )
        return list(result.scalars().all())

    # ========================================================================
    # RESEARCH NOTES
    # ========================================================================

    @staticmethod
    async def create_research_note(
        db: AsyncSession,
        project_id: int,
        author_id: int,
        **note_data: Any,
    ) -> ResearchNote:
        note = ResearchNote(
            project_id=project_id, author_id=author_id, **note_data
        )
        db.add(note)
        await db.commit()
        await db.refresh(note)
        return note

    @staticmethod
    async def list_research_notes(
        db: AsyncSession,
        project_id: int,
        note_type: Optional[str] = None,
        person_id: Optional[int] = None,
        unresolved_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> List[ResearchNote]:
        query = select(ResearchNote).where(ResearchNote.project_id == project_id)

        if note_type:
            query = query.where(ResearchNote.note_type == note_type)
        if person_id:
            query = query.where(ResearchNote.person_id == person_id)
        if unresolved_only:
            query = query.where(ResearchNote.is_resolved == False)

        query = query.order_by(
            desc(ResearchNote.is_pinned),
            desc(ResearchNote.priority),
            desc(ResearchNote.created_at),
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # RECORD LINKING ENGINE
    # ========================================================================

    @staticmethod
    async def find_potential_record_links(
        db: AsyncSession, project_id: int, threshold: float = 0.6
    ) -> List[RecordLink]:
        # Get all persons
        persons_result = await db.execute(
            select(GenealogyPerson).where(
                GenealogyPerson.project_id == project_id
            )
        )
        persons = list(persons_result.scalars().all())

        # Get all documents with OCR text
        docs_result = await db.execute(
            select(GenealogyDocument).where(
                and_(
                    GenealogyDocument.project_id == project_id,
                    GenealogyDocument.ocr_text.isnot(None),
                )
            )
        )
        documents = list(docs_result.scalars().all())

        # Get existing links to avoid duplicates
        existing_result = await db.execute(
            select(RecordLink).where(RecordLink.project_id == project_id)
        )
        existing_links = set()
        for link in existing_result.scalars().all():
            key = (
                link.source_person_id,
                link.target_document_id,
            )
            existing_links.add(key)

        new_links = []

        # Match persons to documents
        for person in persons:

            for doc in documents:
                if (person.id, doc.id) in existing_links:
                    continue

                score, reasons, fields = (
                    GenealogyResearchService._calculate_person_document_similarity(
                        person, doc
                    )
                )

                if score >= threshold:
                    link = RecordLink(
                        project_id=project_id,
                        source_person_id=person.id,
                        target_document_id=doc.id,
                        similarity_score=score,
                        match_reasons=json.dumps(reasons),
                        matched_fields=json.dumps(fields),
                        status=RecordLinkStatus.SUGGESTED,
                    )
                    db.add(link)
                    new_links.append(link)

        # Match persons to each other (potential duplicate detection)
        for i, p1 in enumerate(persons):
            for p2 in persons[i + 1 :]:
                key_fwd = (p1.id, p2.id)
                if key_fwd in existing_links:
                    continue

                score, reasons, fields = (
                    GenealogyResearchService._calculate_person_similarity(p1, p2)
                )

                if score >= threshold:
                    link = RecordLink(
                        project_id=project_id,
                        source_person_id=p1.id,
                        target_person_id=p2.id,
                        similarity_score=score,
                        match_reasons=json.dumps(reasons),
                        matched_fields=json.dumps(fields),
                        status=RecordLinkStatus.SUGGESTED,
                    )
                    db.add(link)
                    new_links.append(link)

        if new_links:
            await db.commit()

        return new_links

    @staticmethod
    def _calculate_person_document_similarity(
        person: GenealogyPerson, document: GenealogyDocument
    ) -> Tuple[float, List[str], Dict[str, float]]:
        reasons = []
        fields = {}
        scores = []

        ocr_text = (document.ocr_text or "").lower()
        if not ocr_text:
            return 0.0, [], {}

        # Name matching
        full_name = f"{person.given_names} {person.surname or ''}".strip().lower()
        name_score = fuzz.partial_ratio(full_name, ocr_text) / 100.0
        if name_score > 0.7:
            reasons.append("name_match")
            fields["name"] = round(name_score, 2)
            scores.append(name_score * 0.5)  # Name is weighted 50%

        # Surname matching
        if person.surname:
            surname_score = fuzz.partial_ratio(person.surname.lower(), ocr_text) / 100.0
            if surname_score > 0.8:
                reasons.append("surname_match")
                fields["surname"] = round(surname_score, 2)
                scores.append(surname_score * 0.2)

        # Date matching
        if person.birth_date:
            date_str = person.birth_date.lower()
            if date_str in ocr_text:
                reasons.append("birth_date_match")
                fields["birth_date"] = 1.0
                scores.append(0.15)

        # Location matching
        if person.birth_place:
            place_score = fuzz.partial_ratio(person.birth_place.lower(), ocr_text) / 100.0
            if place_score > 0.7:
                reasons.append("location_match")
                fields["location"] = round(place_score, 2)
                scores.append(place_score * 0.15)

        total = sum(scores) if scores else 0.0
        return min(total, 1.0), reasons, fields

    @staticmethod
    def _calculate_person_similarity(
        p1: GenealogyPerson, p2: GenealogyPerson
    ) -> Tuple[float, List[str], Dict[str, float]]:
        reasons = []
        fields = {}
        scores = []

        # Name matching
        name1 = f"{p1.given_names} {p1.surname or ''}".strip().lower()
        name2 = f"{p2.given_names} {p2.surname or ''}".strip().lower()
        name_score = fuzz.ratio(name1, name2) / 100.0
        if name_score > 0.8:
            reasons.append("name_similarity")
            fields["name"] = round(name_score, 2)
            scores.append(name_score * 0.4)

        # Birth date matching
        if p1.birth_date and p2.birth_date:
            if p1.birth_date == p2.birth_date:
                reasons.append("same_birth_date")
                fields["birth_date"] = 1.0
                scores.append(0.25)
            else:
                date_score = fuzz.ratio(p1.birth_date, p2.birth_date) / 100.0
                if date_score > 0.7:
                    reasons.append("similar_birth_date")
                    fields["birth_date"] = round(date_score, 2)
                    scores.append(date_score * 0.15)

        # Birth place matching
        if p1.birth_place and p2.birth_place:
            place_score = fuzz.ratio(
                p1.birth_place.lower(), p2.birth_place.lower()
            ) / 100.0
            if place_score > 0.7:
                reasons.append("similar_birth_place")
                fields["birth_place"] = round(place_score, 2)
                scores.append(place_score * 0.2)

        # Gender match
        if p1.gender and p2.gender and p1.gender == p2.gender:
            reasons.append("same_gender")
            fields["gender"] = 1.0
            scores.append(0.1)

        total = sum(scores) if scores else 0.0
        return min(total, 1.0), reasons, fields

    @staticmethod
    async def get_pending_record_links(
        db: AsyncSession, project_id: int, skip: int = 0, limit: int = 50
    ) -> List[RecordLink]:
        result = await db.execute(
            select(RecordLink)
            .where(
                and_(
                    RecordLink.project_id == project_id,
                    RecordLink.status == RecordLinkStatus.SUGGESTED,
                )
            )
            .order_by(desc(RecordLink.similarity_score))
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def review_record_link(
        db: AsyncSession,
        link_id: int,
        status: RecordLinkStatus,
        reviewed_by: int,
        notes: Optional[str] = None,
    ) -> Optional[RecordLink]:
        result = await db.execute(
            select(RecordLink).where(RecordLink.id == link_id)
        )
        link = result.scalar_one_or_none()
        if not link:
            return None

        link.status = status
        link.reviewed_by = reviewed_by
        link.reviewed_at = datetime.now(timezone.utc)
        link.reviewer_notes = notes

        # If confirmed and it links a person to a document, create the link
        if (
            status == RecordLinkStatus.CONFIRMED
            and link.source_person_id
            and link.target_document_id
        ):
            existing = await db.execute(
                select(PersonDocumentLink).where(
                    and_(
                        PersonDocumentLink.person_id == link.source_person_id,
                        PersonDocumentLink.document_id == link.target_document_id,
                    )
                )
            )
            if not existing.scalar_one_or_none():
                doc_link = PersonDocumentLink(
                    person_id=link.source_person_id,
                    document_id=link.target_document_id,
                    created_by=reviewed_by,
                    notes="Auto-linked via record linking engine",
                )
                db.add(doc_link)

        await db.commit()
        await db.refresh(link)
        return link

    # ========================================================================
    # RESEARCH GUIDANCE AI
    # ========================================================================

    @staticmethod
    async def generate_research_suggestions(
        db: AsyncSession, project_id: int
    ) -> List[ResearchGuidanceSuggestion]:
        # Get all persons
        persons_result = await db.execute(
            select(GenealogyPerson).where(
                GenealogyPerson.project_id == project_id
            )
        )
        persons = list(persons_result.scalars().all())

        # Get existing suggestions to avoid duplicates
        existing_result = await db.execute(
            select(ResearchGuidanceSuggestion).where(
                and_(
                    ResearchGuidanceSuggestion.project_id == project_id,
                    ResearchGuidanceSuggestion.is_dismissed == False,
                    ResearchGuidanceSuggestion.is_completed == False,
                )
            )
        )
        existing_titles = {s.title for s in existing_result.scalars().all()}

        suggestions = []

        for person in persons:
            full_name = f"{person.given_names} {person.surname or ''}".strip()

            # Suggest vital records for missing birth info
            if not person.birth_date:
                title = f"Find birth record for {full_name}"
                if title not in existing_titles:
                    suggestion = ResearchGuidanceSuggestion(
                        project_id=project_id,
                        person_id=person.id,
                        suggestion_type=ResearchGuidanceType.NEXT_RECORD,
                        title=title,
                        description=f"No birth date found for {full_name}. Search vital records, church baptismal records, or census data to establish birth date.",
                        rationale="Birth dates are fundamental anchoring data for genealogy research.",
                        suggested_database=ExternalDatabaseSource.FAMILYSEARCH,
                        suggested_record_type="vital_records",
                        suggested_search_terms=json.dumps(
                            [full_name, person.surname or ""]
                        ),
                        priority=2,
                    )
                    db.add(suggestion)
                    suggestions.append(suggestion)

            # Suggest parent search for orphan persons
            rels_result = await db.execute(
                select(FamilyRelationship).where(
                    and_(
                        FamilyRelationship.person2_id == person.id,
                        FamilyRelationship.relationship_type
                        == RelationshipType.PARENT_CHILD,
                    )
                )
            )
            parents = list(rels_result.scalars().all())

            if not parents and not person.is_living:
                title = f"Identify parents of {full_name}"
                if title not in existing_titles:
                    desc_text = f"No parents linked for {full_name}."
                    if person.birth_place:
                        desc_text += f" Search records in {person.birth_place}."
                    if person.birth_date:
                        desc_text += f" Focus on records around {person.birth_date}."
                    desc_text += " Check census records, birth certificates, and church records."

                    suggestion = ResearchGuidanceSuggestion(
                        project_id=project_id,
                        person_id=person.id,
                        suggestion_type=ResearchGuidanceType.NEXT_RECORD,
                        title=title,
                        description=desc_text,
                        rationale="Extending the family tree upward through parental connections.",
                        suggested_database=ExternalDatabaseSource.FAMILYSEARCH,
                        suggested_record_type="census",
                        suggested_location=person.birth_place,
                        priority=1,
                    )
                    db.add(suggestion)
                    suggestions.append(suggestion)

            # Suggest alternate spelling search
            if person.surname and not person.alternate_names:
                title = f"Check alternate spellings for {person.surname}"
                if title not in existing_titles:
                    suggestion = ResearchGuidanceSuggestion(
                        project_id=project_id,
                        person_id=person.id,
                        suggestion_type=ResearchGuidanceType.ALTERNATE_SPELLING,
                        title=title,
                        description=f"The surname '{person.surname}' may have alternate historical spellings. Search with phonetic variations, Soundex equivalents, and common misspellings.",
                        rationale="Historical records often contain spelling variations that can hide relevant results.",
                        suggested_search_terms=json.dumps(
                            [person.surname, full_name]
                        ),
                        priority=0,
                    )
                    db.add(suggestion)
                    suggestions.append(suggestion)

            # Suggest immigration records for foreign-born
            if person.birth_place and person.nationality:
                title = f"Search immigration records for {full_name}"
                if title not in existing_titles:
                    suggestion = ResearchGuidanceSuggestion(
                        project_id=project_id,
                        person_id=person.id,
                        suggestion_type=ResearchGuidanceType.DATABASE_SUGGESTION,
                        title=title,
                        description=f"Search passenger lists and naturalization records for {full_name} from {person.birth_place}.",
                        rationale="Immigration records can provide family connections and origin details.",
                        suggested_database=ExternalDatabaseSource.ANCESTRY,
                        suggested_record_type="immigration",
                        suggested_location=person.birth_place,
                        priority=1,
                    )
                    db.add(suggestion)
                    suggestions.append(suggestion)

        if suggestions:
            await db.commit()

        return suggestions

    @staticmethod
    async def get_active_suggestions(
        db: AsyncSession,
        project_id: int,
        person_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> List[ResearchGuidanceSuggestion]:
        query = select(ResearchGuidanceSuggestion).where(
            and_(
                ResearchGuidanceSuggestion.project_id == project_id,
                ResearchGuidanceSuggestion.is_dismissed == False,
                ResearchGuidanceSuggestion.is_completed == False,
            )
        )

        if person_id:
            query = query.where(
                ResearchGuidanceSuggestion.person_id == person_id
            )

        query = query.order_by(
            desc(ResearchGuidanceSuggestion.priority),
            desc(ResearchGuidanceSuggestion.created_at),
        ).offset(skip).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    # ========================================================================
    # DNA MATCHING
    # ========================================================================

    @staticmethod
    async def create_dna_profile(
        db: AsyncSession,
        project_id: int,
        created_by: int,
        **profile_data: Any,
    ) -> DNAProfile:
        profile = DNAProfile(
            project_id=project_id, created_by=created_by, **profile_data
        )
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def create_dna_match(
        db: AsyncSession, **match_data: Any
    ) -> DNAMatch:
        match = DNAMatch(**match_data)
        db.add(match)
        await db.commit()
        await db.refresh(match)
        return match

    @staticmethod
    async def get_dna_matches(
        db: AsyncSession, profile_id: int
    ) -> List[DNAMatch]:
        result = await db.execute(
            select(DNAMatch)
            .where(
                or_(
                    DNAMatch.profile1_id == profile_id,
                    DNAMatch.profile2_id == profile_id,
                )
            )
            .order_by(desc(DNAMatch.shared_centimorgans))
        )
        return list(result.scalars().all())

    # ========================================================================
    # EXTERNAL REFERENCES
    # ========================================================================

    @staticmethod
    async def create_external_reference(
        db: AsyncSession,
        project_id: int,
        created_by: int,
        **ref_data: Any,
    ) -> ExternalRecordReference:
        ref = ExternalRecordReference(
            project_id=project_id, created_by=created_by, **ref_data
        )
        db.add(ref)
        await db.commit()
        await db.refresh(ref)
        return ref

    @staticmethod
    async def get_person_external_references(
        db: AsyncSession, person_id: int
    ) -> List[ExternalRecordReference]:
        result = await db.execute(
            select(ExternalRecordReference).where(
                ExternalRecordReference.person_id == person_id
            )
        )
        return list(result.scalars().all())

    # ========================================================================
    # SEARCH
    # ========================================================================

    @staticmethod
    async def search_project(
        db: AsyncSession,
        project_id: int,
        query: str,
        search_persons: bool = True,
        search_documents: bool = True,
        search_notes: bool = True,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        results = []
        search_pattern = f"%{query}%"

        if search_persons:
            persons_result = await db.execute(
                select(GenealogyPerson)
                .where(
                    and_(
                        GenealogyPerson.project_id == project_id,
                        or_(
                            GenealogyPerson.given_names.ilike(search_pattern),
                            GenealogyPerson.surname.ilike(search_pattern),
                            GenealogyPerson.maiden_name.ilike(search_pattern),
                            GenealogyPerson.nickname.ilike(search_pattern),
                            GenealogyPerson.biography.ilike(search_pattern),
                        ),
                    )
                )
                .limit(limit)
            )
            for person in persons_result.scalars().all():
                results.append(
                    {
                        "result_type": "person",
                        "id": person.id,
                        "title": f"{person.given_names} {person.surname or ''}",
                        "snippet": person.biography[:200] if person.biography else None,
                        "project_id": project_id,
                        "relevance_score": 1.0,
                    }
                )

        if search_documents:
            docs_result = await db.execute(
                select(GenealogyDocument)
                .where(
                    and_(
                        GenealogyDocument.project_id == project_id,
                        or_(
                            GenealogyDocument.title.ilike(search_pattern),
                            GenealogyDocument.description.ilike(search_pattern),
                            GenealogyDocument.ocr_text.ilike(search_pattern),
                        ),
                    )
                )
                .limit(limit)
            )
            for doc in docs_result.scalars().all():
                results.append(
                    {
                        "result_type": "document",
                        "id": doc.id,
                        "title": doc.title,
                        "snippet": doc.description[:200] if doc.description else None,
                        "project_id": project_id,
                        "relevance_score": 0.9,
                    }
                )

        if search_notes:
            notes_result = await db.execute(
                select(ResearchNote)
                .where(
                    and_(
                        ResearchNote.project_id == project_id,
                        or_(
                            ResearchNote.title.ilike(search_pattern),
                            ResearchNote.content.ilike(search_pattern),
                        ),
                    )
                )
                .limit(limit)
            )
            for note in notes_result.scalars().all():
                results.append(
                    {
                        "result_type": "note",
                        "id": note.id,
                        "title": note.title,
                        "snippet": note.content[:200] if note.content else None,
                        "project_id": project_id,
                        "relevance_score": 0.8,
                    }
                )

        # Sort by relevance
        results.sort(key=lambda r: r["relevance_score"], reverse=True)
        return results[:limit]

    # ========================================================================
    # DASHBOARD
    # ========================================================================

    @staticmethod
    async def get_project_dashboard(
        db: AsyncSession, project_id: int
    ) -> Dict[str, Any]:
        # Recent persons
        persons_result = await db.execute(
            select(GenealogyPerson)
            .where(GenealogyPerson.project_id == project_id)
            .order_by(desc(GenealogyPerson.updated_at))
            .limit(5)
        )
        recent_persons = list(persons_result.scalars().all())

        # Recent documents
        docs_result = await db.execute(
            select(GenealogyDocument)
            .where(GenealogyDocument.project_id == project_id)
            .order_by(desc(GenealogyDocument.created_at))
            .limit(5)
        )
        recent_documents = list(docs_result.scalars().all())

        # Pending record links
        links_count_result = await db.execute(
            select(func.count(RecordLink.id)).where(
                and_(
                    RecordLink.project_id == project_id,
                    RecordLink.status == RecordLinkStatus.SUGGESTED,
                )
            )
        )
        pending_links = links_count_result.scalar() or 0

        # Unresolved notes
        notes_count_result = await db.execute(
            select(func.count(ResearchNote.id)).where(
                and_(
                    ResearchNote.project_id == project_id,
                    ResearchNote.is_resolved == False,
                )
            )
        )
        unresolved_notes = notes_count_result.scalar() or 0

        # Active guidance
        guidance_result = await db.execute(
            select(ResearchGuidanceSuggestion)
            .where(
                and_(
                    ResearchGuidanceSuggestion.project_id == project_id,
                    ResearchGuidanceSuggestion.is_dismissed == False,
                    ResearchGuidanceSuggestion.is_completed == False,
                )
            )
            .order_by(desc(ResearchGuidanceSuggestion.priority))
            .limit(5)
        )
        active_guidance = list(guidance_result.scalars().all())

        # Collaborator count
        collab_count_result = await db.execute(
            select(func.count(ProjectCollaborator.id)).where(
                and_(
                    ProjectCollaborator.project_id == project_id,
                    ProjectCollaborator.is_active == True,
                )
            )
        )
        collaborator_count = collab_count_result.scalar() or 0

        return {
            "recent_persons": recent_persons,
            "recent_documents": recent_documents,
            "pending_record_links": pending_links,
            "unresolved_notes": unresolved_notes,
            "active_guidance": active_guidance,
            "collaborator_count": collaborator_count,
        }
