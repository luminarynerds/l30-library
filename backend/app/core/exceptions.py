# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Dict, List, Optional

from .error_codes import ErrorCode, get_error_message, get_status_code


class APIError(Exception):

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        self.code = code
        self.message = message or get_error_message(code)
        self.status_code = status_code or get_status_code(code)
        self.details = details
        self.headers = headers

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        error_dict: Dict[str, Any] = {
            "code": self.code.value,
            "message": self.message,
            "status_code": self.status_code,
        }

        if self.details:
            error_dict["details"] = self.details

        return error_dict


class ValidationError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.VALIDATION_FAILED,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=400,
            details=details,
            headers=headers,
        )


class ResourceNotFoundError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.RESOURCE_NOT_FOUND,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=404,
            headers=headers,
        )


class UnauthorizedError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.UNAUTHORIZED,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=401,
            headers=headers,
        )


class ForbiddenError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INSUFFICIENT_PERMISSIONS,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=403,
            details=details,
            headers=headers,
        )


class ConflictError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.RESOURCE_ALREADY_EXISTS,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=409,
            details=details,
            headers=headers,
        )


class BusinessLogicError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.BUSINESS_LOGIC_ERROR,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or get_error_message(code),
            status_code=422,
            details=details,
            headers=headers,
        )


class InternalServerError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or "An unexpected error occurred",
            status_code=500,
            headers=headers,
        )


class ServiceUnavailableError(APIError):

    def __init__(
        self,
        code: ErrorCode = ErrorCode.SERVICE_UNAVAILABLE,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=code,
            message=message or "Service is temporarily unavailable",
            status_code=503,
            headers=headers,
        )


class RateLimitError(APIError):

    def __init__(
        self,
        message: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ):
        super().__init__(
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            message=message or get_error_message(ErrorCode.RATE_LIMIT_EXCEEDED),
            status_code=429,
            headers=headers,
        )
