# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.error_codes import ErrorCode
from ...core.exceptions import ResourceNotFoundError, ValidationError

from ...models.legal import (
    LegalClinic, LegalClinicRegistration, ClinicStatus, RegistrationStatus,
    DeadlineRule, DeadlineCalculation, FormFinderWizardSession,
    FormFinderQuestion, FormFinderRule, WizardSessionStatus, FormCompletionSession,
    FormCompletionStatus
)

logger = get_logger(__name__)


# ============================================================================
# Legal Clinic Services
# ============================================================================

async def get_clinic_by_id(
    db: AsyncSession,
    clinic_id: int
) -> Optional[LegalClinic]:
    result = await db.execute(
        select(LegalClinic)
        .options(
            selectinload(LegalClinic.topic),
            selectinload(LegalClinic.provider),
            selectinload(LegalClinic.registrations)
        )
        .where(LegalClinic.id == clinic_id)
    )
    return result.scalar_one_or_none()


async def list_clinics(
    db: AsyncSession,
    topic_id: Optional[int] = None,
    provider_id: Optional[int] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    is_virtual: Optional[bool] = None,
    status: Optional[ClinicStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalClinic], int]:
    base_query = select(LegalClinic).options(
        selectinload(LegalClinic.topic),
        selectinload(LegalClinic.provider)
    )
    count_query = select(func.count(LegalClinic.id))

    filters = []
    if topic_id is not None:
        filters.append(LegalClinic.topic_id == topic_id)
    if provider_id is not None:
        filters.append(LegalClinic.provider_id == provider_id)
    if from_date is not None:
        filters.append(LegalClinic.date >= from_date)
    if to_date is not None:
        filters.append(LegalClinic.date <= to_date)
    if is_virtual is not None:
        filters.append(LegalClinic.is_virtual == is_virtual)
    if status is not None:
        filters.append(LegalClinic.status == status)

    if filters:
        base_query = base_query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalClinic.date, LegalClinic.start_time)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    clinics = result.scalars().all()

    return clinics, total


async def list_upcoming_clinics(
    db: AsyncSession,
    days: int = 30,
    limit: int = 10
) -> list[LegalClinic]:
    today = date.today()
    end_date = today + timedelta(days=days)

    result = await db.execute(
        select(LegalClinic)
        .options(selectinload(LegalClinic.topic))
        .where(
            LegalClinic.date >= today,
            LegalClinic.date <= end_date,
            LegalClinic.status.in_([
                ClinicStatus.scheduled,
                ClinicStatus.registration_open
            ])
        )
        .order_by(LegalClinic.date, LegalClinic.start_time)
        .limit(limit)
    )
    return result.scalars().all()


async def create_clinic(
    db: AsyncSession,
    clinic_data: dict,
    created_by_id: Optional[int] = None
) -> LegalClinic:
    clinic = LegalClinic(**clinic_data, created_by_id=created_by_id)
    db.add(clinic)
    await db.commit()
    await db.refresh(clinic)
    return clinic


async def update_clinic(
    db: AsyncSession,
    clinic_id: int,
    clinic_data: dict
) -> LegalClinic:
    clinic = await get_clinic_by_id(db, clinic_id)
    if not clinic:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal clinic not found"
        )

    for key, value in clinic_data.items():
        if value is not None:
            setattr(clinic, key, value)

    await db.commit()
    await db.refresh(clinic)
    return clinic


async def register_for_clinic(
    db: AsyncSession,
    clinic_id: int,
    registration_data: dict,
    patron_id: Optional[int] = None
) -> LegalClinicRegistration:
    clinic = await get_clinic_by_id(db, clinic_id)
    if not clinic:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal clinic not found"
        )

    # Check if registration is open
    if clinic.status not in [ClinicStatus.scheduled, ClinicStatus.registration_open]:
        raise ValidationError(
            code=ErrorCode.INVALID_OPERATION,
            message="Registration is not open for this clinic"
        )

    # Check capacity
    if clinic.current_registrations >= clinic.capacity:
        # Add to waitlist if available
        if clinic.current_waitlist >= clinic.waitlist_capacity:
            raise ValidationError(
                code=ErrorCode.INVALID_OPERATION,
                message="Clinic is full and waitlist is at capacity"
            )

        registration = LegalClinicRegistration(
            clinic_id=clinic_id,
            patron_id=patron_id,
            status=RegistrationStatus.waitlisted,
            waitlist_position=clinic.current_waitlist + 1,
            **registration_data
        )
        clinic.current_waitlist += 1
    else:
        registration = LegalClinicRegistration(
            clinic_id=clinic_id,
            patron_id=patron_id,
            status=RegistrationStatus.confirmed,
            **registration_data
        )
        clinic.current_registrations += 1

    db.add(registration)
    await db.commit()
    await db.refresh(registration)
    return registration


