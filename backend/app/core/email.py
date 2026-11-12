# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import base64
import contextlib
import time
from typing import Optional

import httpx

from .config import get_settings
from .frontend_routes import routes
from .branding import branding
from .logging import get_logger

settings = get_settings()
logger = get_logger(__name__)


# Per-worker pacing for Resend's published 5 req/s rate limit. A bursty
# fan-out (e.g. submit-for-approval notifying every director in one
# request handler) was tripping HTTP 429 even on a 2-call burst, with
# failures landing in failed_notification_records for retry; pacing
# avoids the round-trip into the retry queue. Cross-worker coordination
# is not handled here -- if N workers each fire a burst, aggregate can
# still exceed the cap. For library-scale traffic the in-worker pacing
# is sufficient; the retry queue covers the residual.
_resend_pace_lock = asyncio.Lock()
_resend_last_call_monotonic: float = 0.0


async def _resend_pace() -> None:
    interval = settings.resend_min_interval_s
    if interval <= 0:
        return
    global _resend_last_call_monotonic
    async with _resend_pace_lock:
        now = time.monotonic()
        gap = now - _resend_last_call_monotonic
        if gap < interval:
            await asyncio.sleep(interval - gap)
        _resend_last_call_monotonic = time.monotonic()

# Design system color constants
COLORS = {
    "heading": "#2C1810",
    "body": "#5C4F3D",
    "button": branding.primary_color,
    "button_hover": "#D68533",
    "border": "#F0EDE8",
    "divider": "#E5E0D8",
    "text_light": "#8B7B6A",
}

# CAN-SPAM 15 USC 7704(a)(5): commercial email must include sender's valid physical postal address.
# Resolve at call time so live branding changes take effect without a process restart.
def get_physical_address() -> dict[str, str]:
    return {
        "name": settings.library_name,
        "street": branding.address_line1,
        "city": branding.city,
        "state": branding.state,
        "zip": branding.zip_code,
        "country": branding.country,
    }


def get_can_spam_footer(
    unsubscribe_url: Optional[str] = None,
    preferences_url: Optional[str] = None,
    is_transactional: bool = False,
) -> str:
    address = get_physical_address()
    address_line = (
        f"{address['name']}<br>"
        f"{address['street']}<br>"
        f"{address['city']}, {address['state']} {address['zip']}<br>"
        f"{address['country']}"
    )

    unsubscribe_section = ""
    if not is_transactional and unsubscribe_url:
        unsubscribe_section = f"""
        <p style="margin: 10px 0;">
            <a href="{unsubscribe_url}" style="color: {COLORS['text_light']}; text-decoration: underline;">
                Unsubscribe from these emails
            </a>
        </p>
        """

    preferences_section = ""
    if preferences_url:
        preferences_section = f"""
        <p style="margin: 10px 0;">
            <a href="{preferences_url}" style="color: {COLORS['text_light']}; text-decoration: underline;">
                Manage your email preferences
            </a>
        </p>
        """

    transactional_note = ""
    if is_transactional:
        transactional_note = """
        <p style="margin: 10px 0; font-style: italic;">
            This is a transactional email related to your library account.
        </p>
        """

    return f"""
    <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid {COLORS['divider']};">
        <table width="100%" cellpadding="0" cellspacing="0" style="font-size: 12px; color: {COLORS['text_light']}; text-align: center;">
            <tr>
                <td>
                    <p style="margin: 0 0 10px 0;">
                        <strong>{settings.app_name}</strong>
                    </p>
                    <p style="margin: 0; line-height: 1.6;">
                        {address_line}
                    </p>
                    {transactional_note}
                    {unsubscribe_section}
                    {preferences_section}
                    <p style="margin: 15px 0 0 0; font-size: 11px;">
                        © {settings.app_name}. All rights reserved.
                    </p>
                </td>
            </tr>
        </table>
    </div>
    """


# RFC 2606 / RFC 6761 reserved domains that never resolve to a real mailbox.
# Seed/demo and test fixtures address these (e.g. *.invalid); handing them to
# the provider only produces hard bounces that erode sender reputation and trip
# volume alerts. The 2026-06-07 teacher reading-list fan-out sent ~450 calls to
# example.invalid in 60s, tripping Resend's volume alert -- guarding here stops
# any sender (every path funnels through send_email) from reaching the provider
# with a non-deliverable recipient.
_RESERVED_EMAIL_DOMAINS = frozenset({
    "example.com",
    "example.org",
    "example.net",
    "localhost",
})
_RESERVED_EMAIL_TLDS = (".invalid", ".test", ".example", ".localhost")


def _is_reserved_recipient(to_email: str) -> bool:
    addr = (to_email or "").strip().lower()
    if "@" not in addr:
        return False
    domain = addr.rsplit("@", 1)[1]
    return domain in _RESERVED_EMAIL_DOMAINS or domain.endswith(_RESERVED_EMAIL_TLDS)


