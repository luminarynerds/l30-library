# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unified Compliance Audit API Endpoints

Provides a consolidated API for the unified compliance audit platform:
- Compliance requirement registry (CRUD + verification)
- Immutable audit trail (query + integrity verification)
- Automated compliance scanning
- Violation management
- Retention policy enforcement
- Staff access logs
- Incident reporting workflow
- Report generation (CIPA, board executive, law enforcement transparency, etc.)
- Compliance officer dashboard
"""

from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...models.unified_compliance_audit import (
    AccessType, ComplianceIncident, ComplianceReport, UnifiedComplianceRequirement,
    ComplianceViolation, DataCategory, ImmutableAuditEntry, IncidentCategory,
    ComplianceIncidentSeverity, IncidentStatus, RegulationType, ReportStatus, ReportType,
    RequirementStatus, RetentionAction, RetentionPolicyRule, StaffAccessLog,
    VerificationMethod, ViolationSeverity, ViolationStatus,
)
from ...models.user import User, UserRole
from ...services.unified_compliance_service import UnifiedComplianceService
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(
    prefix="/unified-compliance",
    tags=["unified-compliance-audit"],
)


# ============================================================================
# Pydantic Schemas
# ============================================================================

class ComplianceRequirementCreate(BaseModel):
    regulation_type: str
    regulation_citation: Optional[str] = None
    regulation_url: Optional[str] = None
    requirement_code: str
    requirement_title: str
    requirement_description: str
    applies_to_minors: bool = False
    implementation_description: Optional[str] = None
    verification_method: Optional[str] = None
    verification_frequency_days: int = 90
    risk_if_non_compliant: Optional[str] = None
    penalty_description: Optional[str] = None
    state_code: Optional[str] = None
    notes: Optional[str] = None


class ComplianceRequirementUpdate(BaseModel):
    status: Optional[str] = None
    implementation_description: Optional[str] = None
    implementation_date: Optional[date] = None
    verification_method: Optional[str] = None
    verification_frequency_days: Optional[int] = None
    risk_if_non_compliant: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class ViolationUpdate(BaseModel):
    status: Optional[str] = None
    assigned_to_id: Optional[int] = None
    remediation_plan: Optional[str] = None
    remediation_deadline: Optional[date] = None
    remediation_notes: Optional[str] = None
    root_cause: Optional[str] = None


class IncidentCreate(BaseModel):
    category: str
    severity: str
    title: str
    description: str
    discovery_date: Optional[datetime] = None
    affected_systems: List[str] = []
    affected_data_types: List[str] = []
    affected_records_count: int = 0
    affected_individuals_count: int = 0
    involves_minors: bool = False
    regulations_implicated: List[str] = []


class IncidentStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class RetentionRuleCreate(BaseModel):
    rule_name: str
    rule_description: Optional[str] = None
    data_category: str
    target_table: str
    target_conditions: dict = {}
    retention_days: int
    retention_basis: Optional[str] = None
    expiry_action: str
    regulation_type: Optional[str] = None
    regulation_citation: Optional[str] = None
    state_code: Optional[str] = None
    execution_frequency_hours: int = 24
    notes: Optional[str] = None


class ReportGenerateRequest(BaseModel):
    report_type: str
    period_start: date
    period_end: date


class PaginatedResponse(BaseModel):
    total: int
    page: int
    page_size: int
    total_pages: int


# ============================================================================
# Compliance Officer Dashboard
# ============================================================================

@router.get("/dashboard")
async def get_compliance_officer_dashboard(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get unified compliance officer dashboard.

    Returns aggregated data from all compliance subsystems:
    - Overall compliance score
    - Requirement status by regulation
    - Open violations and incidents
    - Staff access flags
    - Law enforcement request status
    - Upcoming deadlines
    """
    dashboard = await UnifiedComplianceService.get_officer_dashboard(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
    )
    return {"status": "success", "data": dashboard}


# ============================================================================
# Compliance Requirements
# ============================================================================

