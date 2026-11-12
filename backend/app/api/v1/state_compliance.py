# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
State Compliance API Endpoints.

Provides access to state-specific compliance requirements including:
- Patron confidentiality laws
- Data retention periods
- Law enforcement response requirements
- State library reporting
- ID verification requirements
"""

from app.core.logging import get_logger
from datetime import date
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...services.state_compliance_service import StateComplianceService
from .auth import get_current_user
from .dependencies import require_admin
from fastapi import Depends

router = APIRouter(prefix="/state-compliance", tags=["state-compliance"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class StateComplianceSummary(BaseModel):
    state_code: str
    state_name: str
    configured: bool
    last_reviewed: Optional[str] = None
    confidentiality: Optional[dict] = None
    retention: Optional[dict] = None
    law_enforcement: Optional[dict] = None
    reporting: Optional[dict] = None
    id_verification: Optional[dict] = None
    accessibility: Optional[dict] = None


class DisclosureValidationRequest(BaseModel):
    state_code: str = Field(..., min_length=2, max_length=2)
    request_type: str = Field(..., description="Type of request: subpoena, warrant, court_order, informal")
    record_type: str = Field(default="circulation", description="Type of record: circulation, registration, internet, programs")
    has_court_order: bool = False
    has_subpoena: bool = False
    has_warrant: bool = False
    is_grand_jury: bool = False


class DisclosureValidationResponse(BaseModel):
    valid: bool
    reason: str
    state_code: str
    confidentiality_statute: Optional[str] = None
    confidentiality_strength: Optional[str] = None
    record_protected: bool = True
    requires_court_order: bool = True
    patron_notification_required: bool = True
    patron_notification_allowed: bool = True
    notification_delay_days: int = 0
    applicable_exceptions: List[dict] = []


class RegistrationValidationRequest(BaseModel):
    state_code: str = Field(..., min_length=2, max_length=2)
    age: int = Field(..., ge=0, le=150)
    has_photo_id: bool = False
    photo_id_type: Optional[str] = None
    has_residency_proof: bool = False
    residency_proof_type: Optional[str] = None


class RegistrationValidationResponse(BaseModel):
    valid: bool
    missing_requirements: List[str]
    is_adult: bool
    state_code: str
    card_validity_years: int


class RetentionPeriods(BaseModel):
    checkout_record_retention_years: int
    financial_record_retention_years: int
    patron_data_retention_after_closure_days: int
    system_log_retention_days: int


class ReportingRequirements(BaseModel):
    state_library_name: Optional[str] = None
    state_library_id: Optional[str] = None
    annual_report_due: Optional[str] = None
    required_statistics: List[str] = []
    report_template: Optional[str] = None
    state_code: str


class UpcomingDeadline(BaseModel):
    state_code: str
    state_name: str
    state_library_name: Optional[str] = None
    due_date: str
    days_until_due: int
    report_template: Optional[str] = None


class PatronNotificationRequirements(BaseModel):
    notification_required: bool
    notification_allowed: bool
    delay_days: int
    state_code: Optional[str] = None
    confidentiality_strength: Optional[str] = None


# =============================================================================
# Helper Functions
# =============================================================================


def require_staff_or_higher(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )
    return current_user


def require_director_or_higher(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Director access required"
        )
    return current_user


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/states", response_model=List[dict])
async def list_configured_states(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    List all configured states.

    Returns basic info about each state's compliance configuration.
    """
    service = StateComplianceService(db)
    configs = await service.get_all_state_configs()

    return [
        {
            "state_code": c.state_code,
            "state_name": c.state_name,
            "confidentiality_strength": str(c.confidentiality_strength),
            "confidentiality_statute": c.confidentiality_statute,
            "last_reviewed": c.last_reviewed_at.isoformat() if c.last_reviewed_at else None,
        }
        for c in configs
    ]