async def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_data: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
    unsubscribe_url: Optional[str] = None,
    list_unsubscribe_header: Optional[str] = None,
    categories: Optional[list[str]] = None,
    patron_id: Optional[int] = None,
    notification_type: Optional[str] = None,
) -> bool:
    # Derive template name from subject for tracking
    _template = (categories[0] if categories else subject[:50]).lower().replace(" ", "_")

    # Never call the provider for reserved/non-deliverable recipients (seed,
    # demo, test fixtures). Skip silently and report success so callers neither
    # retry nor queue a DLQ row for an address that can never receive mail.
    if _is_reserved_recipient(to_email):
        logger.info(
            "Email skipped: non-deliverable reserved recipient domain",
            extra={"to_email": to_email, "subject": subject, "template": _template},
        )
        return True

    # --- Email safeguard checks (fail-open if Redis unavailable) ---
    try:
        from .email_safeguards import (
            check_daily_cap,
            check_dedup,
            increment_cap_skipped,
            increment_daily_count,
            mark_sent,
        )

        # Check daily send cap
        if not await check_daily_cap():
            logger.warning(
                "Email suppressed by daily cap",
                extra={"to_email": to_email, "subject": subject, "template": _template},
            )
            # Route to DLQ + counter so cap-hits are visible to admins.
            # NOTE: notification_retry_job does NOT replay content -- this provides
            # visibility and escalation tracking, but not auto-redelivery. The DLQ
            # row will progress to ABANDONED on retry. v2: content/template-param
            # registry for true replay.
            try:
                await increment_cap_skipped()
                from .notification_tracker import track_notification
                await track_notification(
                    channel="email",
                    template_name=_template,
                    recipient=to_email,
                    success=False,
                    error="daily cap reached",
                    error_type="daily_cap_exceeded",
                    subject=subject,
                )
            except Exception:  # noqa: BLE001  # tracking boundary — DLQ recording must never block email return path
                # Tracking must never block the caller's return path.
                logger.warning(
                    "Failed to record daily-cap suppression in DLQ",
                    extra={"to_email": to_email, "subject": subject},
                    exc_info=True,
                )
            return False

        # Check per-patron deduplication if patron context is available
        if patron_id is not None and notification_type is not None:
            if not await check_dedup(patron_id, notification_type):
                logger.info(
                    "Email suppressed by deduplication",
                    extra={
                        "to_email": to_email,
                        "subject": subject,
                        "patron_id": patron_id,
                        "notification_type": notification_type,
                    },
                )
                return True  # Return True so callers don't retry a deduped send
    except Exception:  # noqa: BLE001  # fail-open boundary — safeguards must not block email sending
        # Safeguards must never block email sending
        logger.warning(
            "Email safeguard checks failed, proceeding with send",
            extra={"to_email": to_email, "subject": subject},
        )

    _api_key = settings.resend_api_key

    if not _api_key:
        if settings.environment == "production":
            logger.error(
                "CRITICAL: No email provider configured in production",
                extra={"to_email": to_email, "subject": subject},
            )
            return False
        logger.info(
            "No email provider configured - email not sent",
            extra={"to_email": to_email, "subject": subject, "attachment": attachment_filename},
        )
        return True  # Return True in dev mode so flow continues

    try:
        # Build headers for CAN-SPAM compliance
        email_headers = {}
        if list_unsubscribe_header:
            email_headers["List-Unsubscribe"] = list_unsubscribe_header
            email_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        elif unsubscribe_url:
            email_headers["List-Unsubscribe"] = f"<{unsubscribe_url}>"
            email_headers["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

        # Build attachment list
        attachments = []
        if attachment_data and attachment_filename:
            encoded = base64.b64encode(attachment_data).decode()
            attachments.append({
                "content": encoded,
                "filename": attachment_filename,
                "content_type": "application/pdf",
            })

        # Resend API (https://resend.com/docs/api-reference/emails/send-email)
        payload = {
            "from": f"{settings.app_name} <{settings.from_email}>",
            "to": [to_email],
            "subject": subject,
            "html": html_content,
        }
        if email_headers:
            payload["headers"] = email_headers
        if attachments:
            payload["attachments"] = attachments
        if categories:
            payload["tags"] = [{"name": c, "value": "1"} for c in categories[:5]]

        api_url = "https://api.resend.com/emails"
        auth_header = f"Bearer {_api_key}"

        await _resend_pace()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_url,
                headers={
                    "Authorization": auth_header,
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            sent_ok = response.status_code in (200, 201, 202)

            # 2xx with an error body is a silent failure mode -- some
            # Resend variants embed a statusCode field in the response body.
            # Without this check, callers think transactional email was
            # delivered when it was not.
            if sent_ok:
                try:
                    body = response.json()
                except ValueError:  # json.JSONDecodeError subclasses ValueError
                    body = None
                if isinstance(body, dict):
                    if body.get('errors'):
                        sent_ok = False
                    elif isinstance(body.get('statusCode'), int) and body['statusCode'] >= 400:
                        sent_ok = False


            if not sent_ok:
                error_detail = ""
                # response.text may be missing or undecodable; log without it.
                with contextlib.suppress(AttributeError, UnicodeDecodeError):
                    error_detail = response.text[:500]
                logger.error(
                    "resend API error",
                    extra={
                        "to_email": to_email,
                        "subject": subject,
                        "status_code": response.status_code,
                        "error": error_detail,
                    },
                )

            if sent_ok:
                await _track_email(_template, to_email, success=True, subject=subject)
                try:
                    await increment_daily_count()
                    if patron_id is not None and notification_type is not None:
                        await mark_sent(patron_id, notification_type)
                except Exception:  # noqa: BLE001  # tracking boundary — post-send safeguard updates must not affect return
                    logger.warning(
                        "Email safeguard post-send tracking failed",
                        extra={"to_email": to_email, "subject": subject},
                    )
            else:
                await _track_email(
                    _template, to_email, success=False, subject=subject,
                    error=f"resend returned {response.status_code}",
                    error_type="api_error", http_status_code=response.status_code,
                )

            return sent_ok
    except httpx.TimeoutException:
        logger.warning(
            "Email send timeout",
            extra={"to_email": to_email, "subject": subject},
        )
        await _track_email(
            _template, to_email, success=False, subject=subject,
            error="resend request timeout", error_type="timeout",
        )
        return False
    except httpx.RequestError as e:
        logger.error(
            "Email request error",
            extra={"to_email": to_email, "subject": subject, "error": str(e)},
        )
        await _track_email(
            _template, to_email, success=False, subject=subject,
            error=str(e), error_type="request_error",
        )
        return False
    except (ValueError, KeyError, TypeError, AttributeError) as e:
        # Catch data validation and encoding errors
        logger.error(
            "Failed to send email",
            extra={
                "to_email": to_email,
                "subject": subject,
                "error": str(e),
                "error_type": type(e).__name__,
            },
            exc_info=True,
        )
        await _track_email(
            _template, to_email, success=False, subject=subject,
            error=str(e), error_type=type(e).__name__,
        )
        return False


async def _track_email(template: str, recipient: str, *, success: bool, subject: str = "", **kwargs) -> None:
    try:
        from .notification_tracker import track_notification
        await track_notification("email", template, recipient, success=success, subject=subject, **kwargs)
    except Exception:  # noqa: BLE001  # tracking boundary — must never break email sending
        pass  # Tracking must never break email sending


async def send_password_reset_email(
    to_email: str, reset_token: str, first_name: str
) -> bool:
    reset_url = f"{routes.url(settings.frontend_url, routes.reset_password)}?token={reset_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Password Reset Request</h2>
        <p>Hi {first_name},</p>
        <p>We received a request to reset your password for your {settings.app_name} account.</p>
        <p>Click the button below to reset your password:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" 
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Reset Password
            </a>
        </p>
        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            This link will expire in 1 hour. If you didn't request this reset, 
            you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">{settings.app_name}</p>
    </div>
    """

    return await send_email(to_email, "Reset Your Password", html)


async def send_verification_email(
    to_email: str, verification_token: str, first_name: str
) -> bool:
    verify_url = f"{routes.url(settings.frontend_url, routes.verify_email)}?token={verification_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Verify Your Email</h2>
        <p>Hi {first_name},</p>
        <p>Welcome to {settings.app_name}! Please verify your email address to complete your registration.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" 
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Verify Email
            </a>
        </p>
        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            If you didn't create an account with us, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">{settings.app_name}</p>
    </div>
    """

    return await send_email(to_email, "Verify Your Email Address", html)


async def send_magic_link_email(
    to_email: str, magic_link_token: str, first_name: str
) -> bool:
    magic_link_url = f"{routes.url(settings.frontend_url, routes.auth_magic_link)}?token={magic_link_token}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Sign In to Your Account</h2>
        <p>Hi {first_name},</p>
        <p>You requested a magic link to sign in to your {settings.app_name} account.
           Click the button below to sign in — no password needed.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{magic_link_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Sign In
            </a>
        </p>
        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            This link will expire in 15 minutes and can only be used once.
            If you didn't request this, you can safely ignore this email.
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">{settings.app_name}</p>
    </div>
    """

    return await send_email(to_email, "Your Sign-In Link", html)


async def send_hold_ready_notification(
    to_email: str,
    first_name: str,
    book_title: str,
    book_author: str | None,
    pickup_location: str | None,
    expires_at: str,
) -> bool:
    holds_url = routes.url(settings.frontend_url, routes.account_holds)
    author_line = f"<p style=\"color: {COLORS['text_light']}; margin: 5px 0;\">by {book_author}</p>" if book_author else ""
    location_section = f"""
        <tr>
            <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Pickup Location:</td>
            <td style="padding: 10px 0; color: {COLORS['body']};">{pickup_location}</td>
        </tr>""" if pickup_location else ""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Your Hold is Ready!</h2>
        <p>Hi {first_name},</p>
        <p>Great news! The item you placed on hold is now available for pickup.</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{book_title}</h3>
            {author_line}

            <table style="width: 100%; margin-top: 15px;">
                {location_section}
                <tr>
                    <td style="padding: 10px 0; font-weight: bold; color: {COLORS['heading']};">Pickup By:</td>
                    <td style="padding: 10px 0; color: #C0392B; font-weight: bold;">{expires_at}</td>
                </tr>
            </table>
        </div>

        <p style="color: {COLORS['body']};">
            Please pick up your item by the date shown above. After this date,
            the hold will expire and the item will be made available to the next patron in line.
        </p>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{holds_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Holds
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    return await send_email(to_email, f"Your Hold is Ready: {book_title}", html)


async def send_hold_bumped_to_front_notification(
    to_email: str,
    first_name: str,
    book_title: str,
    book_author: str | None,
) -> bool:
    holds_url = routes.url(settings.frontend_url, routes.account_holds)
    author_line = (
        f"<p style=\"color: {COLORS['text_light']}; margin: 5px 0;\">by {book_author}</p>"
        if book_author else ""
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">You're still next in line</h2>
        <p>Hi {first_name},</p>
        <p>The copy of the item below that you were waiting for was checked out
           in person at the library. You haven't lost your place &mdash; you are
           still next in line, and we'll email you again as soon as it's returned.</p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{book_title}</h3>
            {author_line}
        </div>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{holds_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Holds
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(to_email, f"You're still next in line: {book_title}", html)


async def send_hold_released_notification(
    to_email: str,
    first_name: str,
    book_title: str,
    book_author: str | None,
) -> bool:
    catalog_url = routes.url(settings.frontend_url, routes.catalog)
    author_line = (
        f"<p style=\"color: {COLORS['text_light']}; margin: 5px 0;\">by {book_author}</p>"
        if book_author else ""
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Your hold was released</h2>
        <p>Hi {first_name},</p>
        <p>The item below was checked out in person at the library, and your hold
           on it has been released. If you'd still like to read it, you're welcome
           to place a new hold any time.</p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{book_title}</h3>
            {author_line}
        </div>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{catalog_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Browse the Catalog
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(to_email, f"Your hold was released: {book_title}", html)


# ============================================================================
# Card Application Notifications
# ============================================================================

CARD_APPLICATION_REVIEW_DAYS = 3


async def send_card_application_received(
    to_email: str,
    first_name: str,
    check_token: str | None = None,
) -> bool:
    status_block = ""
    if check_token:
        check_url = routes.url(
            settings.frontend_url,
            routes.card_application_status,
            token=check_token,
        )
        status_block = f"""
        <p style="color: {COLORS['body']};">
            Want to check on your application later?
            <a href="{check_url}" style="color: {COLORS['heading']};">
                Check the status of your application
            </a>.
        </p>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">We Received Your Library Card Application</h2>
        <p>Hi {first_name},</p>
        <p>
            Thanks for applying for a library card with {settings.app_name}.
            Your application has been received and is in our review queue.
        </p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">What happens next?</h3>
            <p style="color: {COLORS['body']}; margin: 0;">
                A staff member will review your application within
                <strong>{CARD_APPLICATION_REVIEW_DAYS} business days</strong>.
                You'll get another email from us as soon as a decision is made.
            </p>
        </div>

        {status_block}

        <p style="color: {COLORS['body']};">
            If you have questions in the meantime, just reply to this email or
            stop by the library and ask for help at the front desk.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    return await send_email(
        to_email,
        "We received your library card application",
        html,
        categories=["card_application_received"],
        notification_type="card_application_received",
    )


async def send_card_application_approved(
    to_email: str,
    first_name: str,
    card_number: str,
    pickup_location: str | None,
) -> bool:
    if pickup_location:
        pickup_block = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Pick up your physical card</h3>
            <p style="color: {COLORS['body']}; margin: 0;">
                Stop by <strong>{pickup_location}</strong> with a photo ID to
                collect your physical library card. Until then, you can use the
                card number above to sign in online and place holds.
            </p>
        </div>
        """
    else:
        pickup_block = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">You're all set</h3>
            <p style="color: {COLORS['body']}; margin: 0;">
                Your card is digital-only — you can use the number above to
                sign in online and start placing holds right away. If you'd
                like a physical card later, just ask at any branch.
            </p>
        </div>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Welcome to {settings.app_name}!</h2>
        <p>Hi {first_name},</p>
        <p>
            Good news — your library card application has been
            <strong>approved</strong>. Your new card number is:
        </p>

        <p style="text-align: center; font-size: 22px; font-weight: bold;
                  color: {COLORS['heading']}; letter-spacing: 2px;
                  background-color: #F0EDE8; padding: 18px; border-radius: 6px;">
            {card_number}
        </p>

        {pickup_block}

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    return await send_email(
        to_email,
        "Your library card application was approved",
        html,
        categories=["card_application_approved"],
        notification_type="card_application_approved",
    )


async def send_card_application_denied(
    to_email: str,
    first_name: str,
    denial_reason: str | None,
) -> bool:
    if denial_reason:
        reason_block = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px;
                    margin: 20px 0; border-left: 4px solid {COLORS['button']};">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Reason</h3>
            <p style="color: {COLORS['body']}; margin: 0;">{denial_reason}</p>
        </div>
        """
    else:
        reason_block = f"""
        <p style="color: {COLORS['body']};">
            Please contact staff for more details about this decision.
        </p>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">An update on your library card application</h2>
        <p>Hi {first_name},</p>
        <p>
            We weren't able to approve your library card application at this time.
        </p>

        {reason_block}

        <p style="color: {COLORS['body']};">
            If your situation changes or you have questions, please reach out
            to library staff — we're happy to help you figure out next steps.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """

    return await send_email(
        to_email,
        "Update on your library card application",
        html,
        categories=["card_application_denied"],
        notification_type="card_application_denied",
    )


async def send_deletion_request_email(
    to_email: str,
    first_name: str,
    deletion_date: str,
    cancel_url: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Account Deletion Request Received</h2>
        <p>Hi {first_name},</p>
        <p>We've received your request to delete your {settings.app_name} account.</p>

        <div style="background-color: #FFF3CD; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC107;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Important Information</h3>
            <p style="margin-bottom: 10px;"><strong>Your account will be permanently deleted on:</strong></p>
            <p style="font-size: 18px; color: #C0392B; font-weight: bold;">{deletion_date}</p>
        </div>

        <h3 style="color: {COLORS['heading']};">What happens next?</h3>
        <ul style="color: {COLORS['body']}; line-height: 1.8;">
            <li>You have <strong>30 days</strong> to cancel this request</li>
            <li>You can still log in and use your account during this period</li>
            <li>We recommend downloading your data before deletion</li>
            <li>After deletion, you cannot recover your account</li>
        </ul>

        <h3 style="color: {COLORS['heading']};">What will be deleted?</h3>
        <ul style="color: {COLORS['body']}; line-height: 1.8;">
            <li>Personal information (name, email, phone, address)</li>
            <li>Reading history and preferences</li>
            <li>Holds history and favorites</li>
            <li>Reading lists and achievements</li>
        </ul>

        <h3 style="color: {COLORS['heading']};">What will be retained (anonymized)?</h3>
        <ul style="color: {COLORS['body']}; line-height: 1.8;">
            <li>Anonymized circulation statistics (for library analytics)</li>
            <li>Financial records (legal requirement)</li>
        </ul>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{cancel_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Cancel Deletion Request
            </a>
        </p>

        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            Changed your mind? Click the button above or log into your account to cancel this request.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            If you did not request this deletion, please contact us immediately at (613) 555-1234.
        </p>
    </div>
    """

    return await send_email(to_email, "Account Deletion Request Confirmation", html)


async def send_deletion_cancelled_email(
    to_email: str,
    first_name: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Account Deletion Cancelled</h2>
        <p>Hi {first_name},</p>
        <p>Good news! Your account deletion request has been cancelled.</p>

        <div style="background-color: #D4EDDA; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28A745;">
            <p style="color: #155724; margin: 0;">
                <strong>Your {settings.app_name} account is safe and will remain active.</strong>
            </p>
        </div>

        <p style="color: {COLORS['body']};">
            All your data, reading history, and preferences have been preserved.
            You can continue using your account as normal.
        </p>

        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            If you didn't cancel this request, or if you have any concerns,
            please contact us at (613) 555-1234.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">{settings.app_name}</p>
    </div>
    """

    return await send_email(to_email, "Account Deletion Cancelled", html)


async def send_deletion_complete_email(
    to_email: str,
    first_name: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Account Deletion Complete</h2>
        <p>Hi {first_name},</p>
        <p>As requested, your {settings.app_name} account has been permanently deleted.</p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">What has been removed:</h3>
            <ul style="color: {COLORS['body']}; line-height: 1.8;">
                <li>Your personal information (name, email, phone, address)</li>
                <li>Reading history and preferences</li>
                <li>Holds history and favorites</li>
                <li>Reading lists and achievements</li>
                <li>All login credentials and sessions</li>
            </ul>
        </div>

        <p style="color: {COLORS['body']};">
            For fraud prevention, this email address cannot be used to create a new account
            for <strong>90 days</strong>.
        </p>

        <p style="color: {COLORS['body']};">
            We're sorry to see you go. If you'd like to use {settings.app_name} again
            in the future, you're welcome to create a new account after the waiting period.
        </p>

        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            Thank you for being a part of our library community.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is a final confirmation. You do not need to take any action.
        </p>
    </div>
    """

    return await send_email(to_email, "Your Account Has Been Deleted", html)


async def send_staff_deletion_notification_email(
    to_email: str,
    first_name: str,
    staff_name: str,
    deletion_date: str,
    reason: str | None = None,
) -> bool:
    reason_section = ""
    if reason:
        reason_section = f"""
        <p style="color: {COLORS['body']};"><strong>Reason provided:</strong> {reason}</p>
        """

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Account Deletion Request Processed</h2>
        <p>Hi {first_name},</p>
        <p>Per your request, a staff member has initiated the deletion of your {settings.app_name} account.</p>

        <div style="background-color: #FFF3CD; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #FFC107;">
            <p style="margin-bottom: 10px;"><strong>Processed by:</strong> {staff_name}</p>
            <p style="margin-bottom: 10px;"><strong>Account deletion scheduled for:</strong></p>
            <p style="font-size: 18px; color: #C0392B; font-weight: bold;">{deletion_date}</p>
            {reason_section}
        </div>

        <h3 style="color: {COLORS['heading']};">Important Information</h3>
        <ul style="color: {COLORS['body']}; line-height: 1.8;">
            <li>You have <strong>30 days</strong> to cancel this request</li>
            <li>Contact the library at (613) 555-1234 to cancel</li>
            <li>We recommend downloading your data before deletion</li>
        </ul>

        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            If you did not request this deletion, please contact the library immediately.
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">{settings.app_name}</p>
    </div>
    """

    return await send_email(to_email, "Account Deletion Request Processed", html)

# Marketing Email Functions (Newsletter, Alerts, Double Opt-In)
# =============================================================================


async def send_newsletter_double_optin_email(
    to_email: str,
    first_name: str,
    confirmation_token: str,
) -> bool:
    confirm_url = f"{routes.url(settings.frontend_url, routes.newsletter_confirm)}?token={confirmation_token}"
    name = first_name if first_name else "there"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Confirm Your Newsletter Subscription</h2>
        <p>Hi {name},</p>
        <p>Thank you for signing up for the {settings.app_name} newsletter!</p>
        <p>Please confirm your subscription by clicking the button below:</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{confirm_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Confirm Subscription
            </a>
        </p>
        <p style="color: {COLORS['text_light']}; font-size: 14px;">
            If you didn't sign up for our newsletter, you can safely ignore this email.
            This link will expire in 7 days.
        </p>
        {get_can_spam_footer(is_transactional=True)}
    </div>
    """

    return await send_email(
        to_email,
        "Confirm Your Newsletter Subscription",
        html,
        categories=["newsletter", "double-optin"],
    )


async def send_newsletter_welcome_email(
    to_email: str,
    first_name: str,
    unsubscribe_url: str,
    preferences_url: str,
) -> bool:
    name = first_name if first_name else "there"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Welcome to Our Newsletter!</h2>
        <p>Hi {name},</p>
        <p>Thank you for confirming your subscription to the {settings.app_name} newsletter!</p>

        <div style="background-color: #D4EDDA; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28A745;">
            <p style="color: #155724; margin: 0;">
                <strong>You're all set!</strong> You'll now receive our updates about:
            </p>
            <ul style="color: #155724; margin: 10px 0 0 0; padding-left: 20px;">
                <li>New book arrivals and featured collections</li>
                <li>Library events and programs</li>
                <li>Reading recommendations</li>
                <li>Community news and updates</li>
            </ul>
        </div>

        <p style="color: {COLORS['body']};">
            You can <a href="{preferences_url}" style="color: {COLORS['button']};">manage your interests</a>
            to receive more personalized content.
        </p>

        {get_can_spam_footer(unsubscribe_url=unsubscribe_url, preferences_url=preferences_url)}
    </div>
    """

    return await send_email(
        to_email,
        f"Welcome to the {settings.app_name} Newsletter!",
        html,
        unsubscribe_url=unsubscribe_url,
        categories=["newsletter", "welcome"],
    )


async def send_new_arrival_alert_email(
    to_email: str,
    first_name: str,
    category_name: str,
    items: list[dict],
    unsubscribe_url: str,
    preferences_url: str,
) -> bool:
    name = first_name if first_name else "there"

    # Build items HTML
    items_html = ""
    for item in items[:10]:  # Limit to 10 items
        cover_html = ""
        if item.get("cover_url"):
            cover_html = f'''
            <td style="width: 80px; vertical-align: top; padding-right: 15px;">
                <img src="{item['cover_url']}" alt="" style="width: 70px; border-radius: 4px;">
            </td>
            '''

        items_html += f"""
        <tr>
            <td style="padding: 15px 0; border-bottom: 1px solid {COLORS['divider']};">
                <table cellpadding="0" cellspacing="0" width="100%">
                    <tr>
                        {cover_html}
                        <td style="vertical-align: top;">
                            <a href="{item.get('catalog_url', '#')}"
                               style="color: {COLORS['heading']}; font-weight: bold; text-decoration: none; font-size: 16px;">
                                {item.get('title', 'Unknown Title')}
                            </a>
                            <p style="color: {COLORS['text_light']}; margin: 5px 0 0 0; font-size: 14px;">
                                by {item.get('author', 'Unknown Author')}
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
        """

    catalog_url = f"{routes.url(settings.frontend_url, routes.catalog)}?category={category_name.lower().replace(' ', '-')}"

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">New Arrivals in {category_name}</h2>
        <p>Hi {name},</p>
        <p>We've just added new items to our <strong>{category_name}</strong> collection that you might enjoy!</p>

        <table cellpadding="0" cellspacing="0" width="100%" style="margin: 20px 0;">
            {items_html}
        </table>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{catalog_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View All New {category_name}
            </a>
        </p>

        {get_can_spam_footer(unsubscribe_url=unsubscribe_url, preferences_url=preferences_url)}
    </div>
    """

    return await send_email(
        to_email,
        f"New Arrivals: {category_name}",
        html,
        unsubscribe_url=unsubscribe_url,
        categories=["new-arrivals", category_name.lower().replace(" ", "-")],
    )


async def send_newsletter_email(
    to_email: str,
    first_name: str,
    subject: str,
    preview_text: str,
    html_content: str,
    unsubscribe_url: str,
    preferences_url: str,
    campaign_name: Optional[str] = None,
) -> bool:
    name = first_name if first_name else "Valued Patron"

    # Add preview text and personal greeting
    full_html = f"""
    <div style="display: none; max-height: 0; overflow: hidden; font-size: 1px; line-height: 1px; color: #ffffff;">
        {preview_text}
    </div>
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <p style="color: {COLORS['body']};">Hi {name},</p>
        {html_content}
        {get_can_spam_footer(unsubscribe_url=unsubscribe_url, preferences_url=preferences_url)}
    </div>
    """

    categories = ["newsletter"]
    if campaign_name:
        categories.append(campaign_name)

    return await send_email(
        to_email,
        subject,
        full_html,
        unsubscribe_url=unsubscribe_url,
        categories=categories,
    )


async def send_interest_confirmation_email(
    to_email: str,
    first_name: str,
    interests: list[str],
    unsubscribe_url: str,
    preferences_url: str,
) -> bool:
    name = first_name if first_name else "there"

    interests_html = "".join(f"<li>{interest}</li>" for interest in interests)

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Your Interests Have Been Updated</h2>
        <p>Hi {name},</p>
        <p>We've updated your newsletter preferences. You'll now receive updates about:</p>

        <div style="background-color: {COLORS['border']}; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <ul style="color: {COLORS['body']}; margin: 0; padding-left: 20px; line-height: 1.8;">
                {interests_html}
            </ul>
        </div>

        <p style="color: {COLORS['body']};">
            Want to add more interests or change your preferences?
            <a href="{preferences_url}" style="color: {COLORS['button']};">Update your settings</a>
        </p>

        {get_can_spam_footer(unsubscribe_url=unsubscribe_url, preferences_url=preferences_url)}
    </div>
    """

    return await send_email(
        to_email,
        "Your Newsletter Preferences Have Been Updated",
        html,
        unsubscribe_url=unsubscribe_url,
        categories=["newsletter", "preferences-updated"],
    )


async def verify_delivery(message_id: str) -> bool | None:
    logger.debug("Delivery verification requested for message_id=%s", message_id)
    return None  # Unknown until event webhook data is stored


def handle_bounce(email: str, reason: str) -> None:
    logger.warning(
        "Email bounce recorded",
        extra={"email": email, "reason": reason},
    )


# --- Security Alert Emails ---


async def send_security_alert_new_login(
    to_email: str,
    first_name: str,
    device: str,
    ip_address: str,
    timestamp: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">New sign-in to your account</h2>
        <p style="color: {COLORS['body']};">Hi {first_name},</p>
        <p style="color: {COLORS['body']};">We noticed a new sign-in to your library account:</p>
        <div style="background-color: {COLORS['border']}; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>Device:</strong> {device}</p>
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>IP Address:</strong> {ip_address}</p>
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>Time:</strong> {timestamp}</p>
        </div>
        <p style="color: {COLORS['body']};">If this was you, no action is needed.</p>
        <p style="color: {COLORS['body']};"><strong>If this wasn't you</strong>, change your password immediately and review your active sessions in Account &gt; Security.</p>
    </div>
    """
    return await send_email(to_email, "New sign-in to your library account", html)


async def send_security_alert_failed_attempts(
    to_email: str,
    first_name: str,
    attempt_count: int,
    ip_address: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Failed sign-in attempts on your account</h2>
        <p style="color: {COLORS['body']};">Hi {first_name},</p>
        <p style="color: {COLORS['body']};">We detected {attempt_count} failed sign-in attempts on your account from IP address {ip_address}.</p>
        <p style="color: {COLORS['body']};">If this was you, you can reset your password. If not, your account is safe — the attempts did not succeed.</p>
        <p style="color: {COLORS['body']};">You can review your security settings in Account &gt; Security.</p>
    </div>
    """
    return await send_email(to_email, "Failed sign-in attempts on your account", html)


async def send_security_alert_change(
    to_email: str,
    first_name: str,
    change_type: str,
    device: str,
    ip_address: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Security change on your account</h2>
        <p style="color: {COLORS['body']};">Hi {first_name},</p>
        <p style="color: {COLORS['body']};">A security change was made to your library account:</p>
        <div style="background-color: {COLORS['border']}; padding: 16px; border-radius: 8px; margin: 16px 0;">
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>Change:</strong> {change_type}</p>
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>Device:</strong> {device}</p>
            <p style="margin: 4px 0; color: {COLORS['body']};"><strong>IP Address:</strong> {ip_address}</p>
        </div>
        <p style="color: {COLORS['body']};">If you made this change, no action is needed.</p>
        <p style="color: {COLORS['body']};"><strong>If you didn't make this change</strong>, contact library staff immediately.</p>
    </div>
    """
    return await send_email(to_email, f"Security change: {change_type}", html)


async def send_recovery_email_verification(
    to_email: str,
    first_name: str,
    verification_url: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Verify your recovery email</h2>
        <p style="color: {COLORS['body']};">Hi {first_name},</p>
        <p style="color: {COLORS['body']};">You added this email as a recovery email for your library account. Please verify it:</p>
        <p style="margin: 24px 0; text-align: center;">
            <a href="{verification_url}" style="background: {COLORS['button']}; color: white; padding: 12px 24px; border-radius: 8px; text-decoration: none; font-weight: bold;">Verify Recovery Email</a>
        </p>
        <p style="color: {COLORS['text_light']};">This link expires in 24 hours.</p>
        <p style="color: {COLORS['text_light']};">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    return await send_email(to_email, "Verify your recovery email", html)


# ============================================================================
# Book Club Waitlist Notifications
# ============================================================================
# Two transactional sends for the waitlist feature. Tag names
# (categories) MUST stay unique vs every other send in this module —
# Resend 422s on a duplicate tag name within a batch, and the
# uniqueness convention is enforced project-wide
# (feedback_resend_tag_name_uniqueness). Callers ALWAYS log
# "EMAIL_SEND <tag> user=X club=Y" BEFORE invoking these because the
# daily-cap safeguard silently drops sends and still returns truthy
# (feedback_l30_email_safeguard_cap_masks_failure).


def _book_club_url(club_id: int) -> str:
    settings = get_settings()
    base = (settings.frontend_url or "").rstrip("/")
    return f"{base}/book-clubs/{club_id}"


async def send_waitlist_promotion_email(user, club) -> bool:
    first_name = getattr(user, "first_name", None) or "there"
    club_url = _book_club_url(club.id)
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">You're In! A Spot Opened Up</h2>
        <p>Hi {first_name},</p>
        <p>
            Good news — a spot opened up in
            <strong>{club.name}</strong> and you've been moved off the
            waitlist into the group. You're now a member.
        </p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">{club.name}</h3>
            <p style="color: {COLORS['body']}; margin: 0;">
                Head to the club page to see upcoming meetings and what
                the group is reading next.
            </p>
        </div>

        <p style="text-align: center; margin: 30px 0;">
            <a href="{club_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View the Book Club
            </a>
        </p>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {get_settings().app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        user.email,
        f"You're now in the {club.name} book club",
        html,
        categories=["book_club_waitlist_promoted"],
        notification_type="book_club_waitlist_promoted",
    )


async def send_waitlist_archived_notice_email(user, club) -> bool:
    first_name = getattr(user, "first_name", None) or "there"
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Update on a Book Club Waitlist</h2>
        <p>Hi {first_name},</p>
        <p>
            We wanted to let you know that the
            <strong>{club.name}</strong> book club is no longer running,
            so the waitlist you were on has been cleared. You don't need
            to do anything.
        </p>

        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: {COLORS['body']}; margin: 0;">
                There are other book clubs you can join — browse them
                anytime from your account, and feel free to ask staff
                for a recommendation.
            </p>
        </div>

        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {get_settings().app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        user.email,
        f"The {club.name} book club waitlist has been cleared",
        html,
        categories=["book_club_waitlist_archived_notice"],
        notification_type="book_club_waitlist_archived_notice",
    )


# ============================================================================
# Parent Connection Group Lifecycle Notifications (cg_lifecycle_001)
# ============================================================================
# Three transactional sends covering admin lifecycle actions on connection
# groups. Each has its own Resend tag name — Resend 422s on duplicates
# (feedback_resend_tag_name_uniqueness). Send ONE per patron; cap-safeguard
# may drop sends mid-batch, so callers ALWAYS log
# "EMAIL_SEND <tag> user=X group=Y" BEFORE invoking these
# (feedback_l30_email_safeguard_cap_masks_failure).


def _connection_group_url(group_id: int) -> str:
    s = get_settings()
    base = (s.frontend_url or "").rstrip("/")
    return f"{base}/parent-onboarding/connection-groups/{group_id}"


def _format_date_friendly(d) -> str:
    try:
        return d.strftime("%a, %b %-d, %Y")
    except (AttributeError, ValueError, TypeError):
        return str(d)


def _format_time_friendly(t: str | None) -> str:
    if not t:
        return ""
    try:
        hh, mm = t.split(":")
        h = int(hh)
        suffix = "AM" if h < 12 else "PM"
        h12 = h % 12 or 12
        return f"{h12}:{mm} {suffix}"
    except (ValueError, AttributeError):
        return t


async def send_connection_group_meeting_cancelled_email(
    user, group, meeting, patron_message: str | None = None,
) -> bool:
    first_name = getattr(user, "first_name", None) or "there"
    group_url = _connection_group_url(group.id)
    when = _format_date_friendly(meeting.meeting_date)
    when_time = _format_time_friendly(meeting.scheduled_time)
    when_full = f"{when} at {when_time}" if when_time else when

    optional_message = ""
    if patron_message:
        # Trust patron_message text but escape angle brackets defensively.
        safe = (patron_message
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
        optional_message = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: {COLORS['body']}; margin: 0; white-space: pre-wrap;">{safe}</p>
        </div>"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">A meeting has been cancelled</h2>
        <p>Hi {first_name},</p>
        <p>
            The <strong>{group.name}</strong> meeting on
            <strong>{when_full}</strong> has been cancelled.
        </p>
        {optional_message}
        <p>
            The rest of the group's schedule is unaffected. You can see
            upcoming meetings on the group page.
        </p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{group_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View {group.name}
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {get_settings().app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        user.email,
        f"{group.name}: meeting on {when} cancelled",
        html,
        categories=["connection_group_meeting_cancelled"],
        notification_type="connection_group_meeting_cancelled",
    )


async def send_connection_group_meeting_rescheduled_email(
    user, group, old_meeting, new_meeting, patron_message: str | None = None,
) -> bool:
    first_name = getattr(user, "first_name", None) or "there"
    group_url = _connection_group_url(group.id)
    old_when = _format_date_friendly(old_meeting.meeting_date)
    new_when = _format_date_friendly(new_meeting.meeting_date)
    new_time = _format_time_friendly(new_meeting.scheduled_time)
    new_full = f"{new_when} at {new_time}" if new_time else new_when

    optional_message = ""
    if patron_message:
        safe = (patron_message
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
        optional_message = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: {COLORS['body']}; margin: 0; white-space: pre-wrap;">{safe}</p>
        </div>"""

    location_line = ""
    if new_meeting.location and new_meeting.location != old_meeting.location:
        location_line = (
            f"<p>The new location is "
            f"<strong>{new_meeting.location}</strong>.</p>"
        )

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">A meeting has been rescheduled</h2>
        <p>Hi {first_name},</p>
        <p>
            The <strong>{group.name}</strong> meeting originally on
            <strong>{old_when}</strong> has been moved to
            <strong>{new_full}</strong>.
        </p>
        {location_line}
        {optional_message}
        <p style="text-align: center; margin: 30px 0;">
            <a href="{group_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View {group.name}
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {get_settings().app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        user.email,
        f"{group.name}: meeting moved to {new_when}",
        html,
        categories=["connection_group_meeting_rescheduled"],
        notification_type="connection_group_meeting_rescheduled",
    )


async def send_connection_group_archived_email(
    user, group, patron_message: str | None = None,
) -> bool:
    first_name = getattr(user, "first_name", None) or "there"

    optional_message = ""
    if patron_message:
        safe = (patron_message
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
        optional_message = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: {COLORS['body']}; margin: 0; white-space: pre-wrap;">{safe}</p>
        </div>"""

    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Thank you for being part of {group.name}</h2>
        <p>Hi {first_name},</p>
        <p>
            The <strong>{group.name}</strong> group has wrapped up. We
            wanted to let you know directly rather than have the page
            quietly disappear from your list.
        </p>
        {optional_message}
        <p>
            There are other groups and programs you can join — feel free
            to browse them from your account, or ask a librarian for a
            recommendation.
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {get_settings().app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        user.email,
        f"{group.name} has wrapped up",
        html,
        categories=["connection_group_archived"],
        notification_type="connection_group_archived",
    )


async def send_teacher_application_received(
    to_email: str,
    first_name: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">We received your teacher application</h2>
        <p>Hi {first_name},</p>
        <p>
            Thanks for applying for a teacher account with {settings.app_name}.
            A librarian will review your application and follow up by email.
        </p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">What happens next?</h3>
            <p style="color: {COLORS['body']}; margin: 0;">
                A staff member will review your application and let you know
                the decision by email. You can also stop by the library and
                ask for help at the front desk if you have questions.
            </p>
        </div>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        to_email,
        "We received your teacher application",
        html,
        categories=["teacher_application_received"],
        notification_type="teacher_application_received",
    )


async def send_teacher_application_approved(
    to_email: str,
    first_name: str,
    school_name: str,
) -> bool:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Welcome, teacher!</h2>
        <p>Hi {first_name},</p>
        <p>
            Good news -- your teacher application has been <strong>approved</strong>.
            Your account is now linked to <strong>{school_name}</strong> and you
            have access to teacher-only features at {settings.app_name}.
        </p>
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <p style="color: {COLORS['body']}; margin: 0;">
                Sign in to your account to start using teacher tools. If something
                doesn't look right, reply to this email or visit the library.
            </p>
        </div>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        to_email,
        "Your teacher application was approved",
        html,
        categories=["teacher_application_approved"],
        notification_type="teacher_application_approved",
    )


async def send_teacher_application_denied(
    to_email: str,
    first_name: str,
    denial_reason: str,
) -> bool:
    reason_block = ""
    if denial_reason:
        reason_block = f"""
        <div style="background-color: #F0EDE8; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: {COLORS['heading']}; margin-top: 0;">Reason</h3>
            <p style="color: {COLORS['body']}; margin: 0; white-space: pre-wrap;">{denial_reason}</p>
        </div>
        """
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Update on your teacher application</h2>
        <p>Hi {first_name},</p>
        <p>
            Thanks for applying for a teacher account with {settings.app_name}.
            Unfortunately, we were not able to approve your application at this time.
        </p>
        {reason_block}
        <p style="color: {COLORS['body']};">
            If you think this was a mistake or circumstances have changed,
            please reply to this email or stop by the library.
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name}<br>
            This is an automated notification. Please do not reply to this email.
        </p>
    </div>
    """
    return await send_email(
        to_email,
        "Update on your teacher application",
        html,
        categories=["teacher_application_denied"],
        notification_type="teacher_application_denied",
    )
