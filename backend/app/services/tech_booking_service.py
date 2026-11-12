# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_email, COLORS
from ..models.tech_booking import (
    BookingStatus, TechFollowUpStatus, SkillLevel, TechTopic,
    TechAssistanceBooking, TechAssistanceStaff, TechFollowUpBooking,
    TechResourceHandout, TechSessionNote, TechSkillImpact,
    TechVolunteerTutor
)
from ..models.user import User

logger = get_logger(__name__)
settings = get_settings()

# Constants
NO_SHOW_GRACE_MINUTES = 15  # Minutes after start time before marking as no-show
REMINDER_HOURS_BEFORE = 24  # Hours before appointment to send reminder


async def check_staff_availability(
    db: AsyncSession,
    staff_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[int] = None,
) -> bool:
    # Get staff member to check max concurrent sessions
    stmt = select(TechAssistanceStaff).where(TechAssistanceStaff.id == staff_id)
    result = await db.execute(stmt)
    staff = result.scalar_one_or_none()

    if not staff:
        return False

    # Check for overlapping bookings
    query = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.assigned_staff_id == staff_id)
        .where(
            TechAssistanceBooking.status.in_([
                BookingStatus.pending,
                BookingStatus.confirmed,
                BookingStatus.in_progress,
            ])
        )
        .where(
            and_(
                TechAssistanceBooking.start_time < end_time,
                TechAssistanceBooking.end_time > start_time,
            )
        )
    )

    if exclude_booking_id:
        query = query.where(TechAssistanceBooking.id != exclude_booking_id)

    result = await db.execute(query)
    conflicting_bookings = list(result.scalars().all())

    # Check if adding this booking would exceed max concurrent sessions
    if len(conflicting_bookings) >= staff.max_concurrent_sessions:
        return False

    return True


async def get_conflicting_bookings(
    db: AsyncSession,
    staff_id: int,
    start_time: datetime,
    end_time: datetime,
    exclude_booking_id: Optional[int] = None,
) -> list[TechAssistanceBooking]:
    query = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.assigned_staff_id == staff_id)
        .where(
            TechAssistanceBooking.status.in_([
                BookingStatus.pending,
                BookingStatus.confirmed,
                BookingStatus.in_progress,
            ])
        )
        .where(
            and_(
                TechAssistanceBooking.start_time < end_time,
                TechAssistanceBooking.end_time > start_time,
            )
        )
    )

    if exclude_booking_id:
        query = query.where(TechAssistanceBooking.id != exclude_booking_id)

    result = await db.execute(query)
    return list(result.scalars().all())


async def match_staff_by_expertise(
    db: AsyncSession,
    topic: str,
    preferred_staff_id: Optional[int] = None,
) -> Optional[TechAssistanceStaff]:
    # If preferred staff is specified, check if they have expertise
    if preferred_staff_id:
        stmt = select(TechAssistanceStaff).where(
            TechAssistanceStaff.id == preferred_staff_id,
            TechAssistanceStaff.is_active == True
        )
        result = await db.execute(stmt)
        staff = result.scalar_one_or_none()
        if staff and topic in staff.expertise_topics:
            return staff

    # Find any active staff with expertise in the topic
    stmt = (
        select(TechAssistanceStaff)
        .where(TechAssistanceStaff.is_active == True)
    )
    result = await db.execute(stmt)
    all_staff = list(result.scalars().all())

    # Filter staff with expertise in this topic
    matching_staff = [s for s in all_staff if topic in s.expertise_topics]

    if not matching_staff:
        return None

    # Return the first available staff (or implement more sophisticated matching)
    return matching_staff[0]


