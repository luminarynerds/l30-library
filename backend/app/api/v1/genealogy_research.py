# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Genealogy Research Platform API Endpoints.

Comprehensive REST API for collaborative genealogy research:
- Research project CRUD with collaboration
- Person/family tree management
- Document management with OCR
- Timeline events
- Research notes
- Record linking engine
- DNA matching interface
- Research guidance AI
- External database references
- Search across all entities
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.genealogy_research import (
    DNAMatch,
    DNAProfile,
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
    ResearchGuidanceSuggestion,
    ResearchNote,
    TimelineEvent,
)
from ...models.user import User
from ...schemas.genealogy_research import (
    CollaboratorInvite,
    CollaboratorResponse,
    CollaboratorUpdate,
    DNAMatchCreate,
    DNAMatchResponse,
    DNAProfileCreate,
    DNAProfileResponse,
    DocumentCreate,
    DocumentResponse,
    DocumentSummary,
    DocumentUpdate,
    ExternalReferenceCreate,
    ExternalReferenceResponse,
    FamilyTreeResponse,
    FamilyTreeNode,
    GenealogySearchQuery,
    GenealogySearchResponse,
    GenealogySearchResult,
    GuidanceComplete,
    GuidanceDismiss,
    PersonCreate,
    PersonDocumentLinkCreate,
    PersonDocumentLinkResponse,
    PersonResponse,
    PersonSummary,
    PersonUpdate,
    RecordLinkResponse,
    RecordLinkReview,
    RelationshipCreate,
    RelationshipResponse,
    RelationshipUpdate,
    ResearchGuidanceResponse,
    ResearchNoteCreate,
    ResearchNoteResponse,
    ResearchNoteUpdate,
    ResearchProjectCreate,
    ResearchProjectDashboard,
    ResearchProjectResponse,
    ResearchProjectSummary,
    ResearchProjectUpdate,
    TimelineEventCreate,
    TimelineEventResponse,
    TimelineEventUpdate,
    PersonTimelineResponse,
    FamilyTimelineResponse,
)
from ...services.genealogy_research_service import GenealogyResearchService
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_staff

router = APIRouter(prefix="/genealogy/research", tags=["genealogy-research"])


# ============================================================================
# HELPER: project access check
# ============================================================================


async def _check_access(
    db: AsyncSession,
    project_id: int,
    user_id: int,
    required_role: Optional[ProjectRole] = None,
) -> ProjectCollaborator:
    # Also allow if project is public and user just wants to view
    project = await GenealogyResearchService.get_project(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research project not found",
        )

    collab = await GenealogyResearchService.check_project_access(
        db, project_id, user_id, required_role
    )
    if not collab:
        if project.is_public and required_role is None:
            # Allow public read access - create a fake viewer collaborator
            fake = ProjectCollaborator()
            fake.role = ProjectRole.VIEWER
            return fake
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this research project",
        )
    return collab


# ============================================================================
# RESEARCH PROJECTS
# ============================================================================


