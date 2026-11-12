# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Medical Emergency Alerts API Endpoints

Provides endpoints for staff to trigger, view, and manage medical emergency responses:
- Trigger medical emergencies (cardiac, respiratory, severe injury, etc.)
- View active emergencies and response status
- Call emergency services (911) with medical context
- Access nearby AED and first aid kit locations
- Retrieve staff with medical training
- Access patron medical information (if available)
- Manage emergency response (stabilized, transferred, resolved)
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.emergency_alert import (
    MedicalEmergencyAlert, EmergencyAlertType, EmergencyAlertStatus, EmergencyAlertSeverity
)
from ....models.user import User
from ....services.medical_emergency_service import (
    trigger_medical_emergency_alert,
    call_emergency_services,
    get_staff_with_medical_training,
    get_patron_medical_info,
    get_aed_locations,
    get_first_aid_kit_locations,
    resolve_emergency_alert,
    get_active_emergencies,
    record_aed_usage,
)
from ..auth import get_current_user
from ..dependencies import require_staff

router = APIRouter(prefix="/staff", tags=["staff-medical-emergencies"])


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class MedicalContextRequest(BaseModel):
    symptoms: Optional[List[str]] = None
    consciousness_level: Optional[str] = None  # alert, responsive, unresponsive
    breathing: Optional[str] = None  # normal, distressed, absent
    chest_pain: Optional[bool] = None
    severe_bleeding: Optional[bool] = None
    notes: Optional[str] = None


class TriggerMedicalEmergencyRequest(BaseModel):
    emergency_type: EmergencyAlertType = Field(..., description="Type of medical emergency")
    location: str = Field(..., description="Physical location (e.g., 'Main Branch - Reading Room 3A')")
    branch_id: Optional[int] = Field(None, description="Branch ID where emergency occurred")
    patron_id: Optional[int] = Field(None, description="ID of affected patron (if known)")
    caller_description: Optional[str] = Field(None, description="Witness account of situation")
    medical_context: Optional[MedicalContextRequest] = None


class CallEmergencyServicesRequest(BaseModel):
    alert_id: int = Field(..., description="ID of the emergency alert")
    eta_minutes: Optional[int] = Field(None, description="ETA provided by 911 dispatch")


class ResolveEmergencyRequest(BaseModel):
    status: EmergencyAlertStatus = Field(..., description="New status for emergency")
    notes: Optional[str] = None


class StaffMedicalInfo(BaseModel):
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    qualifications: List[str]
    available_for_response: bool
    notes: Optional[str] = None


class PatronMedicalAlertInfo(BaseModel):
    allergies: Optional[str] = None
    medical_conditions: Optional[str] = None
    medications: Optional[str] = None
    medical_notes: Optional[str] = None
    emergency_contact_1_name: Optional[str] = None
    emergency_contact_1_phone: Optional[str] = None
    emergency_contact_1_relationship: Optional[str] = None
    emergency_contact_2_name: Optional[str] = None
    emergency_contact_2_phone: Optional[str] = None
    emergency_contact_2_relationship: Optional[str] = None
    primary_physician_name: Optional[str] = None
    primary_physician_phone: Optional[str] = None


class AEDLocationInfo(BaseModel):
    id: int
    location_description: str
    room_number: Optional[str] = None
    floor: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    access_instructions: Optional[str] = None
    visible_signage: bool
    directional_signage: bool
    last_inspection: Optional[str] = None


class FirstAidKitInfo(BaseModel):
    id: int
    location_description: str
    room_number: Optional[str] = None
    floor: Optional[str] = None
    access_instructions: Optional[str] = None
    visible_signage: bool
    kit_type: str
    staff_trained: bool
    last_checked: Optional[str] = None


class EmergencyAlertResponse(BaseModel):
    id: int
    emergency_type: EmergencyAlertType
    severity: EmergencyAlertSeverity
    status: EmergencyAlertStatus
    location: str
    branch_id: Optional[int] = None
    patron_id: Optional[int] = None
    caller_description: Optional[str] = None
    emergency_services_called: bool
    emergency_services_eta_minutes: Optional[int] = None
    aed_used: bool
    created_at: datetime
    emergency_services_called_at: Optional[datetime] = None


