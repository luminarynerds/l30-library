# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import html
from app.core.logging import get_logger
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = get_logger(__name__)


@dataclass
class ValidationResult:

    is_valid: bool
    sanitized_input: str | None = None
    errors: list[str] = None
    warnings: list[str] = None


class InputValidator:

    # Maximum lengths for different input types
    MAX_LENGTHS = {
        "title": 500,
        "author": 200,
        "challenger_name": 200,
        "reason": 5000,
        "email": 254,
        "description": 10000,
        "name": 255,
        "query": 1000,
        "search": 1000,
        "comment": 5000,
        "note": 5000,
        "address": 500,
        "phone": 50,
        "url": 2048,
        "isbn": 20,
        "barcode": 50,
    }

    # Patterns for potentially malicious content
    SUSPICIOUS_PATTERNS = [
        r"<script[^>]*>.*?</script>",  # Script tags
        r"javascript:",  # JavaScript protocols
        r"on\w+\s*=",  # Event handlers
        r"<iframe[^>]*>",  # Iframes
        r"<object[^>]*>",  # Objects
        r"<embed[^>]*>",  # Embeds
        r"eval\s*\(",  # eval calls
        r"exec\s*\(",  # exec calls
        r"system\s*\(",  # system calls
        r"import\s+os",  # OS imports
        r"__import__",  # Dynamic imports
        r"\\x[0-9a-fA-F]{2}",  # Hex encoding
        r"%[0-9a-fA-F]{2}",  # URL encoding of suspicious chars
    ]
    # NOTE: Path traversal (CWE-22) is now handled by _is_path_traversal() method
    # which provides comprehensive protection against both Unix and Windows variants

    # SQL injection patterns (more specific to avoid false positives)
    SQL_INJECTION_PATTERNS = [
        r"\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE|UNION|DECLARE)\s+\w+",
        r"(-{2}|\/\*|\*\/)",  # SQL comments
        r'\b(OR|AND)\s+[\'"]?\d+[\'"]?\s*=\s*[\'"]?\d+[\'"]?',  # OR 1=1, AND 1=1
        r";\s*(SELECT|INSERT|UPDATE|DELETE|DROP)",  # Statement termination
    ]

    # Command injection patterns (more specific to avoid false positives)
    COMMAND_INJECTION_PATTERNS = [
        r"[;&|`$].*[;&|`$]",  # Multiple shell metacharacters
        r"\b(cat|ls|pwd|id|whoami|uname|ps|kill|rm|mv|cp|chmod|chown)\s+/",  # Commands with paths
        r"\b(curl|wget|nc|netcat|telnet|ssh)\s+\w+",  # Network commands with targets
    ]

    def __init__(self):
        # Compile patterns for performance
        self.suspicious_regex = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS
        ]
        self.sql_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.SQL_INJECTION_PATTERNS
        ]
        self.command_regex = [
            re.compile(pattern, re.IGNORECASE)
            for pattern in self.COMMAND_INJECTION_PATTERNS
        ]

    def _is_path_traversal(self, value: str) -> bool:
        # Normalize path: converts all backslashes to forward slashes
        # and resolves . and .. patterns
        normalized = os.path.normpath(value).replace("\\", "/")

        # Check for ".." in normalized path (directory traversal)
        if ".." in normalized:
            logger.warning("Path traversal detected via '..' pattern: %s", value)
            return True

        # Check for absolute paths (starting with / or Windows drive letters)
        if normalized.startswith("/"):
            logger.warning("Absolute Unix path detected: %s", value)
            return True

        # Check for Windows absolute paths (e.g., C:\, D:\, etc.)
        if re.match(r"^[a-zA-Z]:", normalized):
            logger.warning("Absolute Windows path detected: %s", value)
            return True

        # Check for alternative path traversal patterns using pathlib
        try:
            path_obj = Path(value)
            # Check if the path contains parent references when resolved
            # This catches cases like "....", "..\\..\\", etc.
            parts = path_obj.parts
            if ".." in parts:
                logger.warning("Path traversal detected via path parts: %s", value)
                return True
        except (ValueError, OSError):
            # Invalid path syntax might indicate attack attempt
            logger.warning("Invalid path syntax detected: %s", value)
            return True

        return False

    def validate_challenge_input(
        self, challenge_data: dict[str, Any]
    ) -> ValidationResult:
        errors = []
        warnings = []
        sanitized_data = {}

        # Validate required fields
        required_fields = ["challenger_name", "reason"]
        for field in required_fields:
            if not challenge_data.get(field):
                errors.append(f"Required field '{field}' is missing or empty")

        # Validate and sanitize each field
        for field, value in challenge_data.items():
            if value is None:
                continue

            if isinstance(value, str):
                result = self._validate_string_field(field, value)
                if not result.is_valid:
                    errors.extend(result.errors or [])
                    warnings.extend(result.warnings or [])
                else:
                    sanitized_data[field] = result.sanitized_input
            else:
                # Non-string fields (IDs, booleans, etc.)
                sanitized_data[field] = value

        return ValidationResult(
            is_valid=len(errors) == 0,
            sanitized_input=sanitized_data if len(errors) == 0 else None,
            errors=errors,
            warnings=warnings,
        )

    def _validate_string_field(self, field_name: str, value: str) -> ValidationResult:
        errors = []
        warnings = []

        # Check length
        max_length = self.MAX_LENGTHS.get(field_name, 1000)
        if len(value) > max_length:
            errors.append(
                f"Field '{field_name}' exceeds maximum length of {max_length} characters"
            )
            return ValidationResult(False, None, errors, warnings)

        # Check for null bytes
        if "\x00" in value:
            errors.append(f"Field '{field_name}' contains null bytes")
            return ValidationResult(False, None, errors, warnings)

        # Check for path traversal (CWE-22) - both Unix and Windows variants
        if self._is_path_traversal(value):
            errors.append(
                f"Field '{field_name}' contains potentially malicious path traversal"
            )
            return ValidationResult(False, None, errors, warnings)

        # Check for suspicious patterns
        for regex in self.suspicious_regex:
            if regex.search(value):
                errors.append(
                    f"Field '{field_name}' contains potentially malicious content"
                )
                logger.warning(
                    f"Suspicious pattern detected in {field_name}: {regex.pattern}"
                )
                return ValidationResult(False, None, errors, warnings)

        # Check for SQL injection
        for regex in self.sql_regex:
            if regex.search(value):
                errors.append(f"Field '{field_name}' contains potential SQL injection")
                logger.warning("SQL injection pattern detected in %s", field_name)
                return ValidationResult(False, None, errors, warnings)

        # Check for command injection
        for regex in self.command_regex:
            if regex.search(value):
                warnings.append(
                    f"Field '{field_name}' contains potential command injection patterns"
                )
                logger.warning("Command injection pattern detected in %s", field_name)

        # Sanitize the input
        sanitized = self._sanitize_string(value)

        return ValidationResult(
            is_valid=True, sanitized_input=sanitized, errors=errors, warnings=warnings
        )

    def _sanitize_string(self, value: str) -> str:
        # HTML escape
        sanitized = html.escape(value, quote=True)

        # Remove control characters except tab, newline, and carriage return
        sanitized = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]", "", sanitized)

        # Normalize whitespace
        sanitized = re.sub(r"\s+", " ", sanitized)

        # Strip leading/trailing whitespace
        sanitized = sanitized.strip()

        return sanitized

    def validate_ai_response(self, response: dict[str, Any]) -> ValidationResult:
        errors = []
        warnings = []
        sanitized_response = {}

        # Expected response fields with their types
        expected_fields = {
            "sentiment_score": (float, int),
            "coordinated_attack_likelihood": (float, int),
            "recommended_action": str,
            "confidence_score": (float, int),
            "reasoning": str,
            "alert_level": str,
            "tags": list,
        }

        for field, expected_type in expected_fields.items():
            if field in response:
                value = response[field]

                # Type validation
                if isinstance(expected_type, tuple):
                    if not isinstance(value, expected_type):
                        warnings.append(
                            f"AI response field '{field}' has unexpected type"
                        )
                else:
                    if not isinstance(value, expected_type):
                        warnings.append(
                            f"AI response field '{field}' has unexpected type"
                        )

                # Range validation for scores
                if field.endswith("_score") or field.endswith("_likelihood"):
                    if isinstance(value, (int, float)):
                        if not 0 <= value <= 1:
                            warnings.append(
                                f"Score field '{field}' outside valid range [0,1]"
                            )
                            # Clamp to valid range
                            value = max(0, min(1, value))

                # Sanitize string fields
                if isinstance(value, str):
                    result = self._validate_string_field(field, value)
                    if result.is_valid:
                        sanitized_response[field] = result.sanitized_input
                    else:
                        warnings.extend(result.errors or [])
                        sanitized_response[field] = (
                            "AI response contained invalid content"
                        )
                elif isinstance(value, list):
                    # Sanitize list items if they're strings
                    sanitized_list = []
                    for item in value:
                        if isinstance(item, str):
                            result = self._validate_string_field(f"{field}_item", item)
                            if result.is_valid:
                                sanitized_list.append(result.sanitized_input)
                        else:
                            sanitized_list.append(item)
                    sanitized_response[field] = sanitized_list
                else:
                    sanitized_response[field] = value

        return ValidationResult(
            is_valid=True,  # AI responses get warnings, not rejections
            sanitized_input=sanitized_response,
            errors=errors,
            warnings=warnings,
        )


# Global validator instance
input_validator = InputValidator()
