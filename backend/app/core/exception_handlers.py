# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import sentry_sdk
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .exceptions import APIError
from .logging import get_logger

logger = get_logger(__name__)


def _get_request_id(request: Request) -> str:
    state_id = getattr(request.state, "request_id", None) if hasattr(request, "state") else None
    if state_id:
        return state_id
    return request.headers.get("x-request-id", "")


async def api_error_handler(request: Request, exc: APIError):
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code.value,
                "message": exc.message,
                "request_id": request_id,
                **({"details": exc.details} if exc.details else {}),
            }
        },
        headers={
            "X-Request-ID": request_id,
            **(exc.headers or {}),
        } if request_id or exc.headers else None,
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = _get_request_id(request)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": exc.detail,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = _get_request_id(request)
    # Extract field errors without exposing internal details
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error.get("loc", []))
        errors.append({
            "field": field,
            "message": error.get("msg", "Invalid value"),
            "type": error.get("type", "validation_error"),
        })

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": errors,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _get_request_id(request)

    # Log the full exception for debugging
    logger.error(
        "Unhandled exception",
        exc_info=True,
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_type": type(exc).__name__,
        },
    )

    # Report to Sentry
    sentry_sdk.capture_exception(exc)

    # Return generic error to avoid leaking internal details
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id} if request_id else None,
    )
