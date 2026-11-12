# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Law Enforcement Request API Endpoints.

SECURITY NOTICE: These endpoints are STRICTLY restricted to users with
DIRECTOR or LEGAL roles. Access attempts by other roles will be logged
and rejected.

This module handles:
- Law enforcement request tracking and management
- Legal review workflow
- Patron data export for compliance
- Immutable audit logging
- Transparency reporting
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.law_enforcement_request import (
    ChecklistItemType,
    LegalReviewStatus,
    RequestType,
    WorkflowStatus,
)
from ...models.user import User, UserRole
from ...schemas.law_enforcement_request import (
    AddNoteRequest,
    AuditLogResponse,
    ChecklistItemResponse,
    ChecklistItemUpdate,
    LawEnforcementRequestCreate,
    LawEnforcementRequestListItem,
    LawEnforcementRequestListResponse,
    LawEnforcementRequestResponse,
    LawEnforcementRequestUpdate,
    LawEnforcementStatsResponse,
    LegalReviewUpdate,
    PatronDataExportRequest,
    PatronDataExportResponse,
    PatronNotificationRecord,
    PatronSummary,
    RenderedTemplate,
    ResponseTemplateCreate,
    ResponseTemplateResponse,
    ResponseTemplateUpdate,
    ResponseUpdate,
    TransparencyReport,
    TransparencyReportRequest,
    WorkflowStatusUpdate,
)
from ...core.authorization import has_permission
from ...services.law_enforcement_service import LawEnforcementService
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/law-enforcement", tags=["law-enforcement"])


# =============================================================================
# Role-Based Access Control
# =============================================================================

# Permission code for law enforcement access
LAW_ENFORCEMENT_PERMISSION = "law_enforcement_access"

# Roles that ALWAYS have access (regardless of permission assignment)
AUTHORIZED_ROLES = {
    UserRole.SUPER_ADMIN,
    UserRole.ADMIN,
    UserRole.DIRECTOR,
    UserRole.LEGAL,
}


