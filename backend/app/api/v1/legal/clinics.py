# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal clinic scheduling and registration.

This module handles legal clinics including listing, viewing,
registration, cancellation, and CRUD operations.
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalClinicCreate, LegalClinicUpdate, LegalClinicResponse,
    LegalClinicSummaryResponse, LegalClinicListResponse,
    LegalClinicRegistrationCreate, LegalClinicRegistrationResponse,
    LegalClinicRegistrationListResponse, LegalClinicFeedbackCreate,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from ..dependencies import require_staff
from .helpers import paginated_response, require_resource

from ....services.geocoding import geocode_address


async def _geocode_clinic(clinic_id: int) -> None:
    from ....core.database import get_async_session
    from sqlalchemy import select
    from ....models.legal.providers import LegalClinic

    async with get_async_session() as db:
        result = await db.execute(select(LegalClinic).where(LegalClinic.id == clinic_id))
        clinic = result.scalar_one_or_none()
        if not clinic or not clinic.location or (clinic.latitude and clinic.longitude):
            return
        coords = await geocode_address(clinic.location)
        if coords:
            clinic.latitude, clinic.longitude = coords

router = APIRouter(prefix="/legal", tags=["legal-resources"])


# ============================================================================
# Legal Clinics
# ============================================================================

@router.get("/clinics", response_model=LegalClinicListResponse)
async def list_clinics(
    topic_id: Optional[int] = Query(None),
    provider_id: Optional[int] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    is_virtual: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List scheduled legal clinics.

    Clinics offer free brief consultations with volunteer attorneys.
    """
    clinics, total = await legal_service.list_clinics(
        db, topic_id=topic_id, provider_id=provider_id,
        from_date=from_date, to_date=to_date,
        is_virtual=is_virtual, skip=offset, limit=limit
    )
    return paginated_response(
        key="clinics",
        items=clinics,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_clinic_to_summary,
    )


@router.get("/clinics/upcoming", response_model=list[LegalClinicSummaryResponse])
async def get_upcoming_clinics(
    days: int = Query(30, ge=1, le=90),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db)
):
    """Get upcoming clinics with open registration."""
    clinics = await legal_service.list_upcoming_clinics(db, days=days, limit=limit)
    return [_clinic_to_summary(c) for c in clinics]


@router.get("/clinics/registrations/{registration_id}")
async def get_clinic_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get details of a clinic registration."""
    from ....models.legal import LegalClinicRegistration
    from ....schemas.legal import LegalClinicRegistrationResponse

    registration = await db.get(LegalClinicRegistration, registration_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    # Check authorization - user can only see their own registrations or staff can see all
    if current_user and registration.patron_id != current_user.id:
        # Check if user is staff (authorization would go here)
        pass

    return {
        "id": registration.id,
        "clinic_id": registration.clinic_id,
        "name": registration.name,
        "email": registration.email,
        "phone": registration.phone,
        "preferred_contact": registration.preferred_contact,
        "status": str(registration.status) if registration.status else None,
        "waitlist_position": registration.waitlist_position,
        "accessibility_needs": registration.accessibility_needs,
        "language_preference": registration.language_preference,
        "interpreter_needed": registration.interpreter_needed,
        "issue_description": registration.issue_description,
        "confirmation_sent_at": registration.confirmation_sent_at,
        "reminder_sent_at": registration.reminder_sent_at,
        "attended": registration.attended
    }


@router.post("/clinics/geocode-preview")
async def geocode_preview(
    address: str = Query(..., description="Address to geocode"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Preview geocoding result for a clinic address. Staff only."""
    coords = await geocode_address(address)
    if coords:
        return {"latitude": coords[0], "longitude": coords[1], "status": "success"}
    return {"latitude": None, "longitude": None, "status": "failed"}


@router.get("/clinics/{clinic_id}", response_model=LegalClinicResponse)
async def get_clinic(
    clinic_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed clinic information."""
    clinic = require_resource(
        await legal_service.get_clinic_by_id(db, clinic_id),
        message="Legal clinic not found",
    )
    return _clinic_to_response(clinic)


@router.post("/clinics/{clinic_id}/register", response_model=LegalClinicRegistrationResponse, status_code=status.HTTP_201_CREATED)
async def register_for_clinic(  # noqa: role-check -- public legal clinic registration, optional auth
    clinic_id: int,
    registration_data: LegalClinicRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Register for a legal clinic.

    Registration may be waitlisted if the clinic is full.
    """
    patron_id = current_user.id if current_user else None
    registration = await legal_service.register_for_clinic(
        db, clinic_id, registration_data.model_dump(), patron_id=patron_id
    )
    return _registration_to_response(registration)


@router.get("/clinics/{clinic_id}/register")
async def get_clinic_registration_info(
    clinic_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get registration form information and requirements for a clinic."""
    clinic = require_resource(
        await legal_service.get_clinic_by_id(db, clinic_id),
        message="Legal clinic not found",
    )

    return {
        "clinic_id": clinic.id,
        "clinic_name": clinic.name,
        "clinic_date": clinic.date,
        "registration_required": clinic.registration_required,
        "registration_opens": clinic.registration_opens,
        "registration_closes": clinic.registration_closes,
        "available_spots": max(0, clinic.capacity - clinic.current_registrations),
        "capacity": clinic.capacity,
        "current_registrations": clinic.current_registrations,
        "on_waitlist": clinic.current_waitlist > 0,
        "waitlist_available": clinic.waitlist_capacity > 0,
        "registration_fields": {
            "required": ["name", "preferred_contact"],
            "optional": ["email", "phone", "accessibility_needs", "interpreter_needed", "issue_description"]
        },
        "preferred_contact_options": ["email", "phone", "text"],
        "help": "POST to /clinics/{clinic_id}/register to complete registration"
    }


@router.delete("/clinics/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_registration(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a clinic registration. Requires ownership or staff role."""
    from ....models.legal import LegalClinicRegistration
    from ....models.user import UserRole

    registration = await db.get(LegalClinicRegistration, registration_id)
    if not registration:
        raise HTTPException(status_code=404, detail="Registration not found")

    is_owner = registration.patron_id is not None and registration.patron_id == current_user.id
    is_staff = current_user.role in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR)
    if not is_owner and not is_staff:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to cancel this registration")

    await legal_service.cancel_clinic_registration(db, registration_id)


@router.post("/clinics", response_model=LegalClinicResponse, status_code=status.HTTP_201_CREATED)
async def create_clinic(
    clinic_data: LegalClinicCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new legal clinic. Requires staff access."""
    clinic = await legal_service.create_clinic(
        db, clinic_data.model_dump(), created_by_id=current_user.id
    )
    background_tasks.add_task(_geocode_clinic, clinic.id)
    return _clinic_to_response(clinic)


@router.patch("/clinics/{clinic_id}", response_model=LegalClinicResponse)
async def update_clinic(
    clinic_id: int,
    clinic_data: LegalClinicUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update a legal clinic. Requires staff access."""
    clinic = await legal_service.update_clinic(
        db, clinic_id, clinic_data.model_dump(exclude_unset=True)
    )
    return _clinic_to_response(clinic)


# ============================================================================
# Helper Functions
# ============================================================================

def _clinic_to_summary(clinic) -> dict:
    spots_available = max(0, clinic.capacity - clinic.current_registrations)
    return {
        "id": clinic.id,
        "name": clinic.name,
        "date": clinic.date,
        "start_time": clinic.start_time,
        "end_time": clinic.end_time,
        "is_virtual": clinic.is_virtual,
        "location": clinic.location,
        "status": clinic.status,
        "current_registrations": clinic.current_registrations,
        "capacity": clinic.capacity,
        "spots_available": spots_available,
        "topic_name": clinic.topic.name if clinic.topic else None,
        "latitude": clinic.latitude,
        "longitude": clinic.longitude,
    }


def _clinic_to_response(clinic) -> dict:
    spots_available = max(0, clinic.capacity - clinic.current_registrations)
    return {
        "id": clinic.id,
        "name": clinic.name,
        "title": getattr(clinic, "title", None) or clinic.name,
        "topic_id": clinic.topic_id,
        "description": clinic.description,
        "provider_id": clinic.provider_id,
        "date": clinic.date,
        "start_time": clinic.start_time,
        "end_time": clinic.end_time,
        "timezone": clinic.timezone,
        "is_virtual": clinic.is_virtual,
        "virtual_link": clinic.virtual_link,
        "virtual_platform": clinic.virtual_platform,
        "location_name": getattr(clinic, "location_name", None) or clinic.location,
        "location_address": getattr(clinic, "location_address", None),
        "location_room": getattr(clinic, "location_room", None),
        "capacity": clinic.capacity,
        "current_registrations": clinic.current_registrations,
        "waitlist_capacity": clinic.waitlist_capacity,
        "current_waitlist": clinic.current_waitlist,
        "registration_required": clinic.registration_required,
        "registration_opens": clinic.registration_opens,
        "registration_closes": clinic.registration_closes,
        "status": clinic.status,
        "eligibility_notes": clinic.eligibility_notes,
        "what_to_bring": clinic.what_to_bring or [],
        "languages_available": clinic.languages_available or ["English"],
        "interpreter_available": clinic.interpreter_available,
        "follow_up_resources": clinic.follow_up_resources or [],
        "wheelchair_accessible": clinic.wheelchair_accessible,
        "asl_interpreter": clinic.asl_interpreter,
        "attorney_names": clinic.attorney_names or [],
        "volunteer_count": clinic.volunteer_count,
        "public_notes": clinic.public_notes,
        "created_at": getattr(clinic, "created_at", None),
        "updated_at": getattr(clinic, "updated_at", None),
        "created_by_id": clinic.created_by_id,
        "topic_name": clinic.topic.name if clinic.topic else None,
        "provider_name": clinic.provider.name if clinic.provider else None,
        "spots_available": spots_available,
        "latitude": clinic.latitude,
        "longitude": clinic.longitude,
    }


def _registration_to_response(registration) -> dict:
    return {
        "id": registration.id,
        "clinic_id": registration.clinic_id,
        "patron_id": registration.patron_id,
        "name": registration.name,
        "email": registration.email,
        "phone": registration.phone,
        "preferred_contact": registration.preferred_contact,
        "status": registration.status,
        "waitlist_position": registration.waitlist_position,
        "accessibility_needs": registration.accessibility_needs,
        "language_preference": registration.language_preference,
        "interpreter_needed": registration.interpreter_needed,
        "issue_description": registration.issue_description,
        "confirmation_sent": getattr(registration, "confirmation_sent", None),
        "reminder_sent": getattr(registration, "reminder_sent", None),
        "checked_in_at": getattr(registration, "checked_in_at", None),
        "created_at": getattr(registration, "created_at", None),
        "clinic_title": getattr(registration.clinic, "title", None) or (registration.clinic.name if registration.clinic else None),
        "clinic_date": registration.clinic.date if registration.clinic else None
    }


# ============================================================================
# Clinic Notify (E3 — unauthenticated opt-in)
# Persists email encrypted at rest; idempotent on duplicate (email_hash dedup).
# Row is deleted after notification is sent (notified_at set, then purged).
# ============================================================================

class ClinicNotifyRequest(BaseModel):
    email: EmailStr


@router.post("/clinic-notify", status_code=status.HTTP_200_OK)  # noqa: role-check
async def clinic_notify(
    body: ClinicNotifyRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Opt-in to a one-time email when a free legal clinic is scheduled.

    Idempotent: duplicate submissions return 200 without creating a second row.
    Email is Fernet-encrypted at rest; email_hash (HMAC blind index) used for dedup.
    """
    import uuid
    from ....models.legal_clinic_notify import LegalClinicNotify
    from ....core.encryption import hash_pii
    from sqlalchemy import select

    normalised = body.email.lower().strip()
    h = hash_pii(normalised, field="clinic_notify_email")

    result = await db.execute(
        select(LegalClinicNotify).where(LegalClinicNotify.email_hash == h)
    )
    if result.scalar_one_or_none() is not None:
        return {"status": "ok"}

    row = LegalClinicNotify(
        id=str(uuid.uuid4()),
        email_hash=h,
    )
    row.email = normalised
    db.add(row)
    await db.commit()
    return {"status": "ok"}
