# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board documents management API endpoints with lifecycle and authorization."""

from datetime import datetime, timezone
from typing import List, Optional
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....core.shortcuts import get_or_404

logger = get_logger(__name__)
from ....core.audit_log import audit_log_event
from ....models.board import BoardDocument, BoardMeeting, DocumentStatus, BoardDocumentVersion
from ....models.board_audit_log import BoardAuditLog, BoardAuditAction
from ....models.user import User, UserRole
from ....schemas.board import (
    BoardDocumentCreate,
    BoardDocumentResponse,
    BoardDocumentUpdate,
    DocumentVersionCreate,
    DocumentVersionResponse,
)
from ..auth import get_current_user
from ..dependencies import is_admin

router = APIRouter(prefix="/board/documents", tags=["board-documents"])


def _check_director_or_staff(current_user: User):
    valid_roles = [UserRole.DIRECTOR, UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN]
    if current_user.role not in valid_roles:
        raise HTTPException(status_code=403, detail="Director or staff access required")


# ============ Public Document Endpoints ============


@router.get("", response_model=List[BoardDocumentResponse])
async def get_public_documents(
    document_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get public board documents."""
    query = select(BoardDocument).where(
        and_(BoardDocument.is_public == True, BoardDocument.status == "published")
    )
    if document_type:
        query = query.where(BoardDocument.document_type == document_type)
    query = (
        query
        .options(selectinload(BoardDocument.created_by), selectinload(BoardDocument.published_by))
        .order_by(BoardDocument.published_date.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    return result.scalars().all()


# ============ Document CRUD ============


@router.get("/{document_id}", response_model=BoardDocumentResponse)
async def get_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a board document by ID. Public documents available to all, private to authorized users."""
    doc = await get_or_404(db, BoardDocument, document_id, "Document not found")

    if not doc.is_public:
        raise HTTPException(status_code=404, detail="Document not found")

    # Increment view count
    doc.view_count = (doc.view_count or 0) + 1

    # Log document view to audit trail
    now = datetime.now(timezone.utc)
    audit_entry = BoardAuditLog(
        user_id=None,  # Public access, no authenticated user required
        action=BoardAuditAction.DOCUMENT_VIEWED,
        entity_type="BoardDocument",
        entity_id=document_id,
        details={
            "document_title": doc.title,
            "document_type": doc.document_type or "unknown",
            "is_public": doc.is_public,
            "view_count": doc.view_count,
            "viewed_at": now.isoformat()
        },
        notes=f"Document '{doc.title}' viewed (view #{doc.view_count})"
    )
    db.add(audit_entry)

    await db.commit()

    return doc


@router.post("/{document_id}/publish", response_model=BoardDocumentResponse, status_code=status.HTTP_200_OK)
async def publish_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Publish a document (draft -> published).
    Requires DIRECTOR or STAFF/ADMIN role.
    Document lifecycle: draft -> published -> archived
    """
    _check_director_or_staff(current_user)

    doc = await get_or_404(db, BoardDocument, document_id, "Document not found")

    if not doc.is_public:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate state transition: only draft documents can be published
    if doc.status == DocumentStatus.PUBLISHED.value:
        raise HTTPException(
            status_code=400,
            detail="Document is already published"
        )
    elif doc.status == DocumentStatus.ARCHIVED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot publish an archived document"
        )

    # Use transaction for atomic state change
    try:
        now = datetime.now(timezone.utc)
        doc.status = DocumentStatus.PUBLISHED.value
        doc.published_date = now
        doc.published_by_id = current_user.id
        doc.updated_at = now

        # Log document publication to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.DOCUMENT_PUBLISHED,
            entity_type="BoardDocument",
            entity_id=document_id,
            details={
                "old_status": DocumentStatus.DRAFT.value,
                "new_status": DocumentStatus.PUBLISHED.value,
                "document_title": doc.title,
                "document_type": doc.document_type or "unknown",
                "published_at": now.isoformat(),
                "published_by": f"{current_user.first_name} {current_user.last_name}"
            },
            notes=f"Document '{doc.title}' published by {current_user.email}"
        )
        db.add(audit_entry)
        audit_log_event(
            event_type="BOARD_DOCUMENT_PUBLISHED",
            user_id=current_user.id,
            email=current_user.email,
            ip_address=str(request.client.host) if request.client else "unknown",
            severity="INFO",
            details={"document_id": document_id, "entity_type": "BoardDocument", "document_title": doc.title},
        )

        await db.commit()
        await db.refresh(doc)
        return doc
    except Exception:
        await db.rollback()
        logger.exception("Failed to publish document")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


@router.post("/{document_id}/archive", response_model=BoardDocumentResponse, status_code=status.HTTP_200_OK)
async def archive_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Archive a document (published -> archived).
    Requires DIRECTOR or STAFF/ADMIN role.
    Document lifecycle: draft -> published -> archived
    """
    _check_director_or_staff(current_user)

    doc = await get_or_404(db, BoardDocument, document_id, "Document not found")

    if not doc.is_public:
        raise HTTPException(status_code=404, detail="Document not found")

    # Validate state transition: only published documents can be archived
    if doc.status == DocumentStatus.DRAFT.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot archive a draft document. Publish it first."
        )
    elif doc.status == DocumentStatus.ARCHIVED.value:
        raise HTTPException(
            status_code=400,
            detail="Document is already archived"
        )

    # Use transaction for atomic state change
    try:
        now = datetime.now(timezone.utc)
        old_status = doc.status
        doc.status = DocumentStatus.ARCHIVED.value
        doc.updated_at = now

        # Log document archival to audit trail
        audit_entry = BoardAuditLog(
            user_id=current_user.id,
            action=BoardAuditAction.DOCUMENT_ARCHIVED,
            entity_type="BoardDocument",
            entity_id=document_id,
            details={
                "old_status": old_status,
                "new_status": DocumentStatus.ARCHIVED.value,
                "document_title": doc.title,
                "document_type": doc.document_type or "unknown",
                "archived_at": now.isoformat(),
                "archived_by": f"{current_user.first_name} {current_user.last_name}"
            },
            notes=f"Document '{doc.title}' archived by {current_user.email}"
        )
        db.add(audit_entry)
        audit_log_event(
            event_type="BOARD_DOCUMENT_ARCHIVED",
            user_id=current_user.id,
            email=current_user.email,
            ip_address=str(request.client.host) if request.client else "unknown",
            severity="INFO",
            details={"document_id": document_id, "entity_type": "BoardDocument", "document_title": doc.title},
        )

        await db.commit()
        await db.refresh(doc)
        return doc
    except Exception:
        await db.rollback()
        logger.exception("Failed to archive document")
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR) from None


