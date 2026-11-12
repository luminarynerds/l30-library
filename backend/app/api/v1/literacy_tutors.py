# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Literacy Tutor Management API Routes.

Endpoints for:
- Tutor registration and profiles
- Qualifications and certifications
- Training records
- Availability scheduling
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date

from app.core.database import get_db
from app.models.literacy_tutor import (
    TutorProfile, LiteracyTutorQualification, LiteracyTutorTrainingRecord,
    LiteracyTutorAvailability, TutorStatus, QualificationType, TrainingTopic
)
from app.schemas.literacy import (
    TutorRegistrationRequest, TutorResponse, QualificationRequest
)
from .dependencies import require_staff
from fastapi import Depends
from ...models.user import User

router = APIRouter(prefix="/literacy/tutors", tags=["literacy_tutors"])


@router.post("/register", response_model=dict)
async def register_tutor(
    request: TutorRegistrationRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Register a new tutor in the literacy program.

    Creates a tutor profile with initial specializations and capabilities.
    """
    tutor = TutorProfile(
        user_id=request.user_id,
        status=TutorStatus.PROSPECTIVE,
        is_active=True,
        primary_focus=request.primary_focus,
        languages_spoken=request.languages_spoken,
        specializations=request.specializations,
        can_teach_ged=request.can_teach_ged,
        can_teach_esol=request.can_teach_esol,
        can_work_with_special_needs=request.can_work_with_special_needs,
        years_experience=request.years_experience,
        preferred_learner_level=request.preferred_learner_level,
        can_teach_remote=request.can_teach_remote,
        can_teach_in_person=request.can_teach_in_person,
        bio=request.bio,
        has_completed_mandatory_training=False,
        background_check_completed=False,
        confidentiality_agreement_signed=False
    )
    db.add(tutor)
    await db.commit()
    await db.refresh(tutor)

    return {
        "id": tutor.id,
        "user_id": tutor.user_id,
        "status": str(tutor.status),
        "message": "Tutor registered successfully. Please complete mandatory training."
    }


@router.get("/{tutor_id}", response_model=TutorResponse)
async def get_tutor(
    tutor_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get tutor profile details."""
    tutor = await db.get(TutorProfile, tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    return TutorResponse.model_validate(tutor)


@router.put("/{tutor_id}")
async def update_tutor(
    tutor_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Update tutor profile information."""
    tutor = await db.get(TutorProfile, tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    allowed_fields = {
        'primary_focus', 'languages_spoken', 'specializations',
        'can_teach_ged', 'can_teach_esol', 'can_work_with_special_needs',
        'years_experience', 'preferred_learner_level', 'bio', 'status'
    }

    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(tutor, field, value)

    await db.commit()
    return TutorResponse.model_validate(tutor)


@router.post("/{tutor_id}/qualifications")
async def add_qualification(
    tutor_id: int,
    request: QualificationRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Add a certification or qualification for a tutor."""
    tutor = await db.get(TutorProfile, tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    qualification = LiteracyTutorQualification(
        tutor_id=tutor_id,
        qualification_type=request.qualification_type,
        issuer=request.issuer,
        issue_date=request.issue_date,
        expiry_date=request.expiry_date,
        credential_url=request.credential_url
    )
    db.add(qualification)
    await db.commit()

    return {
        "id": qualification.id,
        "qualification_type": request.qualification_type,
        "issue_date": request.issue_date.isoformat(),
        "expiry_date": request.expiry_date.isoformat() if request.expiry_date else None
    }


@router.get("/{tutor_id}/availability")
async def get_availability(
    tutor_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get tutor's availability schedule."""
    availability = await db.scalars(
        select(LiteracyTutorAvailability).where(
            LiteracyTutorAvailability.tutor_id == tutor_id
        )
    )

    return [
        {
            "id": slot.id,
            "day_of_week": slot.day_of_week,
            "day_name": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][slot.day_of_week],
            "start_time": slot.start_time,
            "end_time": slot.end_time,
            "location": slot.location,
            "is_active": slot.is_active
        }
        for slot in availability
    ]


@router.put("/{tutor_id}/availability")
async def set_availability(
    tutor_id: int,
    availability_slots: List[dict],
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Update tutor's weekly availability schedule."""
    tutor = await db.get(TutorProfile, tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    # Delete existing availability
    await db.execute(
        select(LiteracyTutorAvailability).where(
            LiteracyTutorAvailability.tutor_id == tutor_id
        )
    )

    # Add new availability slots
    for slot in availability_slots:
        availability = LiteracyTutorAvailability(
            tutor_id=tutor_id,
            day_of_week=slot['day_of_week'],
            start_time=slot['start_time'],
            end_time=slot['end_time'],
            location=slot.get('location'),
            is_active=True
        )
        db.add(availability)

    await db.commit()
    return {"message": "Availability updated successfully"}


@router.post("/{tutor_id}/training")
async def record_training(
    tutor_id: int,
    training_data: dict,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Record tutor training completion."""
    tutor = await db.get(TutorProfile, tutor_id)
    if not tutor:
        raise HTTPException(status_code=404, detail="Tutor not found")

    training = LiteracyTutorTrainingRecord(
        tutor_id=tutor_id,
        trainer_id=training_data.get('trainer_id'),
        training_topic=training_data['training_topic'],
        training_date=training_data['training_date'],
        hours_completed=training_data['hours_completed'],
        training_type=training_data.get('training_type'),
        training_provider=training_data.get('training_provider'),
        materials_url=training_data.get('materials_url'),
        certificate_url=training_data.get('certificate_url'),
        is_completed=True
    )
    db.add(training)
    await db.commit()

    return {
        "id": training.id,
        "training_topic": training_data['training_topic'],
        "hours_completed": float(training_data['hours_completed']),
        "training_date": training_data['training_date'].isoformat()
    }


@router.get("/{tutor_id}/training-history")
async def get_training_history(
    tutor_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get tutor's training and professional development history."""
    training_records = await db.scalars(
        select(LiteracyTutorTrainingRecord)
        .where(LiteracyTutorTrainingRecord.tutor_id == tutor_id)
        .order_by(LiteracyTutorTrainingRecord.training_date.desc())
    )

    return [
        {
            "id": record.id,
            "training_topic": str(record.training_topic),
            "training_date": record.training_date.isoformat(),
            "hours_completed": float(record.hours_completed),
            "training_provider": record.training_provider,
            "is_completed": record.is_completed
        }
        for record in training_records
    ]


@router.get("/search")
async def search_tutors(
    can_teach_ged: bool = Query(False),
    can_teach_esol: bool = Query(False),
    languages: Optional[str] = Query(None),
    specialization: Optional[str] = Query(None),
    remote: bool = Query(False),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    Search for available tutors with optional filtering.

    Filters by specialization, language, teaching modality, and availability.
    """
    query = select(TutorProfile).where(TutorProfile.is_active == True)

    if can_teach_ged:
        query = query.where(TutorProfile.can_teach_ged == True)

    if can_teach_esol:
        query = query.where(TutorProfile.can_teach_esol == True)

    if remote:
        query = query.where(TutorProfile.can_teach_remote == True)

    tutors = await db.scalars(
        query.limit(limit).offset(offset)
    )

    return [
        {
            "id": tutor.id,
            "user_id": tutor.user_id,
            "primary_focus": tutor.primary_focus,
            "languages_spoken": tutor.languages_spoken,
            "can_teach_ged": tutor.can_teach_ged,
            "can_teach_esol": tutor.can_teach_esol,
            "total_learners_taught": tutor.total_learners_taught,
            "average_satisfaction": float(tutor.average_learner_satisfaction) if tutor.average_learner_satisfaction else None
        }
        for tutor in tutors
    ]
