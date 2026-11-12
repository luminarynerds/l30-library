# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal Documents API - Document Management Endpoints

Provides endpoints for:
- Document CRUD operations
- Version management
- Document search and filtering
- Document approval workflow
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ....core.database import get_db
from ....models.legal_compliance import (
    LegalDocument, DocumentVersion, LegalDocumentType, DocumentCategory,
    LegalDocumentStatus, AuditEventType, DocumentAuditLog
)
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/legal/documents", tags=["legal-documents"])


@router.get("")
async def list_documents(
    status: Optional[LegalDocumentStatus] = None,
    category: Optional[DocumentCategory] = None,
    document_type: Optional[str] = None,
    search: Optional[str] = None,
    expiring_within_days: Optional[int] = None,
    review_overdue: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List legal documents with filtering."""
    query = select(LegalDocument).options(
        joinedload(LegalDocument.owner),
        joinedload(LegalDocument.current_version)
    )

    # Apply filters
    filters = []
    if status:
        filters.append(LegalDocument.status == status)
    if category:
        filters.append(LegalDocument.category == category)
    if document_type:
        filters.append(LegalDocument.document_type == document_type)
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                LegalDocument.title.ilike(search_pattern),
                LegalDocument.description.ilike(search_pattern),
                LegalDocument.document_number.ilike(search_pattern)
            )
        )
    if expiring_within_days:
        target_date = date.today() + timedelta(days=expiring_within_days)
        filters.append(
            and_(
                LegalDocument.expiration_date.isnot(None),
                LegalDocument.expiration_date <= target_date
            )
        )
    if review_overdue:
        filters.append(
            and_(
                LegalDocument.next_review_date.isnot(None),
                LegalDocument.next_review_date < date.today()
            )
        )

    if filters:
        query = query.where(and_(*filters))

    # Apply pagination
    query = query.order_by(LegalDocument.created_at.desc())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    documents = result.scalars().all()

    return {
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "document_number": doc.document_number,
                "document_type": doc.document_type,
                "category": str(doc.category),
                "status": str(doc.status),
                "effective_date": doc.effective_date.isoformat() if doc.effective_date else None,
                "expiration_date": doc.expiration_date.isoformat() if doc.expiration_date else None,
                "next_review_date": doc.next_review_date.isoformat() if doc.next_review_date else None,
                "owner": {
                    "id": doc.owner.id,
                    "name": f"{doc.owner.first_name} {doc.owner.last_name}"
                } if doc.owner else None,
                "current_version": {
                    "id": doc.current_version.id,
                    "version_number": doc.current_version.version_number
                } if doc.current_version else None,
                "created_at": doc.created_at.isoformat()
            }
            for doc in documents
        ],
        "total": len(documents),
        "limit": limit,
        "offset": offset
    }


@router.get("/{document_id}")
async def get_document(
    document_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific legal document with full details."""
    query = select(LegalDocument).where(LegalDocument.id == document_id).options(
        joinedload(LegalDocument.owner),
        joinedload(LegalDocument.approved_by),
        joinedload(LegalDocument.created_by),
        joinedload(LegalDocument.current_version),
        selectinload(LegalDocument.versions),
        selectinload(LegalDocument.compliance_links),
        selectinload(LegalDocument.review_cycles)
    )

    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": document.id,
        "title": document.title,
        "document_number": document.document_number,
        "document_type": document.document_type,
        "category": str(document.category),
        "description": document.description,
        "purpose": document.purpose,
        "scope": document.scope,
        "status": str(document.status),
        "effective_date": document.effective_date.isoformat() if document.effective_date else None,
        "expiration_date": document.expiration_date.isoformat() if document.expiration_date else None,
        "last_reviewed_date": document.last_reviewed_date.isoformat() if document.last_reviewed_date else None,
        "next_review_date": document.next_review_date.isoformat() if document.next_review_date else None,
        "authority_source": document.authority_source,
        "authority_citation": document.authority_citation,
        "responsible_department": document.responsible_department,
        "tags": document.tags,
        "keywords": document.keywords,
        "approval_required": document.approval_required,
        "approved_at": document.approved_at.isoformat() if document.approved_at else None,
        "owner": {
            "id": document.owner.id,
            "name": f"{document.owner.first_name} {document.owner.last_name}"
        } if document.owner else None,
        "approved_by": {
            "id": document.approved_by.id,
            "name": f"{document.approved_by.first_name} {document.approved_by.last_name}"
        } if document.approved_by else None,
        "current_version": {
            "id": document.current_version.id,
            "version_number": document.current_version.version_number,
            "file_url": document.current_version.file_url
        } if document.current_version else None,
        "version_count": len(document.versions),
        "compliance_link_count": len(document.compliance_links),
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat() if document.updated_at else None
    }