# ============ Document Upload / Update / Delete ============


@router.post("", response_model=BoardDocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    document: BoardDocumentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a new board document (staff/admin)."""
    _check_director_or_staff(current_user)

    db_doc = BoardDocument(
        **document.model_dump(),
        status=DocumentStatus.DRAFT.value,
        created_by_id=current_user.id,
    )
    db.add(db_doc)
    await db.commit()
    await db.refresh(db_doc)
    audit_log_event(
        event_type="BOARD_DOCUMENT_UPLOADED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"document_id": db_doc.id, "entity_type": "BoardDocument", "title": db_doc.title},
    )
    return db_doc


@router.put("/{document_id}", response_model=BoardDocumentResponse)
async def update_document(
    document_id: int,
    document: BoardDocumentUpdate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a board document (staff/admin)."""
    _check_director_or_staff(current_user)

    db_doc = await get_or_404(db, BoardDocument, document_id, "Document not found")

    if db_doc.status == DocumentStatus.ARCHIVED.value:
        raise HTTPException(
            status_code=400,
            detail="Cannot update an archived document"
        )

    for key, value in document.model_dump(exclude_unset=True).items():
        setattr(db_doc, key, value)

    db_doc.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(db_doc)
    audit_log_event(
        event_type="BOARD_DOCUMENT_UPDATED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="INFO",
        details={"document_id": document_id, "entity_type": "BoardDocument", "updated_fields": list(document.model_dump(exclude_unset=True).keys())},
    )
    return db_doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a board document (admin only)."""
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")

    db_doc = await get_or_404(db, BoardDocument, document_id, "Document not found")

    audit_log_event(
        event_type="BOARD_DOCUMENT_DELETED",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=str(request.client.host) if request.client else "unknown",
        severity="WARNING",
        details={"document_id": document_id, "entity_type": "BoardDocument", "title": db_doc.title},
    )
    await db.delete(db_doc)
    await db.commit()
    return {"message": "Document deleted"}


# ============ Document Version Endpoints ============


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
async def list_document_versions(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all versions for a document (staff/admin).

    Version history exposes each version's file_url, including drafts and
    versions of non-public documents, so it is restricted to staff.
    """
    _check_director_or_staff(current_user)

    await get_or_404(db, BoardDocument, document_id, "Document not found")

    query = (
        select(BoardDocumentVersion)
        .where(BoardDocumentVersion.document_id == document_id)
        .order_by(BoardDocumentVersion.version_number.asc())
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/{document_id}/versions",
    response_model=DocumentVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_document_version(
    document_id: int,
    version_data: DocumentVersionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new version for a document (staff/admin)."""
    _check_director_or_staff(current_user)

    await get_or_404(db, BoardDocument, document_id, "Document not found")

    # Determine the next version number
    count_query = select(BoardDocumentVersion).where(BoardDocumentVersion.document_id == document_id)
    result = await db.execute(count_query)
    existing = result.scalars().all()
    next_version = len(existing) + 1

    db_version = BoardDocumentVersion(
        document_id=document_id,
        version_number=next_version,
        created_by_id=current_user.id,
        **version_data.model_dump(),
    )
    db.add(db_version)
    await db.commit()
    await db.refresh(db_version)
    return db_version


@router.get("/{document_id}/versions/{version_number}", response_model=DocumentVersionResponse)
async def get_document_version(
    document_id: int,
    version_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific version of a document by version number (staff/admin)."""
    _check_director_or_staff(current_user)

    await get_or_404(db, BoardDocument, document_id, "Document not found")

    query = select(BoardDocumentVersion).where(
        and_(
            BoardDocumentVersion.document_id == document_id,
            BoardDocumentVersion.version_number == version_number,
        )
    )
    result = await db.execute(query)
    version = result.scalar_one_or_none()
    if not version:
        raise HTTPException(status_code=404, detail="Version not found")
    return version
