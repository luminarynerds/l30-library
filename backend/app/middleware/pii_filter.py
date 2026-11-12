# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

import functools
import inspect
from app.core.logging import get_logger
from typing import Any, Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.responses import Response

from ..core.pii_audit import log_pii_access
from ..core.pii_scope import (
    FIELD_SENSITIVITY,
    PIISensitivity,
    filter_report_response,
    get_max_visibility,
)

logger = get_logger(__name__)


def pii_filtered(fn: Callable) -> Callable:

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        # --- resolve the current user and db from kwargs ---
        current_user = kwargs.get("current_user")
        db = kwargs.get("db")
        request: Request | None = kwargs.get("request")

        # Call the original endpoint
        response = await fn(*args, **kwargs)

        # If there is no user context we cannot filter; return as-is
        if current_user is None:
            return response

        # If the response is already a streaming/file Response, skip filtering
        if isinstance(response, Response):
            return response

        user_role = current_user.role
        max_vis = get_max_visibility(user_role)

        # Apply PII filtering
        filtered_data, fields_redacted = filter_report_response(response, user_role)

        # Determine which fields were accessed (visible to the user)
        fields_accessed: list[str] = []
        if isinstance(response, dict):
            # Collect PII field names present in the original data
            _collect_pii_fields(response, fields_accessed)
        elif isinstance(response, list):
            for item in response:
                if isinstance(item, dict):
                    _collect_pii_fields(item, fields_accessed)

        # Deduplicate
        fields_accessed = list(dict.fromkeys(fields_accessed))
        fields_redacted = list(dict.fromkeys(fields_redacted))

        # Only the fields the user *could* see (not redacted)
        visible_fields = [f for f in fields_accessed if f not in fields_redacted]

        # Extract patron IDs from the data if present
        patron_ids = _extract_patron_ids(response)

        # Determine client IP
        ip_address: str | None = None
        if request is not None:
            ip_address = request.client.host if request.client else None

        # Determine endpoint path
        endpoint_path = ""
        if request is not None:
            endpoint_path = str(request.url.path)

        # Log PII access if any PII fields above PUBLIC were involved
        has_pii_above_public = any(
            FIELD_SENSITIVITY.get(f, PIISensitivity.PUBLIC) > PIISensitivity.PUBLIC
            for f in fields_accessed
        )
        if has_pii_above_public:
            await log_pii_access(
                db=db,
                user_id=current_user.id,
                user_role=user_role,
                endpoint=endpoint_path,
                fields_accessed=visible_fields,
                fields_redacted=fields_redacted,
                patron_ids_accessed=patron_ids,
                ip_address=ip_address,
            )

        return filtered_data

    return wrapper


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _collect_pii_fields(data: dict, accumulator: list[str]) -> None:
    for key in data:
        if key in FIELD_SENSITIVITY and key not in accumulator:
            accumulator.append(key)
    # Check nested structures
    for value in data.values():
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _collect_pii_fields(item, accumulator)
        elif isinstance(value, dict):
            _collect_pii_fields(value, accumulator)


def _extract_patron_ids(data: Any) -> list[int]:
    patron_ids: list[int] = []
    if isinstance(data, dict):
        for key in ("patron_id", "user_id"):
            val = data.get(key)
            if isinstance(val, int) and val not in patron_ids:
                patron_ids.append(val)
        for value in data.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        patron_ids.extend(
                            pid for pid in _extract_patron_ids(item) if pid not in patron_ids
                        )
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                patron_ids.extend(
                    pid for pid in _extract_patron_ids(item) if pid not in patron_ids
                )
    return patron_ids
