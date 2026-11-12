# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_email
from ..models.computer import (
    Computer, ComputerReservation, ComputerSession, ComputerWaitlist,
    GuestPass, SessionExtensionRequest, ComputerUsageStats, ComputerSystemLog,
    ComputerType, ComputerStatus, ComputerReservationStatus, ComputerWaitlistStatus,
    ExtensionStatus
)
from ..models.cipa_compliance import ComputerSessionStatus
from ..models.user import User
from . import operations_audit_service as ops_audit

logger = get_logger(__name__)
settings = get_settings()

# Constants
SESSION_WARNING_MINUTES_BEFORE = 5
NO_SHOW_GRACE_MINUTES = 15
GUEST_PASS_VALIDITY_DAYS = 7
WAITLIST_EXPIRY_HOURS = 24


async def check_computer_availability(
    db: AsyncSession,
    computer_id: int,
    start_time: datetime,
    duration_minutes: int,
    exclude_reservation_id: Optional[int] = None,
) -> bool:
    end_time = start_time + timedelta(minutes=duration_minutes)

    query = (
        select(ComputerReservation)
        .where(ComputerReservation.computer_id == computer_id)
        .where(
            ComputerReservation.status.in_([
                ComputerReservationStatus.confirmed,
                ComputerReservationStatus.in_session,
            ])
        )
        .where(
            and_(
                ComputerReservation.reserved_start_time < end_time,
                ComputerReservation.reserved_end_time > start_time,
            )
        )
    )

    if exclude_reservation_id:
        query = query.where(ComputerReservation.id != exclude_reservation_id)

    result = await db.execute(query)
    conflicting = result.scalar_one_or_none()

    return conflicting is None


async def get_available_computers(
    db: AsyncSession,
    start_time: datetime,
    duration_minutes: int,
    computer_type: Optional[ComputerType] = None,
    branch_id: Optional[int] = None,
) -> List[Computer]:
    query = (
        select(Computer)
        .where(Computer.is_active == True)
        .where(Computer.status == ComputerStatus.available)
    )

    if computer_type:
        query = query.where(Computer.computer_type == computer_type)

    if branch_id:
        query = query.where(Computer.branch_id == branch_id)

    computers = await db.execute(query)
    available_computers = []

    for computer in computers.scalars():
        if await check_computer_availability(db, computer.id, start_time, duration_minutes):
            available_computers.append(computer)

    return available_computers


async def create_reservation(
    db: AsyncSession,
    computer_id: int,
    patron_id: Optional[int],
    start_time: datetime,
    duration_minutes: int,
    is_guest_pass: bool = False,
    guest_name: Optional[str] = None,
    guest_email: Optional[str] = None,
    guest_phone: Optional[str] = None,
) -> Optional[ComputerReservation]:
    # Lock the computer row first. Concurrent create_reservation calls for
    # the same computer block here and re-evaluate availability serially,
    # closing the SELECT-then-INSERT TOCTOU window.
    computer_q = (
        select(Computer)
        .where(Computer.id == computer_id)
        .with_for_update()
    )
    computer = (await db.execute(computer_q)).scalar_one_or_none()
    if not computer or not computer.is_active:
        logger.warning(f"Computer {computer_id} not found or inactive")
        return None

    # Re-check availability under the row lock.
    if not await check_computer_availability(db, computer_id, start_time, duration_minutes):
        logger.warning(f"Computer {computer_id} not available for requested time")
        return None

    # Create guest pass code if needed
    guest_pass_code = None
    if is_guest_pass:
        guest_pass_code = f"GUEST-{uuid4().hex[:8].upper()}"

    end_time = start_time + timedelta(minutes=duration_minutes)

    reservation = ComputerReservation(
        computer_id=computer_id,
        patron_id=patron_id,
        reserved_start_time=start_time,
        reserved_end_time=end_time,
        status=ComputerReservationStatus.confirmed if patron_id else ComputerReservationStatus.pending,
        session_duration_minutes=duration_minutes,
        is_guest_pass=is_guest_pass,
        guest_pass_code=guest_pass_code,
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
    )

    db.add(reservation)
    await db.flush()

    # Log the event
    await log_system_event(
        db,
        event_type="reservation_created",
        description=f"Reservation created for computer {computer.name}",
        computer_id=computer_id,
        reservation_id=reservation.id,
        user_id=patron_id,
    )

    return reservation


