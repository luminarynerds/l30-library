# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal service provider directory.

This module handles legal service providers (legal aid, pro bono, etc.)
including listing, searching, viewing, and CRUD operations.
"""

from typing import Optional
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.legal.eligibility import LegalEligibilityThreshold
from ....models.legal.providers import LegalServiceProvider
from ....models.user import User, UserRole
from ....schemas.legal import (
    LegalServiceProviderCreate, LegalServiceProviderUpdate,
    LegalServiceProviderResponse, LegalServiceProviderSummaryResponse,
    LegalServiceProviderListResponse, LegalServiceProviderSearchRequest,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from ..dependencies import require_staff
from .helpers import paginated_response, require_resource


STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR)


def _require_staff(user: User) -> None:
    if user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )

router = APIRouter(prefix="/legal", tags=["legal-resources"])


# ============================================================================
# Service Providers (Legal Aid Directory)
# ============================================================================

@router.get("/providers", response_model=LegalServiceProviderListResponse)
async def list_providers(
    provider_type: Optional[str] = Query(None, description="Filter by provider type"),
    topic_id: Optional[int] = Query(None, description="Filter by legal topic"),
    city: Optional[str] = Query(None, description="Filter by city"),
    state: Optional[str] = Query(None, description="Filter by state"),
    language: Optional[str] = Query(None, description="Filter by language spoken"),
    accepts_walkins: Optional[bool] = Query(None),
    virtual_services: Optional[bool] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List legal service providers (legal aid, pro bono, etc.).

    Includes eligibility information, services offered, and languages.
    """
    providers, total = await legal_service.list_providers(
        db, provider_type=provider_type, topic_id=topic_id,
        city=city, state=state, language=language,
        accepts_walkins=accepts_walkins, virtual_services=virtual_services,
        skip=offset, limit=limit
    )
    return paginated_response(
        key="providers",
        items=providers,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_provider_to_summary,
    )


