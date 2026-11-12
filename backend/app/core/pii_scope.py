# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import copy
from app.core.logging import get_logger
import re
from enum import IntEnum, auto
from typing import Any

from ..models.user import UserRole

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Sensitivity levels
# ---------------------------------------------------------------------------

class PIISensitivity(IntEnum):
    PUBLIC = 1
    INTERNAL = 2
    SENSITIVE = 3
    RESTRICTED = 4


# ---------------------------------------------------------------------------
# Role -> maximum visibility mapping
# ---------------------------------------------------------------------------

# Maps each UserRole to the *maximum* PII sensitivity level that role may see.
# Roles not listed here default to PUBLIC.
ROLE_VISIBILITY: dict[UserRole, PIISensitivity] = {
    # Non-staff roles -- PUBLIC only
    UserRole.PATRON: PIISensitivity.PUBLIC,
    UserRole.CHILD: PIISensitivity.PUBLIC,
    UserRole.BOOKMOBILE: PIISensitivity.PUBLIC,
    UserRole.HOMEBOND: PIISensitivity.PUBLIC,

    # Staff -- INTERNAL
    UserRole.STAFF: PIISensitivity.INTERNAL,

    # Librarian-level (Director, Legal) -- SENSITIVE
    UserRole.DIRECTOR: PIISensitivity.SENSITIVE,
    UserRole.LEGAL: PIISensitivity.SENSITIVE,

    # Admins -- RESTRICTED (full access)
    UserRole.ADMIN: PIISensitivity.RESTRICTED,
    UserRole.SUPER_ADMIN: PIISensitivity.RESTRICTED,
}


def get_max_visibility(role: UserRole) -> PIISensitivity:
    return ROLE_VISIBILITY.get(role, PIISensitivity.PUBLIC)


# ---------------------------------------------------------------------------
# Field -> sensitivity classification
# ---------------------------------------------------------------------------

# Each key is the field name as it appears in report dicts.  The value is the
# *minimum* sensitivity level required to see the field un-redacted.
FIELD_SENSITIVITY: dict[str, PIISensitivity] = {
    # PUBLIC fields -- everyone can see
    "patron_name": PIISensitivity.PUBLIC,
    "patron_id": PIISensitivity.PUBLIC,
    "patron_type": PIISensitivity.PUBLIC,
    "first_name": PIISensitivity.PUBLIC,
    "last_name": PIISensitivity.PUBLIC,
    "name": PIISensitivity.PUBLIC,
    "library_card_last4": PIISensitivity.PUBLIC,

    # INTERNAL fields -- staff and above
    "patron_library_card": PIISensitivity.INTERNAL,
    "library_card": PIISensitivity.INTERNAL,
    "patron_email_masked": PIISensitivity.INTERNAL,
    "email_masked": PIISensitivity.INTERNAL,
    "checkout_history_summary": PIISensitivity.INTERNAL,

    # SENSITIVE fields -- director/legal and above
    "patron_email": PIISensitivity.SENSITIVE,
    "email": PIISensitivity.SENSITIVE,
    "patron_phone": PIISensitivity.SENSITIVE,
    "phone": PIISensitivity.SENSITIVE,
    "date_of_birth": PIISensitivity.SENSITIVE,
    "checkout_history": PIISensitivity.SENSITIVE,
    "notice_preference": PIISensitivity.SENSITIVE,

    # RESTRICTED fields -- admin only
    "patron_address": PIISensitivity.RESTRICTED,
    "address": PIISensitivity.RESTRICTED,
    "address_line1": PIISensitivity.RESTRICTED,
    "address_line2": PIISensitivity.RESTRICTED,
    "city": PIISensitivity.RESTRICTED,
    "state": PIISensitivity.RESTRICTED,
    "zip_code": PIISensitivity.RESTRICTED,
    "ssn": PIISensitivity.RESTRICTED,
    "linked_accounts": PIISensitivity.RESTRICTED,
    "law_enforcement_flags": PIISensitivity.RESTRICTED,
    "emergency_contact_name": PIISensitivity.RESTRICTED,
    "emergency_contact_phone": PIISensitivity.RESTRICTED,
}


def get_field_sensitivity(field_name: str) -> PIISensitivity | None:
    return FIELD_SENSITIVITY.get(field_name)


# ---------------------------------------------------------------------------
# Masking helpers
# ---------------------------------------------------------------------------

def mask_email(value: str | None) -> str | None:
    if not value:
        return value
    try:
        local, domain = value.rsplit("@", 1)
    except ValueError:
        return "***"
    if local:
        return f"{local[0]}***@{domain}"
    return f"***@{domain}"


def mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    digits = re.sub(r"\D", "", value)
    if len(digits) < 4:
        return "***"
    return f"***-***-{digits[-4:]}"


