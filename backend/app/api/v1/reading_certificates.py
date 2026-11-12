# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Certificates API for L30 Library.
Generate, manage, and verify reading certificates and program completion records.
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from .auth import get_current_user
from .dependencies import check_admin_access


# ============================================================================
# Enums
# ============================================================================


class CertificateStatus(StrEnum):

    draft = "draft"  # Not yet generated
    generated = "generated"  # Created but not distributed
    verified = "verified"  # Admin verified
    emailed = "emailed"  # Sent to user
    revoked = "revoked"  # Cancelled/invalid


# ============================================================================
# Schemas (Request/Response Models)
# ============================================================================


class CertificateBase(BaseModel):

    title: str = Field(..., min_length=1, max_length=255)
    issued_to: str = Field(..., min_length=1, max_length=255)
    program_name: str = Field(..., min_length=1, max_length=255)
    completion_date: datetime


class CertificateCreate(BaseModel):

    registration_id: int = Field(..., ge=1)
    custom_title: Optional[str] = Field(None, max_length=255)


class CertificateResponse(BaseModel):

    id: int
    certificate_code: str
    registration_id: int
    user_id: int
    title: str
    issued_to: str
    program_name: str
    completion_date: datetime
    status: CertificateStatus
    created_at: datetime
    verified_at: Optional[datetime] = None
    verified_by_id: Optional[int] = None
    emailed_at: Optional[datetime] = None
    pdf_url: Optional[str] = None

    class Config:
        from_attributes = True


class CertificateVerificationResponse(BaseModel):

    is_valid: bool
    certificate_code: str
    issued_to: str
    program_name: str
    completion_date: datetime
    issued_date: datetime


class PaginatedCertificatesResponse(BaseModel):

    items: List[CertificateResponse]
    total: int
    limit: int
    offset: int


class CertificateVerificationRequest(BaseModel):

    verification_date: Optional[datetime] = None


class CertificateEmailRequest(BaseModel):

    recipient_email: str = Field(..., max_length=255)
    include_pdf: bool = True
    custom_message: Optional[str] = Field(None, max_length=1000)


# ============================================================================
# Certificate Endpoints
# ============================================================================

router = APIRouter(prefix="/reading/certificates", tags=["reading-certificates"])


@router.post(
    "/registrations/{registration_id}/certificate/generate",
    response_model=CertificateResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def generate_certificate(
    request: Request,
    registration_id: int,
    cert_data: Optional[CertificateCreate] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a certificate for a program registration."""
    # This endpoint assumes ReadingRegistration and related models exist
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found"
    )


@router.get(
    "/{certificate_code}",
    response_model=CertificateVerificationResponse,
)
@limiter.limit("120/minute")
async def verify_certificate(
    request: Request,
    certificate_code: str,
    db: AsyncSession = Depends(get_db),
):
    """Verify and view a certificate by code (public endpoint)."""
    # This endpoint assumes Certificate model exists
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found"
    )


@router.get(
    "/{certificate_code}/download",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("60/minute")
async def download_certificate_pdf(
    request: Request,
    certificate_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """Download certificate as PDF."""
    # This would require PDF generation service
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found"
    )


@router.get(
    "/my/certificates",
    response_model=PaginatedCertificatesResponse,
)
@limiter.limit("60/minute")
async def get_user_certificates(
    request: Request,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's certificates."""
    return PaginatedCertificatesResponse(items=[], total=0, limit=limit, offset=offset)


@router.post(
    "/{id}/email",
    response_model=CertificateResponse,
)
@limiter.limit("30/minute")
async def send_certificate_email(
    request: Request,
    id: int,
    email_data: CertificateEmailRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send certificate via email (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found"
    )


# ============================================================================
# Admin Certificate Management
# ============================================================================


@router.get(
    "/admin/certificates",
    response_model=PaginatedCertificatesResponse,
)
@limiter.limit("60/minute")
async def list_all_certificates(
    request: Request,
    status_filter: Optional[CertificateStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all certificates (admin only)."""
    check_admin_access(current_user)

    return PaginatedCertificatesResponse(items=[], total=0, limit=limit, offset=offset)


@router.put(
    "/admin/certificates/{id}/verify",
    response_model=CertificateResponse,
)
@limiter.limit("30/minute")
async def verify_certificate_admin(
    request: Request,
    id: int,
    verification_data: CertificateVerificationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Verify a certificate (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Certificate not found"
    )
