# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Public Records Request API Endpoints.

Handles FOIA and state public records requests.
Access restricted to STAFF, ADMIN, and SUPER_ADMIN roles.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from app.core.logging import get_logger

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.turnstile import verify_turnstile
from ...models.public_records_request import (
    ExemptionType,
    JurisdictionType,
    PublicRecordsRequestStatus,
    PublicRecordsRequestType,
)
from ...models.user import User, UserRole
from ...services.public_records_service import PublicRecordsService
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/public-records", tags=["public-records"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PublicRecordsRequestCreate(BaseModel):
    request_type: PublicRecordsRequestType
    jurisdiction: JurisdictionType
    requester_name: str = Field(..., min_length=1, max_length=200)
    requester_email: Optional[str] = Field(None, max_length=255)
    requester_phone: Optional[str] = Field(None, max_length=50)
    requester_organization: Optional[str] = Field(None, max_length=255)
    requester_address: Optional[str] = None
    is_media: bool = False
    is_commercial: bool = False
    date_received: datetime
    description: str = Field(..., min_length=10)
    records_date_range_start: Optional[date] = None
    records_date_range_end: Optional[date] = None
    preferred_format: Optional[str] = Field(None, max_length=100)


class PublicRecordsRequestUpdate(BaseModel):
    requester_name: Optional[str] = Field(None, max_length=200)
    requester_email: Optional[str] = Field(None, max_length=255)
    requester_phone: Optional[str] = Field(None, max_length=50)
    requester_organization: Optional[str] = Field(None, max_length=255)
    requester_address: Optional[str] = None
    description: Optional[str] = None
    records_date_range_start: Optional[date] = None
    records_date_range_end: Optional[date] = None
    preferred_format: Optional[str] = Field(None, max_length=100)
    internal_notes: Optional[str] = None


class StatusUpdate(BaseModel):
    status: PublicRecordsRequestStatus
    notes: Optional[str] = None


class AssignmentUpdate(BaseModel):
    assign_to_id: int


class ExtensionRequest(BaseModel):
    additional_days: int = Field(..., ge=1, le=60)
    reason: str = Field(..., min_length=10)


class FeeEstimate(BaseModel):
    pages: int = Field(..., ge=0)
    search_hours: float = Field(..., ge=0)
    review_hours: float = Field(..., ge=0)
    copy_fee_per_page: Optional[Decimal] = None
    search_fee_per_hour: Optional[Decimal] = None
    review_fee_per_hour: Optional[Decimal] = None


class FeeWaiver(BaseModel):
    reason: str = Field(..., min_length=10)


class FeePayment(BaseModel):
    amount: Decimal = Field(..., ge=0)


class RedactionCreate(BaseModel):
    document_name: str = Field(..., min_length=1, max_length=255)
    exemption_type: ExemptionType
    page_number: Optional[int] = None
    section_reference: Optional[str] = Field(None, max_length=255)
    exemption_description: Optional[str] = None
    redaction_description: Optional[str] = None


class ResponseRecord(BaseModel):
    response_method: str = Field(..., max_length=100)
    records_provided_count: int = Field(0, ge=0)
    records_withheld_count: int = Field(0, ge=0)
    response_summary: Optional[str] = None
    denial_reason: Optional[str] = None
    exemptions_cited: Optional[list[str]] = None


class DenialRecord(BaseModel):
    denial_reason: str = Field(..., min_length=10)
    exemptions_cited: list[str] = Field(..., min_items=1)


class AppealRecord(BaseModel):
    notes: Optional[str] = None


class AppealDecision(BaseModel):
    decision: str = Field(..., pattern="^(upheld|overturned|partial)$")
    notes: Optional[str] = None


class NoteAdd(BaseModel):
    note: str = Field(..., min_length=1)