async def validate_booking_rules(
    db: AsyncSession,
    start_time: datetime,
    end_time: datetime,
    user: Optional[User] = None,
) -> list[str]:
    errors = []
    now = datetime.now(timezone.utc)

    # Check if booking is in the past
    if end_time < now:
        errors.append("Cannot book in the past")
        return errors

    if start_time < now:
        errors.append("Start time cannot be in the past")

    # Check duration (minimum 30 minutes, maximum 2 hours)
    duration_minutes = (end_time - start_time).total_seconds() / 60
    if duration_minutes < 30:
        errors.append("Minimum session duration is 30 minutes")
    if duration_minutes > 120:
        errors.append("Maximum session duration is 2 hours")

    # Check advance booking (at least 24 hours in advance)
    if start_time > now:
        hours_until = (start_time - now).total_seconds() / 3600
        if hours_until < 24:
            errors.append("Sessions must be booked at least 24 hours in advance")

        # Check not booking too far in advance (90 days max)
        days_until = (start_time.date() - now.date()).days
        if days_until > 90:
            errors.append("Cannot book more than 90 days in advance")

    return errors


async def send_booking_confirmation(
    db: AsyncSession,
    booking: TechAssistanceBooking,
) -> bool:
    try:
        contact_email = booking.contact_email
        if booking.patron_id:
            stmt = select(User).where(User.id == booking.patron_id)
            result = await db.execute(stmt)
            patron = result.scalar_one_or_none()
            if patron:
                contact_email = patron.email

        if not contact_email:
            logger.warning(f"No email address for booking {booking.id}")
            return False

        subject = f"Tech Help Session Confirmed - {booking.topic.replace('_', ' ').title()}"

        body = f"""
        <h2>Your Tech Help Session is Confirmed</h2>
        <p>Thank you for booking a technology assistance session!</p>

        <h3>Session Details:</h3>
        <ul>
            <li><strong>Topic:</strong> {booking.topic.replace('_', ' ').title()}</li>
            <li><strong>Date/Time:</strong> {booking.start_time.strftime('%A, %B %d, %Y at %I:%M %p')}</li>
            <li><strong>Duration:</strong> {int((booking.end_time - booking.start_time).total_seconds() / 60)} minutes</li>
            <li><strong>Your Skill Level:</strong> {booking.skill_level.title()}</li>
        </ul>

        <p>Please arrive 5 minutes early. If you need to reschedule or cancel, please let us know as soon as possible.</p>
        <p>Our staff will be happy to help you build your tech confidence!</p>
        """

        await send_email(
            to_email=contact_email,
            subject=subject,
            html_content=body,
        )

        # Update confirmation sent timestamp
        booking.confirmation_sent_at = datetime.now(timezone.utc)
        await db.commit()

        return True
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash booking flow
        logger.error(f"Failed to send confirmation for booking {booking.id}: {e}")
        return False


async def send_appointment_reminder(
    db: AsyncSession,
    booking: TechAssistanceBooking,
) -> bool:
    try:
        contact_email = booking.contact_email
        if booking.patron_id:
            stmt = select(User).where(User.id == booking.patron_id)
            result = await db.execute(stmt)
            patron = result.scalar_one_or_none()
            if patron:
                contact_email = patron.email

        if not contact_email:
            return False

        subject = "Reminder: Your Tech Help Session is Tomorrow"

        body = f"""
        <h2>Upcoming Tech Help Session</h2>
        <p>This is a friendly reminder about your technology assistance session!</p>

        <h3>Session Details:</h3>
        <ul>
            <li><strong>Topic:</strong> {booking.topic.replace('_', ' ').title()}</li>
            <li><strong>Time:</strong> {booking.start_time.strftime('%I:%M %p')}</li>
            <li><strong>Date:</strong> {booking.start_time.strftime('%A, %B %d, %Y')}</li>
        </ul>

        <p>Please plan to arrive 5 minutes early. We're looking forward to helping you!</p>
        """

        await send_email(
            to_email=contact_email,
            subject=subject,
            html_content=body,
        )

        # Update reminder sent timestamp
        booking.reminder_sent_at = datetime.now(timezone.utc)
        await db.commit()

        return True
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash reminder flow
        logger.error(f"Failed to send reminder for booking {booking.id}: {e}")
        return False


