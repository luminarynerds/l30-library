# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for court location directory.

This module handles court location management including
listing, viewing, and CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    CourtLocationCreate, CourtLocationUpdate, CourtLocationResponse,
    CourtLocationSummaryResponse, CourtLocationListResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from ..dependencies import require_staff
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-compliance"])


# ============================================================================
# Court Locations
# ============================================================================

@router.get("/courts", response_model=CourtLocationListResponse)
async def list_courts(
    court_type: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    city: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    has_self_help: Optional[bool] = Query(None),
    e_filing: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List court locations.

    Includes hours, self-help center information, and e-filing availability.
    """
    courts, total = await legal_service.list_courts(
        db, court_type=court_type, jurisdiction=jurisdiction,
        city=city, state=state, has_self_help=has_self_help,
        e_filing=e_filing, skip=offset, limit=limit
    )
    return paginated_response(
        key="courts",
        items=courts,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_court_to_summary,
    )


@router.get("/courts/{court_id}", response_model=CourtLocationResponse)
async def get_court(
    court_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed court location information.

    Includes filing hours, what to bring, dress code, parking,
    and remote hearing information.
    """
    court = require_resource(
        await legal_service.get_court_by_id(db, court_id),
        message="Court location not found",
    )
    return _court_to_response(court)


@router.post("/courts", response_model=CourtLocationResponse, status_code=status.HTTP_201_CREATED)
async def create_court(
    court_data: CourtLocationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new court location. Requires staff access."""
    court = await legal_service.create_court(
        db, court_data.model_dump(), created_by_id=current_user.id
    )
    return _court_to_response(court)


@router.patch("/courts/{court_id}", response_model=CourtLocationResponse)
async def update_court(
    court_id: int,
    court_data: CourtLocationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update a court location. Requires staff access."""
    court = await legal_service.update_court(
        db, court_id, court_data.model_dump(exclude_unset=True)
    )
    return _court_to_response(court)


# ============================================================================
# Helper Functions
# ============================================================================

def _court_to_summary(court) -> dict:
    return {
        "id": court.id,
        "name": court.name,
        "court_type": court.court_type,
        "city": court.city,
        "state": court.state,
        "phone": court.phone,
        "has_self_help_center": court.has_self_help_center,
        "e_filing_available": court.e_filing_available,
        "is_active": court.is_active
    }


def _court_to_response(court) -> dict:
    return {
        "id": court.id,
        "name": court.name,
        "code": court.code,
        "court_type": court.court_type,
        "jurisdiction": court.jurisdiction,
        "jurisdiction_code": court.jurisdiction_code,
        "address_line1": court.address_line1,
        "address_line2": court.address_line2,
        "city": court.city,
        "state": court.state,
        "zip_code": court.zip_code,
        "phone": court.phone,
        "phone_clerk": court.phone_clerk,
        "phone_self_help": court.phone_self_help,
        "fax": court.fax,
        "email": court.email,
        "website": court.website,
        "general_hours": court.general_hours or {},
        "filing_hours": court.filing_hours or {},
        "self_help_hours": court.self_help_hours or {},
        "holiday_closures": court.holiday_closures or [],
        "has_self_help_center": court.has_self_help_center,
        "self_help_services": court.self_help_services or [],
        "self_help_appointment_required": court.self_help_appointment_required,
        "self_help_appointment_url": court.self_help_appointment_url,
        "e_filing_available": court.e_filing_available,
        "e_filing_url": court.e_filing_url,
        "e_filing_instructions": court.e_filing_instructions,
        "what_to_bring": court.what_to_bring or [],
        "dress_code": court.dress_code,
        "prohibited_items": court.prohibited_items or [],
        "parking_info": court.parking_info,
        "parking_cost": court.parking_cost,
        "wheelchair_accessible": court.wheelchair_accessible,
        "accessibility_notes": court.accessibility_notes,
        "remote_hearings_available": court.remote_hearings_available,
        "remote_hearing_platform": court.remote_hearing_platform,
        "remote_hearing_instructions": court.remote_hearing_instructions,
        "latitude": court.latitude,
        "longitude": court.longitude,
        "directions_notes": court.directions_notes,
        "is_active": court.is_active,
        "created_at": court.created_at,
        "updated_at": court.updated_at,
        "created_by_id": court.created_by_id
    }
