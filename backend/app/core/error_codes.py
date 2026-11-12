# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum
from typing import Dict


class ErrorCode(StrEnum):

    # =========================================================================
    # AUTHENTICATION (40x - Client responsibility)
    # =========================================================================

    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    TOKEN_INVALID = "TOKEN_INVALID"
    TOKEN_REVOKED = "TOKEN_REVOKED"
    MFA_REQUIRED = "MFA_REQUIRED"
    MFA_INVALID = "MFA_INVALID"
    SESSION_EXPIRED = "SESSION_EXPIRED"

    # =========================================================================
    # AUTHORIZATION (403 - Client responsibility)
    # =========================================================================

    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INSUFFICIENT_ROLE = "INSUFFICIENT_ROLE"
    RESOURCE_FORBIDDEN = "RESOURCE_FORBIDDEN"
    OPERATION_FORBIDDEN = "OPERATION_FORBIDDEN"
    PATRON_BLOCKED = "PATRON_BLOCKED"
    PATRON_DECEASED = "PATRON_DECEASED"
    STAFF_ONLY = "STAFF_ONLY"
    ADMIN_ONLY = "ADMIN_ONLY"

    # =========================================================================
    # VALIDATION (400 - Client responsibility)
    # =========================================================================

    VALIDATION_FAILED = "VALIDATION_FAILED"
    INVALID_REQUEST_BODY = "INVALID_REQUEST_BODY"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    INVALID_EMAIL = "INVALID_EMAIL"
    INVALID_PASSWORD = "INVALID_PASSWORD"
    INVALID_ISBN = "INVALID_ISBN"
    INVALID_DATE = "INVALID_DATE"
    INVALID_ENUM = "INVALID_ENUM"
    INVALID_JSON = "INVALID_JSON"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    FIELD_TOO_LONG = "FIELD_TOO_LONG"
    FIELD_TOO_SHORT = "FIELD_TOO_SHORT"
    DUPLICATE_EMAIL = "DUPLICATE_EMAIL"
    DUPLICATE_ISBN = "DUPLICATE_ISBN"
    DUPLICATE_BARCODE = "DUPLICATE_BARCODE"

    # =========================================================================
    # RESOURCE NOT FOUND (404)
    # =========================================================================

    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PATRON_NOT_FOUND = "PATRON_NOT_FOUND"
    CATALOG_ITEM_NOT_FOUND = "CATALOG_ITEM_NOT_FOUND"
    CHECKOUT_NOT_FOUND = "CHECKOUT_NOT_FOUND"
    HOLD_NOT_FOUND = "HOLD_NOT_FOUND"
    FINE_NOT_FOUND = "FINE_NOT_FOUND"
    LEARNING_PATH_NOT_FOUND = "LEARNING_PATH_NOT_FOUND"
    EVENT_NOT_FOUND = "EVENT_NOT_FOUND"
    READING_PROGRAM_NOT_FOUND = "READING_PROGRAM_NOT_FOUND"
    COLLECTION_NOT_FOUND = "COLLECTION_NOT_FOUND"
    REPORT_NOT_FOUND = "REPORT_NOT_FOUND"

    # =========================================================================
    # CONFLICT (409 - State mismatch)
    # =========================================================================

    RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
    DUPLICATE_OPERATION = "DUPLICATE_OPERATION"
    INVALID_STATE = "INVALID_STATE"
    CHECKOUT_EXISTS = "CHECKOUT_EXISTS"
    HOLD_EXISTS = "HOLD_EXISTS"
    CANNOT_CHECKOUT = "CANNOT_CHECKOUT"
    CANNOT_RETURN = "CANNOT_RETURN"
    CANNOT_PLACE_HOLD = "CANNOT_PLACE_HOLD"
    ITEM_NOT_AVAILABLE = "ITEM_NOT_AVAILABLE"
    ITEM_CHECKED_OUT = "ITEM_CHECKED_OUT"
    ITEM_ON_HOLD = "ITEM_ON_HOLD"
    PATRON_HAS_OUTSTANDING_FINE = "PATRON_HAS_OUTSTANDING_FINE"
    PATRON_ACCOUNT_SUSPENDED = "PATRON_ACCOUNT_SUSPENDED"
    PATRON_CARD_EXPIRED = "PATRON_CARD_EXPIRED"

    # =========================================================================
    # BUSINESS LOGIC ERRORS (422 - Unprocessable entity)
    # =========================================================================

    BUSINESS_LOGIC_ERROR = "BUSINESS_LOGIC_ERROR"
    OPERATION_NOT_ALLOWED = "OPERATION_NOT_ALLOWED"
    INSUFFICIENT_INVENTORY = "INSUFFICIENT_INVENTORY"
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INVALID_TRANSITION = "INVALID_TRANSITION"
    CIRCULAR_DEPENDENCY = "CIRCULAR_DEPENDENCY"
    ITEM_NOT_HOLDABLE = "ITEM_NOT_HOLDABLE"

    # =========================================================================
    # SYSTEM ERRORS (50x - Server responsibility)
    # =========================================================================

    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    CACHE_ERROR = "CACHE_ERROR"
    FILE_OPERATION_ERROR = "FILE_OPERATION_ERROR"
    EMAIL_SEND_ERROR = "EMAIL_SEND_ERROR"


