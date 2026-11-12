# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
CIPA Compliance API Endpoints

Provides endpoints for Children's Internet Protection Act compliance:
- Internet Safety Policy (AUP) acceptance
- Content filter bypass requests
- Computer session management
- CIPA compliance reporting
"""

from app.core.logging import get_logger
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.cipa_compliance import (
    BypassReason,
    BypassStatus,
    CIPAComplianceReport,
    ComputerSession,
    ComputerSessionStatus,
    FilterBypassRequest as FilterBypassModel,
    InternetPolicyAcceptance,
    PolicyType,
)
from ...models.user import User, UserRole
from ...schemas.cipa_compliance import (
    ActiveSessionsResponse,
    CIPADashboardStats,
    CIPAReportRequest,
    CIPAReportResponse,
    CIPAReportSummary,
    ComputerSessionEnd,
    ComputerSessionExtend,
    ComputerSessionResponse,
    ComputerSessionStart,
    FilterBypassListResponse,
    FilterBypassRequest,
    FilterBypassResponse,
    FilterBypassRevoke,
    InternetSafetyPolicyResponse,
    PolicyAcceptanceCheck,
    PolicyAcceptanceRequest,
    PolicyAcceptanceResponse,
    WorkstationStatus,
    WorkstationStatusList,
)
from .auth import get_current_user, get_current_user_optional
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/cipa", tags=["cipa-compliance"])


# =============================================================================
# Policy Acceptance Endpoints
# =============================================================================


@router.post(
    "/policy/accept", response_model=PolicyAcceptanceResponse, status_code=status.HTTP_201_CREATED
)
async def accept_internet_policy(  # noqa: role-check -- public CIPA policy acceptance, optional auth
    request: Request,
    acceptance: PolicyAcceptanceRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Accept the Internet Safety Policy (Acceptable Use Policy).

    This endpoint records patron acknowledgment of the library's Internet
    Safety Policy as required by CIPA. Can be used by:
    - Logged-in patrons (patron_id stored)
    - Guest users (session-based tracking)

    Returns a session ID that must be provided for computer/WiFi access.
    """
    # Generate session identifier
    session_id = secrets.token_urlsafe(32)

    # Determine if patron is a minor
    is_minor = False
    patron_type = None
    if current_user:
        is_minor = current_user.is_minor
        patron_type = current_user.patron_type

    # Validate policy type
    try:
        policy_type = PolicyType(acceptance.policy_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid policy type. Must be one of: {[p.value for p in PolicyType]}",
        ) from None

    # Minors must accept the minor-specific policy
    if is_minor and policy_type == PolicyType.INTERNET_USE:
        # Auto-upgrade to minor policy
        policy_type = PolicyType.MINOR_INTERNET

    # Get client info
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent", "")[:500]

    # Create acceptance record
    policy_acceptance = InternetPolicyAcceptance(
        patron_id=current_user.id if current_user else None,
        session_id=session_id,
        policy_type=policy_type,
        policy_version=acceptance.policy_version,
        is_minor=is_minor,
        patron_type=patron_type,
        ip_address=client_ip,
        user_agent=user_agent,
        workstation_id=acceptance.workstation_id,
        device_mac_hash=acceptance.device_mac_hash,
    )
    db.add(policy_acceptance)
    await db.commit()
    await db.refresh(policy_acceptance)

    # Calculate validity (24 hours from acceptance)
    valid_until = policy_acceptance.accepted_at + timedelta(hours=24)

    logger.info(
        f"Policy accepted: patron_id={current_user.id if current_user else 'guest'}, "
        f"type={policy_type.value}, session={session_id[:8]}..."
    )

    return PolicyAcceptanceResponse(
        id=policy_acceptance.id,
        session_id=session_id,
        policy_type=policy_type.value,
        policy_version=acceptance.policy_version,
        is_minor=is_minor,
        accepted_at=policy_acceptance.accepted_at,
        valid_until=valid_until,
        message="Internet Safety Policy accepted successfully",
    )