@router.get("/requirements")
async def list_requirements(
    regulation_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    state_code: Optional[str] = Query(None),
    is_active: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List compliance requirements with filtering."""
    query = select(UnifiedComplianceRequirement).where(
        and_(
            UnifiedComplianceRequirement.organization_id == (current_user.home_library_system_id or 1),
            UnifiedComplianceRequirement.is_active == is_active,
        )
    )

    if regulation_type:
        query = query.where(
            UnifiedComplianceRequirement.regulation_type == regulation_type
        )
    if status_filter:
        query = query.where(UnifiedComplianceRequirement.status == status_filter)
    if state_code:
        query = query.where(UnifiedComplianceRequirement.state_code == state_code)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Paginate
    query = query.order_by(
        UnifiedComplianceRequirement.regulation_type,
        UnifiedComplianceRequirement.requirement_code,
    )
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    requirements = result.scalars().all()

    items = [
        {
            "id": r.id,
            "regulation_type": str(r.regulation_type),
            "regulation_citation": r.regulation_citation,
            "requirement_code": r.requirement_code,
            "requirement_title": r.requirement_title,
            "requirement_description": r.requirement_description,
            "applies_to_minors": r.applies_to_minors,
            "status": str(r.status),
            "implementation_description": r.implementation_description,
            "implementation_date": r.implementation_date.isoformat() if r.implementation_date else None,
            "verification_method": str(r.verification_method) if r.verification_method else None,
            "last_verified_date": r.last_verified_date.isoformat() if r.last_verified_date else None,
            "next_verification_due": r.next_verification_due.isoformat() if r.next_verification_due else None,
            "verification_frequency_days": r.verification_frequency_days,
            "risk_score": r.risk_score,
            "state_code": r.state_code,
            "is_active": r.is_active,
        }
        for r in requirements
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/requirements")
async def create_requirement(
    data: ComplianceRequirementCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new compliance requirement."""
    reg_type = RegulationType(data.regulation_type)
    ver_method = VerificationMethod(data.verification_method) if data.verification_method else None

    req = UnifiedComplianceRequirement(
        organization_id=(current_user.home_library_system_id or 1),
        regulation_type=reg_type,
        regulation_citation=data.regulation_citation,
        regulation_url=data.regulation_url,
        requirement_code=data.requirement_code,
        requirement_title=data.requirement_title,
        requirement_description=data.requirement_description,
        applies_to_minors=data.applies_to_minors,
        status=RequirementStatus.not_implemented,
        implementation_description=data.implementation_description,
        verification_method=ver_method,
        verification_frequency_days=data.verification_frequency_days,
        risk_if_non_compliant=data.risk_if_non_compliant,
        penalty_description=data.penalty_description,
        state_code=data.state_code,
        notes=data.notes,
    )
    db.add(req)

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="requirement_created",
        action_category="compliance_management",
        resource_type="compliance_requirement",
        resource_description=f"{data.regulation_type}: {data.requirement_code}",
    )

    await db.commit()
    await db.refresh(req)
    return {"status": "success", "data": {"id": req.id}, "message": "Requirement created"}