async def send_handout_materials(
    db: AsyncSession,
    booking: TechAssistanceBooking,
    resources: list[TechResourceHandout],
) -> bool:
    try:
        contact_email = booking.contact_email
        if booking.patron_id:
            stmt = select(User).where(User.id == booking.patron_id)
            result = await db.execute(stmt)
            patron = result.scalar_one_or_none()
            if patron:
                contact_email = patron.email

        if not contact_email or not resources:
            return False

        subject = f"Tech Help Resources - {booking.topic.replace('_', ' ').title()}"

        resources_html = ""
        for resource in resources:
            resources_html += f"""
            <div style="margin-bottom: 15px; padding: 10px; background-color: #f5f5f5; border-left: 3px solid #0066cc;">
                <h4>{resource.title}</h4>
                {f'<p>{resource.description}</p>' if resource.description else ''}
                {f'<p><a href="{resource.resource_url}">View Resource</a></p>' if resource.resource_url else ''}
            </div>
            """

        body = f"""
        <h2>Your Tech Help Resources</h2>
        <p>Thank you for attending our tech help session on {booking.topic.replace('_', ' ').title()}!</p>

        <p>Here are some helpful resources to continue your learning:</p>
        {resources_html}

        <p>Feel free to reach out if you have any follow-up questions!</p>
        """

        await send_email(
            to_email=contact_email,
            subject=subject,
            html_content=body,
        )

        # Mark resources as sent
        for resource in resources:
            resource.sent_to_patron = True
            resource.sent_at = datetime.now(timezone.utc)
            resource.sent_method = "email"

        await db.commit()
        return True
    except Exception as e:  # noqa: BLE001 - notification boundary — email failure must not crash handout flow
        logger.error(f"Failed to send handout materials for booking {booking.id}: {e}")
        return False


async def get_upcoming_appointments_for_reminders(
    db: AsyncSession,
) -> list[TechAssistanceBooking]:
    now = datetime.now(timezone.utc)
    reminder_window_start = now + timedelta(hours=REMINDER_HOURS_BEFORE - 1)
    reminder_window_end = now + timedelta(hours=REMINDER_HOURS_BEFORE + 1)

    stmt = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.status == BookingStatus.confirmed)
        .where(TechAssistanceBooking.reminder_sent_at.is_(None))
        .where(TechAssistanceBooking.start_time >= reminder_window_start)
        .where(TechAssistanceBooking.start_time <= reminder_window_end)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def mark_no_shows(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    grace_cutoff = now - timedelta(minutes=NO_SHOW_GRACE_MINUTES)

    stmt = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.status == BookingStatus.confirmed)
        .where(TechAssistanceBooking.start_time < grace_cutoff)
        .where(TechAssistanceBooking.checked_in_at.is_(None))
    )

    result = await db.execute(stmt)
    no_show_bookings = list(result.scalars().all())

    for booking in no_show_bookings:
        booking.status = BookingStatus.no_show

    await db.commit()
    return len(no_show_bookings)


async def schedule_follow_up(
    db: AsyncSession,
    original_booking_id: int,
    suggested_topics: Optional[list[str]] = None,
    reason: Optional[str] = None,
    suggested_timing: Optional[str] = None,
) -> TechFollowUpBooking:
    follow_up = TechFollowUpBooking(
        original_booking_id=original_booking_id,
        status=TechFollowUpStatus.pending,
        suggested_topics=suggested_topics or [],
        reason=reason,
        suggested_timing=suggested_timing,
    )

    db.add(follow_up)
    await db.commit()
    await db.refresh(follow_up)

    return follow_up