class MedicalEmergencyResponsePackage(BaseModel):
    alert: EmergencyAlertResponse
    nearest_aeds: List[AEDLocationInfo]
    nearest_first_aid_kits: List[FirstAidKitInfo]
    trained_staff: List[StaffMedicalInfo]
    patron_medical_info: Optional[PatronMedicalAlertInfo] = None


class ActiveEmergenciesResponse(BaseModel):
    emergencies: List[EmergencyAlertResponse]
    total_active: int
    life_threatening_count: int
    urgent_count: int
    serious_count: int


# ============================================================================
# Emergency Alert Endpoints
# ============================================================================

@router.post("/medical-emergency", response_model=EmergencyAlertResponse, status_code=status.HTTP_201_CREATED)
async def trigger_medical_emergency(
    request: TriggerMedicalEmergencyRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a medical emergency alert.

    This alerts trained staff, pulls up patron medical info (if available),
    displays nearby AED/first aid kit locations, and facilitates 911 coordination.

    **Different emergency, different response**:
    - Cardiac events and unconscious patients = LIFE_THREATENING
    - Respiratory distress and allergic reactions = URGENT
    - Other medical issues = SERIOUS
    """
    medical_context = None
    if request.medical_context:
        medical_context = request.medical_context.dict(exclude_none=True)

    alert = await trigger_medical_emergency_alert(
        db=db,
        emergency_type=request.emergency_type,
        location=request.location,
        branch_id=request.branch_id,
        patron_id=request.patron_id,
        caller_id=staff_user.id,
        caller_description=request.caller_description,
        medical_context=medical_context,
        created_by_id=staff_user.id,
    )

    await db.commit()

    return EmergencyAlertResponse(
        id=alert.id,
        emergency_type=alert.emergency_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        branch_id=alert.branch_id,
        patron_id=alert.patron_id,
        caller_description=alert.caller_description,
        emergency_services_called=alert.emergency_services_called,
        emergency_services_eta_minutes=alert.emergency_services_eta_minutes,
        aed_used=alert.aed_used,
        created_at=alert.created_at,
        emergency_services_called_at=alert.emergency_services_called_at,
    )


@router.post("/medical-emergency/{alert_id}/call-911", response_model=EmergencyAlertResponse)
async def call_911_for_emergency(
    alert_id: int,
    request: CallEmergencyServicesRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Call 911 for a medical emergency with auto-dial context.

    This records that emergency services have been called and tracks ETA.
    In a real implementation, this could trigger actual 911 dialing with
    medical emergency classification and location.
    """
    alert = await call_emergency_services(
        db=db,
        alert_id=alert_id,
        eta_minutes=request.eta_minutes,
    )

    await db.commit()

    return EmergencyAlertResponse(
        id=alert.id,
        emergency_type=alert.emergency_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        branch_id=alert.branch_id,
        patron_id=alert.patron_id,
        caller_description=alert.caller_description,
        emergency_services_called=alert.emergency_services_called,
        emergency_services_eta_minutes=alert.emergency_services_eta_minutes,
        aed_used=alert.aed_used,
        created_at=alert.created_at,
        emergency_services_called_at=alert.emergency_services_called_at,
    )


@router.get("/medical-emergency/{alert_id}/response-package", response_model=MedicalEmergencyResponsePackage)
async def get_emergency_response_package(
    alert_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get complete emergency response information package.

    Returns:
    - The emergency alert details
    - Nearest AED locations with access instructions
    - Nearest first aid kit locations
    - Staff with medical training (CPR, First Aid, AED trained)
    - Patron's medical information (allergies, conditions) if available
    """
    # Fetch the alert
    from sqlalchemy import select
    alert = await get_or_404(db, MedicalEmergencyAlert, alert_id, "Emergency alert not found")

    # Get response resources
    aeds = await get_aed_locations(db, branch_id=alert.branch_id, in_service_only=True)
    first_aid_kits = await get_first_aid_kit_locations(
        db, branch_id=alert.branch_id, in_service_only=True
    )
    trained_staff = await get_staff_with_medical_training(
        db, branch_id=alert.branch_id
    )

    # Get patron medical info if available and patron is known
    patron_medical_info = None
    if alert.patron_id:
        patron_info_dict = await get_patron_medical_info(db, alert.patron_id)
        if patron_info_dict:
            patron_medical_info = PatronMedicalAlertInfo(
                allergies=patron_info_dict.get("allergies"),
                medical_conditions=patron_info_dict.get("medical_conditions"),
                medications=patron_info_dict.get("medications"),
                medical_notes=patron_info_dict.get("medical_notes"),
            )
            # Add emergency contacts if available
            if patron_info_dict.get("emergency_contacts"):
                contacts = patron_info_dict["emergency_contacts"]
                if contacts[0]:
                    patron_medical_info.emergency_contact_1_name = contacts[0].get("name")
                    patron_medical_info.emergency_contact_1_phone = contacts[0].get("phone")
                    patron_medical_info.emergency_contact_1_relationship = contacts[0].get("relationship")
                if len(contacts) > 1 and contacts[1]:
                    patron_medical_info.emergency_contact_2_name = contacts[1].get("name")
                    patron_medical_info.emergency_contact_2_phone = contacts[1].get("phone")
                    patron_medical_info.emergency_contact_2_relationship = contacts[1].get("relationship")

    alert_response = EmergencyAlertResponse(
        id=alert.id,
        emergency_type=alert.emergency_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        branch_id=alert.branch_id,
        patron_id=alert.patron_id,
        caller_description=alert.caller_description,
        emergency_services_called=alert.emergency_services_called,
        emergency_services_eta_minutes=alert.emergency_services_eta_minutes,
        aed_used=alert.aed_used,
        created_at=alert.created_at,
        emergency_services_called_at=alert.emergency_services_called_at,
    )

    return MedicalEmergencyResponsePackage(
        alert=alert_response,
        nearest_aeds=[AEDLocationInfo(**aed) for aed in aeds],
        nearest_first_aid_kits=[FirstAidKitInfo(**kit) for kit in first_aid_kits],
        trained_staff=[
            StaffMedicalInfo(
                id=staff["id"],
                name=staff["name"],
                email=staff["email"],
                phone=staff["phone"],
                qualifications=staff["qualifications"],
                available_for_response=staff["available_for_response"],
                notes=staff["notes"],
            )
            for staff in trained_staff
        ],
        patron_medical_info=patron_medical_info,
    )


@router.get("/medical-emergency/active", response_model=ActiveEmergenciesResponse)
async def list_active_emergencies(
    branch_id: Optional[int] = Query(None, description="Filter by branch"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all active medical emergencies (for monitoring/dashboard).
    Useful for coordination center view.
    """
    emergencies = await get_active_emergencies(db, branch_id=branch_id)

    life_threatening = sum(1 for e in emergencies if e.severity == EmergencyAlertSeverity.LIFE_THREATENING)
    urgent = sum(1 for e in emergencies if e.severity == EmergencyAlertSeverity.URGENT)
    serious = sum(1 for e in emergencies if e.severity == EmergencyAlertSeverity.SERIOUS)

    return ActiveEmergenciesResponse(
        emergencies=[
            EmergencyAlertResponse(
                id=e.id,
                emergency_type=e.emergency_type,
                severity=e.severity,
                status=e.status,
                location=e.location,
                branch_id=e.branch_id,
                patron_id=e.patron_id,
                caller_description=e.caller_description,
                emergency_services_called=e.emergency_services_called,
                emergency_services_eta_minutes=e.emergency_services_eta_minutes,
                aed_used=e.aed_used,
                created_at=e.created_at,
                emergency_services_called_at=e.emergency_services_called_at,
            )
            for e in emergencies
        ],
        total_active=len(emergencies),
        life_threatening_count=life_threatening,
        urgent_count=urgent,
        serious_count=serious,
    )


@router.post("/medical-emergency/{alert_id}/resolve", response_model=EmergencyAlertResponse)
async def resolve_emergency(
    alert_id: int,
    request: ResolveEmergencyRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve/close a medical emergency alert.
    Status options: STABILIZED (patient stable), TRANSFERRED (to hospital), RESOLVED (no longer needed)
    """
    alert = await resolve_emergency_alert(
        db=db,
        alert_id=alert_id,
        status=request.status,
        resolved_by_id=staff_user.id,
    )

    await db.commit()

    return EmergencyAlertResponse(
        id=alert.id,
        emergency_type=alert.emergency_type,
        severity=alert.severity,
        status=alert.status,
        location=alert.location,
        branch_id=alert.branch_id,
        patron_id=alert.patron_id,
        caller_description=alert.caller_description,
        emergency_services_called=alert.emergency_services_called,
        emergency_services_eta_minutes=alert.emergency_services_eta_minutes,
        aed_used=alert.aed_used,
        created_at=alert.created_at,
        emergency_services_called_at=alert.emergency_services_called_at,
    )


@router.post("/medical-emergency/{alert_id}/record-aed-usage")
async def record_aed_deployed(
    alert_id: int,
    aed_location_id: int = Query(..., description="ID of AED that was used"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Record that AED was deployed for this emergency"""
    alert = await record_aed_usage(db, alert_id, aed_location_id)
    await db.commit()

    return {
        "success": True,
        "alert_id": alert.id,
        "aed_used": alert.aed_used,
        "aed_location_id": alert.aed_location_id,
    }


# ============================================================================
# Information Lookup Endpoints
# ============================================================================

@router.get("/medical-training/staff", response_model=List[StaffMedicalInfo])
async def get_trained_staff(
    branch_id: Optional[int] = Query(None, description="Filter by branch"),
    training_type: Optional[str] = Query(None, description="Filter by training type (cpr, first_aid, aed)"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get staff with medical training and certifications.

    Useful for:
    - Finding available responders during emergency
    - Identifying staff who can provide CPR, first aid, AED assistance
    - Planning training and certification renewal
    """
    trained_staff = await get_staff_with_medical_training(
        db, branch_id=branch_id, training_type=training_type
    )

    return [
        StaffMedicalInfo(
            id=staff["id"],
            name=staff["name"],
            email=staff["email"],
            phone=staff["phone"],
            qualifications=staff["qualifications"],
            available_for_response=staff["available_for_response"],
            notes=staff["notes"],
        )
        for staff in trained_staff
    ]


@router.get("/aed-locations", response_model=List[AEDLocationInfo])
async def get_aed_locations_endpoint(
    branch_id: Optional[int] = Query(None, description="Filter by branch"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get AED locations.

    Response includes:
    - Location description and room/floor info
    - Access instructions (for locked cases, codes, etc.)
    - Signage visibility (helps locate quickly)
    - Last inspection date (maintenance tracking)
    """
    aeds = await get_aed_locations(db, branch_id=branch_id, in_service_only=True)
    return [AEDLocationInfo(**aed) for aed in aeds]


@router.get("/first-aid-kit-locations", response_model=List[FirstAidKitInfo])
async def get_first_aid_kit_locations_endpoint(
    branch_id: Optional[int] = Query(None, description="Filter by branch"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get first aid kit locations.

    Response includes:
    - Kit location and access information
    - Kit type (standard, comprehensive, portable)
    - Staff trained flag (who knows how to use the kit)
    - Last checked date (ensures supplies are current)
    """
    kits = await get_first_aid_kit_locations(
        db, branch_id=branch_id, in_service_only=True
    )
    return [FirstAidKitInfo(**kit) for kit in kits]
