# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re
from app.core.logging import get_logger
from typing import Optional, Any

from fastapi import HTTPException, status

logger = get_logger(__name__)

# Security constraints
MAX_SITUATION_NOTES_LENGTH = 500
MAX_METADATA_SIZE = 10000  # Max size in bytes for serialized metadata
MAX_METADATA_KEYS = 20
MAX_STRING_VALUE_LENGTH = 1000

# Dangerous patterns that could indicate SQL injection attempts
SQL_INJECTION_PATTERNS = [
    r"('\s*(OR|AND)\s*'?\d+)",  # ' OR '1'='1
    r"(\bUNION\b.*\bSELECT\b)",  # UNION SELECT
    r"(\bDROP\b.*\bTABLE\b)",  # DROP TABLE
    r"(\bINSERT\b.*\bINTO\b)",  # INSERT INTO
    r"(\bUPDATE\b.*\bSET\b)",  # UPDATE ... SET
    r"(\bDELETE\b.*\bFROM\b)",  # DELETE FROM
    r"(--\s*$)",  # SQL comment at end
    r"(;\s*DROP\b)",  # ; DROP
    r"(\bEXEC\b|\bEXECUTE\b)",  # EXEC/EXECUTE
    r"(\bSCRIPT\b.*>)",  # Script tags
]

# Compile patterns for performance
COMPILED_SQL_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in SQL_INJECTION_PATTERNS]

# XSS patterns
XSS_PATTERNS = [
    r"<script\b[^>]*>",  # <script> tags
    r"javascript:",  # javascript: protocol
    r"on\w+\s*=",  # Event handlers like onclick=
    r"<iframe\b[^>]*>",  # <iframe> tags
    r"<object\b[^>]*>",  # <object> tags
    r"<embed\b[^>]*>",  # <embed> tags
]

COMPILED_XSS_PATTERNS = [re.compile(pattern, re.IGNORECASE) for pattern in XSS_PATTERNS]


def sanitize_input(value: str) -> str:
    if not value:
        return value

    # Remove null bytes (can cause issues in C-based libraries)
    sanitized = value.replace("\x00", "")

    # Normalize whitespace
    sanitized = " ".join(sanitized.split())

    return sanitized


def detect_sql_injection(value: str) -> bool:
    if not value:
        return False

    for pattern in COMPILED_SQL_PATTERNS:
        if pattern.search(value):
            return True

    return False


def detect_xss(value: str) -> bool:
    if not value:
        return False

    for pattern in COMPILED_XSS_PATTERNS:
        if pattern.search(value):
            return True

    return False


def validate_situation_notes(notes: Optional[str]) -> Optional[str]:
    if not notes:
        return None

    # Length check
    if len(notes) > MAX_SITUATION_NOTES_LENGTH:
        logger.warning(
            "Panic alert situation notes exceeds maximum length",
            extra={"length": len(notes), "max_length": MAX_SITUATION_NOTES_LENGTH}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "SITUATION_NOTES_TOO_LONG",
                    "message": f"Situation notes must not exceed {MAX_SITUATION_NOTES_LENGTH} characters",
                    "max_length": MAX_SITUATION_NOTES_LENGTH,
                }
            }
        )

    # SQL injection check
    if detect_sql_injection(notes):
        logger.error(
            "Potential SQL injection detected in panic alert situation notes",
            extra={"notes_preview": notes[:100]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Situation notes contain invalid characters or patterns",
                }
            }
        )

    # XSS check
    if detect_xss(notes):
        logger.error(
            "Potential XSS detected in panic alert situation notes",
            extra={"notes_preview": notes[:100]}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_INPUT",
                    "message": "Situation notes contain invalid characters or patterns",
                }
            }
        )

    # Sanitize and return
    return sanitize_input(notes)