class PublicRecordsRequestResponse(BaseModel):
    id: int
    tracking_number: str
    request_type: str
    jurisdiction: str
    requester_name: str
    requester_organization: Optional[str]
    requester_email: Optional[str]
    is_media: bool
    is_commercial: bool
    date_received: datetime
    date_acknowledged: Optional[datetime]
    description: str
    response_deadline: date
    extended_deadline: Optional[date]
    status: str
    assigned_to_id: Optional[int]
    fee_estimate: Optional[float]
    fee_waived: bool
    fee_paid: Optional[float]
    response_date: Optional[datetime]
    records_provided_count: Optional[int]
    records_withheld_count: Optional[int]
    appeal_filed: bool
    is_overdue: bool
    days_until_deadline: int
    created_at: datetime

    class Config:
        from_attributes = True


class PublicRecordsRequestPublicSubmit(BaseModel):
    requester_name: str = Field(..., min_length=1, max_length=200)
    requester_email: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=4000)

    preferred_format: Optional[str] = Field(default="digital", pattern="^(digital|paper|either)$")
    jurisdiction: Optional[JurisdictionType] = Field(default=JurisdictionType.OHIO)

    # Optional context linkage
    meeting_id: Optional[int] = None
    committee_id: Optional[int] = None

    # Cloudflare Turnstile token from the widget; verified server-side
    turnstile_token: str = Field(..., min_length=1)


class PublicRecordsRequestPublicLogEntry(BaseModel):
    tracking_number: str
    request_type: str
    jurisdiction: str

    # PII-safe requester fields only
    requester_name: str
    requester_organization: Optional[str] = None
    is_media: bool
    is_commercial: bool

    description: str
    date_received: date
    response_deadline: date
    date_completed: Optional[date] = None
    status: str

    meeting_id: Optional[int] = None
    committee_id: Optional[int] = None

    fees_collected: Optional[Decimal] = None

    class Config:
        from_attributes = True


class PublicRecordsRequestSubmissionAck(BaseModel):
    tracking_number: str
    response_deadline: date
    status: str


# =============================================================================
# Helper Functions
# =============================================================================


