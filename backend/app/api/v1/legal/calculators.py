# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal calculators.

This module handles deadline calculations, fee waiver eligibility checks,
and expungement eligibility checks.
"""

from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    DeadlineRuleResponse, DeadlineCalculationRequest, DeadlineCalculationResponse,
    FeeWaiverEligibilityCheckRequest, FeeWaiverEligibilityResponse,
    ExpungementEligibilityCheckRequest, ExpungementEligibilityResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional

router = APIRouter(prefix="/legal", tags=["legal-compliance"])


# ============================================================================
# Deadline Calculator
# ============================================================================

@router.get("/deadlines/rules", response_model=list[DeadlineRuleResponse])
async def list_deadline_rules(
    deadline_type: Optional[str] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    topic_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """List available deadline calculation rules."""
    rules = await legal_service.list_deadline_rules(
        db, deadline_type=deadline_type, jurisdiction=jurisdiction, topic_id=topic_id
    )
    return [_deadline_rule_to_response(r) for r in rules]


@router.post("/deadlines/calculate", response_model=DeadlineCalculationResponse)
async def calculate_deadline(
    calculation_request: DeadlineCalculationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional)
):
    """
    Calculate a legal deadline.

    Accounts for business days, court holidays, and provides reminder options.
    """
    patron_id = current_user.id if current_user else None
    calculation = await legal_service.calculate_deadline(
        db,
        rule_id=calculation_request.rule_id,
        rule_slug=calculation_request.rule_slug,
        start_date=calculation_request.start_date,
        patron_id=patron_id,
        reminder_email=calculation_request.reminder_email,
        reminder_phone=calculation_request.reminder_phone,
        enable_reminders=calculation_request.enable_reminders,
        user_notes=calculation_request.user_notes
    )

    rule = await legal_service.get_deadline_rule(db, rule_id=calculation.rule_id)

    # Calculate warning dates
    warning_dates = []
    for days_before in (rule.warning_days or [7, 3, 1]):
        warning_date = calculation.deadline_date - timedelta(days=days_before)
        if warning_date > calculation.start_date:
            warning_dates.append(warning_date)

    days_until = (calculation.deadline_date - date.today()).days

    return {
        "id": calculation.id,
        "rule_name": rule.name if rule else "Unknown",
        "start_date": calculation.start_date,
        "deadline_date": calculation.deadline_date,
        "days_until_deadline": days_until,
        "warning_dates": warning_dates,
        "reminders_enabled": calculation.reminders_enabled,
        "user_notes": calculation.user_notes
    }


@router.get("/deadlines/calculate")
async def get_deadlines_calculate(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user_optional),
):
    """Get available deadline calculation rules and documentation."""
    rules = await legal_service.list_deadline_rules(db)
    return {
        "description": "Calculate legal deadlines with business day accounting",
        "available_rules": [_deadline_rule_to_response(r) for r in rules],
        "total_rules": len(rules),
        "requirements": {
            "required": ["rule_id or rule_slug", "start_date"],
            "optional": ["reminder_email", "reminder_phone", "enable_reminders", "user_notes"]
        }
    }


# ============================================================================
# Fee Waiver Calculator
# ============================================================================

@router.post("/fee-waiver/check", response_model=FeeWaiverEligibilityResponse)
async def check_fee_waiver_eligibility(
    check_request: FeeWaiverEligibilityCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Check if you may qualify for a fee waiver.

    Based on income, household size, and public benefits.
    This is an estimate - the court makes the final determination.
    """
    result = await legal_service.check_fee_waiver_eligibility(
        db,
        jurisdiction=check_request.jurisdiction,
        household_size=check_request.household_size,
        annual_income=check_request.annual_income,
        receives_public_benefits=check_request.receives_public_benefits
    )
    return result


@router.get("/fee-waiver/check")
async def get_fee_waiver_check(
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """Get fee waiver eligibility check documentation and requirements."""
    return {
        "description": "Check if you may qualify for a fee waiver",
        "type": "preliminary_assessment",
        "disclaimer": "This is an estimate only. The court makes the final determination.",
        "requirements": {
            "required": ["jurisdiction"],
            "optional": ["household_size", "annual_income", "receives_public_benefits"]
        },
        "income_threshold_note": "Thresholds vary by jurisdiction and are based on federal poverty levels",
        "help_available": "For complex cases, consult with a legal aid organization or attorney"
    }


# ============================================================================
# Expungement Eligibility
# ============================================================================

@router.post("/expungement/check", response_model=ExpungementEligibilityResponse)
async def check_expungement_eligibility(
    check_request: ExpungementEligibilityCheckRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Check basic expungement eligibility.

    This is a preliminary check only. Eligibility depends on many factors.
    Consult with an attorney for complex cases.
    """
    result = await legal_service.check_expungement_eligibility(
        db,
        jurisdiction=check_request.jurisdiction,
        offense_category=check_request.offense_category,
        offense_type=check_request.offense_type,
        conviction_date=check_request.conviction_date,
        sentence_completed_date=check_request.sentence_completed_date
    )
    return result


@router.get("/expungement/check")
async def check_expungement_check(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check status for /expungement/check."""
    return {"status": "ok"}


# ============================================================================
# Helper Functions
# ============================================================================

def _deadline_rule_to_response(rule) -> dict:
    return {
        "id": rule.id,
        "name": rule.name,
        "slug": rule.slug,
        "description": rule.description,
        "deadline_type": rule.deadline_type,
        "days": rule.days,
        "use_business_days": rule.use_business_days,
        "exclude_holidays": rule.exclude_holidays,
        "start_event": rule.start_event,
        "legal_citation": rule.legal_citation,
        "jurisdiction": rule.jurisdiction,
        "court_type": rule.court_type
    }