@router.post(
    "/projects",
    response_model=ResearchProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_project(
    project_data: ResearchProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new genealogy research project."""
    project = await GenealogyResearchService.create_project(
        db,
        owner_id=current_user.id,
        **project_data.model_dump(),
    )
    return project


@router.get("/projects", response_model=List[ResearchProjectSummary])
async def list_my_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List research projects the current user has access to."""
    return await GenealogyResearchService.list_user_projects(
        db, current_user.id, skip, limit
    )


@router.get("/projects/public", response_model=List[ResearchProjectSummary])
async def list_public_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List publicly available research projects."""
    result = await db.execute(
        select(GenealogyResearchProject)
        .where(GenealogyResearchProject.is_public == True)
        .order_by(desc(GenealogyResearchProject.updated_at))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/projects/{project_id}", response_model=ResearchProjectResponse)
async def get_research_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get research project details."""
    await _check_access(db, project_id, current_user.id)
    project = await GenealogyResearchService.get_project(db, project_id)
    return project


@router.put("/projects/{project_id}", response_model=ResearchProjectResponse)
async def update_research_project(
    project_id: int,
    update_data: ResearchProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update research project (admin/owner only)."""
    await _check_access(db, project_id, current_user.id, ProjectRole.ADMIN)

    project = await GenealogyResearchService.get_project(db, project_id)
    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    await db.refresh(project)
    return project


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_research_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a research project (owner only)."""
    await _check_access(db, project_id, current_user.id, ProjectRole.OWNER)

    project = await GenealogyResearchService.get_project(db, project_id)
    await db.delete(project)
    await db.commit()


# ============================================================================
# COLLABORATORS
# ============================================================================


@router.post(
    "/projects/{project_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def invite_collaborator(
    project_id: int,
    invite: CollaboratorInvite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Invite a user to collaborate on a project (admin/owner only)."""
    await _check_access(db, project_id, current_user.id, ProjectRole.ADMIN)

    # Check if user is already a collaborator
    existing = await GenealogyResearchService.check_project_access(
        db, project_id, invite.user_id
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already a collaborator",
        )

    return await GenealogyResearchService.invite_collaborator(
        db, project_id, invite.user_id, invite.role, current_user.id
    )


@router.get(
    "/projects/{project_id}/collaborators",
    response_model=List[CollaboratorResponse],
)
async def list_collaborators(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List project collaborators."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.get_project_collaborators(db, project_id)


@router.put(
    "/projects/{project_id}/collaborators/{user_id}",
    response_model=CollaboratorResponse,
)
async def update_collaborator_role(
    project_id: int,
    user_id: int,
    update: CollaboratorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a collaborator's role (owner only)."""
    await _check_access(db, project_id, current_user.id, ProjectRole.OWNER)

    result = await db.execute(
        select(ProjectCollaborator).where(
            and_(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == user_id,
            )
        )
    )
    collab = result.scalar_one_or_none()
    if not collab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found",
        )

    collab.role = update.role
    await db.commit()
    await db.refresh(collab)
    return collab


@router.delete(
    "/projects/{project_id}/collaborators/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_collaborator(
    project_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a collaborator from a project (admin/owner or self-remove)."""
    if user_id != current_user.id:
        await _check_access(db, project_id, current_user.id, ProjectRole.ADMIN)

    result = await db.execute(
        select(ProjectCollaborator).where(
            and_(
                ProjectCollaborator.project_id == project_id,
                ProjectCollaborator.user_id == user_id,
            )
        )
    )
    collab = result.scalar_one_or_none()
    if not collab:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collaborator not found",
        )

    if collab.role == ProjectRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the project owner",
        )

    collab.is_active = False
    await db.commit()


# ============================================================================
# PERSONS (Family Tree Members)
# ============================================================================


@router.post(
    "/projects/{project_id}/persons",
    response_model=PersonResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_person(
    project_id: int,
    person_data: PersonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a new person to the family tree."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_person(
        db,
        project_id=project_id,
        created_by=current_user.id,
        **person_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/persons",
    response_model=List[PersonSummary],
)
async def list_persons(
    project_id: int,
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List persons in a research project."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.list_project_persons(
        db, project_id, search, skip, limit
    )


@router.get(
    "/projects/{project_id}/persons/{person_id}",
    response_model=PersonResponse,
)
async def get_person(
    project_id: int,
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a person's full details."""
    await _check_access(db, project_id, current_user.id)

    person = await GenealogyResearchService.get_person(db, person_id)
    if not person or person.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )
    return person


@router.put(
    "/projects/{project_id}/persons/{person_id}",
    response_model=PersonResponse,
)
async def update_person(
    project_id: int,
    person_id: int,
    person_data: PersonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a person's details."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    person = await GenealogyResearchService.get_person(db, person_id)
    if not person or person.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )

    updated = await GenealogyResearchService.update_person(
        db, person_id, **person_data.model_dump(exclude_unset=True)
    )
    return updated


@router.delete(
    "/projects/{project_id}/persons/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_person(
    project_id: int,
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a person from the project."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    person = await GenealogyResearchService.get_person(db, person_id)
    if not person or person.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )

    await db.delete(person)
    await db.commit()


# ============================================================================
# RELATIONSHIPS
# ============================================================================


@router.post(
    "/projects/{project_id}/relationships",
    response_model=RelationshipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_relationship(
    project_id: int,
    rel_data: RelationshipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a family relationship between two persons."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    # Verify both persons belong to this project
    for pid in [rel_data.person1_id, rel_data.person2_id]:
        person = await GenealogyResearchService.get_person(db, pid)
        if not person or person.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Person {pid} not found in this project",
            )

    return await GenealogyResearchService.create_relationship(
        db,
        project_id=project_id,
        created_by=current_user.id,
        **rel_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/persons/{person_id}/relationships",
    response_model=List[RelationshipResponse],
)
async def get_person_relationships(
    project_id: int,
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all relationships for a person."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.get_person_relationships(db, person_id)


@router.delete(
    "/projects/{project_id}/relationships/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_relationship(
    project_id: int,
    relationship_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a family relationship."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(FamilyRelationship).where(
            and_(
                FamilyRelationship.id == relationship_id,
                FamilyRelationship.project_id == project_id,
            )
        )
    )
    rel = result.scalar_one_or_none()
    if not rel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found",
        )

    await db.delete(rel)
    await db.commit()


# ============================================================================
# FAMILY TREE
# ============================================================================


@router.get(
    "/projects/{project_id}/tree",
    response_model=FamilyTreeResponse,
)
async def get_family_tree(
    project_id: int,
    root_person_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the complete family tree for visualization."""
    await _check_access(db, project_id, current_user.id)

    tree_data = await GenealogyResearchService.build_family_tree(
        db, project_id, root_person_id
    )

    # Convert to response format
    nodes = []
    for person_id, node_data in tree_data["nodes"].items():
        person = node_data["person"]
        nodes.append(
            FamilyTreeNode(
                person=PersonSummary(
                    id=person.id,
                    given_names=person.given_names,
                    surname=person.surname,
                    birth_date=person.birth_date,
                    death_date=person.death_date,
                    gender=str(person.gender) if person.gender else None,
                    is_living=person.is_living,
                    profile_photo_url=person.profile_photo_url,
                    confidence_level=person.confidence_level,
                ),
                parents=node_data["parents"],
                children=node_data["children"],
                spouses=node_data["spouses"],
                siblings=node_data["siblings"],
            )
        )

    return FamilyTreeResponse(
        project_id=project_id,
        root_person_id=root_person_id,
        nodes=nodes,
        relationships=[
            RelationshipResponse.model_validate(r)
            for r in tree_data["relationships"]
        ],
        generation_count=tree_data["generation_count"],
        person_count=tree_data["person_count"],
    )


# ============================================================================
# DOCUMENTS
# ============================================================================


@router.post(
    "/projects/{project_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    project_id: int,
    doc_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload/create a document record."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_document(
        db,
        project_id=project_id,
        uploaded_by=current_user.id,
        **doc_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/documents",
    response_model=List[DocumentSummary],
)
async def list_documents(
    project_id: int,
    document_type: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List documents in a project."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.list_project_documents(
        db, project_id, document_type, search, skip, limit
    )


@router.get(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    project_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get document details."""
    await _check_access(db, project_id, current_user.id)

    result = await db.execute(
        select(GenealogyDocument).where(
            and_(
                GenealogyDocument.id == document_id,
                GenealogyDocument.project_id == project_id,
            )
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )
    return doc


@router.put(
    "/projects/{project_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def update_document(
    project_id: int,
    document_id: int,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update document metadata or annotations."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(GenealogyDocument).where(
            and_(
                GenealogyDocument.id == document_id,
                GenealogyDocument.project_id == project_id,
            )
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(doc, field, value)

    await db.commit()
    await db.refresh(doc)
    return doc


@router.post(
    "/projects/{project_id}/documents/{document_id}/ocr",
    response_model=DocumentResponse,
)
async def process_document_ocr(
    project_id: int,
    document_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger OCR processing for a document.
    In production, this would queue the OCR job. Here we simulate
    the OCR result being stored.
    """
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(GenealogyDocument).where(
            and_(
                GenealogyDocument.id == document_id,
                GenealogyDocument.project_id == project_id,
            )
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        )

    # Mark as processing - actual OCR would be async
    doc.status = "processing"
    await db.commit()
    await db.refresh(doc)
    return doc


@router.post(
    "/projects/{project_id}/document-links",
    response_model=PersonDocumentLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def link_person_to_document(
    project_id: int,
    link_data: PersonDocumentLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link a person to a document."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.link_person_to_document(
        db,
        person_id=link_data.person_id,
        document_id=link_data.document_id,
        created_by=current_user.id,
        role_in_document=link_data.role_in_document,
        page_number=link_data.page_number,
        excerpt=link_data.excerpt,
        notes=link_data.notes,
    )


# ============================================================================
# TIMELINE
# ============================================================================


@router.post(
    "/projects/{project_id}/timeline-events",
    response_model=TimelineEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_timeline_event(
    project_id: int,
    event_data: TimelineEventCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a timeline event for a person."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_timeline_event(
        db,
        project_id=project_id,
        created_by=current_user.id,
        **event_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/persons/{person_id}/timeline",
    response_model=PersonTimelineResponse,
)
async def get_person_timeline(
    project_id: int,
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a person's timeline events."""
    await _check_access(db, project_id, current_user.id)

    person = await GenealogyResearchService.get_person(db, person_id)
    if not person or person.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Person not found"
        )

    events = await GenealogyResearchService.get_person_timeline(db, person_id)
    return PersonTimelineResponse(
        person_id=person_id,
        person_name=f"{person.given_names} {person.surname or ''}".strip(),
        events=[TimelineEventResponse.model_validate(e) for e in events],
    )


@router.get(
    "/projects/{project_id}/family-timeline",
    response_model=FamilyTimelineResponse,
)
async def get_family_timeline(
    project_id: int,
    person_ids: str = Query(..., description="Comma-separated person IDs"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a merged timeline for multiple family members."""
    await _check_access(db, project_id, current_user.id)

    ids = [int(pid.strip()) for pid in person_ids.split(",") if pid.strip()]
    events = await GenealogyResearchService.get_family_timeline(
        db, project_id, ids
    )

    return FamilyTimelineResponse(
        project_id=project_id,
        person_ids=ids,
        events=[TimelineEventResponse.model_validate(e) for e in events],
    )


@router.put(
    "/projects/{project_id}/timeline-events/{event_id}",
    response_model=TimelineEventResponse,
)
async def update_timeline_event(
    project_id: int,
    event_id: int,
    update_data: TimelineEventUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a timeline event."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(TimelineEvent).where(
            and_(
                TimelineEvent.id == event_id,
                TimelineEvent.project_id == project_id,
            )
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline event not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(event, field, value)

    await db.commit()
    await db.refresh(event)
    return event


@router.delete(
    "/projects/{project_id}/timeline-events/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_timeline_event(
    project_id: int,
    event_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a timeline event."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(TimelineEvent).where(
            and_(
                TimelineEvent.id == event_id,
                TimelineEvent.project_id == project_id,
            )
        )
    )
    event = result.scalar_one_or_none()
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Timeline event not found",
        )

    await db.delete(event)
    await db.commit()


# ============================================================================
# RESEARCH NOTES
# ============================================================================


@router.post(
    "/projects/{project_id}/notes",
    response_model=ResearchNoteResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_research_note(
    project_id: int,
    note_data: ResearchNoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a research note."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_research_note(
        db,
        project_id=project_id,
        author_id=current_user.id,
        **note_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/notes",
    response_model=List[ResearchNoteResponse],
)
async def list_research_notes(
    project_id: int,
    note_type: Optional[str] = Query(None),
    person_id: Optional[int] = Query(None),
    unresolved_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List research notes in a project."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.list_research_notes(
        db, project_id, note_type, person_id, unresolved_only, skip, limit
    )


@router.put(
    "/projects/{project_id}/notes/{note_id}",
    response_model=ResearchNoteResponse,
)
async def update_research_note(
    project_id: int,
    note_id: int,
    update_data: ResearchNoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a research note."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(ResearchNote).where(
            and_(
                ResearchNote.id == note_id,
                ResearchNote.project_id == project_id,
            )
        )
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research note not found",
        )

    for field, value in update_data.model_dump(exclude_unset=True).items():
        setattr(note, field, value)

    await db.commit()
    await db.refresh(note)
    return note


# ============================================================================
# RECORD LINKING ENGINE
# ============================================================================


@router.post(
    "/projects/{project_id}/record-links/analyze",
    response_model=List[RecordLinkResponse],
)
async def analyze_record_links(
    project_id: int,
    threshold: float = Query(0.6, ge=0.0, le=1.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the record linking engine to find potential matches
    between persons and documents based on similarity analysis.
    """
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    new_links = await GenealogyResearchService.find_potential_record_links(
        db, project_id, threshold
    )
    return new_links


@router.get(
    "/projects/{project_id}/record-links",
    response_model=List[RecordLinkResponse],
)
async def list_record_links(
    project_id: int,
    status_filter: Optional[str] = Query(None, alias="status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List record links for a project."""
    await _check_access(db, project_id, current_user.id)

    query = select(RecordLink).where(RecordLink.project_id == project_id)
    if status_filter:
        query = query.where(RecordLink.status == status_filter)

    query = query.order_by(desc(RecordLink.similarity_score)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.put(
    "/projects/{project_id}/record-links/{link_id}",
    response_model=RecordLinkResponse,
)
async def review_record_link(
    project_id: int,
    link_id: int,
    review: RecordLinkReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Review a suggested record link (confirm or reject)."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    link = await GenealogyResearchService.review_record_link(
        db, link_id, review.status, current_user.id, review.reviewer_notes
    )
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Record link not found",
        )
    return link


# ============================================================================
# DNA MATCHING
# ============================================================================


@router.post(
    "/projects/{project_id}/dna-profiles",
    response_model=DNAProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dna_profile(
    project_id: int,
    profile_data: DNAProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a DNA profile for a person."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_dna_profile(
        db,
        project_id=project_id,
        created_by=current_user.id,
        **profile_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/dna-profiles",
    response_model=List[DNAProfileResponse],
)
async def list_dna_profiles(
    project_id: int,
    person_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List DNA profiles in a project."""
    await _check_access(db, project_id, current_user.id)

    query = select(DNAProfile).where(DNAProfile.project_id == project_id)
    if person_id:
        query = query.where(DNAProfile.person_id == person_id)

    result = await db.execute(query.order_by(desc(DNAProfile.created_at)))
    return result.scalars().all()


@router.post(
    "/projects/{project_id}/dna-matches",
    response_model=DNAMatchResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_dna_match(
    project_id: int,
    match_data: DNAMatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a DNA match between two profiles."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_dna_match(
        db, **match_data.model_dump()
    )


@router.get(
    "/projects/{project_id}/dna-profiles/{profile_id}/matches",
    response_model=List[DNAMatchResponse],
)
async def get_dna_matches(
    project_id: int,
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get DNA matches for a profile."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.get_dna_matches(db, profile_id)


# ============================================================================
# RESEARCH GUIDANCE
# ============================================================================


@router.post(
    "/projects/{project_id}/guidance/generate",
    response_model=List[ResearchGuidanceResponse],
)
async def generate_research_guidance(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate AI research guidance suggestions for a project."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.generate_research_suggestions(
        db, project_id
    )


@router.get(
    "/projects/{project_id}/guidance",
    response_model=List[ResearchGuidanceResponse],
)
async def list_research_guidance(
    project_id: int,
    person_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active research guidance suggestions."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.get_active_suggestions(
        db, project_id, person_id, skip, limit
    )


@router.put(
    "/projects/{project_id}/guidance/{suggestion_id}/dismiss",
    response_model=ResearchGuidanceResponse,
)
async def dismiss_guidance(
    project_id: int,
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Dismiss a research guidance suggestion."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(ResearchGuidanceSuggestion).where(
            and_(
                ResearchGuidanceSuggestion.id == suggestion_id,
                ResearchGuidanceSuggestion.project_id == project_id,
            )
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )

    suggestion.is_dismissed = True
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


@router.put(
    "/projects/{project_id}/guidance/{suggestion_id}/complete",
    response_model=ResearchGuidanceResponse,
)
async def complete_guidance(
    project_id: int,
    suggestion_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a research guidance suggestion as completed."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    result = await db.execute(
        select(ResearchGuidanceSuggestion).where(
            and_(
                ResearchGuidanceSuggestion.id == suggestion_id,
                ResearchGuidanceSuggestion.project_id == project_id,
            )
        )
    )
    suggestion = result.scalar_one_or_none()
    if not suggestion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Suggestion not found",
        )

    suggestion.is_completed = True
    suggestion.completed_by = current_user.id
    suggestion.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(suggestion)
    return suggestion


# ============================================================================
# EXTERNAL REFERENCES
# ============================================================================


@router.post(
    "/projects/{project_id}/external-references",
    response_model=ExternalReferenceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_external_reference(
    project_id: int,
    ref_data: ExternalReferenceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a reference to an external genealogy database record."""
    await _check_access(db, project_id, current_user.id, ProjectRole.EDITOR)

    return await GenealogyResearchService.create_external_reference(
        db,
        project_id=project_id,
        created_by=current_user.id,
        **ref_data.model_dump(),
    )


@router.get(
    "/projects/{project_id}/persons/{person_id}/external-references",
    response_model=List[ExternalReferenceResponse],
)
async def get_person_external_references(
    project_id: int,
    person_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get external database references for a person."""
    await _check_access(db, project_id, current_user.id)
    return await GenealogyResearchService.get_person_external_references(
        db, person_id
    )


# ============================================================================
# SEARCH
# ============================================================================


@router.post(
    "/projects/{project_id}/search",
    response_model=GenealogySearchResponse,
)
async def search_project(
    project_id: int,
    search_query: GenealogySearchQuery,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search across all entities in a project."""
    await _check_access(db, project_id, current_user.id)

    results = await GenealogyResearchService.search_project(
        db,
        project_id,
        search_query.query,
        search_query.search_persons,
        search_query.search_documents,
        search_query.search_notes,
    )

    return GenealogySearchResponse(
        query=search_query.query,
        total_results=len(results),
        results=[GenealogySearchResult(**r) for r in results],
    )


# ============================================================================
# DASHBOARD
# ============================================================================


@router.get(
    "/projects/{project_id}/dashboard",
    response_model=ResearchProjectDashboard,
)
async def get_project_dashboard(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the research project dashboard with summary data."""
    await _check_access(db, project_id, current_user.id)

    project = await GenealogyResearchService.get_project(db, project_id)
    dashboard = await GenealogyResearchService.get_project_dashboard(
        db, project_id
    )

    return ResearchProjectDashboard(
        project=ResearchProjectResponse.model_validate(project),
        recent_persons=[
            PersonSummary.model_validate(p) for p in dashboard["recent_persons"]
        ],
        recent_documents=[
            DocumentSummary.model_validate(d) for d in dashboard["recent_documents"]
        ],
        pending_record_links=dashboard["pending_record_links"],
        unresolved_notes=dashboard["unresolved_notes"],
        active_guidance=[
            ResearchGuidanceResponse.model_validate(g) for g in dashboard["active_guidance"]
        ],
        collaborator_count=dashboard["collaborator_count"],
    )