@router.get("/states/{state_code}", response_model=StateComplianceSummary)
async def get_state_compliance_summary(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get complete compliance summary for a state.

    Returns all compliance requirements including confidentiality,
    retention, law enforcement, reporting, ID verification, and accessibility.
    """
    service = StateComplianceService(db)
    summary = await service.get_full_compliance_summary(state_code.upper())

    if not summary.get("configured"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No compliance configuration for state {state_code.upper()}"
        )

    return StateComplianceSummary(**summary)


@router.post("/validate-disclosure", response_model=DisclosureValidationResponse)
async def validate_disclosure_request(
    request: DisclosureValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Validate whether a disclosure request meets state requirements.

    This endpoint should be called when processing law enforcement requests
    to verify that the request meets the state's legal requirements.

    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    result = await service.validate_disclosure_request(
        state_code=request.state_code.upper(),
        request_type=request.request_type,
        record_type=request.record_type,
        has_court_order=request.has_court_order,
        has_subpoena=request.has_subpoena,
        has_warrant=request.has_warrant,
        is_grand_jury=request.is_grand_jury,
    )

    return DisclosureValidationResponse(**result)


@router.get("/states/{state_code}/retention", response_model=RetentionPeriods)
async def get_retention_periods(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get data retention periods for a state.

    Returns state-specific overrides or system defaults.
    """
    service = StateComplianceService(db)
    periods = await service.get_retention_periods(state_code.upper())
    return RetentionPeriods(**periods)


@router.get("/states/{state_code}/law-enforcement", response_model=dict)
async def get_law_enforcement_requirements(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Get law enforcement response requirements for a state.

    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    return await service.get_le_response_requirements(state_code.upper())


@router.get("/states/{state_code}/notification", response_model=PatronNotificationRequirements)
async def get_patron_notification_requirements(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Get patron notification requirements for a state.

    Determines whether patrons must or can be notified when their
    records are disclosed to law enforcement.

    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    result = await service.get_patron_notification_requirements(state_code.upper())
    return PatronNotificationRequirements(**result)


@router.get("/states/{state_code}/reporting", response_model=ReportingRequirements)
async def get_reporting_requirements(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get state library reporting requirements.

    Returns information about required reports, deadlines, and templates.
    """
    service = StateComplianceService(db)
    result = await service.get_reporting_requirements(state_code.upper())
    return ReportingRequirements(**result)


@router.get("/deadlines", response_model=List[UpcomingDeadline])
async def get_upcoming_report_deadlines(
    days_ahead: int = Query(90, ge=1, le=365, description="Number of days to look ahead"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get upcoming state library report deadlines.

    Returns a list of upcoming deadlines sorted by due date.
    """
    service = StateComplianceService(db)
    deadlines = await service.get_upcoming_report_deadlines(days_ahead)
    return [UpcomingDeadline(**d) for d in deadlines]


@router.get("/states/{state_code}/id-verification", response_model=dict)
async def get_id_verification_requirements(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get ID verification requirements for library card registration.

    Returns requirements for photo ID, residency proof, and accepted document types.
    """
    service = StateComplianceService(db)
    return await service.get_id_verification_requirements(state_code.upper())


@router.post("/validate-registration", response_model=RegistrationValidationResponse)
async def validate_registration_documents(
    request: RegistrationValidationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Validate registration documents against state requirements.

    Call this when processing new patron registrations to verify
    that all required documents have been provided.
    """
    service = StateComplianceService(db)
    result = await service.validate_registration_documents(
        state_code=request.state_code.upper(),
        age=request.age,
        has_photo_id=request.has_photo_id,
        photo_id_type=request.photo_id_type,
        has_residency_proof=request.has_residency_proof,
        residency_proof_type=request.residency_proof_type,
    )
    return RegistrationValidationResponse(**result)


@router.get("/states/{state_code}/accessibility", response_model=dict)
async def get_accessibility_requirements(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get state-specific accessibility requirements beyond federal ADA.

    Returns any additional state-level accessibility laws and notes.
    """
    service = StateComplianceService(db)
    return await service.get_accessibility_requirements(state_code.upper())


@router.post("/initialize-defaults", status_code=status.HTTP_201_CREATED)
async def initialize_default_configurations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
    _guard: User = Depends(require_admin),
):
    """
    Initialize default state compliance configurations.

    Creates default configurations for major states (CA, TX, NY, FL, IL).
    Only creates configurations that don't already exist.

    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    created = await service.initialize_default_configs()

    return {
        "message": f"Initialized {created} state compliance configurations",
        "created_count": created,
    }


# =============================================================================
# Local (County/Municipal) Compliance Endpoints
# =============================================================================


@router.get("/local/{state_code}", response_model=List[dict])
async def list_local_configs_for_state(
    state_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    List all local compliance configurations for a state.

    Returns county, city, and district-level compliance overrides.
    """
    service = StateComplianceService(db)
    configs = await service.get_local_configs_for_state(state_code.upper())

    return [
        {
            "id": c.id,
            "jurisdiction_type": c.jurisdiction_type,
            "jurisdiction_name": c.jurisdiction_name,
            "jurisdiction_code": c.jurisdiction_code,
            "has_privacy_override": c.privacy_stricter_than_state,
            "has_retention_override": c.local_retention_override,
            "sanctuary_city": c.sanctuary_city_policies,
            "is_active": c.is_active,
        }
        for c in configs
    ]


@router.get("/effective/{state_code}", response_model=dict)
async def get_effective_compliance(
    state_code: str,
    jurisdiction: Optional[str] = Query(None, description="Local jurisdiction name"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get effective compliance requirements combining state and local.

    When a jurisdiction is specified, local requirements override
    state requirements where applicable (stricter takes precedence).
    """
    service = StateComplianceService(db)
    return await service.get_effective_compliance(state_code.upper(), jurisdiction)


# =============================================================================
# Regulation Monitoring Endpoints
# =============================================================================


@router.get("/regulations", response_model=List[dict])
async def list_regulations(
    jurisdiction_type: Optional[str] = Query(None, description="federal, state, or local"),
    jurisdiction_code: Optional[str] = Query(None, description="State code for state/local"),
    status_filter: Optional[str] = Query(None, description="Filter by status: proposed, pending, enacted, effective, repealed"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    List tracked regulations with optional filters.

    Returns regulations being monitored for compliance changes.
    """
    from ...models.state_compliance import RegulationChangeStatus

    status_enum = None
    if status_filter:
        try:
            status_enum = RegulationChangeStatus(status_filter)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status: {status_filter}"
            ) from None

    service = StateComplianceService(db)
    regulations = await service.get_active_regulations(
        jurisdiction_type=jurisdiction_type,
        jurisdiction_code=jurisdiction_code,
        status=status_enum,
    )

    return [
        {
            "id": r.id,
            "regulation_name": r.regulation_name,
            "regulation_number": r.regulation_number,
            "jurisdiction_type": r.jurisdiction_type,
            "jurisdiction_code": r.jurisdiction_code,
            "source": str(r.source),
            "status": str(r.status),
            "effective_date": r.effective_date.isoformat() if r.effective_date else None,
            "priority": r.priority,
            "requires_action": r.requires_action,
            "action_deadline": r.action_deadline.isoformat() if r.action_deadline else None,
        }
        for r in regulations
    ]


@router.get("/regulations/requiring-action", response_model=List[dict])
async def list_regulations_requiring_action(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    List regulations that require action.

    Returns regulations with pending action items that haven't been reviewed.
    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    regulations = await service.get_regulations_requiring_action()

    return [
        {
            "id": r.id,
            "regulation_name": r.regulation_name,
            "regulation_number": r.regulation_number,
            "jurisdiction_type": r.jurisdiction_type,
            "priority": r.priority,
            "action_deadline": r.action_deadline.isoformat() if r.action_deadline else None,
            "action_notes": r.action_notes,
            "affects": {
                "patron_privacy": r.affects_patron_privacy,
                "data_retention": r.affects_data_retention,
                "law_enforcement": r.affects_law_enforcement,
                "accessibility": r.affects_accessibility,
            },
        }
        for r in regulations
    ]


@router.get("/regulations/deadlines", response_model=List[dict])
async def get_regulation_deadlines(
    days_ahead: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get upcoming regulation action deadlines.

    Returns deadlines within the specified number of days, including overdue items.
    """
    service = StateComplianceService(db)
    return await service.check_regulation_deadlines(days_ahead)


@router.get("/alerts", response_model=List[dict])
async def list_unresolved_alerts(
    priority: Optional[str] = Query(None, description="critical, high, medium, low"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    List unresolved regulation alerts.

    Returns alerts that haven't been resolved, optionally filtered by priority.
    """
    service = StateComplianceService(db)
    alerts = await service.get_unresolved_alerts(priority=priority)

    return [
        {
            "id": a.id,
            "regulation_monitor_id": a.regulation_monitor_id,
            "alert_type": a.alert_type,
            "title": a.title,
            "description": a.description,
            "priority": a.priority,
            "assigned_to_id": a.assigned_to_id,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in alerts
    ]


@router.post("/alerts/{alert_id}/resolve")
async def resolve_regulation_alert(
    alert_id: int,
    resolution_notes: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Mark a regulation alert as resolved.

    Requires DIRECTOR or higher access.
    """
    service = StateComplianceService(db)
    try:
        alert = await service.resolve_alert(
            alert_id=alert_id,
            resolved_by_id=current_user.id,
            resolution_notes=resolution_notes,
        )
        return {
            "message": "Alert resolved",
            "alert_id": alert.id,
            "resolved_at": alert.resolved_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


# =============================================================================
# Compliance Dashboard Endpoints
# =============================================================================


@router.get("/dashboard", response_model=dict)
async def get_compliance_dashboard(
    state_code: Optional[str] = Query(None, description="Filter by state"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get compliance dashboard data.

    Returns aggregated compliance data including deadlines, alerts,
    compliance scores, and status summaries.
    """
    service = StateComplianceService(db)
    return await service.get_compliance_dashboard_data(
        user_id=current_user.id,
        state_code=state_code.upper() if state_code else None,
    )


@router.put("/dashboard/config", response_model=dict)
async def update_dashboard_config(
    enabled_widgets: Optional[List[str]] = None,
    email_alerts_enabled: Optional[bool] = None,
    alert_frequency: Optional[str] = None,
    default_state_filter: Optional[str] = None,
    default_date_range_days: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Update user's compliance dashboard configuration.

    Allows customizing which widgets to display and alert preferences.
    """
    service = StateComplianceService(db)
    kwargs = {}
    if enabled_widgets is not None:
        kwargs["enabled_widgets"] = enabled_widgets
    if email_alerts_enabled is not None:
        kwargs["email_alerts_enabled"] = email_alerts_enabled
    if alert_frequency is not None:
        kwargs["alert_frequency"] = alert_frequency
    if default_state_filter is not None:
        kwargs["default_state_filter"] = default_state_filter.upper()
    if default_date_range_days is not None:
        kwargs["default_date_range_days"] = default_date_range_days

    config = await service.create_or_update_dashboard_config(
        user_id=current_user.id, **kwargs
    )

    return {
        "message": "Dashboard configuration updated",
        "enabled_widgets": config.enabled_widgets,
        "email_alerts_enabled": config.email_alerts_enabled,
        "alert_frequency": config.alert_frequency,
    }


# =============================================================================
# VPAT (Accessibility) Endpoints
# =============================================================================


@router.get("/vpat/current", response_model=dict)
async def get_current_vpat(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get the current VPAT report.

    Returns the most recent VPAT (Voluntary Product Accessibility Template)
    accessibility conformance report.
    """
    service = StateComplianceService(db)
    vpat = await service.get_current_vpat()

    if not vpat:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No VPAT report found"
        )

    return {
        "id": vpat.id,
        "report_name": vpat.report_name,
        "report_version": vpat.report_version,
        "product_name": vpat.product_name,
        "product_version": vpat.product_version,
        "evaluation_date": vpat.evaluation_date.isoformat(),
        "overall_conformance": str(vpat.overall_conformance),
        "wcag_version": vpat.wcag_version,
        "wcag_level": vpat.wcag_level,
        "is_current": vpat.is_current,
    }


@router.get("/vpat/{vpat_id}/document", response_model=dict)
async def get_vpat_document(
    vpat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Generate a complete VPAT document.

    Returns the full VPAT document structure that can be rendered
    to HTML, PDF, or other formats.
    """
    service = StateComplianceService(db)
    try:
        return await service.generate_vpat_document(vpat_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


class CreateVPATRequest(BaseModel):
    report_name: str = Field(..., min_length=1, max_length=255)
    report_version: str = Field(..., min_length=1, max_length=20)
    evaluation_date: date
    product_version: Optional[str] = None
    evaluator_name: Optional[str] = None
    evaluator_organization: Optional[str] = None
    wcag_version: str = "2.1"
    wcag_level: str = "AA"
    initialize_criteria: bool = True


@router.post("/vpat", status_code=status.HTTP_201_CREATED, response_model=dict)
async def create_vpat_report(
    request: CreateVPATRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Create a new VPAT report.

    Creates a new VPAT accessibility conformance report. If initialize_criteria
    is True, populates the report with all WCAG 2.1 AA criteria.

    Requires DIRECTOR or higher access.
    """
    from ...models.state_compliance import VPATConformanceLevel

    service = StateComplianceService(db)
    vpat = await service.create_vpat_report(
        report_name=request.report_name,
        report_version=request.report_version,
        evaluation_date=request.evaluation_date,
        created_by_id=current_user.id,
        product_version=request.product_version,
        evaluator_name=request.evaluator_name,
        evaluator_organization=request.evaluator_organization,
        wcag_version=request.wcag_version,
        wcag_level=request.wcag_level,
    )

    criteria_count = 0
    if request.initialize_criteria:
        criteria_count = await service.initialize_vpat_with_default_criteria(
            vpat_report_id=vpat.id,
            default_conformance=VPATConformanceLevel.NOT_EVALUATED,
        )

    return {
        "id": vpat.id,
        "report_name": vpat.report_name,
        "report_version": vpat.report_version,
        "criteria_initialized": criteria_count,
        "message": f"VPAT report created with {criteria_count} criteria",
    }


@router.get("/vpat/{vpat_id}/criteria", response_model=List[dict])
async def get_vpat_criteria(
    vpat_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """
    Get all criteria for a VPAT report.

    Returns the evaluation status for each WCAG criterion.
    """
    service = StateComplianceService(db)
    criteria = await service.get_vpat_criteria(vpat_id)

    return [
        {
            "id": c.id,
            "standard": c.standard,
            "criterion_id": c.criterion_id,
            "criterion_name": c.criterion_name,
            "level": c.level,
            "conformance_level": str(c.conformance_level),
            "remarks": c.remarks,
        }
        for c in criteria
    ]


class UpdateVPATCriterionRequest(BaseModel):
    conformance_level: str = Field(..., description="supports, partially_supports, does_not_support, not_applicable")
    remarks: Optional[str] = None


@router.put("/vpat/criteria/{criterion_id}", response_model=dict)
async def update_vpat_criterion(
    criterion_id: int,
    request: UpdateVPATCriterionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_director_or_higher),
):
    """
    Update a VPAT criterion evaluation.

    Sets the conformance level and remarks for a specific criterion.
    Requires DIRECTOR or higher access.
    """
    from sqlalchemy import select
    from ...models.state_compliance import VPATConformanceLevel, VPATCriterion

    try:
        conformance = VPATConformanceLevel(request.conformance_level)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conformance level: {request.conformance_level}"
        ) from None

    result = await db.execute(
        select(VPATCriterion).where(VPATCriterion.id == criterion_id)
    )
    criterion = result.scalar_one_or_none()

    if not criterion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Criterion {criterion_id} not found"
        )

    criterion.conformance_level = conformance
    criterion.remarks = request.remarks
    await db.commit()

    return {
        "id": criterion.id,
        "criterion_id": criterion.criterion_id,
        "conformance_level": str(criterion.conformance_level),
        "remarks": criterion.remarks,
        "message": "Criterion updated",
    }


@router.get("/dashboard/config", response_model=dict)
async def get_dashboard_config(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff_or_higher),
):
    """Get the current user's compliance dashboard configuration."""
    service = StateComplianceService(db)
    config = await service.get_dashboard_config(user_id=current_user.id)
    if not config:
        return {
            "configured": False,
            "enabled_widgets": [],
            "email_alerts_enabled": False,
            "alert_frequency": "weekly",
        }
    return {
        "configured": True,
        "enabled_widgets": config.enabled_widgets,
        "email_alerts_enabled": config.email_alerts_enabled,
        "alert_frequency": config.alert_frequency,
    }




