# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.database import get_db
from ....core.email import send_verification_email
from ....core.rate_limit import client_ip, limiter
from ....core.turnstile import verify_turnstile
from ....core.security import (
    PasswordValidationError,
    create_verification_token,
    get_verification_token_expiry,
    hash_password_async,
    hash_reset_token,
    validate_password,
)
from ....models.user import User, UserRole, email_blind_hash
from ....schemas.user import MessageResponse, UserCreate, UserResponse
from .helpers import generate_temp_card, get_current_user
from ....services.reports.cache_invalidator import invalidate_patron_reports

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register(
    request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)
):
    """Register a new patron account."""

    if not await verify_turnstile(user_in.turnstile_token, client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry."
        )
    # Check if email exists -- use generic message to prevent user enumeration
    result = await db.execute(select(User).where(User.email_hash == email_blind_hash(user_in.email)))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="We couldn't create your account. Please check that all required fields are filled in and try again.")

    # Check if email is blocked from re-registration (90-day fraud prevention)
    from ..privacy import check_email_blocked
    is_blocked, block_expires = await check_email_blocked(db, user_in.email)
    if is_blocked:
        # Don't reveal exact reason for security
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email is not available for registration right now."
        )

    # Validate password
    try:
        validate_password(user_in.password)
    except PasswordValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Generate verification token -- store hashed, send plain (like reset tokens)
    verification_token = create_verification_token()

    # Create user
    user = User(
        email=user_in.email,
        password_hash=await hash_password_async(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        address=user_in.address,
        role=UserRole.PATRON,
        library_card=generate_temp_card(),
        card_type="temporary",
        card_trial_expires_at=datetime.now(timezone.utc) + timedelta(days=settings.temporary_card_trial_days),
        email_verified=False,
        verification_token=hash_reset_token(verification_token),
        verification_token_expires=get_verification_token_expiry(),
    )
    if user_in.phone:
        user.set_phone(user_in.phone)
    # Assign home_library_system_id so this patron counts toward the onboarding
    # checklist add_patrons step (which filters by this column).
    from app.services.setup_service import get_default_library_system_id
    user.home_library_system_id = await get_default_library_system_id(db)
    db.add(user)
    # Flush so user.id is assigned before we link any orphan card applications;
    # both writes share the same transaction so the linkage is atomic with the
    # user create.
    await db.flush()

    # Link any anonymous (user_id IS NULL) pending/under-review card
    # applications submitted with the same email to this new account. Without
    # this, staff approval writes the assigned card number into the
    # application row but never back to the user (see
    # api/v1/card_applications.py:review_application), leaving the patron with
    # a temp card and an orphan approved application.
    #
    # Email comparison is case-insensitive: UserCreate.email goes through
    # TestableEmail / validate_email_allow_test which normalizes, but
    # CardApplicationCreate.email uses plain EmailStr which only normalizes
    # the domain. Without lower-casing both sides, "Jane@example.com" on
    # the application and "jane@example.com" on the new user would not
    # match and the bug would silently re-appear.
    from sqlalchemy import func
    from ....models.card_application import (
        CardApplicationStatus,
        LibraryCardApplication,
    )
    await db.execute(
        LibraryCardApplication.__table__.update()
        .where(
            func.lower(LibraryCardApplication.email) == user_in.email.lower(),
            LibraryCardApplication.user_id.is_(None),
            LibraryCardApplication.status.in_(
                [
                    CardApplicationStatus.pending,
                    CardApplicationStatus.under_review,
                ]
            ),
        )
        .values(user_id=user.id)
    )

    await db.commit()
    await db.refresh(user)
    # Set explicitly to avoid lazy-load MissingGreenlet error in async serialization

    # Invalidate patron report cache after new registration
    await invalidate_patron_reports()

    # NOTE: Residency is intentionally NOT auto-detected at signup.
    # The registration payload stores address as a single freeform string
    # (UserCreate.address), so user.zip_code/state are unpopulated here and
    # detect_residency() was a silent no-op. Residency is set by staff during
    # card-application review (or via the admin residency_override).

    # Send the plain token to user via email (they need this to verify)
    try:
        await send_verification_email(user.email, verification_token, user.first_name)
    except Exception as e:  # noqa: BLE001  # best-effort email — registration must not fail if email fails
        logger.warning(f"Failed to send verification email for user_id={user.id}: {e}")

    # Send welcome email
    try:
        from app.services.notifications.email_sender import EmailSenderService
        from app.services.notifications.types import NotificationType as NType
        email_service = EmailSenderService()
        await email_service.send_templated(
            notification_type=NType.WELCOME_EMAIL,
            recipient_email=user.email,
            context_data={
                "patron_name": user.first_name,
                "library_name": get_settings().library_name,
                "card_number": user.library_card or "",
            },
            user_id=user.id,
            db=db,
        )
    except Exception as e:  # noqa: BLE001  # best-effort welcome email — registration must not fail if email fails
        logger.warning(f"Failed to send welcome email for user_id={user.id}: {e}")

    return user


@router.post("/check-duplicate", response_model=MessageResponse)
# NOTE: No Turnstile gate. By design this is an existence-oracle for real-time
# duplicate detection during registration: adding a captcha raises the cost
# per probe but does not close the oracle, and fresh-token UX is non-trivial
# because the same page already mints a single-use Turnstile token for the
# actual /register submit and Cloudflare tokens are single-use server-side.
# Mitigation is aggressive rate-limiting + generic email-vs-phone error
# text. Real fix is product-level: move existence checks post-submit with
# uniform error handling. Documented in the rate-limiting tiered-policy
# audit (Stage 0 §11) maintained outside this repo.
@limiter.limit("5/minute")
async def check_duplicate(
    request: Request,
    db: AsyncSession = Depends(get_db),
    email: Optional[str] = None,
    phone: Optional[str] = None,
):
    """Check if a patron with the given email or phone already exists.

    Used for real-time duplicate detection during registration.
    Returns success message if no duplicate found, otherwise returns error.

    SECURITY: Rate-limited aggressively (5/min) to mitigate user enumeration.
    Uses generic error messages that don't distinguish email vs phone conflicts.
    """
    if not email and not phone:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please provide either an email address or phone number so we can set up your account.")

    # Check both fields independently (constant-time to prevent timing attacks)
    # Always execute both checks regardless of first result to avoid user enumeration
    email_exists = False
    phone_exists = False

    if email:
        result = await db.execute(select(User).where(User.email_hash == email_blind_hash(email)))
        if result.scalar_one_or_none():
            email_exists = True

    if phone:
        from app.core.encryption import hash_pii
        _stripped = re.sub(r"\D", "", phone)
        _phone_hash = hash_pii(_stripped, field="phone")
        result = await db.execute(select(User).where(User.phone_hash == _phone_hash))
        if result.scalar_one_or_none():
            phone_exists = True

    if email_exists or phone_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this information already exists. Try signing in instead.. Try signing in instead.")

    return MessageResponse(message="No duplicate found")


@router.get("/address-suggestions")
@limiter.limit("10/minute")
async def get_address_suggestions(
    request: Request,
    partial: str = "",
):
    """Get address suggestions based on partial input for autocomplete.

    Used during registration to help patrons quickly enter their address.

    Args:
        partial: Partial address string (minimum 3 characters)

    Returns:
        List of address suggestions
    """
    from ....services.patron_onboarding_service import get_address_suggestions

    if len(partial.strip()) < 3:
        return {"suggestions": []}

    try:
        suggestions = await get_address_suggestions(partial)
        return {"suggestions": suggestions}
    except Exception as e:  # noqa: BLE001  # best-effort address suggestion — return empty on failure
        logger.error(f"Failed to get address suggestions: {e}")
        return {"suggestions": []}


@router.post("/registration-preferences", response_model=MessageResponse)
@limiter.limit("10/minute")
async def save_registration_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    card_delivery: Optional[str] = None,
    auto_enroll_summer_reading: bool = True,
):
    """Save patron registration preferences like card delivery method.

    Called immediately after registration to save preferences.
    - card_delivery: 'print' (physical card) or 'text' (digital via SMS)
    - auto_enroll_summer_reading: auto-enroll in summer reading program if active
    """
    import json
    from ....services.card_delivery_service import process_card_delivery, CardDeliveryMethod
    from ....services.patron_onboarding_service import auto_enroll_summer_reading as enroll_summer_reading

    # Parse custom fields
    custom_fields = {}
    if current_user.custom_fields:
        try:
            custom_fields = json.loads(current_user.custom_fields)
        except (json.JSONDecodeError, TypeError):
            custom_fields = {}

    # Store registration preferences
    if card_delivery:
        custom_fields['card_delivery'] = card_delivery
        # Process card delivery
        try:
            delivery_method = CardDeliveryMethod(card_delivery.lower())
            delivery_result = await process_card_delivery(
                delivery_method=delivery_method,
                library_card_number=current_user.library_card or "",
                first_name=current_user.first_name,
                last_name=current_user.last_name,
                email=current_user.email,
                phone_number=current_user.phone,
            )
            custom_fields['card_delivery_result'] = delivery_result
        except Exception as e:  # noqa: BLE001  # best-effort card delivery — log and continue, prefs still saved
            logger.warning(f"Failed to process card delivery: {e}")

    # Auto-enroll in summer reading if requested
    if auto_enroll_summer_reading:
        try:
            await enroll_summer_reading(current_user.id, db)
        except Exception as e:  # noqa: BLE001  # best-effort summer reading enroll — log and continue, prefs still saved
            logger.warning(f"Failed to auto-enroll in summer reading: {e}")

    custom_fields['auto_enroll_summer_reading'] = auto_enroll_summer_reading
    custom_fields['registration_completed_at'] = datetime.now(timezone.utc).isoformat()

    current_user.custom_fields = json.dumps(custom_fields)
    await db.commit()

    return MessageResponse(message="Registration preferences saved successfully")