async def get_patron_booking_history(
    db: AsyncSession,
    patron_id: int,
    limit: int = 10,
) -> list[TechAssistanceBooking]:
    stmt = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.patron_id == patron_id)
        .order_by(TechAssistanceBooking.start_time.desc())
        .limit(limit)
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_staff_workload(
    db: AsyncSession,
    staff_id: int,
    start_date: datetime,
    end_date: datetime,
) -> dict:
    stmt = (
        select(TechAssistanceBooking)
        .where(TechAssistanceBooking.assigned_staff_id == staff_id)
        .where(TechAssistanceBooking.start_time >= start_date)
        .where(TechAssistanceBooking.start_time <= end_date)
        .where(
            TechAssistanceBooking.status.in_([
                BookingStatus.confirmed,
                BookingStatus.in_progress,
                BookingStatus.completed,
            ])
        )
    )

    result = await db.execute(stmt)
    bookings = list(result.scalars().all())

    # Calculate statistics
    total_sessions = len(bookings)
    total_minutes = sum(
        int((b.end_time - b.start_time).total_seconds() / 60)
        for b in bookings
    )

    # Group by topic
    topics_breakdown = {}
    for booking in bookings:
        topic = booking.topic
        if topic not in topics_breakdown:
            topics_breakdown[topic] = 0
        topics_breakdown[topic] += 1

    return {
        "total_sessions": total_sessions,
        "total_minutes": total_minutes,
        "average_session_minutes": total_minutes // total_sessions if total_sessions > 0 else 0,
        "topics_breakdown": topics_breakdown,
    }


async def get_available_slots(
    db: AsyncSession,
    topic: Optional[str] = None,
    date_start: Optional[datetime] = None,
    date_end: Optional[datetime] = None,
) -> list[dict]:
    now = datetime.now(timezone.utc)
    if not date_start:
        date_start = now + timedelta(days=1)
    if not date_end:
        date_end = date_start + timedelta(days=7)

    # Get active staff
    stmt = select(TechAssistanceStaff).where(TechAssistanceStaff.is_active == True)
    result = await db.execute(stmt)
    all_staff = list(result.scalars().all())

    if topic:
        all_staff = [s for s in all_staff if topic in s.expertise_topics]

    if not all_staff:
        return []

    slots = []
    current_date = date_start.replace(hour=0, minute=0, second=0, microsecond=0)

    while current_date < date_end:
        day_name = current_date.strftime("%A").lower()

        for staff in all_staff:
            # Check staff availability for this day
            availability = staff.availability or {}
            day_avail = availability.get(day_name)

            if not day_avail:
                continue

            start_hour = int(day_avail.get("start", "09:00").split(":")[0])
            end_hour = int(day_avail.get("end", "17:00").split(":")[0])

            # Generate 1-hour slots
            for hour in range(start_hour, end_hour):
                slot_start = current_date.replace(hour=hour, minute=0)
                slot_end = current_date.replace(hour=hour + 1, minute=0)

                # Skip past slots
                if slot_start <= now:
                    continue

                # Check if staff is available (no conflicts)
                is_avail = await check_staff_availability(
                    db, staff.id, slot_start, slot_end
                )

                if is_avail:
                    # Get staff user name
                    staff_name = None
                    if staff.staff_user:
                        staff_name = getattr(staff.staff_user, 'full_name', None)

                    slots.append({
                        "date": current_date.strftime("%Y-%m-%d"),
                        "start_time": f"{hour:02d}:00",
                        "end_time": f"{hour + 1:02d}:00",
                        "staff_id": staff.id,
                        "staff_name": staff_name,
                        "topics": staff.expertise_topics or [],
                    })

        current_date += timedelta(days=1)

    return slots