@router.put("/requirements/{requirement_id}")
async def update_requirement(
    requirement_id: int,
    data: ComplianceRequirementUpdate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a compliance requirement."""
    result = await db.execute(
        select(UnifiedComplianceRequirement).where(
            and_(
                UnifiedComplianceRequirement.id == requirement_id,
                UnifiedComplianceRequirement.organization_id == (current_user.home_library_system_id or 1),
            )
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    old_status = str(req.status)

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "status" and value:
            value = RequirementStatus(value)
        if key == "verification_method" and value:
            value = VerificationMethod(value)
        if hasattr(req, key):
            setattr(req, key, value)

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="requirement_updated",
        action_category="compliance_management",
        resource_type="compliance_requirement",
        resource_id=str(requirement_id),
        old_value={"status": old_status},
        new_value=update_data,
    )

    await db.commit()
    return {"status": "success", "message": "Requirement updated"}


@router.post("/requirements/{requirement_id}/verify")
async def verify_requirement(
    requirement_id: int,
    notes: Optional[str] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record verification of a compliance requirement."""
    result = await db.execute(
        select(UnifiedComplianceRequirement).where(
            and_(
                UnifiedComplianceRequirement.id == requirement_id,
                UnifiedComplianceRequirement.organization_id == (current_user.home_library_system_id or 1),
            )
        )
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    today = date.today()
    req.status = RequirementStatus.verified
    req.last_verified_date = today
    req.last_verified_by_id = current_user.id
    req.next_verification_due = today + timedelta(days=req.verification_frequency_days)
    if notes:
        req.notes = notes

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="requirement_verified",
        action_category="compliance_verification",
        resource_type="compliance_requirement",
        resource_id=str(requirement_id),
        resource_description=req.requirement_title,
    )

    await db.commit()
    return {
        "status": "success",
        "message": "Requirement verified",
        "data": {
            "next_verification_due": req.next_verification_due.isoformat(),
        },
    }


# ============================================================================
# Audit Trail
# ============================================================================

@router.get("/audit-trail")
async def query_audit_trail(
    actor_id: Optional[int] = Query(None),
    resource_type: Optional[str] = Query(None),
    resource_id: Optional[str] = Query(None),
    action_category: Optional[str] = Query(None),
    data_category: Optional[str] = Query(None),
    involves_minor: Optional[bool] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Query the immutable audit trail.

    Supports filtering by actor, resource, category, date range, etc.
    Provides who accessed what, when, and why.
    """
    query = select(ImmutableAuditEntry).where(
        ImmutableAuditEntry.organization_id == (current_user.home_library_system_id or 1)
    )

    if actor_id:
        query = query.where(ImmutableAuditEntry.actor_id == actor_id)
    if resource_type:
        query = query.where(ImmutableAuditEntry.resource_type == resource_type)
    if resource_id:
        query = query.where(ImmutableAuditEntry.resource_id == resource_id)
    if action_category:
        query = query.where(ImmutableAuditEntry.action_category == action_category)
    if data_category:
        query = query.where(ImmutableAuditEntry.data_category == data_category)
    if involves_minor is not None:
        query = query.where(ImmutableAuditEntry.involves_minor == involves_minor)

    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.where(ImmutableAuditEntry.created_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        query = query.where(ImmutableAuditEntry.created_at <= end_dt)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(ImmutableAuditEntry.created_at))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    entries = result.scalars().all()

    items = [
        {
            "id": e.id,
            "sequence_number": e.sequence_number,
            "entry_hash": e.entry_hash[:16] + "...",
            "actor_id": e.actor_id,
            "actor_role": e.actor_role,
            "actor_email": e.actor_email,
            "action": e.action,
            "action_category": e.action_category,
            "resource_type": e.resource_type,
            "resource_id": e.resource_id,
            "resource_description": e.resource_description,
            "justification": e.justification,
            "data_category": str(e.data_category) if e.data_category else None,
            "involves_minor": e.involves_minor,
            "involves_pii": e.involves_pii,
            "ip_address": e.ip_address,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in entries
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/audit-trail/verify-integrity")
async def verify_audit_integrity(
    start_sequence: int = Query(1, ge=1),
    end_sequence: Optional[int] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify the integrity of the tamper-evident audit chain.

    Returns whether the hash chain is intact or has been tampered with.
    """
    result = await UnifiedComplianceService.verify_audit_chain_integrity(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        start_sequence=start_sequence,
        end_sequence=end_sequence,
    )
    return {"status": "success", "data": result}


# ============================================================================
# Compliance Scanning
# ============================================================================

@router.post("/scan")
async def run_compliance_scan(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Run automated compliance scan across all requirements.

    Checks for overdue verifications, expired certifications, lapsed
    insurance, overdue inspections, and retention policy violations.
    """
    scan_result = await UnifiedComplianceService.run_compliance_scan(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
    )

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="compliance_scan_executed",
        action_category="compliance_scanning",
        resource_type="compliance_scan",
        resource_id=scan_result["scan_id"],
        resource_description=f"Found {scan_result['violations_found']} violations",
    )

    await db.commit()
    return {"status": "success", "data": scan_result}


# ============================================================================
# Violations
# ============================================================================

@router.get("/violations")
async def list_violations(
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    requirement_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List compliance violations with filtering."""
    query = select(ComplianceViolation).where(
        ComplianceViolation.organization_id == (current_user.home_library_system_id or 1)
    )
    if severity:
        query = query.where(ComplianceViolation.severity == severity)
    if status_filter:
        query = query.where(ComplianceViolation.status == status_filter)
    if requirement_id:
        query = query.where(ComplianceViolation.requirement_id == requirement_id)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(ComplianceViolation.detected_at))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    violations = result.scalars().all()

    items = [
        {
            "id": v.id,
            "requirement_id": v.requirement_id,
            "title": v.title,
            "description": v.description,
            "severity": str(v.severity),
            "status": str(v.status),
            "detected_at": v.detected_at.isoformat() if v.detected_at else None,
            "detected_by": v.detected_by,
            "scan_id": v.scan_id,
            "affected_records_count": v.affected_records_count,
            "involves_minors": v.involves_minors,
            "assigned_to_id": v.assigned_to_id,
            "remediation_plan": v.remediation_plan,
            "remediation_deadline": v.remediation_deadline.isoformat() if v.remediation_deadline else None,
            "root_cause": v.root_cause,
            "risk_score": v.risk_score,
        }
        for v in violations
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.put("/violations/{violation_id}")
async def update_violation(
    violation_id: int,
    data: ViolationUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a compliance violation (status, remediation plan, etc.)."""
    result = await db.execute(
        select(ComplianceViolation).where(
            and_(
                ComplianceViolation.id == violation_id,
                ComplianceViolation.organization_id == (current_user.home_library_system_id or 1),
            )
        )
    )
    violation = result.scalar_one_or_none()
    if not violation:
        raise HTTPException(status_code=404, detail="Violation not found")

    old_status = str(violation.status)
    update_data = data.model_dump(exclude_unset=True)

    for key, value in update_data.items():
        if key == "status" and value:
            value = ViolationStatus(value)
            if value == ViolationStatus.resolved:
                violation.remediated_at = datetime.now(timezone.utc)
        if hasattr(violation, key):
            setattr(violation, key, value)

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="violation_updated",
        action_category="violation_management",
        resource_type="compliance_violation",
        resource_id=str(violation_id),
        old_value={"status": old_status},
        new_value=update_data,
    )

    await db.commit()
    return {"status": "success", "message": "Violation updated"}


# ============================================================================
# Retention Policies
# ============================================================================

@router.get("/retention-rules")
async def list_retention_rules(
    is_active: bool = Query(True),
    data_category: Optional[str] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List data retention policy rules."""
    query = select(RetentionPolicyRule).where(
        and_(
            RetentionPolicyRule.organization_id == (current_user.home_library_system_id or 1),
            RetentionPolicyRule.is_active == is_active,
        )
    )
    if data_category:
        query = query.where(RetentionPolicyRule.data_category == data_category)

    result = await db.execute(query.order_by(RetentionPolicyRule.rule_name))
    rules = result.scalars().all()

    items = [
        {
            "id": r.id,
            "rule_name": r.rule_name,
            "rule_description": r.rule_description,
            "data_category": str(r.data_category),
            "target_table": r.target_table,
            "retention_days": r.retention_days,
            "retention_basis": r.retention_basis,
            "expiry_action": str(r.expiry_action),
            "regulation_type": str(r.regulation_type) if r.regulation_type else None,
            "regulation_citation": r.regulation_citation,
            "state_code": r.state_code,
            "is_active": r.is_active,
            "last_executed_at": r.last_executed_at.isoformat() if r.last_executed_at else None,
            "next_execution_at": r.next_execution_at.isoformat() if r.next_execution_at else None,
            "execution_frequency_hours": r.execution_frequency_hours,
        }
        for r in rules
    ]

    return {"status": "success", "data": {"items": items, "total": len(items)}}


@router.post("/retention-rules")
async def create_retention_rule(
    data: RetentionRuleCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new data retention policy rule."""
    rule = RetentionPolicyRule(
        organization_id=(current_user.home_library_system_id or 1),
        rule_name=data.rule_name,
        rule_description=data.rule_description,
        data_category=DataCategory(data.data_category),
        target_table=data.target_table,
        target_conditions=data.target_conditions,
        retention_days=data.retention_days,
        retention_basis=data.retention_basis,
        expiry_action=RetentionAction(data.expiry_action),
        regulation_type=RegulationType(data.regulation_type) if data.regulation_type else None,
        regulation_citation=data.regulation_citation,
        state_code=data.state_code,
        execution_frequency_hours=data.execution_frequency_hours,
        approved_by_id=current_user.id,
        approved_at=datetime.now(timezone.utc),
        notes=data.notes,
    )
    db.add(rule)

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="retention_rule_created",
        action_category="retention_management",
        resource_type="retention_policy_rule",
        resource_description=data.rule_name,
    )

    await db.commit()
    await db.refresh(rule)
    return {"status": "success", "data": {"id": rule.id}, "message": "Retention rule created"}


@router.post("/retention-rules/enforce")
async def enforce_retention_policies(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Execute all due retention policies."""
    result = await UnifiedComplianceService.enforce_retention_policies(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
    )

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="retention_enforcement_executed",
        action_category="retention_management",
        resource_type="retention_enforcement",
        resource_description=f"Executed {result['rules_executed']} rules",
    )

    await db.commit()
    return {"status": "success", "data": result}


# ============================================================================
# Staff Access Logs
# ============================================================================

@router.get("/staff-access")
async def query_staff_access_logs(
    staff_id: Optional[int] = Query(None),
    data_category: Optional[str] = Query(None),
    access_type: Optional[str] = Query(None),
    is_flagged: Optional[bool] = Query(None),
    target_patron_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Query staff data access logs."""
    query = select(StaffAccessLog).where(
        StaffAccessLog.organization_id == (current_user.home_library_system_id or 1)
    )

    if staff_id:
        query = query.where(StaffAccessLog.staff_id == staff_id)
    if data_category:
        query = query.where(StaffAccessLog.data_category == data_category)
    if access_type:
        query = query.where(StaffAccessLog.access_type == access_type)
    if is_flagged is not None:
        query = query.where(StaffAccessLog.is_flagged == is_flagged)
    if target_patron_id:
        query = query.where(StaffAccessLog.target_patron_id == target_patron_id)
    if start_date:
        start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        query = query.where(StaffAccessLog.accessed_at >= start_dt)
    if end_date:
        end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
        query = query.where(StaffAccessLog.accessed_at <= end_dt)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(StaffAccessLog.accessed_at))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    logs = result.scalars().all()

    items = [
        {
            "id": l.id,
            "staff_id": l.staff_id,
            "staff_role": l.staff_role,
            "access_type": str(l.access_type) if l.access_type else None,
            "data_category": str(l.data_category) if l.data_category else None,
            "resource_type": l.resource_type,
            "resource_id": l.resource_id,
            "resource_description": l.resource_description,
            "target_patron_id": l.target_patron_id,
            "target_is_minor": l.target_is_minor,
            "justification": l.justification,
            "records_accessed_count": l.records_accessed_count,
            "ip_address": l.ip_address,
            "is_after_hours": l.is_after_hours,
            "is_bulk_access": l.is_bulk_access,
            "is_flagged": l.is_flagged,
            "flag_reason": l.flag_reason,
            "accessed_at": l.accessed_at.isoformat() if l.accessed_at else None,
        }
        for l in logs
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.get("/staff-access/summary")
async def get_staff_access_summary(
    staff_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated staff access summary for compliance review."""
    summary = await UnifiedComplianceService.get_staff_access_summary(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        staff_id=staff_id,
        start_date=start_date,
        end_date=end_date,
    )
    return {"status": "success", "data": summary}


# ============================================================================
# Incident Reporting
# ============================================================================

@router.get("/incidents")
async def list_incidents(
    severity: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List compliance incidents."""
    query = select(ComplianceIncident).where(
        ComplianceIncident.organization_id == (current_user.home_library_system_id or 1)
    )
    if severity:
        query = query.where(ComplianceIncident.severity == severity)
    if status_filter:
        query = query.where(ComplianceIncident.status == status_filter)
    if category:
        query = query.where(ComplianceIncident.category == category)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(ComplianceIncident.reported_at))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    incidents = result.scalars().all()

    items = [
        {
            "id": i.id,
            "incident_number": i.incident_number,
            "category": str(i.category),
            "severity": str(i.severity),
            "status": str(i.status),
            "title": i.title,
            "description": i.description,
            "discovery_date": i.discovery_date.isoformat() if i.discovery_date else None,
            "reported_at": i.reported_at.isoformat() if i.reported_at else None,
            "involves_minors": i.involves_minors,
            "affected_records_count": i.affected_records_count,
            "affected_individuals_count": i.affected_individuals_count,
            "notification_required": i.notification_required,
            "notification_sent": i.notification_sent,
            "notification_deadline": i.notification_deadline.isoformat() if i.notification_deadline else None,
            "assigned_to_id": i.assigned_to_id,
            "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
        }
        for i in incidents
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/incidents")
async def create_incident(
    data: IncidentCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new compliance incident report."""
    incident = await UnifiedComplianceService.create_incident(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        reported_by_id=current_user.id,
        category=IncidentCategory(data.category),
        severity=ComplianceIncidentSeverity(data.severity),
        title=data.title,
        description=data.description,
        discovery_date=data.discovery_date,
        affected_systems=data.affected_systems,
        affected_data_types=data.affected_data_types,
        affected_records_count=data.affected_records_count,
        affected_individuals_count=data.affected_individuals_count,
        involves_minors=data.involves_minors,
        regulations_implicated=data.regulations_implicated,
    )

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="incident_reported",
        action_category="incident_management",
        resource_type="compliance_incident",
        resource_id=str(incident.id),
        resource_description=f"{data.severity}: {data.title}",
    )

    await db.commit()
    return {
        "status": "success",
        "data": {
            "id": incident.id,
            "incident_number": incident.incident_number,
        },
        "message": "Incident reported",
    }


@router.put("/incidents/{incident_id}/status")
async def update_incident_status(
    incident_id: int,
    data: IncidentStatusUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update the status of a compliance incident."""
    await UnifiedComplianceService.update_incident_status(
        db=db,
        incident_id=incident_id,
        new_status=IncidentStatus(data.status),
        updated_by_id=current_user.id,
        notes=data.notes,
    )

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="incident_status_updated",
        action_category="incident_management",
        resource_type="compliance_incident",
        resource_id=str(incident_id),
        new_value={"status": data.status},
    )

    await db.commit()
    return {"status": "success", "message": f"Incident status updated to {data.status}"}


# ============================================================================
# Reports
# ============================================================================

@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List generated compliance reports."""
    query = select(ComplianceReport).where(
        ComplianceReport.organization_id == (current_user.home_library_system_id or 1)
    )
    if report_type:
        query = query.where(ComplianceReport.report_type == report_type)
    if status_filter:
        query = query.where(ComplianceReport.status == status_filter)

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(ComplianceReport.generated_at))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    reports = result.scalars().all()

    items = [
        {
            "id": r.id,
            "report_type": str(r.report_type),
            "title": r.title,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "status": str(r.status),
            "compliance_score": r.compliance_score,
            "total_requirements": r.total_requirements,
            "compliant_count": r.compliant_count,
            "non_compliant_count": r.non_compliant_count,
            "violations_count": r.violations_count,
            "incidents_count": r.incidents_count,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
            "summary": r.summary,
        }
        for r in reports
    ]

    return {
        "status": "success",
        "data": {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        },
    }


@router.post("/reports/generate")
async def generate_report(
    data: ReportGenerateRequest,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a compliance report.

    Supported types: cipa_erate, board_executive, law_enforcement_transparency,
    staff_access_review, incident_summary, violation_summary, data_retention,
    coppa_annual, ferpa_audit, state_compliance, full_audit.
    """
    report = await UnifiedComplianceService.generate_report(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        report_type=ReportType(data.report_type),
        period_start=data.period_start,
        period_end=data.period_end,
        generated_by_id=current_user.id,
    )

    await UnifiedComplianceService.create_audit_entry(
        db=db,
        organization_id=(current_user.home_library_system_id or 1),
        actor_id=current_user.id,
        actor_role=str(current_user.role),
        actor_email=current_user.email,
        action="report_generated",
        action_category="reporting",
        resource_type="compliance_report",
        resource_id=str(report.id),
        resource_description=report.title,
    )

    await db.commit()
    return {
        "status": "success",
        "data": {
            "id": report.id,
            "title": report.title,
            "compliance_score": report.compliance_score,
        },
        "message": "Report generated",
    }


@router.get("/reports/{report_id}")
async def get_report_detail(
    report_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get full report details including data."""
    result = await db.execute(
        select(ComplianceReport).where(
            and_(
                ComplianceReport.id == report_id,
                ComplianceReport.organization_id == (current_user.home_library_system_id or 1),
            )
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "status": "success",
        "data": {
            "id": report.id,
            "report_type": str(report.report_type),
            "title": report.title,
            "period_start": report.period_start.isoformat(),
            "period_end": report.period_end.isoformat(),
            "status": str(report.status),
            "report_data": report.report_data,
            "summary": report.summary,
            "recommendations": report.recommendations,
            "compliance_score": report.compliance_score,
            "total_requirements": report.total_requirements,
            "compliant_count": report.compliant_count,
            "non_compliant_count": report.non_compliant_count,
            "violations_count": report.violations_count,
            "incidents_count": report.incidents_count,
            "generated_at": report.generated_at.isoformat() if report.generated_at else None,
            "reviewed_at": report.reviewed_at.isoformat() if report.reviewed_at else None,
            "approved_at": report.approved_at.isoformat() if report.approved_at else None,
            "submitted_to": report.submitted_to,
            "submitted_at": report.submitted_at.isoformat() if report.submitted_at else None,
        },
    }
