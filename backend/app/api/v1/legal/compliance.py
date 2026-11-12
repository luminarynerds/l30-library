# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Legal Compliance API - Compliance Tracking Endpoints

Provides endpoints for:
- Compliance requirement management
- Compliance status tracking
- Checklist management
- Document-requirement linking
"""
from datetime import date, datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ....core.database import get_db
from ....models.legal_compliance import (
    LegalComplianceRequirement, ComplianceDocumentLink, ComplianceChecklistItem,
    RequirementType, ComplianceStatus, ComplianceAlert, LegalAlertSeverity, AlertStatus
)
from ....models.user import User
from ..dependencies import require_staff

router = APIRouter(prefix="/legal/compliance", tags=["legal-compliance"])


@router.get("/requirements")
async def list_requirements(
    status: Optional[ComplianceStatus] = None,
    requirement_type: Optional[RequirementType] = None,
    risk_level: Optional[str] = None,
    upcoming_deadline_days: Optional[int] = None,
    search: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List compliance requirements with filtering."""
    query = select(LegalComplianceRequirement).options(
        joinedload(LegalComplianceRequirement.compliance_officer),
        selectinload(LegalComplianceRequirement.document_links)
    )

    filters = []
    if status:
        filters.append(LegalComplianceRequirement.compliance_status == status)
    if requirement_type:
        filters.append(LegalComplianceRequirement.requirement_type == requirement_type)
    if risk_level:
        filters.append(LegalComplianceRequirement.risk_level == risk_level)
    if upcoming_deadline_days:
        target_date = date.today() + timedelta(days=upcoming_deadline_days)
        filters.append(
            and_(
                LegalComplianceRequirement.deadline_date.isnot(None),
                LegalComplianceRequirement.deadline_date <= target_date,
                LegalComplianceRequirement.deadline_date >= date.today()
            )
        )
    if search:
        search_pattern = f"%{search}%"
        filters.append(
            or_(
                LegalComplianceRequirement.title.ilike(search_pattern),
                LegalComplianceRequirement.description.ilike(search_pattern),
                LegalComplianceRequirement.requirement_code.ilike(search_pattern)
            )
        )

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(LegalComplianceRequirement.deadline_date.asc().nullslast())
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    requirements = result.scalars().all()

    return {
        "requirements": [
            {
                "id": req.id,
                "title": req.title,
                "requirement_code": req.requirement_code,
                "requirement_type": str(req.requirement_type),
                "compliance_status": str(req.compliance_status),
                "risk_level": req.risk_level,
                "effective_date": req.effective_date.isoformat(),
                "deadline_date": req.deadline_date.isoformat() if req.deadline_date else None,
                "next_assessment_date": req.next_assessment_date.isoformat() if req.next_assessment_date else None,
                "compliance_officer": {
                    "id": req.compliance_officer.id,
                    "name": f"{req.compliance_officer.first_name} {req.compliance_officer.last_name}"
                } if req.compliance_officer else None,
                "document_count": len(req.document_links),
                "created_at": req.created_at.isoformat()
            }
            for req in requirements
        ],
        "total": len(requirements),
        "limit": limit,
        "offset": offset
    }