# Error message templates - these can contain {variable} placeholders
ERROR_MESSAGES: Dict[ErrorCode, str] = {
    # Authentication
    ErrorCode.UNAUTHORIZED: "Authentication required",
    ErrorCode.INVALID_CREDENTIALS: "Invalid credentials provided",
    ErrorCode.TOKEN_EXPIRED: "Authentication token has expired",
    ErrorCode.TOKEN_INVALID: "Authentication token is invalid",
    ErrorCode.TOKEN_REVOKED: "Authentication token has been revoked",
    ErrorCode.MFA_REQUIRED: "Multi-factor authentication is required",
    ErrorCode.MFA_INVALID: "Multi-factor authentication code is invalid",
    ErrorCode.SESSION_EXPIRED: "Your session has expired. Please sign in again.",

    # Authorization
    ErrorCode.INSUFFICIENT_PERMISSIONS: "Insufficient permissions to perform this action",
    ErrorCode.INSUFFICIENT_ROLE: "Your role does not have permission for this operation",
    ErrorCode.RESOURCE_FORBIDDEN: "You do not have access to this resource",
    ErrorCode.OPERATION_FORBIDDEN: "This operation is not allowed",
    ErrorCode.PATRON_BLOCKED: "Your account is currently blocked. Please contact the library for assistance.",
    ErrorCode.PATRON_DECEASED: "Patron account is marked as deceased. All circulation operations are blocked. Please contact staff for estate-related matters.",
    ErrorCode.STAFF_ONLY: "This operation is restricted to staff members",
    ErrorCode.ADMIN_ONLY: "This operation is restricted to administrators",

    # Validation
    ErrorCode.VALIDATION_FAILED: "Request validation failed",
    ErrorCode.INVALID_REQUEST_BODY: "Request body is invalid",
    ErrorCode.INVALID_PARAMETER: "Invalid parameter provided",
    ErrorCode.INVALID_EMAIL: "Email format is invalid",
    ErrorCode.INVALID_PASSWORD: "Password does not meet requirements",
    ErrorCode.INVALID_ISBN: "ISBN format is invalid",
    ErrorCode.INVALID_DATE: "Date format is invalid",
    ErrorCode.INVALID_ENUM: "Invalid enumeration value provided",
    ErrorCode.INVALID_JSON: "Request body contains invalid JSON",
    ErrorCode.MISSING_REQUIRED_FIELD: "Required field is missing",
    ErrorCode.FIELD_TOO_LONG: "Field value exceeds maximum length",
    ErrorCode.FIELD_TOO_SHORT: "Field value is below minimum length",
    ErrorCode.DUPLICATE_EMAIL: "An account with this email already exists. Try signing in instead.",
    ErrorCode.DUPLICATE_ISBN: "ISBN already exists in the catalog",
    ErrorCode.DUPLICATE_BARCODE: "Barcode already exists in the system",

    # Resource Not Found
    ErrorCode.RESOURCE_NOT_FOUND: "Requested resource not found",
    ErrorCode.USER_NOT_FOUND: "We couldn't find that account",
    ErrorCode.PATRON_NOT_FOUND: "We couldn't find that library account",
    ErrorCode.CATALOG_ITEM_NOT_FOUND: "Catalog item not found",
    ErrorCode.CHECKOUT_NOT_FOUND: "Checkout record not found",
    ErrorCode.HOLD_NOT_FOUND: "Hold record not found",
    ErrorCode.FINE_NOT_FOUND: "Fine record not found",
    ErrorCode.LEARNING_PATH_NOT_FOUND: "Learning path not found",
    ErrorCode.EVENT_NOT_FOUND: "Event not found",
    ErrorCode.READING_PROGRAM_NOT_FOUND: "Reading program not found",
    ErrorCode.COLLECTION_NOT_FOUND: "Collection not found",
    ErrorCode.REPORT_NOT_FOUND: "Report not found",

    # Conflict
    ErrorCode.RESOURCE_ALREADY_EXISTS: "Resource already exists",
    ErrorCode.DUPLICATE_OPERATION: "This operation has already been performed",
    ErrorCode.INVALID_STATE: "Resource is in an invalid state for this operation",
    ErrorCode.CHECKOUT_EXISTS: "You already have this item checked out",
    ErrorCode.HOLD_EXISTS: "You already have a hold on this item",
    ErrorCode.CANNOT_CHECKOUT: "This item can't be checked out right now",
    ErrorCode.CANNOT_RETURN: "This item can't be returned at this time",
    ErrorCode.CANNOT_PLACE_HOLD: "You can't place a hold on this item right now",
    ErrorCode.ITEM_NOT_AVAILABLE: "This item is not available at the moment",
    ErrorCode.ITEM_CHECKED_OUT: "This item is currently checked out",
    ErrorCode.ITEM_ON_HOLD: "This item is on hold for someone else",
    ErrorCode.PATRON_HAS_OUTSTANDING_FINE: "You have outstanding fines on your account. Please pay them at the circulation desk or online.",
    ErrorCode.PATRON_ACCOUNT_SUSPENDED: "Your account is currently suspended. Please contact the library to resolve this.",
    ErrorCode.PATRON_CARD_EXPIRED: "Your library card has expired. Visit the library with a valid ID to renew it.",

    # Business Logic
    ErrorCode.BUSINESS_LOGIC_ERROR: "Business logic error occurred",
    ErrorCode.OPERATION_NOT_ALLOWED: "This operation is not allowed",
    ErrorCode.INSUFFICIENT_INVENTORY: "Insufficient inventory to complete operation",
    ErrorCode.QUOTA_EXCEEDED: "Quota exceeded for this operation",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Too many requests. Please wait a moment and try again.",
    ErrorCode.INVALID_TRANSITION: "Invalid state transition requested",
    ErrorCode.CIRCULAR_DEPENDENCY: "Circular dependency detected",
    ErrorCode.ITEM_NOT_HOLDABLE: "This item is not currently available for hold",

    # System Errors
    ErrorCode.INTERNAL_ERROR: "An internal server error occurred",
    ErrorCode.DATABASE_ERROR: "Database operation failed",
    ErrorCode.SERVICE_UNAVAILABLE: "Service is temporarily unavailable",
    ErrorCode.TIMEOUT: "Request timed out",
    ErrorCode.EXTERNAL_SERVICE_ERROR: "External service error occurred",
    ErrorCode.CONFIGURATION_ERROR: "Configuration error occurred",
    ErrorCode.CACHE_ERROR: "Cache operation failed",
    ErrorCode.FILE_OPERATION_ERROR: "File operation failed",
    ErrorCode.EMAIL_SEND_ERROR: "Failed to send email",
}