async def check_in_reservation(
    db: AsyncSession,
    reservation_id: int,
    guest_pass_code: Optional[str] = None,
) -> Optional[ComputerSession]:
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        return None

    # Validate guest pass code if it's a guest pass
    if reservation.is_guest_pass and reservation.guest_pass_code != guest_pass_code:
        logger.warning(f"Invalid guest pass code for reservation {reservation_id}")
        return None

    # Update reservation
    reservation.status = ComputerReservationStatus.in_session
    reservation.checked_in_at = datetime.now(timezone.utc)
    reservation.actual_start_time = datetime.now(timezone.utc)

    # Create session
    session_end_time = reservation.reserved_end_time
    auto_logout_time = session_end_time - timedelta(minutes=SESSION_WARNING_MINUTES_BEFORE)

    session = ComputerSession(
        reservation_id=reservation_id,
        computer_id=reservation.computer_id,
        patron_id=reservation.patron_id,
        session_start_time=datetime.now(timezone.utc),
        session_end_time=session_end_time,
        auto_logout_at=auto_logout_time,
        is_active=True,
    )

    db.add(session)
    await db.flush()

    # Update computer status
    computer = await db.get(Computer, reservation.computer_id)
    if computer:
        computer.status = ComputerStatus.in_use

    # Log event
    await log_system_event(
        db,
        event_type="session_started",
        description=f"Session started on {computer.name}",
        computer_id=reservation.computer_id,
        reservation_id=reservation_id,
        session_id=session.id,
        user_id=reservation.patron_id,
    )

    return session


async def _emit_session_reset_signal(
    *,
    session_id: int,
    computer_id: Optional[int],
    patron_id: Optional[int],
    logoff_reason: str,
) -> bool:
    # Intentionally a no-op. Do not await any real deprovisioning work here
    # until a wipe backend has been chosen, configured, and security-reviewed.
    logger.debug(
        "session_reset_signal_skipped session_id=%s computer_id=%s "
        "patron_id=%s logoff_reason=%s reason=no_integration_wired",
        session_id,
        computer_id,
        patron_id,
        logoff_reason,
    )
    return False