@router.get("/requirements/{requirement_id}")
async def get_requirement(
    requirement_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed compliance requirement."""
    query = select(LegalComplianceRequirement).where(
        LegalComplianceRequirement.id == requirement_id
    ).options(
        joinedload(LegalComplianceRequirement.compliance_officer),
        joinedload(LegalComplianceRequirement.created_by),
        selectinload(LegalComplianceRequirement.document_links),
        selectinload(LegalComplianceRequirement.checklist_item_records)
    )

    result = await db.execute(query)
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    # Calculate completion percentage
    total_items = len(requirement.checklist_item_records)
    completed_items = sum(1 for item in requirement.checklist_item_records if item.is_completed)
    completion_percentage = (completed_items / total_items * 100) if total_items > 0 else 0

    return {
        "id": requirement.id,
        "title": requirement.title,
        "requirement_code": requirement.requirement_code,
        "requirement_type": str(requirement.requirement_type),
        "description": requirement.description,
        "legal_citation": requirement.legal_citation,
        "jurisdiction": requirement.jurisdiction,
        "compliance_status": str(requirement.compliance_status),
        "effective_date": requirement.effective_date.isoformat(),
        "deadline_date": requirement.deadline_date.isoformat() if requirement.deadline_date else None,
        "last_assessed_date": requirement.last_assessed_date.isoformat() if requirement.last_assessed_date else None,
        "next_assessment_date": requirement.next_assessment_date.isoformat() if requirement.next_assessment_date else None,
        "responsible_department": requirement.responsible_department,
        "risk_level": requirement.risk_level,
        "penalties_for_noncompliance": requirement.penalties_for_noncompliance,
        "implementation_notes": requirement.implementation_notes,
        "evidence_required": requirement.evidence_required,
        "compliance_officer": {
            "id": requirement.compliance_officer.id,
            "name": f"{requirement.compliance_officer.first_name} {requirement.compliance_officer.last_name}"
        } if requirement.compliance_officer else None,
        "checklist_completion": {
            "total": total_items,
            "completed": completed_items,
            "percentage": completion_percentage
        },
        "created_at": requirement.created_at.isoformat(),
        "updated_at": requirement.updated_at.isoformat() if requirement.updated_at else None
    }


@router.post("/requirements")
async def create_requirement(
    title: str,
    requirement_type: RequirementType,
    description: str,
    effective_date: date,
    legal_citation: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    deadline_date: Optional[date] = None,
    risk_level: Optional[str] = None,
    responsible_department: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new compliance requirement."""
    # Generate requirement code
    result = await db.execute(select(func.count(LegalComplianceRequirement.id)))
    count = result.scalar()
    requirement_code = f"REQ-{requirement_type.value.upper()[:3]}-{count + 1:05d}"

    requirement = LegalComplianceRequirement(
        title=title,
        requirement_code=requirement_code,
        requirement_type=requirement_type,
        description=description,
        legal_citation=legal_citation,
        jurisdiction=jurisdiction,
        effective_date=effective_date,
        deadline_date=deadline_date,
        risk_level=risk_level,
        responsible_department=responsible_department,
        compliance_officer_id=staff_user.id,
        created_by_id=staff_user.id
    )

    db.add(requirement)
    await db.commit()
    await db.refresh(requirement)

    return {
        "id": requirement.id,
        "requirement_code": requirement.requirement_code,
        "title": requirement.title,
        "compliance_status": str(requirement.compliance_status),
        "created_at": requirement.created_at.isoformat()
    }


@router.put("/requirements/{requirement_id}/status")
async def update_requirement_status(
    requirement_id: int,
    compliance_status: ComplianceStatus,
    assessment_notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update compliance status of a requirement."""
    query = select(LegalComplianceRequirement).where(LegalComplianceRequirement.id == requirement_id)
    result = await db.execute(query)
    requirement = result.scalar_one_or_none()

    if not requirement:
        raise HTTPException(status_code=404, detail="Requirement not found")

    old_status = requirement.compliance_status
    requirement.compliance_status = compliance_status
    requirement.last_assessed_date = date.today()

    if assessment_notes:
        requirement.implementation_notes = assessment_notes

    # Set next assessment date (90 days from now)
    requirement.next_assessment_date = date.today() + timedelta(days=90)

    await db.commit()
    await db.refresh(requirement)

    return {
        "id": requirement.id,
        "old_status": old_status.value,
        "new_status": str(requirement.compliance_status),
        "last_assessed_date": requirement.last_assessed_date.isoformat(),
        "next_assessment_date": requirement.next_assessment_date.isoformat()
    }


@router.post("/requirements/{requirement_id}/documents")
async def link_document_to_requirement(
    requirement_id: int,
    document_id: int,
    relationship_type: str = "implements",
    notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Link a document to a compliance requirement."""
    # Check if link already exists
    existing = await db.execute(
        select(ComplianceDocumentLink).where(
            and_(
                ComplianceDocumentLink.requirement_id == requirement_id,
                ComplianceDocumentLink.document_id == document_id
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Link already exists")

    link = ComplianceDocumentLink(
        requirement_id=requirement_id,
        document_id=document_id,
        relationship_type=relationship_type,
        notes=notes,
        created_by_id=staff_user.id
    )

    db.add(link)
    await db.commit()
    await db.refresh(link)

    return {
        "id": link.id,
        "requirement_id": requirement_id,
        "document_id": document_id,
        "relationship_type": relationship_type,
        "created_at": link.created_at.isoformat()
    }


@router.get("/requirements/{requirement_id}/checklist")
async def get_requirement_checklist(
    requirement_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get checklist items for a requirement."""
    query = select(ComplianceChecklistItem).where(
        ComplianceChecklistItem.requirement_id == requirement_id
    ).options(
        joinedload(ComplianceChecklistItem.completed_by)
    ).order_by(ComplianceChecklistItem.item_order)

    result = await db.execute(query)
    items = result.scalars().all()

    return {
        "checklist_items": [
            {
                "id": item.id,
                "item_text": item.item_text,
                "item_order": item.item_order,
                "is_completed": item.is_completed,
                "completed_date": item.completed_date.isoformat() if item.completed_date else None,
                "completed_by": {
                    "id": item.completed_by.id,
                    "name": f"{item.completed_by.first_name} {item.completed_by.last_name}"
                } if item.completed_by else None,
                "evidence_description": item.evidence_description,
                "evidence_file_url": item.evidence_file_url,
                "notes": item.notes
            }
            for item in items
        ]
    }


@router.post("/requirements/{requirement_id}/checklist")
async def add_checklist_item(
    requirement_id: int,
    item_text: str,
    item_order: int = 0,
    evidence_description: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add a checklist item to a requirement."""
    item = ComplianceChecklistItem(
        requirement_id=requirement_id,
        item_text=item_text,
        item_order=item_order,
        evidence_description=evidence_description
    )

    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "item_text": item.item_text,
        "item_order": item.item_order,
        "created_at": item.created_at.isoformat()
    }


@router.put("/checklist-items/{item_id}/complete")
async def complete_checklist_item(
    item_id: int,
    evidence_file_url: Optional[str] = None,
    notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a checklist item as completed."""
    query = select(ComplianceChecklistItem).where(ComplianceChecklistItem.id == item_id)
    result = await db.execute(query)
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Checklist item not found")

    item.is_completed = True
    item.completed_date = date.today()
    item.completed_by_id = staff_user.id

    if evidence_file_url:
        item.evidence_file_url = evidence_file_url
    if notes:
        item.notes = notes

    await db.commit()
    await db.refresh(item)

    return {
        "id": item.id,
        "is_completed": item.is_completed,
        "completed_date": item.completed_date.isoformat(),
        "completed_by_id": staff_user.id
    }