def validate_metadata(metadata: Optional[dict]) -> Optional[dict]:
    if not metadata:
        return None

    # Type check
    if not isinstance(metadata, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "INVALID_METADATA_TYPE",
                    "message": "Metadata must be a JSON object",
                }
            }
        )

    # Size check (prevent DOS via large payloads)
    import json
    serialized = json.dumps(metadata)
    if len(serialized) > MAX_METADATA_SIZE:
        logger.warning(
            "Panic alert metadata exceeds maximum size",
            extra={"size": len(serialized), "max_size": MAX_METADATA_SIZE}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "METADATA_TOO_LARGE",
                    "message": f"Metadata payload exceeds maximum size of {MAX_METADATA_SIZE} bytes",
                    "max_size": MAX_METADATA_SIZE,
                }
            }
        )

    # Key count check
    if len(metadata) > MAX_METADATA_KEYS:
        logger.warning(
            "Panic alert metadata exceeds maximum key count",
            extra={"key_count": len(metadata), "max_keys": MAX_METADATA_KEYS}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "TOO_MANY_METADATA_KEYS",
                    "message": f"Metadata must not contain more than {MAX_METADATA_KEYS} keys",
                    "max_keys": MAX_METADATA_KEYS,
                }
            }
        )

    # Validate each key-value pair
    sanitized_metadata = {}
    for key, value in metadata.items():
        # Validate key
        if not isinstance(key, str):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_METADATA_KEY",
                        "message": "All metadata keys must be strings",
                    }
                }
            )

        if len(key) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "METADATA_KEY_TOO_LONG",
                        "message": "Metadata keys must not exceed 100 characters",
                    }
                }
            )

        # Validate value
        sanitized_value = _validate_metadata_value(key, value)
        sanitized_metadata[key] = sanitized_value

    return sanitized_metadata


def _validate_metadata_value(key: str, value: Any, depth: int = 0) -> Any:
    # Prevent excessive nesting (DOS protection)
    if depth > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": {
                    "code": "METADATA_TOO_DEEPLY_NESTED",
                    "message": "Metadata objects must not be nested more than 5 levels deep",
                }
            }
        )

    # Validate based on type
    if value is None:
        return None

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        # String length check
        if len(value) > MAX_STRING_VALUE_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "METADATA_VALUE_TOO_LONG",
                        "message": f"Metadata string values must not exceed {MAX_STRING_VALUE_LENGTH} characters",
                        "key": key,
                    }
                }
            )

        # SQL injection check
        if detect_sql_injection(value):
            logger.error(
                f"Potential SQL injection in metadata value for key: {key}",
                extra={"key": key, "value_preview": value[:100]}
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_METADATA_VALUE",
                        "message": f"Invalid characters in metadata value for key: {key}",
                    }
                }
            )

        return sanitize_input(value)

    if isinstance(value, list):
        # Limit list size
        if len(value) > 50:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "METADATA_ARRAY_TOO_LARGE",
                        "message": "Metadata arrays must not contain more than 50 items",
                        "key": key,
                    }
                }
            )
        return [_validate_metadata_value(f"{key}[{i}]", item, depth + 1) for i, item in enumerate(value)]

    if isinstance(value, dict):
        # Limit object size
        if len(value) > MAX_METADATA_KEYS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "METADATA_OBJECT_TOO_LARGE",
                        "message": f"Nested metadata objects must not contain more than {MAX_METADATA_KEYS} keys",
                        "key": key,
                    }
                }
            )
        return {k: _validate_metadata_value(f"{key}.{k}", v, depth + 1) for k, v in value.items()}

    # Unsupported type
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={
            "error": {
                "code": "UNSUPPORTED_METADATA_TYPE",
                "message": f"Unsupported type in metadata for key: {key}",
                "key": key,
            }
        }
    )


class PanicAlertValidator:

    @staticmethod
    def validate_alert_data(
        situation_notes: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> tuple[Optional[str], Optional[dict]]:
        validated_notes = validate_situation_notes(situation_notes)
        validated_metadata = validate_metadata(metadata)

        return (validated_notes, validated_metadata)