async def complete_session(
    db: AsyncSession,
    booking: TechAssistanceBooking,
    notes_data: Optional[dict] = None,
    impact_data: Optional[dict] = None,
    follow_up_needed: bool = False,
    follow_up_topics: Optional[list[str]] = None,
    follow_up_reason: Optional[str] = None,
    follow_up_timing: Optional[str] = None,
    resource_ids_to_send: Optional[list[int]] = None,
    completed_by: Optional[int] = None,
) -> dict:
    result_data = {"booking_id": booking.id}

    # Mark session as completed
    booking.status = BookingStatus.completed
    booking.session_end_actual = datetime.now(timezone.utc)

    # Add session notes if provided
    if notes_data:
        note = TechSessionNote(
            booking_id=booking.id,
            content=notes_data.get("content", ""),
            topics_covered=notes_data.get("topics_covered", []),
            concepts_taught=notes_data.get("concepts_taught", []),
            patron_comprehension_level=notes_data.get("patron_comprehension_level"),
            recommendations=notes_data.get("recommendations"),
            challenges=notes_data.get("challenges"),
            created_by=completed_by,
        )
        db.add(note)
        result_data["notes_added"] = True

    # Record impact if provided
    if impact_data:
        impact = TechSkillImpact(
            booking_id=booking.id,
            skills_learned=impact_data.get("skills_learned", []),
            confidence_before=impact_data.get("confidence_before"),
            confidence_after=impact_data.get("confidence_after"),
            independence_level=impact_data.get("independence_level"),
            goal_achieved=impact_data.get("goal_achieved", False),
            satisfaction_rating=impact_data.get("satisfaction_rating"),
            patron_feedback=impact_data.get("patron_feedback"),
            interested_in_future_sessions=impact_data.get("interested_in_future_sessions", False),
            staff_recommendation=impact_data.get("staff_recommendation"),
        )
        db.add(impact)
        result_data["impact_recorded"] = True

    # Schedule follow-up if needed
    if follow_up_needed:
        follow_up = await schedule_follow_up(
            db,
            booking.id,
            suggested_topics=follow_up_topics,
            reason=follow_up_reason,
            suggested_timing=follow_up_timing,
        )
        result_data["follow_up_id"] = follow_up.id

    # Auto-send resources if specified
    if resource_ids_to_send:
        stmt = select(TechResourceHandout).where(
            TechResourceHandout.booking_id == booking.id,
            TechResourceHandout.id.in_(resource_ids_to_send),
        )
        res = await db.execute(stmt)
        resources = list(res.scalars().all())
        if resources:
            await send_handout_materials(db, booking, resources)
            result_data["resources_sent"] = len(resources)

    await db.commit()
    return result_data


async def get_impact_summary(
    db: AsyncSession,
    patron_id: int,
) -> dict:
    stmt = (
        select(TechSkillImpact)
        .join(TechAssistanceBooking)
        .where(TechAssistanceBooking.patron_id == patron_id)
        .where(TechSkillImpact.booking_id == TechAssistanceBooking.id)
    )

    result = await db.execute(stmt)
    impacts = list(result.scalars().all())

    if not impacts:
        return {
            "total_sessions": 0,
            "average_confidence_improvement": 0,
            "goal_achievement_rate": 0,
            "average_satisfaction": 0,
            "skills_learned": [],
        }

    # Calculate statistics
    total_sessions = len(impacts)
    goals_achieved = sum(1 for i in impacts if i.goal_achieved)

    confidence_improvements = []
    for impact in impacts:
        if impact.confidence_before and impact.confidence_after:
            improvement = impact.confidence_after - impact.confidence_before
            confidence_improvements.append(improvement)

    satisfaction_ratings = [i.satisfaction_rating for i in impacts if i.satisfaction_rating]

    all_skills = []
    for impact in impacts:
        if impact.skills_learned:
            all_skills.extend(impact.skills_learned)

    return {
        "total_sessions": total_sessions,
        "average_confidence_improvement": sum(confidence_improvements) / len(confidence_improvements) if confidence_improvements else 0,
        "goal_achievement_rate": goals_achieved / total_sessions if total_sessions > 0 else 0,
        "average_satisfaction": sum(satisfaction_ratings) / len(satisfaction_ratings) if satisfaction_ratings else 0,
        "skills_learned": list(set(all_skills)),
    }