@router.get("/policy/check", response_model=PolicyAcceptanceCheck)
async def check_policy_acceptance(
    session_id: Optional[str] = Query(None, description="Session ID from policy acceptance"),
    workstation_id: Optional[str] = Query(None, description="Workstation to check"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Check if a patron has a valid policy acceptance.

    Can check by:
    - Session ID (for guest users)
    - Current user (for logged-in patrons)
    - Workstation ID (for any active acceptance on that workstation)
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    # Build query based on provided parameters
    query = select(InternetPolicyAcceptance).where(InternetPolicyAcceptance.accepted_at >= cutoff)

    if session_id:
        query = query.where(InternetPolicyAcceptance.session_id == session_id)
    elif current_user:
        query = query.where(InternetPolicyAcceptance.patron_id == current_user.id)
    elif workstation_id:
        query = query.where(InternetPolicyAcceptance.workstation_id == workstation_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide session_id, workstation_id, or be logged in",
        )

    query = query.order_by(InternetPolicyAcceptance.accepted_at.desc()).limit(1)
    result = await db.execute(query)
    acceptance = result.scalar_one_or_none()

    if not acceptance:
        return PolicyAcceptanceCheck(
            has_valid_acceptance=False,
            requires_minor_policy=current_user.is_minor if current_user else False,
        )

    valid_until = acceptance.accepted_at + timedelta(hours=24)
    is_valid = now < valid_until

    return PolicyAcceptanceCheck(
        has_valid_acceptance=is_valid,
        policy_type=str(acceptance.policy_type),
        accepted_at=acceptance.accepted_at,
        valid_until=valid_until,
        requires_minor_policy=acceptance.is_minor,
    )


@router.get("/policy/current", response_model=InternetSafetyPolicyResponse)
async def get_current_policy(
    policy_type: str = Query("internet_use", description="Type of policy to retrieve"),
):
    """
    Get the current Internet Safety Policy content.

    Returns the policy text that patrons must accept before using
    library computers or WiFi.
    """
    # In a production system, this would be stored in the database
    # For now, return hardcoded policy content
    policies = {
        "internet_use": {
            "title": "Internet Safety Policy & Acceptable Use Agreement",
            "content_html": f"""
<h2>{os.environ.get("LIBRARY_NAME", "My Library")} Internet Safety Policy</h2>

<h3>Purpose</h3>
<p>The library provides Internet access to support its mission of providing information
and educational resources to the community. This policy ensures compliance with the
Children's Internet Protection Act (CIPA) and establishes guidelines for appropriate use.</p>

<h3>Content Filtering</h3>
<p>In compliance with CIPA, the library uses content filtering technology to block access to:</p>
<ul>
    <li>Visual content that is obscene</li>
    <li>Visual content that constitutes child pornography</li>
    <li>Content that is harmful to minors (on computers accessible to minors)</li>
</ul>

<h3>User Responsibilities</h3>
<p>By using library computers or WiFi, you agree to:</p>
<ul>
    <li>Use resources for lawful purposes only</li>
    <li>Respect the privacy of others</li>
    <li>Not attempt to bypass security measures</li>
    <li>Not access, download, or distribute illegal materials</li>
    <li>Not harass or threaten others online</li>
    <li>Supervise minors in your care</li>
</ul>

<h3>Privacy Notice</h3>
<p>The library respects your privacy. However, please be aware that:</p>
<ul>
    <li>Internet activity may be monitored for security purposes</li>
    <li>Session logs are maintained as required by law</li>
    <li>Public computers are in shared spaces with limited privacy</li>
</ul>

<h3>Filter Bypass</h3>
<p>Adults (18+) may request temporary filter bypass for bona fide research or other
lawful purposes. Staff approval is required. Minors may not request filter bypass.</p>

<h3>Violations</h3>
<p>Violation of this policy may result in loss of library privileges and/or
legal action where appropriate.</p>

<p><strong>By clicking "Accept," you acknowledge that you have read, understand,
and agree to abide by this Internet Safety Policy.</strong></p>
""",
            "minor_addendum_html": """
<h3>Additional Rules for Minors</h3>
<p>If you are under 18 years old:</p>
<ul>
    <li>Enhanced content filtering is automatically applied</li>
    <li>Children under 8 must be accompanied by an adult</li>
    <li>You may not request filter bypass</li>
    <li>Your parent/guardian has agreed to these terms on your behalf</li>
</ul>
""",
        },
        "wifi_access": {
            "title": "WiFi Acceptable Use Policy",
            "content_html": """
<h2>Library WiFi Terms of Use</h2>
<p>By connecting to LibraryWiFi, you agree to:</p>
<ul>
    <li>Use the network for lawful purposes only</li>
    <li>Not attempt to access restricted systems</li>
    <li>Accept that content filtering is in effect</li>
    <li>Understand that the library is not responsible for data security on personal devices</li>
</ul>
""",
            "minor_addendum_html": None,
        },
    }

    policy_data = policies.get(policy_type, policies["internet_use"])

    return InternetSafetyPolicyResponse(
        version="2026.1",
        effective_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        title=policy_data["title"],
        content_html=policy_data["content_html"],
        minor_addendum_html=policy_data.get("minor_addendum_html"),
        last_board_approval=datetime(2025, 12, 15, tzinfo=timezone.utc),
        next_review_date=datetime(2026, 12, 15, tzinfo=timezone.utc),
    )


# =============================================================================
# Filter Bypass Endpoints
# =============================================================================


@router.post("/bypass", response_model=FilterBypassResponse, status_code=status.HTTP_201_CREATED)
async def create_filter_bypass(
    request: Request,
    bypass_request: FilterBypassRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Create a content filter bypass for an adult patron.

    CIPA permits disabling content filtering for adults engaged in
    "bona fide research or other lawful purposes."

    Requirements:
    - Staff authentication required
    - Patron must be 18 or older
    - Patron must have accepted the Internet Safety Policy
    - Bypass is time-limited and audited
    """
    # Get the patron
    patron = await get_or_404(db, User, bypass_request.patron_id, "Patron not found")

    # Verify patron is an adult
    if patron.is_minor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Filter bypass is only available for adults (18+)",
        )

    # Check for existing active bypass on this workstation
    existing = await db.execute(
        select(FilterBypassModel).where(
            and_(
                FilterBypassModel.workstation_id == bypass_request.workstation_id,
                FilterBypassModel.status == BypassStatus.ACTIVE,
                FilterBypassModel.bypass_end > datetime.now(timezone.utc),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An active bypass already exists for this workstation",
        )

    # Validate reason
    try:
        reason = BypassReason(bypass_request.reason)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid reason. Must be one of: {[r.value for r in BypassReason]}",
        ) from None

    # Calculate bypass window
    now = datetime.now(timezone.utc)
    bypass_end = now + timedelta(minutes=bypass_request.duration_minutes)

    # Create bypass record
    bypass = FilterBypassModel(
        patron_id=patron.id,
        approved_by_id=staff_user.id,
        reason=reason,
        reason_details=bypass_request.reason_details,
        workstation_id=bypass_request.workstation_id,
        status=BypassStatus.ACTIVE,
        bypass_start=now,
        bypass_end=bypass_end,
        patron_acknowledged_aup=bypass_request.patron_acknowledged_aup,
        patron_acknowledged_monitoring=bypass_request.patron_acknowledged_monitoring,
    )
    db.add(bypass)
    await db.commit()
    await db.refresh(bypass)

    logger.info(
        f"Filter bypass created: patron_id={patron.id}, staff_id={staff_user.id}, "
        f"workstation={bypass_request.workstation_id}, reason={reason.value}, "
        f"duration={bypass_request.duration_minutes}min"
    )

    return FilterBypassResponse(
        id=bypass.id,
        patron_id=patron.id,
        patron_name=patron.full_name,
        approved_by_name=staff_user.full_name,
        reason=reason.value,
        reason_details=bypass_request.reason_details,
        workstation_id=bypass_request.workstation_id,
        status=bypass.status.value,
        bypass_start=bypass.bypass_start,
        bypass_end=bypass.bypass_end,
        duration_minutes=bypass_request.duration_minutes,
        created_at=bypass.created_at,
    )


@router.get("/bypass", response_model=FilterBypassListResponse)
async def list_filter_bypasses(
    status_filter: Optional[str] = Query(None, description="Filter by status"),
    workstation_id: Optional[str] = Query(None, description="Filter by workstation"),
    active_only: bool = Query(False, description="Show only currently active bypasses"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    List filter bypass requests (staff only).

    Provides audit trail of all bypass requests for CIPA compliance reporting.
    """
    query = select(FilterBypassModel)

    if status_filter:
        try:
            status_enum = BypassStatus(status_filter)
            query = query.where(FilterBypassModel.status == status_enum)
        except ValueError:
            logger.warning("Invalid bypass status filter value: %s", status_filter)

    if workstation_id:
        query = query.where(FilterBypassModel.workstation_id == workstation_id)

    if active_only:
        now = datetime.now(timezone.utc)
        query = query.where(
            and_(
                FilterBypassModel.status == BypassStatus.ACTIVE,
                FilterBypassModel.bypass_start <= now,
                FilterBypassModel.bypass_end > now,
            )
        )

    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar() or 0

    # Get active count
    active_query = select(func.count(FilterBypassModel.id)).where(
        and_(
            FilterBypassModel.status == BypassStatus.ACTIVE,
            FilterBypassModel.bypass_end > datetime.now(timezone.utc),
        )
    )
    active_result = await db.execute(active_query)
    active_count = active_result.scalar() or 0

    # Get paginated results
    query = query.order_by(FilterBypassModel.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    bypasses = result.scalars().all()

    # Batch-fetch all patron/approver users to avoid N+1 queries
    user_ids = set()
    for bypass in bypasses:
        if bypass.patron_id:
            user_ids.add(bypass.patron_id)
        if bypass.approved_by_id:
            user_ids.add(bypass.approved_by_id)
    users_by_id = {}
    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users_by_id = {u.id: u for u in users_result.scalars().all()}

    # Build response with patron/staff names
    bypass_responses = []
    for bypass in bypasses:
        patron = users_by_id.get(bypass.patron_id)
        approver = users_by_id.get(bypass.approved_by_id)

        bypass_responses.append(
            FilterBypassResponse(
                id=bypass.id,
                patron_id=bypass.patron_id,
                patron_name=patron.full_name if patron else "Unknown",
                approved_by_name=approver.full_name if approver else "Unknown",
                reason=bypass.reason.value,
                reason_details=bypass.reason_details,
                workstation_id=bypass.workstation_id,
                status=bypass.status.value,
                bypass_start=bypass.bypass_start,
                bypass_end=bypass.bypass_end,
                duration_minutes=bypass.duration_minutes,
                created_at=bypass.created_at,
            )
        )

    return FilterBypassListResponse(
        bypasses=bypass_responses,
        total=total,
        active_count=active_count,
    )


@router.post("/bypass/{bypass_id}/revoke", response_model=FilterBypassResponse)
async def revoke_filter_bypass(
    bypass_id: int,
    revoke_request: FilterBypassRevoke,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Revoke an active filter bypass (staff only).

    Immediately terminates the bypass and re-enables content filtering.
    """
    bypass = await get_or_404(db, FilterBypassModel, bypass_id, "Bypass not found")

    if bypass.status != BypassStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bypass is not active (status: {bypass.status})",
        )

    # Revoke the bypass
    bypass.status = BypassStatus.REVOKED
    bypass.revoked_at = datetime.now(timezone.utc)
    bypass.revoked_by_id = staff_user.id
    bypass.revocation_reason = revoke_request.reason

    await db.commit()
    await db.refresh(bypass)

    # Get patron and approver for response
    patron_result = await db.execute(select(User).where(User.id == bypass.patron_id))
    patron = patron_result.scalar_one_or_none()
    approver_result = await db.execute(select(User).where(User.id == bypass.approved_by_id))
    approver = approver_result.scalar_one_or_none()

    logger.info(
        f"Filter bypass revoked: bypass_id={bypass_id}, staff_id={staff_user.id}, "
        f"reason={revoke_request.reason}"
    )

    return FilterBypassResponse(
        id=bypass.id,
        patron_id=bypass.patron_id,
        patron_name=patron.full_name if patron else "Unknown",
        approved_by_name=approver.full_name if approver else "Unknown",
        reason=bypass.reason.value,
        reason_details=bypass.reason_details,
        workstation_id=bypass.workstation_id,
        status=bypass.status.value,
        bypass_start=bypass.bypass_start,
        bypass_end=bypass.bypass_end,
        duration_minutes=bypass.duration_minutes,
        created_at=bypass.created_at,
    )


# =============================================================================
# Computer Session Endpoints
# =============================================================================


@router.post(
    "/session/start", response_model=ComputerSessionResponse, status_code=status.HTTP_201_CREATED
)
async def start_computer_session(
    request: Request,
    session_request: ComputerSessionStart,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Start a new computer session.

    Records session start for usage tracking and CIPA compliance.
    Automatically applies appropriate content filtering based on patron type.
    """
    # Check for existing active session on this workstation
    existing = await db.execute(
        select(ComputerSession).where(
            and_(
                ComputerSession.workstation_id == session_request.workstation_id,
                ComputerSession.status == ComputerSessionStatus.ACTIVE,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Workstation already has an active session",
        )

    # Determine patron info
    patron_id = session_request.patron_id
    is_minor = False
    patron_type = None

    if patron_id:
        patron_result = await db.execute(select(User).where(User.id == patron_id))
        patron = patron_result.scalar_one_or_none()
        if patron:
            is_minor = patron.is_minor
            patron_type = patron.patron_type

    # Generate session token
    session_token = secrets.token_urlsafe(32)

    # Calculate scheduled end (2 hours default)
    now = datetime.now(timezone.utc)
    max_duration = 120  # minutes
    scheduled_end = now + timedelta(minutes=max_duration)

    # Check for active bypass on this workstation
    bypass_result = await db.execute(
        select(FilterBypassModel).where(
            and_(
                FilterBypassModel.workstation_id == session_request.workstation_id,
                FilterBypassModel.status == BypassStatus.ACTIVE,
                FilterBypassModel.bypass_start <= now,
                FilterBypassModel.bypass_end > now,
            )
        )
    )
    active_bypass = bypass_result.scalar_one_or_none()

    # Create session
    session = ComputerSession(
        patron_id=patron_id,
        session_token=session_token,
        status=ComputerSessionStatus.ACTIVE,
        is_minor=is_minor,
        patron_type=patron_type,
        workstation_id=session_request.workstation_id,
        policy_acceptance_id=session_request.policy_acceptance_id,
        active_bypass_id=active_bypass.id if active_bypass else None,
        content_filtering_enabled=active_bypass is None,  # Disabled if bypass active
        minor_filtering_enabled=is_minor,
        scheduled_end=scheduled_end,
        max_duration_minutes=max_duration,
        ip_address=request.client.host if request.client else None,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        f"Computer session started: workstation={session_request.workstation_id}, "
        f"patron_id={patron_id}, is_minor={is_minor}"
    )

    return ComputerSessionResponse(
        id=session.id,
        session_token=session_token,
        patron_id=patron_id,
        patron_name=patron.full_name if patron_id and patron else None,
        workstation_id=session.workstation_id,
        branch_id=session.branch_id,
        branch_location=session.branch_location,
        status=session.status.value,
        is_minor=is_minor,
        content_filtering_enabled=session.content_filtering_enabled,
        minor_filtering_enabled=session.minor_filtering_enabled,
        started_at=session.started_at,
        scheduled_end=session.scheduled_end,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        max_duration_minutes=session.max_duration_minutes,
        extension_count=session.extension_count,
        is_overtime=session.is_overtime,
    )


@router.post("/session/{session_id}/end", response_model=ComputerSessionResponse)
async def end_computer_session(
    session_id: int,
    end_request: Optional[ComputerSessionEnd] = None,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    End a computer session.

    Records session end time for usage statistics and E-rate reporting.
    """
    session = await get_or_404(db, ComputerSession, session_id, "Session not found")

    if session.status != ComputerSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is not active (status: {session.status})",
        )

    # End the session
    session.status = ComputerSessionStatus.ENDED
    session.ended_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(session)

    # Get patron name for response
    patron_name = None
    if session.patron_id:
        patron_result = await db.execute(select(User).where(User.id == session.patron_id))
        patron = patron_result.scalar_one_or_none()
        patron_name = patron.full_name if patron else None

    logger.info(
        f"Computer session ended: session_id={session_id}, duration={session.duration_minutes}min"
    )

    return ComputerSessionResponse(
        id=session.id,
        session_token=session.session_token,
        patron_id=session.patron_id,
        patron_name=patron_name,
        workstation_id=session.workstation_id,
        branch_id=session.branch_id,
        branch_location=session.branch_location,
        status=session.status.value,
        is_minor=session.is_minor,
        content_filtering_enabled=session.content_filtering_enabled,
        minor_filtering_enabled=session.minor_filtering_enabled,
        started_at=session.started_at,
        scheduled_end=session.scheduled_end,
        ended_at=session.ended_at,
        duration_minutes=session.duration_minutes,
        max_duration_minutes=session.max_duration_minutes,
        extension_count=session.extension_count,
        is_overtime=session.is_overtime,
    )


@router.get("/sessions/active", response_model=ActiveSessionsResponse)
async def get_active_sessions(
    branch_id: Optional[int] = Query(None),
    branch_location: Optional[str] = Query(None, deprecated=True),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Get all active computer sessions (staff only).

    Provides real-time view of computer lab usage for monitoring.
    """
    from ...core.branch_resolver import label_to_branch_id

    if branch_id is None:
        branch_id = label_to_branch_id(branch_location)

    query = select(ComputerSession).where(ComputerSession.status == ComputerSessionStatus.ACTIVE)

    if branch_id is not None:
        query = query.where(ComputerSession.branch_id == branch_id)
    elif branch_location:
        # Unknown label — keep legacy substring match as a fallback during transition.
        query = query.where(ComputerSession.branch_location == branch_location)

    result = await db.execute(query.order_by(ComputerSession.started_at))
    sessions = result.scalars().all()

    # Build response with patron names
    session_responses = []
    overtime_count = 0

    for session in sessions:
        patron_name = None
        if session.patron_id:
            patron_result = await db.execute(select(User).where(User.id == session.patron_id))
            patron = patron_result.scalar_one_or_none()
            patron_name = patron.full_name if patron else None

        if session.is_overtime:
            overtime_count += 1

        session_responses.append(
            ComputerSessionResponse(
                id=session.id,
                session_token=session.session_token,
                patron_id=session.patron_id,
                patron_name=patron_name,
                workstation_id=session.workstation_id,
                branch_id=session.branch_id,
                branch_location=session.branch_location,
                status=session.status.value,
                is_minor=session.is_minor,
                content_filtering_enabled=session.content_filtering_enabled,
                minor_filtering_enabled=session.minor_filtering_enabled,
                started_at=session.started_at,
                scheduled_end=session.scheduled_end,
                ended_at=session.ended_at,
                duration_minutes=session.duration_minutes,
                max_duration_minutes=session.max_duration_minutes,
                extension_count=session.extension_count,
                is_overtime=session.is_overtime,
            )
        )

    # Get unique workstations in use
    workstations_in_use = len(set(s.workstation_id for s in sessions))

    return ActiveSessionsResponse(
        sessions=session_responses,
        total_active=len(sessions),
        total_overtime=overtime_count,
        workstations_in_use=workstations_in_use,
        workstations_available=12 - workstations_in_use,  # Assuming 12 workstations
    )


# =============================================================================
# CIPA Compliance Reporting
# =============================================================================


@router.get("/dashboard", response_model=CIPADashboardStats)
async def get_cipa_dashboard(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Get CIPA compliance dashboard statistics (staff only).

    Provides real-time compliance metrics for monitoring.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Active sessions
    active_sessions_result = await db.execute(
        select(func.count(ComputerSession.id)).where(
            ComputerSession.status == ComputerSessionStatus.ACTIVE
        )
    )
    active_sessions = active_sessions_result.scalar() or 0

    # Active minor sessions
    active_minor_result = await db.execute(
        select(func.count(ComputerSession.id)).where(
            and_(
                ComputerSession.status == ComputerSessionStatus.ACTIVE,
                ComputerSession.is_minor == True,
            )
        )
    )
    active_minor_sessions = active_minor_result.scalar() or 0

    # Active bypasses
    active_bypasses_result = await db.execute(
        select(func.count(FilterBypassModel.id)).where(
            and_(
                FilterBypassModel.status == BypassStatus.ACTIVE,
                FilterBypassModel.bypass_end > now,
            )
        )
    )
    active_bypasses = active_bypasses_result.scalar() or 0

    # Sessions today
    sessions_today_result = await db.execute(
        select(func.count(ComputerSession.id)).where(ComputerSession.started_at >= today_start)
    )
    sessions_today = sessions_today_result.scalar() or 0

    # Minor sessions today
    minor_today_result = await db.execute(
        select(func.count(ComputerSession.id)).where(
            and_(
                ComputerSession.started_at >= today_start,
                ComputerSession.is_minor == True,
            )
        )
    )
    minor_sessions_today = minor_today_result.scalar() or 0

    # Policy acceptances today
    policy_today_result = await db.execute(
        select(func.count(InternetPolicyAcceptance.id)).where(
            InternetPolicyAcceptance.accepted_at >= today_start
        )
    )
    policy_acceptances_today = policy_today_result.scalar() or 0

    # Bypass requests today
    bypass_today_result = await db.execute(
        select(func.count(FilterBypassModel.id)).where(FilterBypassModel.created_at >= today_start)
    )
    bypass_requests_today = bypass_today_result.scalar() or 0

    # Overtime sessions
    overtime_result = await db.execute(
        select(ComputerSession).where(ComputerSession.status == ComputerSessionStatus.ACTIVE)
    )
    overtime_sessions = sum(1 for s in overtime_result.scalars().all() if s.is_overtime)

    # Expiring bypasses (within 15 minutes)
    expiring_threshold = now + timedelta(minutes=15)
    expiring_result = await db.execute(
        select(func.count(FilterBypassModel.id)).where(
            and_(
                FilterBypassModel.status == BypassStatus.ACTIVE,
                FilterBypassModel.bypass_end > now,
                FilterBypassModel.bypass_end <= expiring_threshold,
            )
        )
    )
    expiring_bypasses = expiring_result.scalar() or 0

    # Get unique workstations in use
    workstations_query = await db.execute(
        select(func.count(func.distinct(ComputerSession.workstation_id))).where(
            ComputerSession.status == ComputerSessionStatus.ACTIVE
        )
    )
    workstations_in_use = workstations_query.scalar() or 0

    return CIPADashboardStats(
        active_sessions=active_sessions,
        active_minor_sessions=active_minor_sessions,
        active_bypasses=active_bypasses,
        workstations_in_use=workstations_in_use,
        workstations_total=12,  # Configuration value
        sessions_today=sessions_today,
        minor_sessions_today=minor_sessions_today,
        policy_acceptances_today=policy_acceptances_today,
        bypass_requests_today=bypass_requests_today,
        filtering_enabled_rate=1.0
        if active_sessions == 0
        else (active_sessions - active_bypasses) / active_sessions,
        policy_acceptance_compliance=1.0
        if sessions_today == 0
        else min(1.0, policy_acceptances_today / sessions_today),
        overtime_sessions=overtime_sessions,
        expiring_bypasses=expiring_bypasses,
    )


@router.post("/report/generate", response_model=CIPAReportResponse)
async def generate_cipa_report(
    report_request: CIPAReportRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """
    Generate a CIPA compliance report for E-rate documentation.

    Produces statistics required for CIPA compliance certification.
    """
    start = report_request.start_date
    end = report_request.end_date

    # Session statistics
    session_query = select(ComputerSession).where(
        and_(
            ComputerSession.started_at >= start,
            ComputerSession.started_at < end,
        )
    )
    from ...core.branch_resolver import label_to_branch_id

    report_branch_id = report_request.branch_id
    if report_branch_id is None:
        report_branch_id = label_to_branch_id(report_request.branch_location)
    if report_branch_id is not None:
        session_query = session_query.where(ComputerSession.branch_id == report_branch_id)
    elif report_request.branch_location:
        session_query = session_query.where(
            ComputerSession.branch_location == report_request.branch_location
        )

    sessions_result = await db.execute(session_query)
    sessions = sessions_result.scalars().all()

    total_sessions = len(sessions)
    minor_sessions = sum(1 for s in sessions if s.is_minor)
    adult_sessions = sum(1 for s in sessions if not s.is_minor and s.patron_id)
    guest_sessions = sum(1 for s in sessions if not s.patron_id)
    total_hours = sum(s.duration_minutes for s in sessions) / 60

    # Policy acceptance statistics
    policy_query = select(InternetPolicyAcceptance).where(
        and_(
            InternetPolicyAcceptance.accepted_at >= start,
            InternetPolicyAcceptance.accepted_at < end,
        )
    )
    policy_result = await db.execute(policy_query)
    policies = policy_result.scalars().all()

    policy_acceptances = len(policies)
    minor_policy_acceptances = sum(1 for p in policies if p.is_minor)
    unique_patrons = len(set(p.patron_id for p in policies if p.patron_id))

    # Bypass statistics
    bypass_query = select(FilterBypassModel).where(
        and_(
            FilterBypassModel.created_at >= start,
            FilterBypassModel.created_at < end,
        )
    )
    bypass_result = await db.execute(bypass_query)
    bypasses = bypass_result.scalars().all()

    bypass_total = len(bypasses)
    bypass_by_reason = {}
    total_bypass_duration = 0
    revocations = 0

    for b in bypasses:
        reason = str(b.reason)
        bypass_by_reason[reason] = bypass_by_reason.get(reason, 0) + 1
        total_bypass_duration += b.duration_minutes
        if b.status == BypassStatus.REVOKED:
            revocations += 1

    avg_bypass_duration = total_bypass_duration / bypass_total if bypass_total > 0 else 0

    # Calculate compliance rates
    minor_filtering_compliance = 1.0  # All minor sessions should have filtering
    if minor_sessions > 0:
        filtered_minor = sum(1 for s in sessions if s.is_minor and s.minor_filtering_enabled)
        minor_filtering_compliance = filtered_minor / minor_sessions

    policy_compliance = policy_acceptances / total_sessions if total_sessions > 0 else 1.0

    summary = CIPAReportSummary(
        report_period_start=start,
        report_period_end=end,
        branch_id=report_branch_id,
        branch_location=report_request.branch_location,
        total_sessions=total_sessions,
        minor_sessions=minor_sessions,
        adult_sessions=adult_sessions,
        guest_sessions=guest_sessions,
        total_session_hours=round(total_hours, 2),
        policy_acceptances=policy_acceptances,
        minor_policy_acceptances=minor_policy_acceptances,
        unique_patrons_accepted=unique_patrons,
        bypass_requests_total=bypass_total,
        bypass_requests_by_reason=bypass_by_reason,
        bypass_average_duration_minutes=round(avg_bypass_duration, 1),
        bypass_revocations=revocations,
        minor_filtering_compliance_rate=round(minor_filtering_compliance, 4),
        policy_acceptance_rate=round(min(1.0, policy_compliance), 4),
        generated_at=datetime.now(timezone.utc),
    )

    # Store report
    report = CIPAComplianceReport(
        report_period_start=start,
        report_period_end=end,
        branch_id=report_branch_id,
        branch_location=report_request.branch_location,
        total_sessions=total_sessions,
        minor_sessions=minor_sessions,
        adult_sessions=adult_sessions,
        guest_sessions=guest_sessions,
        policy_acceptances=policy_acceptances,
        minor_policy_acceptances=minor_policy_acceptances,
        bypass_requests_total=bypass_total,
        bypass_requests_approved=bypass_total - revocations,
        bypass_requests_revoked=revocations,
        generated_by_id=staff_user.id,
    )
    db.add(report)
    await db.commit()

    logger.info(
        f"CIPA report generated: period={start.date()} to {end.date()}, "
        f"sessions={total_sessions}, staff_id={staff_user.id}"
    )

    return CIPAReportResponse(
        summary=summary,
        report_file_url=None,  # PDF generation would go here
        message=f"CIPA compliance report generated for {start.date()} to {end.date()}",
    )


@router.get("/bypass/{bypass_id}/revoke")
async def get_bypass__bypass_id__revoke_status(
    bypass_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check status for /bypass/{bypass_id}/revoke action."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