async def cancel_clinic_registration(
    db: AsyncSession,
    registration_id: int
) -> LegalClinicRegistration:
    result = await db.execute(
        select(LegalClinicRegistration)
        .options(selectinload(LegalClinicRegistration.clinic))
        .where(LegalClinicRegistration.id == registration_id)
    )
    registration = result.scalar_one_or_none()

    if not registration:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Registration not found"
        )

    clinic = registration.clinic
    was_confirmed = registration.status == RegistrationStatus.confirmed

    registration.status = RegistrationStatus.cancelled

    # Update clinic counts
    if was_confirmed:
        clinic.current_registrations -= 1
        # Promote from waitlist if applicable
        await _promote_from_waitlist(db, clinic)
    elif registration.status == RegistrationStatus.waitlisted:
        clinic.current_waitlist -= 1

    await db.commit()
    await db.refresh(registration)
    return registration


async def _promote_from_waitlist(
    db: AsyncSession,
    clinic: LegalClinic
) -> None:
    if clinic.current_waitlist > 0:
        result = await db.execute(
            select(LegalClinicRegistration)
            .where(
                LegalClinicRegistration.clinic_id == clinic.id,
                LegalClinicRegistration.status == RegistrationStatus.waitlisted
            )
            .order_by(LegalClinicRegistration.waitlist_position)
            .limit(1)
        )
        next_registration = result.scalar_one_or_none()

        if next_registration:
            next_registration.status = RegistrationStatus.confirmed
            next_registration.waitlist_position = None
            clinic.current_registrations += 1
            clinic.current_waitlist -= 1


# ============================================================================
# Deadline Calculator Services
# ============================================================================

async def get_deadline_rule(
    db: AsyncSession,
    rule_id: Optional[int] = None,
    slug: Optional[str] = None
) -> Optional[DeadlineRule]:
    if rule_id:
        result = await db.execute(
            select(DeadlineRule).where(DeadlineRule.id == rule_id)
        )
    elif slug:
        result = await db.execute(
            select(DeadlineRule).where(DeadlineRule.slug == slug)
        )
    else:
        return None
    return result.scalar_one_or_none()


async def list_deadline_rules(
    db: AsyncSession,
    deadline_type: Optional[str] = None,
    jurisdiction: Optional[str] = None,
    topic_id: Optional[int] = None,
    is_active: bool = True
) -> list[DeadlineRule]:
    query = select(DeadlineRule).where(DeadlineRule.is_active == is_active)

    if deadline_type:
        query = query.where(DeadlineRule.deadline_type == deadline_type)
    if jurisdiction:
        query = query.where(DeadlineRule.jurisdiction == jurisdiction)
    if topic_id:
        query = query.where(DeadlineRule.topic_id == topic_id)

    result = await db.execute(query.order_by(DeadlineRule.name))
    return result.scalars().all()


async def calculate_deadline(
    db: AsyncSession,
    rule_id: Optional[int] = None,
    rule_slug: Optional[str] = None,
    start_date: date = None,
    patron_id: Optional[int] = None,
    reminder_email: Optional[str] = None,
    reminder_phone: Optional[str] = None,
    enable_reminders: bool = False,
    user_notes: Optional[str] = None
) -> DeadlineCalculation:
    rule = await get_deadline_rule(db, rule_id, rule_slug)
    if not rule:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Deadline rule not found"
        )

    # Calculate deadline
    deadline_date = _calculate_deadline_date(
        start_date,
        rule.days,
        rule.use_business_days,
        rule.exclude_holidays
    )

    # Create calculation record
    session_token = secrets.token_urlsafe(32)
    calculation = DeadlineCalculation(
        session_token=session_token,
        patron_id=patron_id,
        rule_id=rule.id,
        start_date=start_date,
        deadline_date=deadline_date,
        reminder_email=reminder_email,
        reminder_phone=reminder_phone,
        reminders_enabled=enable_reminders,
        user_notes=user_notes,
        expires_at=datetime.now(timezone.utc) + timedelta(days=365)
    )

    db.add(calculation)
    await db.commit()
    await db.refresh(calculation)
    return calculation


def _calculate_deadline_date(
    start_date: date,
    days: int,
    use_business_days: bool,
    exclude_holidays: bool
) -> date:
    if use_business_days:
        # Count business days (excluding weekends)
        current = start_date
        days_counted = 0
        while days_counted < days:
            current += timedelta(days=1)
            if current.weekday() < 5:  # Monday = 0, Friday = 4
                days_counted += 1
        return current
    else:
        return start_date + timedelta(days=days)


# ============================================================================
# Form Completion Session Services
# ============================================================================

async def start_form_session(
    db: AsyncSession,
    form_id: Optional[int] = None,
    packet_id: Optional[int] = None,
    patron_id: Optional[int] = None,
    anonymous_mode: bool = True
) -> FormCompletionSession:
    session_token = secrets.token_urlsafe(32)

    session = FormCompletionSession(
        session_token=session_token,
        patron_id=patron_id if not anonymous_mode else None,
        form_id=form_id,
        packet_id=packet_id,
        anonymous_mode=anonymous_mode,
        status=FormCompletionStatus.in_progress
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def complete_form_session(
    db: AsyncSession,
    session_token: str
) -> FormCompletionSession:
    result = await db.execute(
        select(FormCompletionSession)
        .where(FormCompletionSession.session_token == session_token)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Form session not found"
        )

    session.status = FormCompletionStatus.completed
    session.completed_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)
    return session