async def end_session(
    db: AsyncSession,
    session_id: int,
    logoff_reason: str = "time_expired",
    terminated_by_id: Optional[int] = None,
    termination_reason: Optional[str] = None,
) -> Optional[ComputerSession]:
    session = await db.get(ComputerSession, session_id)
    if not session or not session.is_active:
        return None

    now = datetime.now(timezone.utc)
    session.is_active = False
    session.actual_end_time = now
    session.ended_at = now
    session.logoff_reason = logoff_reason
    session.user_initiated_logout = terminated_by_id is None
    if terminated_by_id is not None:
        session.terminated_by_id = terminated_by_id
        session.status = ComputerSessionStatus.TERMINATED
        if termination_reason:
            session.termination_reason = termination_reason[:255]
    else:
        session.status = ComputerSessionStatus.ENDED

    # Update reservation
    reservation = await db.get(ComputerReservation, session.reservation_id)
    if reservation:
        reservation.status = ComputerReservationStatus.completed
        reservation.actual_end_time = datetime.now(timezone.utc)

    # Update computer status
    computer = await db.get(Computer, session.computer_id)
    if computer:
        computer.status = ComputerStatus.available

    # Log event
    await log_system_event(
        db,
        event_type="session_ended",
        description=f"Session ended: {logoff_reason}",
        computer_id=session.computer_id,
        session_id=session_id,
        user_id=session.patron_id,
    )

    # Compute session duration for audit metadata (None if start time missing).
    duration_minutes: Optional[int] = None
    if session.session_start_time and session.actual_end_time:
        delta = session.actual_end_time - session.session_start_time
        duration_minutes = max(0, int(delta.total_seconds() // 60))

    # Fire the deprovisioning hook. Today this is a no-op placeholder; it
    # returns False so the audit trail stays honest about the fact that no
    # workstation reset actually happened.
    reset_trigger_emitted = await _emit_session_reset_signal(
        session_id=session_id,
        computer_id=session.computer_id,
        patron_id=session.patron_id,
        logoff_reason=logoff_reason,
    )

    # Structured operational audit entry (DB-queryable trail).
    await ops_audit.log_computer_session_ended(
        db,
        session_id=session_id,
        computer_id=session.computer_id,
        patron_id=session.patron_id,
        duration_minutes=duration_minutes,
        logoff_reason=logoff_reason,
        reset_trigger_emitted=reset_trigger_emitted,
    )

    # Structured logger line mirroring the audit fields. Explicit
    # reset_trigger_emitted=False makes it grep-able that no wipe fired.
    logger.info(
        "computer_session_ended session_id=%s computer_id=%s patron_id=%s "
        "duration_minutes=%s logoff_reason=%s reset_trigger_emitted=%s",
        session_id,
        session.computer_id,
        session.patron_id,
        duration_minutes,
        logoff_reason,
        reset_trigger_emitted,
    )

    return session


async def request_session_extension(
    db: AsyncSession,
    session_id: int,
    extension_minutes: int,
) -> Optional[SessionExtensionRequest]:
    session = await db.get(ComputerSession, session_id)
    if not session or not session.is_active:
        return None

    reservation = await db.get(ComputerReservation, session.reservation_id)
    if not reservation:
        return None

    # Check if extensions are allowed
    computer = await db.get(Computer, session.computer_id)
    if not computer or not computer.is_extendable:
        return None

    # Check if max extensions reached
    if reservation.extensions_used >= computer.max_extensions_per_day:
        return None

    # Check if requested extension is within limits
    if extension_minutes > computer.max_extension_minutes:
        extension_minutes = computer.max_extension_minutes

    extension_request = SessionExtensionRequest(
        reservation_id=reservation.id,
        session_id=session_id,
        extension_minutes=extension_minutes,
        status=ExtensionStatus.pending,
    )

    db.add(extension_request)
    await db.flush()

    # Log event
    await log_system_event(
        db,
        event_type="extension_requested",
        description=f"Session extension requested: {extension_minutes} minutes",
        session_id=session_id,
        user_id=session.patron_id,
    )

    return extension_request


async def approve_extension(
    db: AsyncSession,
    extension_request_id: int,
    approved_by_staff_id: Optional[int] = None,
) -> Optional[SessionExtensionRequest]:
    extension_request = await db.get(SessionExtensionRequest, extension_request_id)
    if not extension_request:
        return None

    extension_request.status = ExtensionStatus.approved
    extension_request.approved_at = datetime.now(timezone.utc)
    extension_request.approved_by = approved_by_staff_id

    # Update session and reservation
    session = await db.get(ComputerSession, extension_request.session_id)
    reservation = await db.get(ComputerReservation, extension_request.reservation_id)

    if session and reservation:
        new_end_time = session.session_end_time + timedelta(minutes=extension_request.extension_minutes)
        session.session_end_time = new_end_time
        session.auto_logout_at = new_end_time - timedelta(minutes=SESSION_WARNING_MINUTES_BEFORE)
        session.was_extended = True
        session.extension_count += 1

        reservation.extended_until = new_end_time
        reservation.extensions_used += 1
        reservation.extension_requested = True

        # Log event
        await log_system_event(
            db,
            event_type="extension_approved",
            description=f"Extension approved: {extension_request.extension_minutes} minutes",
            session_id=session.id,
            user_id=session.patron_id,
        )

    return extension_request


async def staff_update_reservation(
    db: AsyncSession,
    reservation_id: int,
    new_start: Optional[datetime] = None,
    new_end: Optional[datetime] = None,
) -> tuple[Optional[ComputerReservation], Optional[str]]:
    """Staff reschedule of a reservation.

    Returns (reservation, error) where error is one of:
    'not_found' | 'closed' | 'bad_times' | 'conflict' | 'no_change'.

    A confirmed (not-yet-started) reservation can move both start and end. An
    in-session reservation can only move its end (the start already happened);
    its active session's end + auto-logout are updated to match.
    """
    reservation = await db.get(ComputerReservation, reservation_id)
    if not reservation:
        return None, "not_found"
    if reservation.status in (
        ComputerReservationStatus.cancelled,
        ComputerReservationStatus.completed,
        ComputerReservationStatus.no_show,
    ):
        return None, "closed"

    in_session = reservation.status == ComputerReservationStatus.in_session

    # A started session's start time is immutable.
    if in_session and new_start is not None and new_start != reservation.reserved_start_time:
        return None, "bad_times"

    start = new_start if (new_start is not None and not in_session) else reservation.reserved_start_time
    end = new_end if new_end is not None else reservation.reserved_end_time

    if start == reservation.reserved_start_time and end == reservation.reserved_end_time:
        return None, "no_change"
    if end <= start:
        return None, "bad_times"

    duration = int((end - start).total_seconds() / 60)
    if duration <= 0:
        return None, "bad_times"

    if not await check_computer_availability(
        db, reservation.computer_id, start, duration, exclude_reservation_id=reservation_id
    ):
        return None, "conflict"

    reservation.reserved_start_time = start
    reservation.reserved_end_time = end
    reservation.session_duration_minutes = duration

    if in_session:
        sess_q = (
            select(ComputerSession)
            .where(ComputerSession.reservation_id == reservation_id)
            .where(ComputerSession.is_active == True)  # noqa: E712
        )
        session = (await db.execute(sess_q)).scalars().first()
        if session:
            session.session_end_time = end
            session.auto_logout_at = end - timedelta(minutes=SESSION_WARNING_MINUTES_BEFORE)
            session.was_extended = True
            reservation.extended_until = end

    await log_system_event(
        db,
        event_type="reservation_rescheduled",
        description=f"Reservation {reservation_id} rescheduled to {start.isoformat()}–{end.isoformat()}",
        computer_id=reservation.computer_id,
        reservation_id=reservation_id,
        user_id=reservation.patron_id,
    )
    await db.flush()
    return reservation, None


async def staff_extend_session(
    db: AsyncSession,
    session_id: int,
    extra_minutes: int,
    staff_id: Optional[int] = None,
) -> tuple[Optional[ComputerReservation], Optional[str]]:
    """Staff-granted extension on an active session (no patron request needed).

    Mirrors approve_extension's field updates (session_end_time, auto_logout_at,
    was_extended, extension_count, reservation.extended_until/extensions_used)
    and also bumps the reservation's reserved_end_time so availability stays
    accurate. Returns (reservation, error) with error
    'not_found' | 'no_reservation' | 'no_end'.
    """
    session = await db.get(ComputerSession, session_id)
    if not session or not session.is_active:
        return None, "not_found"

    if not session.reservation_id:
        return None, "no_reservation"
    reservation = await db.get(ComputerReservation, session.reservation_id)
    if reservation is None:
        return None, "no_reservation"

    base_end = session.session_end_time or reservation.reserved_end_time
    if base_end is None:
        return None, "no_end"

    new_end = base_end + timedelta(minutes=extra_minutes)
    session.session_end_time = new_end
    session.auto_logout_at = new_end - timedelta(minutes=SESSION_WARNING_MINUTES_BEFORE)
    session.was_extended = True
    session.extension_count += 1

    reservation.extended_until = new_end
    reservation.reserved_end_time = new_end
    reservation.session_duration_minutes = int(
        (new_end - reservation.reserved_start_time).total_seconds() / 60
    )
    reservation.extensions_used += 1
    reservation.extension_requested = True

    await log_system_event(
        db,
        event_type="extension_approved",
        description=f"Staff {staff_id} extended session {session_id} by {extra_minutes}m",
        computer_id=session.computer_id,
        session_id=session_id,
        reservation_id=session.reservation_id,
        user_id=session.patron_id,
    )
    await db.flush()
    return reservation, None


async def create_guest_pass(
    db: AsyncSession,
    guest_name: str,
    guest_email: Optional[str] = None,
    guest_phone: Optional[str] = None,
    max_sessions: int = 1,
    max_duration_minutes: int = 60,
    issued_by_staff_id: Optional[int] = None,
    allowed_computer_types: Optional[List[str]] = None,
) -> GuestPass:
    pass_code = f"GP-{uuid4().hex[:10].upper()}"

    guest_pass = GuestPass(
        guest_name=guest_name,
        guest_email=guest_email,
        guest_phone=guest_phone,
        pass_code=pass_code,
        max_sessions=max_sessions,
        max_duration_minutes_per_session=max_duration_minutes,
        valid_until=datetime.now(timezone.utc) + timedelta(days=GUEST_PASS_VALIDITY_DAYS),
        is_active=True,
        issued_by_staff_id=issued_by_staff_id,
        allowed_computer_types=allowed_computer_types or [],
    )

    db.add(guest_pass)
    await db.flush()

    # Log event
    await log_system_event(
        db,
        event_type="guest_pass_created",
        description=f"Guest pass created for {guest_name}",
        user_id=issued_by_staff_id,
    )

    return guest_pass


async def validate_guest_pass(db: AsyncSession, pass_code: str) -> Optional[GuestPass]:
    query = select(GuestPass).where(GuestPass.pass_code == pass_code)
    result = await db.execute(query)
    guest_pass = result.scalar_one_or_none()

    if not guest_pass:
        return None

    # Check if pass is still valid
    if not guest_pass.is_active:
        return None

    if guest_pass.valid_until < datetime.now(timezone.utc):
        return None

    if guest_pass.sessions_used >= guest_pass.max_sessions:
        return None

    return guest_pass


async def add_to_waitlist(
    db: AsyncSession,
    computer_id: int,
    patron_id: Optional[int],
    desired_start_time: datetime,
    duration_minutes: int,
    is_guest: bool = False,
    guest_phone: Optional[str] = None,
) -> Optional[ComputerWaitlist]:
    computer = await db.get(Computer, computer_id)
    if not computer:
        return None

    # Get current queue position
    query = (
        select(func.max(ComputerWaitlist.queue_position))
        .where(ComputerWaitlist.computer_id == computer_id)
        .where(ComputerWaitlist.status == ComputerWaitlistStatus.pending)
    )
    result = await db.execute(query)
    max_position = result.scalar() or 0

    waitlist_entry = ComputerWaitlist(
        computer_id=computer_id,
        patron_id=patron_id,
        is_guest=is_guest,
        guest_phone=guest_phone,
        desired_start_time=desired_start_time,
        desired_duration_minutes=duration_minutes,
        status=ComputerWaitlistStatus.pending,
        queue_position=max_position + 1,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=WAITLIST_EXPIRY_HOURS),
    )

    db.add(waitlist_entry)
    await db.flush()

    # Log event
    await log_system_event(
        db,
        event_type="waitlist_added",
        description=f"Added to waitlist for {computer.name}, position {waitlist_entry.queue_position}",
        computer_id=computer_id,
        user_id=patron_id,
    )

    return waitlist_entry


async def get_waitlist_queue(
    db: AsyncSession,
    computer_id: int,
) -> List[ComputerWaitlist]:
    query = (
        select(ComputerWaitlist)
        .where(ComputerWaitlist.computer_id == computer_id)
        .where(ComputerWaitlist.status == ComputerWaitlistStatus.pending)
        .order_by(ComputerWaitlist.queue_position)
    )
    result = await db.execute(query)
    return list(result.scalars())


async def notify_next_in_waitlist(
    db: AsyncSession,
    computer_id: int,
) -> Optional[ComputerWaitlist]:
    queue = await get_waitlist_queue(db, computer_id)
    if not queue:
        return None

    next_entry = queue[0]
    next_entry.status = ComputerWaitlistStatus.notified
    next_entry.notified_at = datetime.now(timezone.utc)

    # Try to send notification
    if next_entry.guest_phone:
        # SMS notification would go here
        next_entry.notification_method = "sms"
    elif next_entry.patron_id:
        # Email notification would go here
        next_entry.notification_method = "email"

    await db.flush()

    # Log event
    await log_system_event(
        db,
        event_type="waitlist_notified",
        description=f"Waitlist position {next_entry.queue_position} notified",
        computer_id=computer_id,
        user_id=next_entry.patron_id,
    )

    return next_entry


async def record_usage_stats(
    db: AsyncSession,
    computer_id: int,
    date: datetime,
) -> ComputerUsageStats:
    # Get existing stats for the day
    query = (
        select(ComputerUsageStats)
        .where(ComputerUsageStats.computer_id == computer_id)
        .where(
            func.date(ComputerUsageStats.date) == func.date(date)
        )
    )
    result = await db.execute(query)
    stats = result.scalar_one_or_none()

    if not stats:
        stats = ComputerUsageStats(
            computer_id=computer_id,
            date=date,
        )
        db.add(stats)
        await db.flush()

    # Recalculate stats for the day
    reservations_query = (
        select(ComputerReservation)
        .where(ComputerReservation.computer_id == computer_id)
        .where(
            func.date(ComputerReservation.reserved_start_time) == func.date(date)
        )
    )
    result = await db.execute(reservations_query)
    reservations = list(result.scalars())

    stats.total_reservations = len(reservations)
    stats.completed_sessions = len([r for r in reservations if r.status == ComputerReservationStatus.completed])
    stats.cancelled_reservations = len([r for r in reservations if r.status == ComputerReservationStatus.cancelled])
    stats.no_show_count = len([r for r in reservations if r.status == ComputerReservationStatus.no_show])
    stats.guest_sessions = len([r for r in reservations if r.is_guest_pass])
    stats.cardholders_sessions = stats.completed_sessions - stats.guest_sessions

    return stats


async def log_system_event(
    db: AsyncSession,
    event_type: str,
    description: str,
    computer_id: Optional[int] = None,
    reservation_id: Optional[int] = None,
    session_id: Optional[int] = None,
    user_id: Optional[int] = None,
    metadata: Optional[dict] = None,
    severity: str = "info",
) -> ComputerSystemLog:
    log_entry = ComputerSystemLog(
        event_type=event_type,
        description=description,
        computer_id=computer_id,
        reservation_id=reservation_id,
        session_id=session_id,
        user_id=user_id,
        system_metadata=metadata or {},
        severity=severity,
    )

    db.add(log_entry)
    await db.flush()

    return log_entry


# ---------------------------------------------------------------------------
# Auto-processing jobs (#8 — auto no-show + auto-logout)
# ---------------------------------------------------------------------------


async def process_computer_no_shows(db: AsyncSession) -> int:
    if not settings.computers_auto_no_show_enabled:
        return 0

    grace_minutes = max(0, settings.computers_auto_no_show_grace_minutes)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=grace_minutes)

    q = (
        select(ComputerReservation)
        .where(ComputerReservation.status == ComputerReservationStatus.confirmed)
        .where(ComputerReservation.reserved_start_time < cutoff)
        .where(ComputerReservation.checked_in_at.is_(None))
    )
    result = await db.execute(q)
    expired = list(result.scalars())
    if not expired:
        return 0

    affected_computers: set[int] = set()
    for reservation in expired:
        reservation.status = ComputerReservationStatus.no_show
        reservation.cancellation_reason = "auto_no_show"
        reservation.cancelled_at = now
        affected_computers.add(reservation.computer_id)
        await log_system_event(
            db,
            event_type="auto_no_show",
            description=(
                f"Reservation {reservation.id} marked no_show after "
                f"{grace_minutes}m grace"
            ),
            computer_id=reservation.computer_id,
            reservation_id=reservation.id,
            user_id=reservation.patron_id,
        )

    # Free affected computers that were holding `reserved` status.
    if affected_computers:
        comp_q = select(Computer).where(Computer.id.in_(affected_computers))
        comp_result = await db.execute(comp_q)
        for computer in comp_result.scalars():
            if computer.status == ComputerStatus.reserved:
                computer.status = ComputerStatus.available

    logger.info(
        "computer_auto_no_show processed=%d grace_minutes=%d",
        len(expired), grace_minutes,
    )

    # Best-effort live-update fan-out; loop locally to avoid one big
    # event swallowing N updates.
    try:
        from . import floor_view_bus
        for reservation in expired:
            await floor_view_bus.publish(
                "session_ended",
                computer_id=reservation.computer_id,
                reservation_id=reservation.id,
                by_staff=False,
                auto=True,
                reason="no_show",
            )
    except Exception:  # noqa: BLE001
        pass

    return len(expired)