@router.post("")
async def create_document(
    title: str,
    document_type: str,
    category: DocumentCategory,
    description: Optional[str] = None,
    purpose: Optional[str] = None,
    scope: Optional[str] = None,
    authority_source: Optional[str] = None,
    authority_citation: Optional[str] = None,
    responsible_department: Optional[str] = None,
    effective_date: Optional[date] = None,
    tags: List[str] = [],
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new legal document."""
    from datetime import timedelta

    # Generate document number
    result = await db.execute(select(func.count(LegalDocument.id)))
    count = result.scalar()
    document_number = f"DOC-{category.value.upper()[:3]}-{count + 1:05d}"

    # Create document
    document = LegalDocument(
        title=title,
        document_number=document_number,
        document_type=document_type,
        category=category,
        description=description,
        purpose=purpose,
        scope=scope,
        status=LegalDocumentStatus.draft,
        authority_source=authority_source,
        authority_citation=authority_citation,
        responsible_department=responsible_department,
        effective_date=effective_date,
        tags=tags,
        owner_id=staff_user.id,
        created_by_id=staff_user.id
    )

    db.add(document)
    await db.flush()

    # Create audit log
    audit_log = DocumentAuditLog(
        document_id=document.id,
        event_type=AuditEventType.created,
        event_description=f"Document created: {title}",
        new_values={"title": title, "document_type": document_type, "category": category.value},
        user_id=staff_user.id,
        user_role=str(staff_user.role)
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(document)

    return {
        "id": document.id,
        "document_number": document.document_number,
        "title": document.title,
        "status": str(document.status),
        "created_at": document.created_at.isoformat()
    }


@router.put("/{document_id}")
async def update_document(
    document_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    purpose: Optional[str] = None,
    scope: Optional[str] = None,
    effective_date: Optional[date] = None,
    expiration_date: Optional[date] = None,
    next_review_date: Optional[date] = None,
    tags: Optional[List[str]] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a legal document."""
    query = select(LegalDocument).where(LegalDocument.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Track changes
    old_values = {}
    new_values = {}
    field_changes = {}

    if title and title != document.title:
        old_values["title"] = document.title
        new_values["title"] = title
        field_changes["title"] = {"old": document.title, "new": title}
        document.title = title

    if description and description != document.description:
        old_values["description"] = document.description
        new_values["description"] = description
        document.description = description

    if purpose is not None:
        document.purpose = purpose
    if scope is not None:
        document.scope = scope
    if effective_date is not None:
        document.effective_date = effective_date
    if expiration_date is not None:
        document.expiration_date = expiration_date
    if next_review_date is not None:
        document.next_review_date = next_review_date
    if tags is not None:
        document.tags = tags

    # Create audit log
    if old_values:
        audit_log = DocumentAuditLog(
            document_id=document.id,
            event_type=AuditEventType.updated,
            event_description=f"Document updated: {document.title}",
            old_values=old_values,
            new_values=new_values,
            field_changes=field_changes,
            user_id=staff_user.id,
            user_role=str(staff_user.role)
        )
        db.add(audit_log)

    await db.commit()
    await db.refresh(document)

    return {
        "id": document.id,
        "title": document.title,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None
    }


@router.post("/{document_id}/versions")
async def create_document_version(
    document_id: int,
    version_number: str,
    change_summary: str,
    content: Optional[str] = None,
    file_url: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new version of a document."""
    # Get document
    query = select(LegalDocument).where(LegalDocument.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Parse version number
    try:
        parts = version_number.split(".")
        major_version = int(parts[0])
        minor_version = int(parts[1]) if len(parts) > 1 else 0
    except (ValueError, IndexError):
        raise HTTPException(status_code=400, detail="Invalid version number format") from None

    # Mark previous versions as not current
    await db.execute(
        update(DocumentVersion)
        .where(
            and_(
                DocumentVersion.document_id == document_id,
                DocumentVersion.is_current == True
            )
        )
        .values(is_current=False)
    )

    # Create new version
    version = DocumentVersion(
        document_id=document_id,
        version_number=version_number,
        major_version=major_version,
        minor_version=minor_version,
        content=content,
        file_url=file_url,
        change_summary=change_summary,
        is_current=True,
        created_by_id=staff_user.id
    )

    db.add(version)
    await db.flush()

    # Update document's current version
    document.current_version_id = version.id

    # Create audit log
    audit_log = DocumentAuditLog(
        document_id=document.id,
        event_type=AuditEventType.version_created,
        event_description=f"Version {version_number} created",
        new_values={"version_number": version_number, "change_summary": change_summary},
        user_id=staff_user.id,
        user_role=str(staff_user.role)
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(version)

    return {
        "id": version.id,
        "version_number": version.version_number,
        "change_summary": version.change_summary,
        "created_at": version.created_at.isoformat()
    }


@router.get("/{document_id}/versions")
async def list_document_versions(
    document_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all versions of a document."""
    query = select(DocumentVersion).where(
        DocumentVersion.document_id == document_id
    ).options(
        joinedload(DocumentVersion.created_by)
    ).order_by(
        DocumentVersion.major_version.desc(),
        DocumentVersion.minor_version.desc()
    )

    result = await db.execute(query)
    versions = result.scalars().all()

    return {
        "versions": [
            {
                "id": v.id,
                "version_number": v.version_number,
                "change_summary": v.change_summary,
                "is_current": v.is_current,
                "file_url": v.file_url,
                "created_by": {
                    "id": v.created_by.id,
                    "name": f"{v.created_by.first_name} {v.created_by.last_name}"
                } if v.created_by else None,
                "created_at": v.created_at.isoformat()
            }
            for v in versions
        ]
    }


@router.post("/{document_id}/approve")
async def approve_document(
    document_id: int,
    approval_notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve a document."""
    query = select(LegalDocument).where(LegalDocument.id == document_id)
    result = await db.execute(query)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status not in [LegalDocumentStatus.draft, LegalDocumentStatus.in_review]:
        raise HTTPException(status_code=400, detail="Document not in reviewable state")

    # Update document
    old_status = document.status
    document.status = LegalDocumentStatus.approved
    document.approved_by_id = staff_user.id
    document.approved_at = datetime.now()

    # Create audit log
    audit_log = DocumentAuditLog(
        document_id=document.id,
        event_type=AuditEventType.approved,
        event_description=f"Document approved by {staff_user.first_name} {staff_user.last_name}",
        old_values={"status": old_status.value},
        new_values={"status": LegalDocumentStatus.approved.value, "approval_notes": approval_notes},
        user_id=staff_user.id,
        user_role=str(staff_user.role)
    )
    db.add(audit_log)

    await db.commit()
    await db.refresh(document)

    return {
        "id": document.id,
        "status": str(document.status),
        "approved_at": document.approved_at.isoformat()
    }


@router.get("/{document_id}/audit-log")
async def get_document_audit_log(
    document_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get audit log for a document."""
    query = select(DocumentAuditLog).where(
        DocumentAuditLog.document_id == document_id
    ).options(
        joinedload(DocumentAuditLog.user)
    ).order_by(
        DocumentAuditLog.created_at.desc()
    ).limit(limit).offset(offset)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "audit_logs": [
            {
                "id": log.id,
                "event_type": str(log.event_type),
                "event_description": log.event_description,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "user": {
                    "id": log.user.id,
                    "name": f"{log.user.first_name} {log.user.last_name}"
                } if log.user else None,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    }
