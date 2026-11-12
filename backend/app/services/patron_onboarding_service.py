# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import and_, or_, select

from ..models.reading import ReadingProgram, ReadingProgramType

logger = get_logger(__name__)


async def check_summer_reading_active(db=None) -> bool:
    if db is not None:
        today = datetime.now(timezone.utc).date()
        result = await db.execute(
            select(ReadingProgram.id)
            .where(
                and_(
                    ReadingProgram.is_active.is_(True),
                    ReadingProgram.start_date <= today,
                    ReadingProgram.end_date >= today,
                    or_(
                        ReadingProgram.program_type == ReadingProgramType.summer,
                        ReadingProgram.name.ilike("%summer%"),
                    ),
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    # For now, assume summer reading is active June-August
    current_month = datetime.now(timezone.utc).month
    return 6 <= current_month <= 8


async def auto_enroll_summer_reading(user_id: int, db) -> bool:
    # Check if summer reading is active
    is_active = await check_summer_reading_active(db)
    if not is_active:
        logger.info(f"Summer reading not active, skipping enrollment for user {user_id}")
        return True

    # Auto-enrollment is not yet implemented - report honestly
    logger.warning(
        f"Summer reading auto-enrollment not implemented: user {user_id} was NOT "
        "enrolled. A SummerReadingEnrollment model and integration with the "
        "reading_registrations table is required to enable this feature."
    )
    return False


async def validate_and_normalize_address(
    address_line1: Optional[str],
    address_line2: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    zip_code: Optional[str] = None,
) -> dict:
    result = {
        "valid": True,
        "normalized": False,
        "address_line1": address_line1,
        "address_line2": address_line2,
        "city": city,
        "state": state,
        "zip_code": zip_code,
        "warnings": [],
    }

    try:
        # External validator integration is optional; run robust local validation/normalization.

        if not address_line1 or len(address_line1.strip()) < 5:
            result["valid"] = False
            result["warnings"].append("Street address is too short or missing")
            return result

        if not city or len(city.strip()) < 2:
            result["valid"] = False
            result["warnings"].append("City is required")
            return result

        if state and len(state) != 2:
            result["warnings"].append("State code should be 2 letters")

        if zip_code and not zip_code.replace("-", "").isdigit():
            result["warnings"].append("ZIP code should contain only digits and hyphens")

        # Normalize state to uppercase
        if state:
            result["state"] = state.upper()

        # Basic normalization
        result["address_line1"] = address_line1.strip().title() if address_line1 else None
        if address_line2:
            result["address_line2"] = address_line2.strip().upper() if address_line2 else None
        result["city"] = city.strip().title() if city else None

        result["normalized"] = True
        return result

    except Exception as e:  # noqa: BLE001 - service-entrypoint boundary — must return graceful result on any validation failure
        logger.error(f"Address validation error: {e}")
        result["valid"] = False
        result["warnings"].append("Address validation failed due to an unexpected error")
        return result


async def get_address_suggestions(partial_address: str) -> list[dict]:
    if not partial_address or len(partial_address.strip()) < 3:
        return []

    try:
        suggestions = [
            {
                "address": "123 Main Street, Springfield, IL 62701",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62701",
            },
            {
                "address": "124 Main Street, Springfield, IL 62701",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62701",
            },
            {
                "address": "125 Market Street, Springfield, IL 62702",
                "city": "Springfield",
                "state": "IL",
                "zip_code": "62702",
            },
        ]

        # Filter suggestions based on partial address
        filtered = [
            s for s in suggestions
            if s["address"].lower().startswith(partial_address.lower())
        ]

        return filtered[:5]  # Return max 5 suggestions

    except (KeyError, AttributeError, TypeError) as e:
        logger.error(f"Failed to get address suggestions: {e}")
        return []


async def calculate_patron_type(
    age: Optional[int] = None,
    date_of_birth: Optional[str] = None,
) -> str:
    # Default to adult if no age info
    if age is None and date_of_birth is None:
        return "adult"

    try:
        if age:
            calculated_age = age
        elif date_of_birth:
            from datetime import date
            birth_date = date.fromisoformat(date_of_birth)
            today = date.today()
            calculated_age = today.year - birth_date.year - (
                (today.month, today.day) < (birth_date.month, birth_date.day)
            )
        else:
            return "adult"

        if calculated_age < 13:
            return "child"
        elif calculated_age < 18:
            return "teen"
        else:
            return "adult"

    except (ValueError, TypeError) as e:
        logger.error(f"Failed to calculate patron type: {e}")
        return "adult"
