# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import functools
from typing import Callable, Optional, Any, TypeVar, Union
from fastapi import HTTPException, status

from .exceptions import APIError

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def handle_service_errors(
    message: Optional[str] = None,
    status_code: Optional[int] = None,
    log_level: str = "error",
) -> Callable[[F], F]:

    def decorator(func: F) -> F:

        # Check if function is async
        if asyncio_iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return await func(*args, **kwargs)
                except HTTPException:
                    # Re-raise HTTPException as-is
                    raise
                except APIError as e:
                    # Convert APIError to HTTPException
                    _log_api_error(func.__name__, e, log_level)
                    raise HTTPException(
                        status_code=e.status_code,
                        detail=e.message,
                        headers=e.headers,
                    ) from e
                except Exception as e:
                    # Catch generic exceptions
                    _log_generic_error(func.__name__, e, log_level)
                    http_status = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
                    error_message = message or "An unexpected error occurred"
                    raise HTTPException(
                        status_code=http_status,
                        detail=error_message,
                    ) from e

            return async_wrapper  # type: ignore

        else:
            # Sync version
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                try:
                    return func(*args, **kwargs)
                except HTTPException:
                    # Re-raise HTTPException as-is
                    raise
                except APIError as e:
                    # Convert APIError to HTTPException
                    _log_api_error(func.__name__, e, log_level)
                    raise HTTPException(
                        status_code=e.status_code,
                        detail=e.message,
                        headers=e.headers,
                    ) from e
                except Exception as e:
                    # Catch generic exceptions
                    _log_generic_error(func.__name__, e, log_level)
                    http_status = status_code or status.HTTP_500_INTERNAL_SERVER_ERROR
                    error_message = message or "An unexpected error occurred"
                    raise HTTPException(
                        status_code=http_status,
                        detail=error_message,
                    ) from e

            return sync_wrapper  # type: ignore

    return decorator


def _log_api_error(
    func_name: str,
    error: APIError,
    log_level: str = "error",
) -> None:
    log_func = getattr(logger, log_level, logger.error)
    log_func(
        f"API error in {func_name}",
        extra={
            "error_code": error.code.value if hasattr(error.code, "value") else str(error.code),
            "status_code": error.status_code,
            "message": error.message,
            "details": error.details,
        },
    )


def _log_generic_error(
    func_name: str,
    error: Exception,
    log_level: str = "error",
) -> None:
    log_func = getattr(logger, log_level, logger.error)
    log_func(
        f"Unhandled exception in {func_name}",
        exc_info=True,
        extra={
            "error_type": error.__class__.__name__,
            "error_message": str(error),
        },
    )


# Import asyncio for checking if function is coroutine
import asyncio


def asyncio_iscoroutinefunction(func: Any) -> bool:
    return asyncio.iscoroutinefunction(func)