def get_error_message(code: ErrorCode, default: str = None) -> str:
    return ERROR_MESSAGES.get(code, default or code.value)


# HTTP Status Code Mapping
ERROR_CODE_TO_STATUS: Dict[ErrorCode, int] = {
    # 400 Bad Request
    ErrorCode.VALIDATION_FAILED: 400,
    ErrorCode.INVALID_REQUEST_BODY: 400,
    ErrorCode.INVALID_PARAMETER: 400,
    ErrorCode.INVALID_EMAIL: 400,
    ErrorCode.INVALID_PASSWORD: 400,
    ErrorCode.INVALID_ISBN: 400,
    ErrorCode.INVALID_DATE: 400,
    ErrorCode.INVALID_ENUM: 400,
    ErrorCode.INVALID_JSON: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.FIELD_TOO_LONG: 400,
    ErrorCode.FIELD_TOO_SHORT: 400,

    # 401 Unauthorized
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.INVALID_CREDENTIALS: 401,
    ErrorCode.TOKEN_EXPIRED: 401,
    ErrorCode.TOKEN_INVALID: 401,
    ErrorCode.TOKEN_REVOKED: 401,
    ErrorCode.MFA_REQUIRED: 401,
    ErrorCode.MFA_INVALID: 401,
    ErrorCode.SESSION_EXPIRED: 401,

    # 403 Forbidden
    ErrorCode.INSUFFICIENT_PERMISSIONS: 403,
    ErrorCode.INSUFFICIENT_ROLE: 403,
    ErrorCode.RESOURCE_FORBIDDEN: 403,
    ErrorCode.OPERATION_FORBIDDEN: 403,
    ErrorCode.PATRON_BLOCKED: 403,
    ErrorCode.PATRON_DECEASED: 403,
    ErrorCode.STAFF_ONLY: 403,
    ErrorCode.ADMIN_ONLY: 403,

    # 404 Not Found
    ErrorCode.RESOURCE_NOT_FOUND: 404,
    ErrorCode.USER_NOT_FOUND: 404,
    ErrorCode.PATRON_NOT_FOUND: 404,
    ErrorCode.CATALOG_ITEM_NOT_FOUND: 404,
    ErrorCode.CHECKOUT_NOT_FOUND: 404,
    ErrorCode.HOLD_NOT_FOUND: 404,
    ErrorCode.FINE_NOT_FOUND: 404,
    ErrorCode.LEARNING_PATH_NOT_FOUND: 404,
    ErrorCode.EVENT_NOT_FOUND: 404,
    ErrorCode.READING_PROGRAM_NOT_FOUND: 404,
    ErrorCode.COLLECTION_NOT_FOUND: 404,
    ErrorCode.REPORT_NOT_FOUND: 404,

    # 409 Conflict
    ErrorCode.RESOURCE_ALREADY_EXISTS: 409,
    ErrorCode.DUPLICATE_OPERATION: 409,
    ErrorCode.INVALID_STATE: 409,
    ErrorCode.CHECKOUT_EXISTS: 409,
    ErrorCode.HOLD_EXISTS: 409,
    ErrorCode.CANNOT_CHECKOUT: 409,
    ErrorCode.CANNOT_RETURN: 409,
    ErrorCode.CANNOT_PLACE_HOLD: 409,
    ErrorCode.ITEM_NOT_AVAILABLE: 409,
    ErrorCode.ITEM_CHECKED_OUT: 409,
    ErrorCode.ITEM_ON_HOLD: 409,
    ErrorCode.PATRON_HAS_OUTSTANDING_FINE: 409,
    ErrorCode.PATRON_ACCOUNT_SUSPENDED: 403,  # Forbidden - patron not allowed to perform operation
    ErrorCode.PATRON_CARD_EXPIRED: 403,

    # 422 Unprocessable Entity
    ErrorCode.BUSINESS_LOGIC_ERROR: 422,
    ErrorCode.OPERATION_NOT_ALLOWED: 422,
    ErrorCode.INSUFFICIENT_INVENTORY: 422,
    ErrorCode.QUOTA_EXCEEDED: 422,
    ErrorCode.INVALID_TRANSITION: 422,
    ErrorCode.CIRCULAR_DEPENDENCY: 422,
    ErrorCode.ITEM_NOT_HOLDABLE: 422,
    ErrorCode.DUPLICATE_EMAIL: 422,
    ErrorCode.DUPLICATE_ISBN: 422,
    ErrorCode.DUPLICATE_BARCODE: 422,

    # 429 Too Many Requests
    ErrorCode.RATE_LIMIT_EXCEEDED: 429,

    # 500+ Server Errors
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.TIMEOUT: 504,
    ErrorCode.EXTERNAL_SERVICE_ERROR: 502,
    ErrorCode.CONFIGURATION_ERROR: 500,
    ErrorCode.CACHE_ERROR: 500,
    ErrorCode.FILE_OPERATION_ERROR: 500,
    ErrorCode.EMAIL_SEND_ERROR: 500,
}


def get_status_code(code: ErrorCode, default: int = 500) -> int:
    return ERROR_CODE_TO_STATUS.get(code, default)
