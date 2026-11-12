# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import hashlib
import re
import secrets
from datetime import datetime, time, timedelta
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .config import get_settings
from .branding import branding
from .logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

# SMS segment constants
GSM_CHARS_PER_SEGMENT = 160
GSM_CHARS_PER_CONCAT_SEGMENT = 153  # With UDH header
UNICODE_CHARS_PER_SEGMENT = 70
UNICODE_CHARS_PER_CONCAT_SEGMENT = 67

# GSM 7-bit default alphabet characters
GSM_BASIC_CHARS = set(
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ ÆæßÉ"
    "!\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "ÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyz"
    "äöñüà"
)

# Extended GSM characters (count as 2 characters)
GSM_EXTENDED_CHARS = set("^{}\\[~]|€")

# Verification-code policy (no Settings fields exist for these; see test_sms_seam.py)
SMS_VERIFICATION_CODE_LENGTH = 6
SMS_VERIFICATION_EXPIRY_MINUTES = 10

# Message-length policy
SMS_MAX_SEGMENTS = 3  # truncate_message default; messages longer than this are trimmed before queuing


class SMSError(Exception):
    pass


class SMSConfigurationError(SMSError):
    pass


class SMSDeliveryError(SMSError):
    pass


class SMSValidationError(SMSError):
    pass


class SMSOptedOutError(SMSError):
    pass


class SMSDNDError(SMSError):
    pass


def normalize_phone_number(phone: str) -> str:
    if not phone:
        raise SMSValidationError("Phone number is required")

    # Remove all non-digit characters except leading +
    cleaned = re.sub(r'[^\d+]', '', phone)

    # Handle different formats
    if cleaned.startswith('+'):
        # Already has country code
        digits = cleaned[1:]
        if len(digits) < 10 or len(digits) > 15:
            raise SMSValidationError(f"Invalid phone number length: {phone}")
        return cleaned
    elif cleaned.startswith('1') and len(cleaned) == 11:
        # US number with country code but no +
        return f"+{cleaned}"
    elif len(cleaned) == 10:
        # US number without country code
        return f"+1{cleaned}"
    else:
        raise SMSValidationError(f"Unable to parse phone number: {phone}")


def validate_phone_number(phone: str) -> bool:
    try:
        normalized = normalize_phone_number(phone)
        # Basic E.164 validation
        return bool(re.match(r'^\+[1-9]\d{9,14}$', normalized))
    except SMSValidationError:
        return False


def is_gsm_message(message: str) -> bool:
    for char in message:
        if char not in GSM_BASIC_CHARS and char not in GSM_EXTENDED_CHARS:
            return False
    return True


def count_gsm_characters(message: str) -> int:
    count = 0
    for char in message:
        if char in GSM_EXTENDED_CHARS:
            count += 2  # Extended chars use escape sequence
        else:
            count += 1
    return count


def calculate_segments(message: str) -> int:
    if not message:
        return 0

    if is_gsm_message(message):
        char_count = count_gsm_characters(message)
        if char_count <= GSM_CHARS_PER_SEGMENT:
            return 1
        return (char_count + GSM_CHARS_PER_CONCAT_SEGMENT - 1) // GSM_CHARS_PER_CONCAT_SEGMENT
    else:
        # Unicode message
        char_count = len(message)
        if char_count <= UNICODE_CHARS_PER_SEGMENT:
            return 1
        return (char_count + UNICODE_CHARS_PER_CONCAT_SEGMENT - 1) // UNICODE_CHARS_PER_CONCAT_SEGMENT


def truncate_message(message: str, max_segments: int = 3) -> str:
    if calculate_segments(message) <= max_segments:
        return message

    if is_gsm_message(message):
        if max_segments == 1:
            max_chars = GSM_CHARS_PER_SEGMENT - 3  # Room for "..."
        else:
            max_chars = (GSM_CHARS_PER_CONCAT_SEGMENT * max_segments) - 3

        # Truncate GSM message
        truncated = ""
        char_count = 0
        for char in message:
            char_len = 2 if char in GSM_EXTENDED_CHARS else 1
            if char_count + char_len > max_chars:
                break
            truncated += char
            char_count += char_len
        return truncated + "..."
    else:
        # Unicode message
        if max_segments == 1:
            max_chars = UNICODE_CHARS_PER_SEGMENT - 3
        else:
            max_chars = (UNICODE_CHARS_PER_CONCAT_SEGMENT * max_segments) - 3
        return message[:max_chars] + "..."


def is_within_dnd_hours(
    dnd_start: time,
    dnd_end: time,
    tz_name: str = "America/New_York",
    check_time: Optional[datetime] = None
) -> bool:
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("America/New_York")

    if check_time is None:
        check_time = datetime.now(tz)
    else:
        check_time = check_time.astimezone(tz)

    current_time = check_time.time()

    # Handle overnight DND (e.g., 21:00 - 08:00)
    if dnd_start > dnd_end:
        # DND is active if current time is after start OR before end
        return current_time >= dnd_start or current_time < dnd_end
    else:
        # Normal range (e.g., 08:00 - 18:00)
        return dnd_start <= current_time < dnd_end


def get_next_available_time(
    dnd_start: time,
    dnd_end: time,
    tz_name: str = "America/New_York"
) -> datetime:
    try:
        tz = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, ValueError):
        tz = ZoneInfo("America/New_York")

    now = datetime.now(tz)

    if not is_within_dnd_hours(dnd_start, dnd_end, tz_name, now):
        return now

    # Schedule for DND end time
    next_time = now.replace(
        hour=dnd_end.hour,
        minute=dnd_end.minute,
        second=0,
        microsecond=0
    )

    # If DND end is before current time (overnight), add a day
    if next_time <= now:
        next_time += timedelta(days=1)

    return next_time


def generate_verification_code(length: int = 6) -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(length))


def hash_verification_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def verify_code(code: str, code_hash: str) -> bool:
    return hashlib.sha256(code.encode()).hexdigest() == code_hash


async def send_sms(to_phone: str, message: str) -> dict:
    if not settings.sms_enabled:
        logger.info(
            "SMS disabled - message not sent",
            extra={"to_phone": to_phone[-4:], "message_length": len(message)}
        )
        return {
            "sid": "disabled",
            "status": "disabled",
            "segments": calculate_segments(message),
            "cost_cents": 0
        }

    # sms_enabled is on but no SMS provider is wired (Twilio integration was
    # removed 2026-06; see git history if reintroducing a provider).
    to_phone = normalize_phone_number(to_phone)
    await _track_sms(
        "sms_send", to_phone, success=False,
        error="No SMS provider configured", error_type="configuration",
    )
    raise SMSConfigurationError("No SMS provider configured")


async def _track_sms(template: str, recipient: str, *, success: bool, **kwargs) -> None:
    try:
        from .notification_tracker import track_notification
        await track_notification("sms", template, recipient, success=success, **kwargs)
    except Exception:  # noqa: BLE001  # tracking boundary — must never break SMS sending
        pass  # Tracking must never break SMS sending


async def send_verification_sms(
    to_phone: str,
    verification_code: str,
    library_name: str = branding.library_name
) -> dict:
    message = f"{library_name}: Your verification code is {verification_code}. Valid for {SMS_VERIFICATION_EXPIRY_MINUTES} minutes."
    return await send_sms(to_phone, message)