@router.post("/providers/search", response_model=LegalServiceProviderListResponse)
async def search_providers(
    search_request: LegalServiceProviderSearchRequest,
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Search for legal service providers."""
    providers, total = await legal_service.list_providers(
        db, **search_request.model_dump(exclude_none=True),
        skip=offset, limit=limit
    )
    return paginated_response(
        key="providers",
        items=providers,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_provider_to_summary,
    )


@router.get("/providers/{provider_id}", response_model=LegalServiceProviderResponse)
async def get_provider(
    provider_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get detailed provider information."""
    provider = require_resource(
        await legal_service.get_provider_by_id(db, provider_id),
        message="Service provider not found",
    )
    return _provider_to_response(provider)


@router.post("/providers", response_model=LegalServiceProviderResponse, status_code=status.HTTP_201_CREATED)
async def create_provider(
    provider_data: LegalServiceProviderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Create a new service provider. Requires staff access."""
    provider = await legal_service.create_provider(
        db, provider_data.model_dump(), created_by_id=current_user.id
    )
    return _provider_to_response(provider)


@router.patch("/providers/{provider_id}", response_model=LegalServiceProviderResponse)
async def update_provider(
    provider_id: int,
    provider_data: LegalServiceProviderUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Update a legal service provider. Requires staff access."""
    provider = await legal_service.update_provider(
        db, provider_id, provider_data.model_dump(exclude_unset=True)
    )
    return _provider_to_response(provider)


# ============================================================================
# Helper Functions
# ============================================================================

def _provider_to_summary(provider) -> dict:
    return {
        "id": provider.id,
        "name": provider.name,
        "slug": provider.slug,
        "provider_type": provider.provider_type,
        "city": provider.city,
        "state": provider.state,
        "phone": provider.phone,
        "languages_spoken": provider.languages_spoken or ["English"],
        "accepts_walkins": provider.accepts_walkins,
        "virtual_services": provider.virtual_services,
        "is_active": provider.is_active
    }


def _provider_to_response(provider) -> dict:
    return {
        "id": provider.id,
        "name": provider.name,
        "slug": provider.slug,
        "provider_type": provider.provider_type,
        "description": provider.description,
        "services": provider.services or [],
        "topic_ids": provider.topic_ids or [],
        "eligibility_criteria": provider.eligibility_criteria,
        "income_limits": provider.income_limits,
        "income_limit_percentage": provider.income_limit_percentage,
        "geographic_restrictions": provider.geographic_restrictions,
        "other_requirements": provider.other_requirements,
        "phone": provider.phone,
        "phone_toll_free": provider.phone_toll_free,
        "email": provider.email,
        "website": provider.website,
        "address_line1": provider.address_line1,
        "address_line2": provider.address_line2,
        "city": provider.city,
        "state": provider.state,
        "zip_code": provider.zip_code,
        "hours": provider.hours or {},
        "hours_notes": provider.hours_notes,
        "languages_spoken": provider.languages_spoken or ["English"],
        "accepts_walkins": provider.accepts_walkins,
        "appointment_required": provider.appointment_required,
        "wheelchair_accessible": provider.wheelchair_accessible,
        "virtual_services": provider.virtual_services,
        "specializations": provider.specializations or [],
        "special_populations": provider.special_populations or [],
        "is_active": provider.is_active,
        "is_verified": provider.is_verified,
        "verified_at": provider.verified_at,
        "view_count": provider.view_count,
        "referral_count": provider.referral_count,
        "created_at": getattr(provider, "created_at", None),
        "updated_at": getattr(provider, "updated_at", None),
        "created_by_id": provider.created_by_id
    }


# ============================================================================
# Eligibility Check
# ============================================================================

@router.get("/eligibility/check")
async def check_eligibility(
    household_size: int = Query(..., ge=1, le=8),
    income: int = Query(..., ge=0),
    db: AsyncSession = Depends(get_db),
):
    """
    Check income eligibility against legal service providers.

    Returns providers with eligibility status:
    - likely_eligible: income at or below limit
    - may_be_eligible: income within 10% above limit
    - over_limit: income more than 10% above limit
    """
    today = date_type.today()
    stmt = (
        select(LegalEligibilityThreshold)
        .where(
            and_(
                LegalEligibilityThreshold.household_size == min(household_size, 8),
                LegalEligibilityThreshold.effective_date <= today,
                (LegalEligibilityThreshold.expires_date.is_(None))
                | (LegalEligibilityThreshold.expires_date >= today),
            )
        )
    )
    result = await db.execute(stmt)
    thresholds = result.scalars().all()

    results = []
    for t in thresholds:
        limit = t.income_limit
        buffer = int(limit * 0.10)
        if income <= limit:
            status = "likely_eligible"
        elif income <= limit + buffer:
            status = "may_be_eligible"
        else:
            status = "over_limit"

        await db.refresh(t, ["provider"])
        provider = t.provider
        results.append({
            "provider_id": provider.id,
            "provider_name": provider.name,
            "phone": provider.phone,
            "virtual_services": provider.virtual_services,
            "status": status,
            "income_limit": limit,
            "percentage_of_fpl": t.percentage_of_fpl,
        })

    return {"results": results, "household_size": household_size, "income": income}


# ============================================================================
# Eligibility Threshold Admin (CRUD)
# ============================================================================

# 2026 Federal Poverty Guidelines (annual, 48 contiguous states + DC).
# Source: HHS Poverty Guidelines for 2026. Add $7,470 for each person
# beyond size 8; we cap at size 8+ which uses size 8 amount per project policy.
FPG_2026_BASE = {1: 15670, 2: 21130, 3: 26590, 4: 32050, 5: 37510, 6: 42970, 7: 48430, 8: 53890}


def _threshold_to_response(t: LegalEligibilityThreshold) -> dict:
    return {
        "id": t.id,
        "provider_id": t.provider_id,
        "provider_name": t.provider.name if t.provider else None,
        "household_size": t.household_size,
        "income_limit": t.income_limit,
        "percentage_of_fpl": t.percentage_of_fpl,
        "effective_date": t.effective_date,
        "expires_date": t.expires_date,
        "created_by_id": t.created_by_id,
        "updated_at": t.updated_at,
    }


class EligibilityThresholdCreate(BaseModel):
    provider_id: int
    household_size: int = Field(..., ge=1, le=8)
    income_limit: int = Field(..., ge=0)
    percentage_of_fpl: int = Field(..., ge=0, le=1000)
    effective_date: date_type
    expires_date: Optional[date_type] = None


class EligibilityThresholdUpdate(BaseModel):
    household_size: Optional[int] = Field(None, ge=1, le=8)
    income_limit: Optional[int] = Field(None, ge=0)
    percentage_of_fpl: Optional[int] = Field(None, ge=0, le=1000)
    effective_date: Optional[date_type] = None
    expires_date: Optional[date_type] = None


class EligibilityFPGImport(BaseModel):
    provider_id: int
    percentage_of_fpl: int = Field(125, ge=0, le=1000)
    effective_date: date_type
    expire_existing: bool = True


@router.get("/eligibility/thresholds")
async def list_eligibility_thresholds(
    provider_id: Optional[int] = Query(None, description="Filter by provider"),
    include_expired: bool = Query(False, description="Include thresholds past expires_date"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List eligibility thresholds. Staff only."""
    _require_staff(current_user)
    today = date_type.today()
    stmt = select(LegalEligibilityThreshold).options(
        selectinload(LegalEligibilityThreshold.provider)
    )
    if provider_id is not None:
        stmt = stmt.where(LegalEligibilityThreshold.provider_id == provider_id)
    if not include_expired:
        stmt = stmt.where(
            (LegalEligibilityThreshold.expires_date.is_(None))
            | (LegalEligibilityThreshold.expires_date >= today)
        )
    stmt = stmt.order_by(
        LegalEligibilityThreshold.provider_id,
        LegalEligibilityThreshold.percentage_of_fpl,
        LegalEligibilityThreshold.household_size,
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return {"thresholds": [_threshold_to_response(t) for t in rows], "total": len(rows)}


@router.post(
    "/eligibility/thresholds",
    status_code=status.HTTP_201_CREATED,
)
async def create_eligibility_threshold(
    data: EligibilityThresholdCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create an eligibility threshold for a provider. Staff only."""
    _require_staff(current_user)

    provider = await db.get(LegalServiceProvider, data.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    threshold = LegalEligibilityThreshold(
        provider_id=data.provider_id,
        household_size=data.household_size,
        income_limit=data.income_limit,
        percentage_of_fpl=data.percentage_of_fpl,
        effective_date=data.effective_date,
        expires_date=data.expires_date,
        created_by_id=current_user.id,
    )
    db.add(threshold)
    await db.commit()
    await db.refresh(threshold, ["provider"])
    return _threshold_to_response(threshold)


@router.patch("/eligibility/thresholds/{threshold_id}")
async def update_eligibility_threshold(
    threshold_id: int,
    data: EligibilityThresholdUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update an eligibility threshold. Staff only."""
    _require_staff(current_user)

    threshold = await db.get(LegalEligibilityThreshold, threshold_id)
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(threshold, field, value)
    await db.commit()
    await db.refresh(threshold, ["provider"])
    return _threshold_to_response(threshold)


@router.delete(
    "/eligibility/thresholds/{threshold_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_eligibility_threshold(
    threshold_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete an eligibility threshold. Staff only."""
    _require_staff(current_user)

    threshold = await db.get(LegalEligibilityThreshold, threshold_id)
    if not threshold:
        raise HTTPException(status_code=404, detail="Threshold not found")
    await db.delete(threshold)
    await db.commit()


@router.post("/eligibility/thresholds/import-fpg-2026")
async def import_fpg_2026(
    payload: EligibilityFPGImport,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Bulk-insert the 2026 Federal Poverty Guidelines for a provider at the given
    percentage of FPL (defaults to 125%, the LSC threshold).

    Inserts one row per household size 1..8. If ``expire_existing`` is true,
    any current rows for the same provider/percentage that are still active
    are marked as expiring the day before ``effective_date``.
    """
    _require_staff(current_user)

    provider = await db.get(LegalServiceProvider, payload.provider_id)
    if not provider:
        raise HTTPException(status_code=404, detail="Provider not found")

    if payload.expire_existing:
        from datetime import timedelta
        expire_on = payload.effective_date - timedelta(days=1)
        existing_stmt = select(LegalEligibilityThreshold).where(
            and_(
                LegalEligibilityThreshold.provider_id == payload.provider_id,
                LegalEligibilityThreshold.percentage_of_fpl == payload.percentage_of_fpl,
                (LegalEligibilityThreshold.expires_date.is_(None))
                | (LegalEligibilityThreshold.expires_date >= payload.effective_date),
            )
        )
        result = await db.execute(existing_stmt)
        for row in result.scalars().all():
            if row.expires_date is None or row.expires_date >= payload.effective_date:
                row.expires_date = expire_on

    multiplier = payload.percentage_of_fpl / 100.0
    created = []
    for size, base in FPG_2026_BASE.items():
        income_limit = int(round(base * multiplier))
        t = LegalEligibilityThreshold(
            provider_id=payload.provider_id,
            household_size=size,
            income_limit=income_limit,
            percentage_of_fpl=payload.percentage_of_fpl,
            effective_date=payload.effective_date,
            expires_date=None,
            created_by_id=current_user.id,
        )
        db.add(t)
        created.append(t)

    await db.commit()
    for t in created:
        await db.refresh(t, ["provider"])

    return {
        "created": [_threshold_to_response(t) for t in created],
        "count": len(created),
    }