async def require_law_enforcement_access(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    # Log access attempt
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("user-agent", "unknown")

    # Check role-based access first
    has_role_access = current_user.role in AUTHORIZED_ROLES

    # Check permission-based access if role doesn't grant access
    has_permission_access = False
    if not has_role_access:
        has_permission_access = await has_permission(
            current_user, LAW_ENFORCEMENT_PERMISSION, db
        )

    if not has_role_access and not has_permission_access:
        # Log unauthorized access attempt
        logger.warning(
            "Unauthorized law enforcement data access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": str(current_user.role),
                "ip_address": client_ip,
                "user_agent": user_agent,
                "endpoint": str(request.url),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access to law enforcement request data is restricted to authorized personnel only",
        )

    access_method = "role" if has_role_access else "permission"
    logger.info(
        "Law enforcement data access granted",
        extra={
            "user_id": current_user.id,
            "user_role": str(current_user.role),
            "access_method": access_method,
            "ip_address": client_ip,
        },
    )

    return current_user


def get_request_metadata(request: Request) -> tuple[Optional[str], Optional[str]]:
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


# =============================================================================
# Request Management Endpoints
# =============================================================================


@router.post(
    "/requests",
    response_model=LawEnforcementRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new law enforcement request",
    description="Log a new law enforcement request for patron data. Creates checklist items and audit trail.",
)
async def create_request(
    request: Request,
    data: LawEnforcementRequestCreate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Create a new law enforcement request."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.create_request(
        data=data,
        created_by=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Get checklist progress
    progress = await service.get_checklist_progress(le_request.id)

    response = LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )

    if le_request.patron:
        response.patron = PatronSummary(
            id=le_request.patron.id,
            first_name=le_request.patron.first_name,
            last_name=le_request.patron.last_name,
            library_card=le_request.patron.library_card,
        )

    return response


@router.get(
    "/requests",
    response_model=LawEnforcementRequestListResponse,
    summary="List law enforcement requests",
    description="List all law enforcement requests with optional filters.",
)
async def list_requests(
    request: Request,
    skip: int = 0,
    limit: int = 50,
    request_type: Optional[RequestType] = None,
    workflow_status: Optional[WorkflowStatus] = None,
    legal_review_status: Optional[LegalReviewStatus] = None,
    year: Optional[int] = None,
    patron_id: Optional[int] = None,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """List law enforcement requests with pagination and filters."""
    service = LawEnforcementService(db)
    requests, total = await service.list_requests(
        skip=skip,
        limit=limit,
        request_type=request_type,
        workflow_status=workflow_status,
        legal_review_status=legal_review_status,
        year=year,
        patron_id=patron_id,
    )

    items = [
        LawEnforcementRequestListItem(
            id=r.id,
            tracking_number=r.tracking_number,
            requesting_agency=r.requesting_agency,
            request_type=r.request_type,
            date_received=r.date_received,
            date_due=r.date_due,
            patron_name_on_request=r.patron_name_on_request,
            legal_review_status=r.legal_review_status,
            workflow_status=r.workflow_status,
        )
        for r in requests
    ]

    return LawEnforcementRequestListResponse(
        items=items,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get(
    "/requests/{request_id}",
    response_model=LawEnforcementRequestResponse,
    summary="Get a law enforcement request",
    description="Get detailed information about a specific law enforcement request.",
)
async def get_request(
    request: Request,
    request_id: int,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific law enforcement request by ID."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.get_request(
        request_id=request_id,
        viewer=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    # Get checklist progress
    progress = await service.get_checklist_progress(le_request.id)

    response = LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )

    if le_request.patron:
        response.patron = PatronSummary(
            id=le_request.patron.id,
            first_name=le_request.patron.first_name,
            last_name=le_request.patron.last_name,
            library_card=le_request.patron.library_card,
        )

    return response


@router.patch(
    "/requests/{request_id}",
    response_model=LawEnforcementRequestResponse,
    summary="Update a law enforcement request",
    description="Update details of a law enforcement request.",
)
async def update_request(
    request: Request,
    request_id: int,
    data: LawEnforcementRequestUpdate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Update a law enforcement request."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.update_request(
        request_id=request_id,
        data=data,
        updated_by=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    progress = await service.get_checklist_progress(le_request.id)

    return LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )


# =============================================================================
# Legal Review Endpoints
# =============================================================================


@router.post(
    "/requests/{request_id}/legal-review",
    response_model=LawEnforcementRequestResponse,
    summary="Update legal review status",
    description="Update the legal review status of a request.",
)
async def update_legal_review(
    request: Request,
    request_id: int,
    data: LegalReviewUpdate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Update the legal review status."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.update_legal_review(
        request_id=request_id,
        data=data,
        reviewer=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    progress = await service.get_checklist_progress(le_request.id)

    return LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )


# =============================================================================
# Workflow Endpoints
# =============================================================================


@router.post(
    "/requests/{request_id}/workflow-status",
    response_model=LawEnforcementRequestResponse,
    summary="Update workflow status",
    description="Update the workflow status of a request.",
)
async def update_workflow_status(
    request: Request,
    request_id: int,
    data: WorkflowStatusUpdate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Update the workflow status."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.update_workflow_status(
        request_id=request_id,
        data=data,
        updated_by=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    progress = await service.get_checklist_progress(le_request.id)

    return LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )


@router.get(
    "/requests/{request_id}/checklist",
    response_model=list[ChecklistItemResponse],
    summary="Get workflow checklist",
    description="Get the workflow checklist for a request.",
)
async def get_checklist(
    request_id: int,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Get the workflow checklist for a request."""
    service = LawEnforcementService(db)
    items = await service.get_checklist(request_id)

    return [
        ChecklistItemResponse(
            id=item.id,
            item_type=item.item_type,
            item_description=item.item_description,
            is_completed=item.is_completed,
            is_required=item.is_required,
            is_applicable=item.is_applicable,
            completed_by_id=item.completed_by_id,
            completed_by_name=(
                f"{item.completed_by.first_name} {item.completed_by.last_name}"
                if item.completed_by
                else None
            ),
            completed_at=item.completed_at,
            completion_notes=item.completion_notes,
            sort_order=item.sort_order,
        )
        for item in items
    ]


@router.patch(
    "/requests/{request_id}/checklist/{item_type}",
    response_model=ChecklistItemResponse,
    summary="Update checklist item",
    description="Update a specific checklist item.",
)
async def update_checklist_item(
    request: Request,
    request_id: int,
    item_type: ChecklistItemType,
    data: ChecklistItemUpdate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Update a checklist item."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)

    if data.is_completed is not None:
        item = await service.update_checklist_item(
            request_id=request_id,
            item_type=item_type,
            is_completed=data.is_completed,
            updated_by=current_user,
            completion_notes=data.completion_notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    else:
        # Just get the item if no update
        items = await service.get_checklist(request_id)
        item = next((i for i in items if i.item_type == item_type), None)

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checklist item not found",
        )

    return ChecklistItemResponse(
        id=item.id,
        item_type=item.item_type,
        item_description=item.item_description,
        is_completed=item.is_completed,
        is_required=item.is_required,
        is_applicable=item.is_applicable,
        completed_by_id=item.completed_by_id,
        completed_by_name=(
            f"{item.completed_by.first_name} {item.completed_by.last_name}"
            if item.completed_by
            else None
        ),
        completed_at=item.completed_at,
        completion_notes=item.completion_notes,
        sort_order=item.sort_order,
    )


# =============================================================================
# Response and Compliance Endpoints
# =============================================================================


@router.post(
    "/requests/{request_id}/response",
    response_model=LawEnforcementRequestResponse,
    summary="Record response sent",
    description="Record that a response was sent to the requesting agency.",
)
async def record_response(
    request: Request,
    request_id: int,
    data: ResponseUpdate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Record the response sent to law enforcement."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    le_request = await service.record_response(
        request_id=request_id,
        data=data,
        responded_by=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    progress = await service.get_checklist_progress(le_request.id)

    return LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )


@router.post(
    "/requests/{request_id}/patron-notification",
    response_model=LawEnforcementRequestResponse,
    summary="Record patron notification",
    description="Record that the affected patron was notified (if legally permitted).",
)
async def record_patron_notification(
    request: Request,
    request_id: int,
    data: PatronNotificationRecord,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Record patron notification."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)

    try:
        le_request = await service.record_patron_notification(
            request_id=request_id,
            notification_method=data.notification_method,
            notified_by=current_user,
            notes=data.notification_notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    if not le_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law enforcement request not found",
        )

    progress = await service.get_checklist_progress(le_request.id)

    return LawEnforcementRequestResponse(
        **{k: v for k, v in le_request.__dict__.items() if not k.startswith("_")},
        checklist_progress=progress,
    )


# =============================================================================
# Data Export Endpoints
# =============================================================================


@router.post(
    "/requests/{request_id}/export-patron-data",
    response_model=PatronDataExportResponse,
    summary="Export patron data for compliance",
    description="Export patron data as required by the law enforcement request.",
)
async def export_patron_data(
    request: Request,
    request_id: int,
    data: PatronDataExportRequest,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Export patron data for a law enforcement request."""
    ip_address, user_agent = get_request_metadata(request)

    # Ensure request_id in path matches body
    if data.request_id != request_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Request ID in path must match request ID in body",
        )

    service = LawEnforcementService(db)

    try:
        export = await service.export_patron_data(
            export_request=data,
            exported_by=current_user,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    return export


# =============================================================================
# Audit Log Endpoints
# =============================================================================


@router.get(
    "/requests/{request_id}/audit-log",
    response_model=list[AuditLogResponse],
    summary="Get audit log",
    description="Get the immutable audit log for a request.",
)
async def get_audit_log(
    request_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Get the audit log for a request."""
    service = LawEnforcementService(db)
    logs = await service.get_audit_log(request_id, skip, limit)

    return [
        AuditLogResponse(
            id=log.id,
            action=log.action,
            performed_by_id=log.performed_by_id,
            performed_by_name=(
                f"{log.performed_by.first_name} {log.performed_by.last_name}"
                if log.performed_by
                else None
            ),
            details=log.details,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log in logs
    ]


@router.post(
    "/requests/{request_id}/notes",
    response_model=AuditLogResponse,
    summary="Add note to request",
    description="Add a note to the request's audit log.",
)
async def add_note(
    request: Request,
    request_id: int,
    data: AddNoteRequest,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Add a note to a request."""
    ip_address, user_agent = get_request_metadata(request)

    service = LawEnforcementService(db)
    audit_log = await service.add_note(
        request_id=request_id,
        note=data.note,
        added_by=current_user,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    return AuditLogResponse(
        id=audit_log.id,
        action=audit_log.action,
        performed_by_id=audit_log.performed_by_id,
        performed_by_name=f"{current_user.first_name} {current_user.last_name}",
        details=audit_log.details,
        ip_address=audit_log.ip_address,
        created_at=audit_log.created_at,
    )


# =============================================================================
# Transparency Reporting Endpoints
# =============================================================================


@router.post(
    "/reports/transparency",
    response_model=TransparencyReport,
    summary="Generate transparency report",
    description="Generate an annual transparency report for law enforcement requests.",
)
async def generate_transparency_report(
    data: TransparencyReportRequest,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Generate annual transparency report."""
    service = LawEnforcementService(db)
    report = await service.generate_transparency_report(
        year=data.year,
        include_details=data.include_details,
    )
    return report


@router.get(
    "/reports/transparency/{year}",
    response_model=TransparencyReport,
    summary="Get transparency report for year",
    description="Get the transparency report for a specific year.",
)
async def get_transparency_report(
    year: int,
    include_details: bool = False,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Get transparency report for a specific year."""
    service = LawEnforcementService(db)
    report = await service.generate_transparency_report(
        year=year,
        include_details=include_details,
    )
    return report


# =============================================================================
# Response Template Endpoints
# =============================================================================


@router.get(
    "/templates",
    response_model=list[ResponseTemplateResponse],
    summary="List response templates",
    description="List all response templates.",
)
async def list_templates(
    template_type: Optional[str] = None,
    active_only: bool = True,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """List response templates."""
    service = LawEnforcementService(db)
    templates = await service.get_templates(
        template_type=template_type,
        active_only=active_only,
    )

    return [
        ResponseTemplateResponse(
            id=t.id,
            name=t.name,
            description=t.description,
            template_type=t.template_type,
            applicable_request_types=t.applicable_request_types,
            subject_template=t.subject_template,
            body_template=t.body_template,
            is_active=t.is_active,
            created_at=t.created_at,
            updated_at=t.updated_at,
        )
        for t in templates
    ]


@router.post(
    "/templates",
    response_model=ResponseTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create response template",
    description="Create a new response template.",
)
async def create_template(
    data: ResponseTemplateCreate,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Create a response template."""
    service = LawEnforcementService(db)
    template = await service.create_template(
        name=data.name,
        description=data.description,
        template_type=data.template_type,
        body_template=data.body_template,
        subject_template=data.subject_template,
        applicable_request_types=data.applicable_request_types,
        created_by=current_user,
    )

    return ResponseTemplateResponse(
        id=template.id,
        name=template.name,
        description=template.description,
        template_type=template.template_type,
        applicable_request_types=template.applicable_request_types,
        subject_template=template.subject_template,
        body_template=template.body_template,
        is_active=template.is_active,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


@router.get(
    "/templates/{template_id}/render/{request_id}",
    response_model=RenderedTemplate,
    summary="Render template for request",
    description="Render a template with data from a specific request.",
)
async def render_template(
    template_id: int,
    request_id: int,
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Render a template with request data."""
    service = LawEnforcementService(db)

    try:
        rendered = await service.render_template(template_id, request_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    return RenderedTemplate(
        subject=rendered["subject"],
        body=rendered["body"],
    )


# =============================================================================
# Statistics Endpoint
# =============================================================================


@router.get(
    "/stats",
    response_model=LawEnforcementStatsResponse,
    summary="Get law enforcement request statistics",
    description="Get summary statistics for law enforcement requests.",
)
async def get_statistics(
    current_user: User = Depends(require_law_enforcement_access),
    db: AsyncSession = Depends(get_db),
):
    """Get overall statistics for law enforcement requests."""
    from sqlalchemy import func

    from ...models.law_enforcement_request import LawEnforcementRequest

    # Total requests
    total_result = await db.execute(
        select(func.count(LawEnforcementRequest.id))
    )
    total = total_result.scalar() or 0

    # Pending review
    pending_result = await db.execute(
        select(func.count(LawEnforcementRequest.id)).where(
            LawEnforcementRequest.legal_review_status == LegalReviewStatus.PENDING_REVIEW
        )
    )
    pending = pending_result.scalar() or 0

    # In progress
    in_progress_result = await db.execute(
        select(func.count(LawEnforcementRequest.id)).where(
            LawEnforcementRequest.workflow_status.in_([
                WorkflowStatus.VALIDATING,
                WorkflowStatus.LEGAL_REVIEW,
                WorkflowStatus.PATRON_NOTIFICATION,
                WorkflowStatus.PREPARING_RESPONSE,
            ])
        )
    )
    in_progress = in_progress_result.scalar() or 0

    # Completed
    completed_result = await db.execute(
        select(func.count(LawEnforcementRequest.id)).where(
            LawEnforcementRequest.workflow_status.in_([
                WorkflowStatus.COMPLETED,
                WorkflowStatus.RESPONSE_SENT,
            ])
        )
    )
    completed = completed_result.scalar() or 0

    # This year
    from datetime import datetime

    current_year = datetime.now().year
    this_year_result = await db.execute(
        select(func.count(LawEnforcementRequest.id)).where(
            func.extract("year", LawEnforcementRequest.date_received) == current_year
        )
    )
    this_year = this_year_result.scalar() or 0

    return LawEnforcementStatsResponse(
        total_requests=total,
        pending_review=pending,
        in_progress=in_progress,
        completed=completed,
        this_year=this_year,
    )


@router.get("/litigation-holds/active-patrons")
async def list_patrons_under_litigation_hold(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List patron IDs with active (non-terminal) law enforcement requests.

    These patrons are excluded from data retention anonymization/deletion.
    Director or legal access required.
    """
    if current_user.role not in [UserRole.DIRECTOR, UserRole.LEGAL, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Director or legal access required")

    from ...services.data_retention_service import get_litigation_hold_patron_ids

    held_ids = await get_litigation_hold_patron_ids(db)

    if not held_ids:
        return {"count": 0, "patrons": []}

    result = await db.execute(
        select(
            User.id,
            User.first_name,
            User.last_name,
            User.library_card,
        ).where(User.id.in_(held_ids))
    )
    patrons = [
        {
            "id": row.id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "library_card": row.library_card,
        }
        for row in result.all()
    ]
    return {"count": len(patrons), "patrons": patrons}