def mask_card_number(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 4:
        return value
    return f"***{value[-4:]}"


def mask_field(value: Any, field_type: str) -> Any:
    maskers = {
        "email": mask_email,
        "phone": mask_phone,
        "card_number": mask_card_number,
    }
    masker = maskers.get(field_type)
    if masker is None:
        return value
    return masker(value)


# ---------------------------------------------------------------------------
# Patron-data filtering
# ---------------------------------------------------------------------------

# Fields that should be replaced with a masked version rather than fully
# redacted when the user's visibility is below the field's level but at or
# above INTERNAL.  Maps field name -> (mask field_type, target output key).
_MASKABLE_FIELDS: dict[str, tuple[str, str]] = {
    "patron_email": ("email", "patron_email_masked"),
    "email": ("email", "email_masked"),
    "patron_phone": ("phone", "patron_phone"),
    "phone": ("phone", "phone"),
    "patron_library_card": ("card_number", "patron_library_card"),
    "library_card": ("card_number", "library_card"),
}

# Sentinel used to mark a redacted value.
REDACTED = "[REDACTED]"


def filter_patron_data(
    patron_dict: dict[str, Any],
    user_role: UserRole,
) -> dict[str, Any]:
    max_vis = get_max_visibility(user_role)
    filtered: dict[str, Any] = {}
    fields_redacted: list[str] = []

    # Keys that the maskable branch will populate (e.g. ``email_masked``).
    # In the in-clearance branch below, never overwrite a value the filter
    # already wrote when iterating a sibling input key (e.g. ``email``).
    masked_output_keys = {out for (_, out) in _MASKABLE_FIELDS.values()}

    for key, value in patron_dict.items():
        sensitivity = FIELD_SENSITIVITY.get(key)

        # Unknown fields pass through (they aren't classified as PII)
        if sensitivity is None:
            filtered[key] = value
            continue

        if sensitivity <= max_vis:
            # User is allowed to see this field, but don't clobber a masked
            # value that the maskable branch already produced for a sibling.
            if key in masked_output_keys and key in filtered:
                continue
            filtered[key] = value
            continue

        # Field is above user's clearance -- redact or mask
        fields_redacted.append(key)

        if key in _MASKABLE_FIELDS:
            mask_type, output_key = _MASKABLE_FIELDS[key]
            filtered[output_key] = mask_field(value, mask_type)
            # Don't include the raw field
        else:
            # Set to None (not "[REDACTED]" sentinel) so typed Pydantic
            # response models -- e.g. date_of_birth: date | None -- don't
            # 500 at response serialization. The redaction signal is
            # preserved via the fields_redacted accumulator returned by
            # filter_report_response.
            filtered[key] = None

    # Inject last-4 of card when the full card was masked/redacted
    for card_key in ("patron_library_card", "library_card"):
        if card_key in patron_dict and card_key in fields_redacted:
            raw_card = patron_dict[card_key]
            if raw_card:
                filtered["library_card_last4"] = mask_card_number(raw_card)

    return filtered


def filter_report_response(
    data: Any,
    user_role: UserRole,
) -> tuple[Any, list[str]]:
    all_redacted: list[str] = []

    if isinstance(data, dict):
        # Check for nested lists that contain patron data
        result = {}
        for key, value in data.items():
            if isinstance(value, list):
                filtered_items = []
                for item in value:
                    if isinstance(item, dict):
                        filtered = filter_patron_data(item, user_role)
                        # Track which fields were redacted
                        for orig_key in item:
                            if orig_key not in filtered and orig_key not in all_redacted:
                                all_redacted.append(orig_key)
                            elif orig_key in filtered and filtered[orig_key] == REDACTED and orig_key not in all_redacted:
                                all_redacted.append(orig_key)
                        filtered_items.append(filtered)
                    else:
                        filtered_items.append(item)
                result[key] = filtered_items
            elif isinstance(value, dict):
                nested_filtered, nested_redacted = filter_report_response(value, user_role)
                result[key] = nested_filtered
                all_redacted.extend(r for r in nested_redacted if r not in all_redacted)
            else:
                result[key] = value
        # Also filter top-level patron fields if present
        top_level_has_pii = any(k in FIELD_SENSITIVITY for k in result)
        if top_level_has_pii:
            result = filter_patron_data(result, user_role)
        return result, all_redacted

    elif isinstance(data, list):
        filtered_items = []
        for item in data:
            if isinstance(item, dict):
                filtered = filter_patron_data(item, user_role)
                for orig_key in item:
                    if orig_key not in filtered and orig_key not in all_redacted:
                        all_redacted.append(orig_key)
                    elif orig_key in filtered and filtered[orig_key] == REDACTED and orig_key not in all_redacted:
                        all_redacted.append(orig_key)
                filtered_items.append(filtered)
            else:
                filtered_items.append(item)
        return filtered_items, all_redacted

    # Scalar or unknown structure -- pass through
    return data, all_redacted