async def process_computer_auto_logouts(db: AsyncSession) -> int:
    if not settings.computers_auto_logout_enabled:
        return 0

    now = datetime.now(timezone.utc)
    q = (
        select(ComputerSession)
        .where(ComputerSession.is_active == True)  # noqa: E712
        .where(ComputerSession.auto_logout_executed == False)  # noqa: E712
        .where(
            or_(
                ComputerSession.auto_logout_at < now,
                and_(
                    ComputerSession.auto_logout_at.is_(None),
                    ComputerSession.scheduled_end < now,
                ),
            )
        )
    )
    result = await db.execute(q)
    sessions_to_end = list(result.scalars())
    if not sessions_to_end:
        return 0

    processed = 0
    for session in sessions_to_end:
        session.auto_logout_executed = True
        ended = await end_session(db, session.id, logoff_reason="auto_logout")
        if ended is not None:
            processed += 1
            await log_system_event(
                db,
                event_type="auto_logout",
                description=f"Session {session.id} auto-logged-out at deadline",
                computer_id=session.computer_id,
                session_id=session.id,
                reservation_id=session.reservation_id,
                user_id=session.patron_id,
            )
            try:
                from . import floor_view_bus
                await floor_view_bus.publish(
                    "session_ended",
                    computer_id=session.computer_id,
                    reservation_id=session.reservation_id,
                    by_staff=False,
                    auto=True,
                    reason="auto_logout",
                )
            except Exception:  # noqa: BLE001
                pass

    logger.info("computer_auto_logout processed=%d", processed)
    return processed