# =============================================================================
# Endpoints
# =============================================================================


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_request(
    request_data: PublicRecordsRequestCreate,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new public records request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.create_request(
        request_type=request_data.request_type,
        jurisdiction=request_data.jurisdiction,
        requester_name=request_data.requester_name,
        requester_email=request_data.requester_email,
        requester_phone=request_data.requester_phone,
        requester_organization=request_data.requester_organization,
        requester_address=request_data.requester_address,
        is_media=request_data.is_media,
        is_commercial=request_data.is_commercial,
        date_received=request_data.date_received,
        description=request_data.description,
        records_date_range_start=request_data.records_date_range_start,
        records_date_range_end=request_data.records_date_range_end,
        preferred_format=request_data.preferred_format,
        created_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    return {
        "id": prr.id,
        "tracking_number": prr.tracking_number,
        "request_type": str(prr.request_type),
        "jurisdiction": str(prr.jurisdiction),
        "requester_name": prr.requester_name,
        "date_received": prr.date_received.isoformat(),
        "response_deadline": prr.response_deadline.isoformat(),
        "status": str(prr.status),
    }


@router.get("")
async def list_requests(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    request_type: Optional[PublicRecordsRequestType] = None,
    status: Optional[PublicRecordsRequestStatus] = None,
    jurisdiction: Optional[JurisdictionType] = None,
    assigned_to_id: Optional[int] = None,
    is_overdue: Optional[bool] = None,
    year: Optional[int] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    List public records requests with optional filters.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    requests, total = await service.list_requests(
        skip=skip,
        limit=limit,
        request_type=request_type,
        status=status,
        jurisdiction=jurisdiction,
        assigned_to_id=assigned_to_id,
        is_overdue=is_overdue,
        year=year,
    )

    return {
        "items": [
            {
                "id": r.id,
                "tracking_number": r.tracking_number,
                "request_type": str(r.request_type),
                "requester_name": r.requester_name,
                "requester_organization": r.requester_organization,
                "date_received": r.date_received.isoformat(),
                "response_deadline": r.response_deadline.isoformat(),
                "extended_deadline": r.extended_deadline.isoformat()
                if r.extended_deadline
                else None,
                "status": str(r.status),
                "assigned_to": r.assigned_to.full_name if r.assigned_to else None,
                "is_overdue": r.is_overdue,
                "days_until_deadline": r.days_until_deadline,
            }
            for r in requests
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/overdue")
async def get_overdue_requests(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all overdue public records requests.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    overdue = await service.get_overdue_requests()

    return {
        "count": len(overdue),
        "items": [
            {
                "id": r.id,
                "tracking_number": r.tracking_number,
                "requester_name": r.requester_name,
                "response_deadline": r.response_deadline.isoformat(),
                "days_overdue": abs(r.days_until_deadline),
                "status": str(r.status),
                "assigned_to": r.assigned_to.full_name if r.assigned_to else None,
            }
            for r in overdue
        ],
    }


@router.get("/statistics/{year}")
async def get_statistics(
    year: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get annual statistics for public records requests.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    return await service.get_statistics(year)


@router.get("/disclosure-log/{year}")
async def get_disclosure_log(
    year: int,
    include_pending: bool = Query(False),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the public disclosure log for a given year.

    This data can be posted publicly for transparency.
    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    return await service.get_disclosure_log(year, include_pending)


@router.get("/{request_id}")
async def get_request(
    request_id: int,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a specific public records request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.get_request(
        request_id=request_id,
        viewer=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "id": prr.id,
        "tracking_number": prr.tracking_number,
        "request_type": str(prr.request_type),
        "jurisdiction": str(prr.jurisdiction),
        "requester_name": prr.requester_name,
        "requester_email": prr.requester_email,
        "requester_phone": prr.requester_phone,
        "requester_organization": prr.requester_organization,
        "requester_address": prr.requester_address,
        "is_media": prr.is_media,
        "is_commercial": prr.is_commercial,
        "date_received": prr.date_received.isoformat(),
        "date_acknowledged": prr.date_acknowledged.isoformat() if prr.date_acknowledged else None,
        "description": prr.description,
        "records_date_range_start": prr.records_date_range_start.isoformat()
        if prr.records_date_range_start
        else None,
        "records_date_range_end": prr.records_date_range_end.isoformat()
        if prr.records_date_range_end
        else None,
        "preferred_format": prr.preferred_format,
        "response_deadline": prr.response_deadline.isoformat(),
        "extended_deadline": prr.extended_deadline.isoformat() if prr.extended_deadline else None,
        "extension_granted": prr.extension_granted,
        "extension_reason": prr.extension_reason,
        "status": str(prr.status),
        "assigned_to_id": prr.assigned_to_id,
        "assigned_to": prr.assigned_to.full_name if prr.assigned_to else None,
        "fee_estimate": float(prr.fee_estimate) if prr.fee_estimate else None,
        "fee_waived": prr.fee_waived,
        "fee_waiver_reason": prr.fee_waiver_reason,
        "fee_paid": float(prr.fee_paid) if prr.fee_paid else None,
        "response_date": prr.response_date.isoformat() if prr.response_date else None,
        "response_method": prr.response_method,
        "records_provided_count": prr.records_provided_count,
        "records_withheld_count": prr.records_withheld_count,
        "response_summary": prr.response_summary,
        "denial_reason": prr.denial_reason,
        "exemptions_cited": prr.exemptions_cited,
        "appeal_filed": prr.appeal_filed,
        "appeal_date": prr.appeal_date.isoformat() if prr.appeal_date else None,
        "appeal_deadline": prr.appeal_deadline.isoformat() if prr.appeal_deadline else None,
        "appeal_decision": prr.appeal_decision,
        "internal_notes": prr.internal_notes,
        "is_overdue": prr.is_overdue,
        "days_until_deadline": prr.days_until_deadline,
        "redactions": [
            {
                "id": red.id,
                "document_name": red.document_name,
                "page_number": red.page_number,
                "exemption_type": str(red.exemption_type),
                "exemption_description": red.exemption_description,
            }
            for red in prr.redactions
        ],
    }


@router.post("/{request_id}/acknowledge")
async def acknowledge_request(
    request_id: int,
    request: Request,
    notes: Optional[str] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Acknowledge receipt of a public records request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.acknowledge_request(
        request_id=request_id,
        acknowledged_by=current_user,
        notes=notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {"message": "Request acknowledged", "status": prr.status}


@router.post("/{request_id}/status")
async def update_status(
    request_id: int,
    status_update: StatusUpdate,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update the status of a public records request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.update_status(
        request_id=request_id,
        new_status=status_update.status,
        updated_by=current_user,
        notes=status_update.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {"message": "Status updated", "status": prr.status}


@router.post("/{request_id}/assign")
async def assign_request(
    request_id: int,
    assignment: AssignmentUpdate,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Assign a request to a staff member.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.assign_request(
        request_id=request_id,
        assign_to_id=assignment.assign_to_id,
        assigned_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {"message": "Request assigned", "assigned_to_id": prr.assigned_to_id}


@router.post("/{request_id}/extend")
async def grant_extension(
    request_id: int,
    extension: ExtensionRequest,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Grant a deadline extension for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.grant_extension(
        request_id=request_id,
        additional_days=extension.additional_days,
        reason=extension.reason,
        granted_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Extension granted",
        "new_deadline": prr.extended_deadline.isoformat(),
    }


@router.post("/{request_id}/estimate-fees")
async def estimate_fees(
    request_id: int,
    fee_data: FeeEstimate,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Estimate fees for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.estimate_fees(
        request_id=request_id,
        pages=fee_data.pages,
        search_hours=fee_data.search_hours,
        review_hours=fee_data.review_hours,
        copy_fee_per_page=fee_data.copy_fee_per_page,
        search_fee_per_hour=fee_data.search_fee_per_hour,
        review_fee_per_hour=fee_data.review_fee_per_hour,
        estimated_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Fee estimate recorded",
        "fee_estimate": float(prr.fee_estimate),
    }


@router.post("/{request_id}/waive-fees")
async def waive_fees(
    request_id: int,
    waiver: FeeWaiver,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Waive fees for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.waive_fees(
        request_id=request_id,
        reason=waiver.reason,
        waived_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {"message": "Fees waived", "status": prr.status}


@router.post("/{request_id}/record-payment")
async def record_fee_payment(
    request_id: int,
    payment: FeePayment,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Record fee payment for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.record_fee_payment(
        request_id=request_id,
        amount=payment.amount,
        recorded_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Payment recorded",
        "amount_paid": float(prr.fee_paid),
        "status": str(prr.status),
    }


@router.post("/{request_id}/redactions")
async def add_redaction(
    request_id: int,
    redaction: RedactionCreate,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a redaction to a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    red = await service.add_redaction(
        request_id=request_id,
        document_name=redaction.document_name,
        exemption_type=redaction.exemption_type,
        redacted_by=current_user,
        page_number=redaction.page_number,
        section_reference=redaction.section_reference,
        exemption_description=redaction.exemption_description,
        redaction_description=redaction.redaction_description,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    return {
        "id": red.id,
        "document_name": red.document_name,
        "exemption_type": str(red.exemption_type),
    }


@router.get("/{request_id}/redactions")
async def get_redactions(
    request_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all redactions for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    redactions = await service.get_redactions(request_id)

    return {
        "items": [
            {
                "id": r.id,
                "document_name": r.document_name,
                "page_number": r.page_number,
                "section_reference": r.section_reference,
                "exemption_type": str(r.exemption_type),
                "exemption_description": r.exemption_description,
                "redaction_description": r.redaction_description,
                "redacted_by": r.redacted_by.full_name if r.redacted_by else None,
                "redacted_at": r.redacted_at.isoformat() if r.redacted_at else None,
                "reviewed_by": r.reviewed_by.full_name if r.reviewed_by else None,
                "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            }
            for r in redactions
        ],
        "total": len(redactions),
    }


@router.post("/{request_id}/respond")
async def record_response(
    request_id: int,
    response_data: ResponseRecord,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Record the response sent for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.record_response(
        request_id=request_id,
        response_method=response_data.response_method,
        responded_by=current_user,
        records_provided_count=response_data.records_provided_count,
        records_withheld_count=response_data.records_withheld_count,
        response_summary=response_data.response_summary,
        denial_reason=response_data.denial_reason,
        exemptions_cited=response_data.exemptions_cited,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Response recorded",
        "status": str(prr.status),
        # Key names match the GET detail view, the generated OpenAPI schema and
        # the frontend client (public-records-api.ts), which all use *_count.
        # This endpoint was the only place using the short names.
        "records_provided_count": prr.records_provided_count,
        "records_withheld_count": prr.records_withheld_count,
        # A FOIA response record has to document when and how it was answered.
        "response_date": prr.response_date.isoformat() if prr.response_date else None,
        "response_method": prr.response_method,
    }


@router.post("/{request_id}/deny")
async def deny_request(
    request_id: int,
    denial: DenialRecord,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Deny a request in its entirety.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.deny_request(
        request_id=request_id,
        denial_reason=denial.denial_reason,
        exemptions_cited=denial.exemptions_cited,
        denied_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Request denied",
        "status": str(prr.status),
        "appeal_deadline": prr.appeal_deadline.isoformat() if prr.appeal_deadline else None,
    }


@router.post("/{request_id}/appeal")
async def record_appeal(
    request_id: int,
    appeal: AppealRecord,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Record that an appeal has been filed.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.record_appeal(
        request_id=request_id,
        recorded_by=current_user,
        appeal_notes=appeal.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {"message": "Appeal recorded", "status": prr.status}


@router.post("/{request_id}/appeal-decision")
async def record_appeal_decision(
    request_id: int,
    decision: AppealDecision,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Record the decision on an appeal.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    prr = await service.record_appeal_decision(
        request_id=request_id,
        decision=decision.decision,
        recorded_by=current_user,
        notes=decision.notes,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    if not prr:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    return {
        "message": "Appeal decision recorded",
        "decision": prr.appeal_decision,
        "status": str(prr.status),
    }


@router.get("/{request_id}/audit-log")
async def get_audit_log(
    request_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the audit log for a request.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    logs = await service.get_audit_log(request_id, skip, limit)

    return {
        "items": [
            {
                "id": log.id,
                "action": str(log.action),
                "performed_by": log.performed_by.full_name if log.performed_by else "System",
                "details": log.details,
                "created_at": log.created_at.isoformat(),
            }
            for log in logs
        ],
    }


@router.post("/{request_id}/notes")
async def add_note(
    request_id: int,
    note_data: NoteAdd,
    request: Request,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a note to a request's audit log.

    Requires STAFF, ADMIN, or SUPER_ADMIN role.
    """

    service = PublicRecordsService(db)
    log = await service.add_note(
        request_id=request_id,
        note=note_data.note,
        added_by=current_user,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    return {"message": "Note added", "audit_log_id": log.id}


# =============================================================================
# Public (unauthenticated) Endpoints
# =============================================================================


async def _send_requester_confirmation_email(prr: "PublicRecordsRequest") -> None:
    from ...core.email import send_email

    if not prr.requester_email:
        return
    settings = get_settings()
    body_html = f"""
<p>Thank you for submitting a public records request to {settings.library_name}.</p>
<p>Your tracking number is <strong>{prr.tracking_number}</strong>.</p>
<p>Expected response by: <strong>{prr.response_deadline.isoformat()}</strong></p>
<p>You can review the status of public records requests at
<a href="{settings.frontend_url}/transparency/records-requests">
{settings.frontend_url}/transparency/records-requests</a>.</p>
"""
    try:
        await send_email(
            to_email=prr.requester_email,
            subject=f"Public records request received — L30 tracking #{prr.tracking_number}",
            html_content=body_html,
            categories=["public-records-requester-confirmation"],
        )
    except Exception as exc:  # noqa: BLE001  # best-effort requester email — request already saved
        logger.warning("Failed to send requester confirmation email: %s", exc)


async def _send_clerk_notification_email(prr: "PublicRecordsRequest") -> None:
    from ...core.email import send_email

    settings = get_settings()
    clerk_addr = getattr(settings, "public_records_clerk_email", None)
    if not clerk_addr:
        logger.warning("PUBLIC_RECORDS_CLERK_EMAIL not configured; skipping clerk notification")
        return
    body_html = f"""
<p>A new public records request was submitted via the public form.</p>
<ul>
  <li>Tracking: {prr.tracking_number}</li>
  <li>Requester: {prr.requester_name} &lt;{prr.requester_email or "no email"}&gt;</li>
  <li>Jurisdiction: {prr.jurisdiction}</li>
  <li>Description: {prr.description[:500]}{"\u2026" if len(prr.description) > 500 else ""}</li>
  <li>Meeting ID: {prr.meeting_id or "\u2014"}</li>
  <li>Response due: {prr.response_deadline.isoformat()}</li>
</ul>
<p>Manage at <a href="{settings.frontend_url}/admin/compliance#public-records">
admin compliance dashboard</a>.</p>
"""
    try:
        await send_email(
            to_email=clerk_addr,
            subject=f"New public records request: tracking #{prr.tracking_number}",
            html_content=body_html,
            categories=["public-records-clerk-notification"],
        )
    except Exception as exc:  # noqa: BLE001  # best-effort clerk notification email
        logger.warning("Failed to send clerk notification email: %s", exc)


@router.post(
    "/public/submit",
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/hour")
async def public_submit(  # noqa: role-check -- public records request intake, Turnstile-gated
    submit_data: PublicRecordsRequestPublicSubmit,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Anonymous patron submission. Turnstile-gated, no auth required."""

    # Turnstile verification
    client_ip = request.client.host if request.client else None
    if not await verify_turnstile(submit_data.turnstile_token, client_ip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    service = PublicRecordsService(db)
    prr = await service.create_request_from_public_form(
        requester_name=submit_data.requester_name,
        requester_email=submit_data.requester_email,
        description=submit_data.description,
        jurisdiction=submit_data.jurisdiction or JurisdictionType.OHIO,
        preferred_format=submit_data.preferred_format or "digital",
        meeting_id=submit_data.meeting_id,
        committee_id=submit_data.committee_id,
        ip_address=client_ip,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    background_tasks.add_task(_send_requester_confirmation_email, prr)
    background_tasks.add_task(_send_clerk_notification_email, prr)

    return PublicRecordsRequestSubmissionAck(
        tracking_number=prr.tracking_number,
        response_deadline=prr.response_deadline,
        status=str(prr.status.value if hasattr(prr.status, "value") else prr.status),
    )


@router.get("/public/disclosure-log")
async def public_disclosure_log(
    year: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """Public disclosure log — PII-redacted, no auth required."""
    from datetime import date as date_type

    year = year or date_type.today().year

    service = PublicRecordsService(db)
    rows = await service.get_disclosure_log_public(year)
    rows = rows[:limit]

    response = JSONResponse(
        content=[
            PublicRecordsRequestPublicLogEntry.model_validate(r).model_dump(mode="json")
            for r in rows
        ]
    )
    response.headers["Cache-Control"] = "public, max-age=600"
    return response
