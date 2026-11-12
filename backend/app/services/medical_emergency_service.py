# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from sqlalchemy import and_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.emergency_alert import (
    MedicalEmergencyAlert, EmergencyAlertType, EmergencyAlertStatus, EmergencyAlertSeverity,
    StaffMedicalTraining, PatronMedicalInfo, AEDLocation, FirstAidKitLocation
)
from ..models.user import User, UserRole
from ..models.multi_branch import Branch


async def trigger_medical_emergency_alert(
    db: AsyncSession,
    emergency_type: EmergencyAlertType,
    location: str,
    branch_id: Optional[int],
    patron_id: Optional[int] = None,
    caller_id: Optional[int] = None,
    caller_description: Optional[str] = None,
    medical_context: Optional[Dict[str, Any]] = None,
    created_by_id: Optional[int] = None,
) -> MedicalEmergencyAlert:
    # Determine severity based on emergency type
    severity = _determine_emergency_severity(emergency_type)

    alert = MedicalEmergencyAlert(
        emergency_type=emergency_type,
        severity=severity,
        location=location,
        branch_id=branch_id,
        patron_id=patron_id,
        caller_id=caller_id,
        caller_description=caller_description,
        medical_context=json.dumps(medical_context) if medical_context else None,
        status=EmergencyAlertStatus.ACTIVE,
        created_by_id=created_by_id,
    )

    db.add(alert)
    await db.flush()
    return alert


def _determine_emergency_severity(emergency_type: EmergencyAlertType) -> EmergencyAlertSeverity:
    life_threatening_types = {
        EmergencyAlertType.CARDIAC_EVENT,
        EmergencyAlertType.UNCONSCIOUS_UNRESPONSIVE,
        EmergencyAlertType.SEVERE_INJURY,
    }

    if emergency_type in life_threatening_types:
        return EmergencyAlertSeverity.LIFE_THREATENING
    elif emergency_type in {
        EmergencyAlertType.RESPIRATORY_DISTRESS,
        EmergencyAlertType.ALLERGIC_REACTION,
    }:
        return EmergencyAlertSeverity.URGENT
    else:
        return EmergencyAlertSeverity.SERIOUS


