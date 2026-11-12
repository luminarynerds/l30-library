# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Partnership tiers sub-router for school reading partnerships.

Extracted from the former ``school_reading_partnerships.py`` monolith.
The full import surface from that file is preserved here so behavior of
moved routes is byte-for-byte identical; unused imports in this slice are
intentional and may be pruned in a follow-up.
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

logger = get_logger(__name__)
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....core.rate_limit import limiter
from ....models.outreach import OutreachPartner, BulkCheckout, PartnershipTier, OutreachPartnerStatus
from ....models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingRegistration,
    SchoolBadge,
    SchoolBadgeEarned,
    SharedReadingList,
    SharedReadingListItem,
    FamilyReadingChallenge,
    FamilyChallengeRegistration,
    TakeHomeReadingBundle,
    BundleDistribution,
    TeacherTrainingModule,
    TrainingCompletion,
    LibraryVisitRequest,
    ReadingListRequest,
    ReadingAmbassadorCertification,
    LibrarianConsultationSlot,
    ConsultationAttendee,
)
from ....models.user import User, UserRole
from ....schemas.reading import (
    SchoolBadgeCreate,
    SchoolBadgeResponse,
    SharedReadingListCreate,
    SharedReadingListItemCreate,
    SharedReadingListItemResponse,
    SharedReadingListResponse,
    FamilyReadingChallengeCreate,
    FamilyReadingChallengeResponse,
    FamilyChallengeRegistrationCreate,
    FamilyChallengeRegistrationResponse,
    TakeHomeReadingBundleCreate,
    TakeHomeReadingBundleResponse,
    TeacherTrainingModuleCreate,
    TeacherTrainingModuleResponse,
    TrainingCompletionResponse,
    ReadingAmbassadorCertificationCreate,
    ReadingAmbassadorCertificationResponse,
    ReadingAmbassadorCertificationListResponse,
    ReadingAmbassadorCertificationListItem,
    ReadingAmbassadorCertificationUpdate,
    LibrarianConsultationSlotCreate,
    LibrarianConsultationSlotResponse,
    LibraryVisitRequestCreate,
    LibraryVisitRequestResponse,
    LibraryVisitApprove,
    LibraryVisitReject,
    ReadingListRequestCreate,
    ReadingListRequestResponse,
    ReadingListRequestReject,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._shared import require_teacher_or_staff, require_teacher_of_school, _strip_patron_identifiers, _PATRON_ID_FIELDS

router = APIRouter()


# ============================================================================
# Partnership Tier Management
# ============================================================================

TIER_BENEFITS = {
    "bronze": {
        "name": "Bronze Partnership",
        "color": "#CD7F32",
        "features": [
            "Monthly outreach visits",
            "Standard bulk checkouts (50 items max)",
            "Email support",
            "Basic reporting",
        ],
        "reading_programs_max": 2,
        "monthly_visits": 1,
        "checkout_limit": 50,
    },
    "silver": {
        "name": "Silver Partnership",
        "color": "#C0C0C0",
        "features": [
            "All Bronze features",
            "Bi-weekly outreach visits",
            "Enhanced bulk checkouts (100 items max)",
            "Dedicated reading programs",
            "Shared reading lists",
            "Priority email support",
            "Monthly progress reports",
        ],
        "reading_programs_max": 5,
        "monthly_visits": 2,
        "checkout_limit": 100,
    },
    "gold": {
        "name": "Gold Partnership",
        "color": "#FFD700",
        "features": [
            "All Silver features",
            "Weekly outreach visits",
            "Premium bulk checkouts (200 items max)",
            "Custom reading programs (Librarian designed)",
            "Quarterly librarian consultations",
            "School-specific badge creation",
            "Teacher professional development",
            "Weekly progress reports",
            "Priority phone support",
        ],
        "reading_programs_max": 10,
        "monthly_visits": 4,
        "checkout_limit": 200,
    },
    "platinum": {
        "name": "Platinum Partnership",
        "color": "#E5E4E2",
        "features": [
            "All Gold features",
            "Twice-weekly visits (customizable)",
            "Unlimited bulk checkouts",
            "Unlimited custom reading programs",
            "Monthly librarian consultations",
            "Reading ambassador training",
            "Student leadership roles",
            "Daily progress tracking",
            "Dedicated staff liaison",
            "Custom curriculum integration",
            "24/7 support with dedicated contact",
        ],
        "reading_programs_max": 999,
        "monthly_visits": 8,
        "checkout_limit": 999,
    },
}


@router.get("/partnership-tiers", response_model=dict)
@limiter.limit("120/minute")
async def get_all_partnership_tiers(request: Request):
    """Get all available partnership tiers and their benefits."""
    return {
        "tiers": [
            {
                "tier": tier_key,
                "details": tier_details,
            }
            for tier_key, tier_details in TIER_BENEFITS.items()
        ]
    }


@router.get("/schools/{school_id}/partnership-tier", response_model=dict)
@limiter.limit("120/minute")
async def get_school_partnership_tier(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """Get partnership tier info for a school."""
    # Verify school exists
    school = await get_or_404(db, OutreachPartner, school_id, "School not found")

    tier = school.partnership_tier
    tier_details = TIER_BENEFITS.get(tier, TIER_BENEFITS["bronze"])

    return {
        "school_id": school_id,
        "school_name": school.name,
        "current_tier": tier,
        "tier_details": tier_details,
        "available_upgrades": [
            t for t in ["silver", "gold", "platinum"] if TIER_BENEFITS.get(t)
        ],
    }


@router.post("/schools/{school_id}/upgrade-tier/{new_tier}")
@limiter.limit("60/minute")
async def upgrade_partnership_tier(
    request: Request,
    school_id: int,
    new_tier: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upgrade a school's partnership tier. Staff only."""
    check_staff_access(current_user)

    # Verify valid tier
    valid_tiers = ["bronze", "silver", "gold", "platinum"]
    if new_tier not in valid_tiers:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid tier")

    # Verify school exists
    school = await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Update tier
    school.partnership_tier = new_tier
    await db.commit()
    await db.refresh(school)

    return {
        "school_id": school_id,
        "school_name": school.name,
        "previous_tier": school.partnership_tier,
        "new_tier": new_tier,
        "tier_details": TIER_BENEFITS.get(new_tier),
        "message": f"Partnership upgraded to {new_tier.title()}!",
    }


@router.get("/schools/{school_id}/tier-benefits", response_model=dict)
@limiter.limit("120/minute")
async def get_school_tier_benefits(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """Get details on benefits available at school's current tier."""
    # Verify school exists
    school = await get_or_404(db, OutreachPartner, school_id, "School not found")

    tier = school.partnership_tier
    tier_details = TIER_BENEFITS.get(tier, TIER_BENEFITS["bronze"])

    # Get current usage stats
    programs_result = await db.execute(
        select(func.count(ReadingProgram.id)).where(ReadingProgram.partner_id == school_id)
    )
    current_programs = programs_result.scalar() or 0

    checkouts_result = await db.execute(
        select(func.count(BulkCheckout.id)).where(BulkCheckout.partner_id == school_id)
    )
    current_checkouts = checkouts_result.scalar() or 0

    return {
        "school_id": school_id,
        "school_name": school.name,
        "tier": tier,
        "tier_details": tier_details,
        "current_usage": {
            "reading_programs": current_programs,
            "programs_limit": tier_details["reading_programs_max"],
            "bulk_checkouts": current_checkouts,
            "checkout_limit": tier_details["checkout_limit"],
        },
        "usage_percentage": {
            "programs": round((current_programs / tier_details["reading_programs_max"]) * 100, 1)
            if tier_details["reading_programs_max"] > 0
            else 0,
        },
    }