async def call_emergency_services(
    db: AsyncSession,
    alert_id: int,
    eta_minutes: Optional[int] = None,
) -> MedicalEmergencyAlert:
    result = await db.execute(
        select(MedicalEmergencyAlert).where(MedicalEmergencyAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert:
        alert.emergency_services_called = True
        alert.emergency_services_called_at = datetime.now(timezone.utc)
        alert.emergency_services_eta_minutes = eta_minutes
        alert.status = EmergencyAlertStatus.EMERGENCY_SERVICES_CALLED
        await db.flush()

    return alert


async def get_staff_with_medical_training(
    db: AsyncSession,
    branch_id: Optional[int] = None,
    training_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    query = select(User, StaffMedicalTraining).join(
        StaffMedicalTraining,
        StaffMedicalTraining.staff_id == User.id
    ).where(
        User.role == UserRole.STAFF,
        StaffMedicalTraining.available_for_emergency_response == True
    )

    if branch_id:
        query = query.where(User.work_branch_id == branch_id)

    results = await db.execute(query)
    staff_training_pairs = results.all()

    staff_list = []
    for user, training in staff_training_pairs:
        training_qualifications = []

        if training.cpr_certified:
            if training.cpr_expiration_date and training.cpr_expiration_date > datetime.now(timezone.utc):
                training_qualifications.append("CPR (Certified)")

        if training.first_aid_certified:
            if training.first_aid_expiration_date and training.first_aid_expiration_date > datetime.now(timezone.utc):
                training_qualifications.append("First Aid (Certified)")

        if training.aed_trained:
            training_qualifications.append("AED Trained")

        if training_type:
            if training_type.lower() == "cpr" and not ("CPR" in " ".join(training_qualifications)):
                continue
            if training_type.lower() == "first_aid" and not ("First Aid" in " ".join(training_qualifications)):
                continue
            if training_type.lower() == "aed" and "AED" not in " ".join(training_qualifications):
                continue

        staff_list.append({
            "id": user.id,
            "name": f"{user.first_name} {user.last_name}",
            "email": user.email,
            "phone": user.phone,
            "branch_id": user.work_branch_id,
            "qualifications": training_qualifications,
            "available_for_response": training.available_for_emergency_response,
            "notes": training.medical_response_notes,
        })

    return staff_list


async def get_patron_medical_info(
    db: AsyncSession,
    patron_id: int,
) -> Optional[Dict[str, Any]]:
    result = await db.execute(
        select(PatronMedicalInfo).where(
            PatronMedicalInfo.patron_id == patron_id,
            PatronMedicalInfo.visible_to_staff == True
        )
    )
    medical_info = result.scalar_one_or_none()

    if not medical_info:
        return None

    return {
        "id": medical_info.id,
        "patron_id": medical_info.patron_id,
        "allergies": medical_info.allergies,
        "medical_conditions": medical_info.medical_conditions,
        "medications": medical_info.medications,
        "medical_notes": medical_info.medical_notes,
        "emergency_contacts": [
            {
                "name": medical_info.emergency_contact_1_name,
                "phone": medical_info.emergency_contact_1_phone,
                "relationship": medical_info.emergency_contact_1_relationship,
            } if medical_info.emergency_contact_1_name else None,
            {
                "name": medical_info.emergency_contact_2_name,
                "phone": medical_info.emergency_contact_2_phone,
                "relationship": medical_info.emergency_contact_2_relationship,
            } if medical_info.emergency_contact_2_name else None,
        ],
        "primary_physician": {
            "name": medical_info.primary_physician_name,
            "phone": medical_info.primary_physician_phone,
            "medical_record_number": medical_info.medical_record_number,
        } if medical_info.primary_physician_name else None,
    }


async def get_aed_locations(
    db: AsyncSession,
    branch_id: Optional[int] = None,
    in_service_only: bool = True,
) -> List[Dict[str, Any]]:
    query = select(AEDLocation)

    if branch_id:
        query = query.where(AEDLocation.branch_id == branch_id)

    if in_service_only:
        query = query.where(AEDLocation.in_service == True)

    results = await db.execute(query)
    locations = results.scalars().all()

    return [
        {
            "id": loc.id,
            "location_description": loc.location_description,
            "room_number": loc.room_number,
            "floor": loc.floor,
            "latitude": loc.latitude,
            "longitude": loc.longitude,
            "access_instructions": loc.access_instructions,
            "visible_signage": loc.visible_signage,
            "directional_signage": loc.directional_signage,
            "last_inspection": loc.last_inspection_date.isoformat() if loc.last_inspection_date else None,
        }
        for loc in locations
    ]


async def get_first_aid_kit_locations(
    db: AsyncSession,
    branch_id: Optional[int] = None,
    in_service_only: bool = True,
) -> List[Dict[str, Any]]:
    query = select(FirstAidKitLocation)

    if branch_id:
        query = query.where(FirstAidKitLocation.branch_id == branch_id)

    if in_service_only:
        query = query.where(FirstAidKitLocation.in_service == True)

    results = await db.execute(query)
    locations = results.scalars().all()

    return [
        {
            "id": loc.id,
            "location_description": loc.location_description,
            "room_number": loc.room_number,
            "floor": loc.floor,
            "access_instructions": loc.access_instructions,
            "visible_signage": loc.visible_signage,
            "kit_type": loc.kit_type,
            "staff_trained": loc.staff_trained,
            "last_checked": loc.last_checked_date.isoformat() if loc.last_checked_date else None,
        }
        for loc in locations
    ]


async def resolve_emergency_alert(
    db: AsyncSession,
    alert_id: int,
    status: EmergencyAlertStatus,
    resolved_by_id: Optional[int] = None,
) -> MedicalEmergencyAlert:
    result = await db.execute(
        select(MedicalEmergencyAlert).where(MedicalEmergencyAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert:
        alert.status = status
        if status in {EmergencyAlertStatus.RESOLVED, EmergencyAlertStatus.TRANSFERRED}:
            alert.resolved_at = datetime.now(timezone.utc)
            alert.resolved_by_id = resolved_by_id
        await db.flush()

    return alert


async def get_active_emergencies(
    db: AsyncSession,
    branch_id: Optional[int] = None,
) -> List[MedicalEmergencyAlert]:
    query = select(MedicalEmergencyAlert).where(
        MedicalEmergencyAlert.status == EmergencyAlertStatus.ACTIVE
    ).order_by(MedicalEmergencyAlert.id.desc())

    if branch_id:
        query = query.where(MedicalEmergencyAlert.branch_id == branch_id)

    results = await db.execute(query)
    return results.scalars().all()


async def record_aed_usage(
    db: AsyncSession,
    alert_id: int,
    aed_location_id: int,
) -> MedicalEmergencyAlert:
    result = await db.execute(
        select(MedicalEmergencyAlert).where(MedicalEmergencyAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if alert:
        alert.aed_used = True
        alert.aed_location_id = aed_location_id
        await db.flush()

    return alert
