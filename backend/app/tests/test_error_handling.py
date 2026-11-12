# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive tests for API error handling and response formatting.

Tests cover:
- Error response format consistency
- Error codes and HTTP status mappings
- Validation error details
- Custom exception classes
- Exception handler behavior
"""

import pytest
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from ..core.error_codes import ErrorCode, get_error_message, get_status_code
from ..core.exceptions import (
    APIError,
    ValidationError,
    ResourceNotFoundError,
    UnauthorizedError,
    ForbiddenError,
    ConflictError,
    BusinessLogicError,
    InternalServerError,
)


# ============================================================================
# Test Fixtures
# ============================================================================


class TestRequest(BaseModel):
    """Test request schema with validation."""
    email: str = Field(..., description="Valid email")
    name: str = Field(..., min_length=1, max_length=100, description="User name")
    age: int = Field(..., ge=0, le=150, description="User age")


@pytest.fixture
def test_app():
    """Create a test FastAPI application with error handlers."""
    app = FastAPI()

    # Import exception handlers. api_error_handler/http_exception_handler/
    # validation_exception_handler are re-exported through app.main; the
    # catch-all unhandled_exception_handler is only defined on
    # core.exception_handlers and was never imported into app.main.
    from ..main import (
        api_error_handler,
        http_exception_handler,
        validation_exception_handler,
    )
    from ..core.exception_handlers import unhandled_exception_handler

    app.add_exception_handler(APIError, api_error_handler)
    from fastapi.exceptions import RequestValidationError
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
    from starlette.exceptions import HTTPException as StarletteHTTPException
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Test endpoints
    @app.post("/test/validation")
    async def test_validation_error(request: TestRequest):
        return {"data": request}

    @app.get("/test/not-found")
    async def test_not_found():
        raise ResourceNotFoundError(code=ErrorCode.USER_NOT_FOUND)

    @app.get("/test/unauthorized")
    async def test_unauthorized():
        raise UnauthorizedError(code=ErrorCode.TOKEN_EXPIRED)

    @app.get("/test/forbidden")
    async def test_forbidden():
        raise ForbiddenError(code=ErrorCode.INSUFFICIENT_PERMISSIONS)

    @app.get("/test/conflict")
    async def test_conflict():
        raise ConflictError(
            code=ErrorCode.DUPLICATE_EMAIL,
            message="This email is already registered"
        )

    @app.get("/test/business-logic")
    async def test_business_logic():
        raise BusinessLogicError(
            code=ErrorCode.CANNOT_CHECKOUT,
            details=[{"reason": "Item not available"}]
        )

    @app.get("/test/internal-error")
    async def test_internal_error():
        raise InternalServerError(code=ErrorCode.DATABASE_ERROR)

    @app.get("/test/unhandled")
    async def test_unhandled():
        raise ValueError("Simulated unhandled error")

    return app


@pytest.fixture
def client(test_app):
    """Create a test client.

    raise_server_exceptions=False: the default (True) makes TestClient
    re-raise any exception that reaches Starlette's ServerErrorMiddleware
    instead of returning the handler's JSON response, which broke every
    test exercising the /test/unhandled endpoint (it raises a bare
    ValueError specifically to exercise unhandled_exception_handler).
    """
    return TestClient(test_app, raise_server_exceptions=False)


# ============================================================================
# Tests for Error Code Registry
# ============================================================================


class TestErrorCodeRegistry:
    """Test error code definitions and mappings."""

    def test_all_error_codes_have_messages(self):
        """Verify all error codes have messages defined."""
        from ..core.error_codes import ERROR_MESSAGES

        for code in ErrorCode:
            assert code in ERROR_MESSAGES, f"No message for {code}"
            assert len(ERROR_MESSAGES[code]) > 0, f"Empty message for {code}"

    def test_all_error_codes_have_status_codes(self):
        """Verify all error codes have status code mappings."""
        from ..core.error_codes import ERROR_CODE_TO_STATUS

        for code in ErrorCode:
            assert code in ERROR_CODE_TO_STATUS, f"No status code for {code}"
            status = ERROR_CODE_TO_STATUS[code]
            assert 400 <= status <= 599, f"Invalid status code {status} for {code}"

    def test_get_error_message_function(self):
        """Test error message retrieval."""
        msg = get_error_message(ErrorCode.USER_NOT_FOUND)
        assert msg == "We couldn't find that account"

        msg = get_error_message(ErrorCode.UNAUTHORIZED)
        assert msg == "Authentication required"

    def test_get_status_code_function(self):
        """Test status code retrieval."""
        assert get_status_code(ErrorCode.USER_NOT_FOUND) == 404
        assert get_status_code(ErrorCode.UNAUTHORIZED) == 401
        assert get_status_code(ErrorCode.INSUFFICIENT_PERMISSIONS) == 403
        assert get_status_code(ErrorCode.DATABASE_ERROR) == 500

    def test_validation_errors_map_to_400(self):
        """Verify all validation errors map to 400."""
        validation_codes = [
            ErrorCode.VALIDATION_FAILED,
            ErrorCode.INVALID_EMAIL,
            ErrorCode.MISSING_REQUIRED_FIELD,
        ]
        for code in validation_codes:
            assert get_status_code(code) == 400

    def test_not_found_errors_map_to_404(self):
        """Verify all not found errors map to 404."""
        not_found_codes = [
            ErrorCode.USER_NOT_FOUND,
            ErrorCode.CATALOG_ITEM_NOT_FOUND,
            ErrorCode.HOLD_NOT_FOUND,
        ]
        for code in not_found_codes:
            assert get_status_code(code) == 404

    def test_conflict_errors_map_to_409(self):
        """Verify conflict errors map to 409.

        DUPLICATE_EMAIL is intentionally excluded: it now maps to 422 (see
        ERROR_CODE_TO_STATUS in error_codes.py) as part of the friendlier
        signup-error rewrite. ConflictError still forces status_code=409
        when raised directly with that code (see test_conflict_error).
        """
        conflict_codes = [
            ErrorCode.RESOURCE_ALREADY_EXISTS,
            ErrorCode.ITEM_CHECKED_OUT,
        ]
        for code in conflict_codes:
            assert get_status_code(code) == 409

        assert get_status_code(ErrorCode.DUPLICATE_EMAIL) == 422


# ============================================================================
# Tests for Exception Classes
# ============================================================================


class TestExceptionClasses:
    """Test custom exception classes."""

    def test_api_error_base_class(self):
        """Test basic APIError functionality."""
        error = APIError(code=ErrorCode.USER_NOT_FOUND)
        assert error.code == ErrorCode.USER_NOT_FOUND
        assert error.message == "We couldn't find that account"
        assert error.status_code == 404
        assert error.details is None

    def test_api_error_with_custom_message(self):
        """Test APIError with custom message."""
        error = APIError(
            code=ErrorCode.USER_NOT_FOUND,
            message="Custom user not found message"
        )
        assert error.message == "Custom user not found message"

    def test_api_error_with_details(self):
        """Test APIError with validation details."""
        details = [
            {"field": "email", "message": "Invalid format"}
        ]
        error = APIError(
            code=ErrorCode.VALIDATION_FAILED,
            details=details
        )
        assert error.details == details

    def test_api_error_to_dict(self):
        """Test APIError serialization to dict."""
        error = APIError(code=ErrorCode.USER_NOT_FOUND)
        error_dict = error.to_dict()
        assert error_dict["code"] == "USER_NOT_FOUND"
        assert error_dict["message"] == "We couldn't find that account"
        assert error_dict["status_code"] == 404

    def test_validation_error(self):
        """Test ValidationError class."""
        error = ValidationError(
            code=ErrorCode.INVALID_EMAIL,
            details=[{"field": "email", "message": "Invalid format"}]
        )
        assert error.status_code == 400
        assert error.code == ErrorCode.INVALID_EMAIL

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError class."""
        error = ResourceNotFoundError(code=ErrorCode.CATALOG_ITEM_NOT_FOUND)
        assert error.status_code == 404
        assert error.code == ErrorCode.CATALOG_ITEM_NOT_FOUND

    def test_unauthorized_error(self):
        """Test UnauthorizedError class."""
        error = UnauthorizedError(code=ErrorCode.TOKEN_EXPIRED)
        assert error.status_code == 401
        assert error.code == ErrorCode.TOKEN_EXPIRED

    def test_forbidden_error(self):
        """Test ForbiddenError class."""
        error = ForbiddenError(code=ErrorCode.INSUFFICIENT_PERMISSIONS)
        assert error.status_code == 403
        assert error.code == ErrorCode.INSUFFICIENT_PERMISSIONS

    def test_conflict_error(self):
        """Test ConflictError class."""
        error = ConflictError(code=ErrorCode.DUPLICATE_EMAIL)
        assert error.status_code == 409
        assert error.code == ErrorCode.DUPLICATE_EMAIL

    def test_business_logic_error(self):
        """Test BusinessLogicError class."""
        error = BusinessLogicError(code=ErrorCode.CANNOT_CHECKOUT)
        assert error.status_code == 422
        assert error.code == ErrorCode.CANNOT_CHECKOUT

    def test_internal_server_error(self):
        """Test InternalServerError class."""
        error = InternalServerError(code=ErrorCode.DATABASE_ERROR)
        assert error.status_code == 500
        assert error.code == ErrorCode.DATABASE_ERROR


# ============================================================================
# Tests for Error Response Format
# ============================================================================


class TestErrorResponseFormat:
    """Test that error responses have consistent format.

    Two envelopes are live in production, per app/main.py's registration:
    - APIError (and subclasses) -> app.main.api_error_handler -> flat
      {"detail": ..., "code": ..., ["details": [...]]}. No "error" wrapper,
      no status_code/timestamp/request_id in the body.
    - RequestValidationError / bare Exception -> the handlers in
      app.core.exception_handlers -> {"error": {"code", "message",
      "request_id", ["details"]}}.
    """

    def test_not_found_error_response_format(self, client):
        """Test 404 error response format."""
        response = client.get("/test/not-found")
        assert response.status_code == 404

        data = response.json()
        assert data["code"] == "USER_NOT_FOUND"
        assert data["detail"] == "We couldn't find that account"

    def test_unauthorized_error_response_format(self, client):
        """Test 401 error response format."""
        response = client.get("/test/unauthorized")
        assert response.status_code == 401

        data = response.json()
        assert data["code"] == "TOKEN_EXPIRED"

    def test_forbidden_error_response_format(self, client):
        """Test 403 error response format."""
        response = client.get("/test/forbidden")
        assert response.status_code == 403

        data = response.json()
        assert data["code"] == "INSUFFICIENT_PERMISSIONS"

    def test_conflict_error_response_format(self, client):
        """Test 409 error response format."""
        response = client.get("/test/conflict")
        assert response.status_code == 409

        data = response.json()
        assert data["code"] == "DUPLICATE_EMAIL"
        assert data["detail"] == "This email is already registered"

    def test_business_logic_error_response_format(self, client):
        """Test 422 error response format."""
        response = client.get("/test/business-logic")
        assert response.status_code == 422

        data = response.json()
        assert data["code"] == "CANNOT_CHECKOUT"
        assert "details" in data
        assert len(data["details"]) > 0

    def test_internal_error_response_format(self, client):
        """Test 500 error response format."""
        response = client.get("/test/internal-error")
        assert response.status_code == 500

        data = response.json()
        assert data["code"] == "DATABASE_ERROR"

    def test_unhandled_error_response_format(self, client):
        """Test unhandled exception response format."""
        response = client.get("/test/unhandled")
        assert response.status_code == 500

        data = response.json()
        error = data["error"]
        assert error["code"] == "INTERNAL_ERROR"
        # Generic message should not expose details
        assert "unexpected" in error["message"].lower()

    def test_validation_error_response_format(self, client):
        """Test validation error response format."""
        response = client.post("/test/validation", json={})
        assert response.status_code == 422

        data = response.json()
        error = data["error"]
        assert error["code"] == "VALIDATION_ERROR"
        assert "details" in error
        assert len(error["details"]) > 0

        # Check detail structure
        for detail in error["details"]:
            assert "field" in detail
            assert "message" in detail
            assert "type" in detail

    def test_validation_error_with_invalid_data(self, client):
        """Test validation error with specific validation failures."""
        invalid_data = {
            "email": "not-an-email",
            "name": "",  # Empty name
            "age": 200  # Too old
        }
        response = client.post("/test/validation", json=invalid_data)
        assert response.status_code == 422

        data = response.json()
        error = data["error"]
        details = error["details"]

        # Should have error details for validation failures
        assert len(details) > 0
        # validation_exception_handler joins pydantic's error `loc` tuple
        # with dots, so a body field comes through as "body.email", not
        # "email" -- compare the last path segment instead of the whole
        # dotted string.
        field_names = {d["field"].rsplit(".", 1)[-1] for d in details}
        # At least some of the invalid fields should be mentioned
        assert any(field in field_names for field in ["email", "name", "age"])


# ============================================================================
# Tests for Request ID Tracking
# ============================================================================


class TestRequestIDTracking:
    """Test that request IDs are included in error responses.

    request_id propagation lives in app.core.exception_handlers only;
    app.main.api_error_handler (used for APIError/not-found) doesn't read
    or emit it, so these use the /test/unhandled endpoint, which goes
    through core.exception_handlers.unhandled_exception_handler.
    """

    def test_request_id_included_in_error_response(self, client):
        """Test that request ID is included in error response."""
        request_id = "test-req-12345"
        response = client.get(
            "/test/unhandled",
            headers={"x-request-id": request_id}
        )

        data = response.json()
        error = data["error"]
        assert "request_id" in error
        assert error["request_id"] == request_id

    def test_request_id_in_response_header(self, client):
        """Test that request ID is included in response header."""
        request_id = "test-req-67890"
        response = client.get(
            "/test/unhandled",
            headers={"x-request-id": request_id}
        )

        assert "x-request-id" in response.headers
        assert response.headers["x-request-id"] == request_id


# ============================================================================
# Tests for Error Response HTTP Status Codes
# ============================================================================


class TestErrorStatusCodes:
    """Test that correct HTTP status codes are returned."""

    def test_validation_error_status_code(self, client):
        """Test 400 status code for validation errors."""
        response = client.post("/test/validation", json={})
        assert response.status_code == 422  # Schema validation returns 422

    def test_not_found_status_code(self, client):
        """Test 404 status code for not found errors."""
        response = client.get("/test/not-found")
        assert response.status_code == 404

    def test_unauthorized_status_code(self, client):
        """Test 401 status code for unauthorized errors."""
        response = client.get("/test/unauthorized")
        assert response.status_code == 401

    def test_forbidden_status_code(self, client):
        """Test 403 status code for forbidden errors."""
        response = client.get("/test/forbidden")
        assert response.status_code == 403

    def test_conflict_status_code(self, client):
        """Test 409 status code for conflict errors."""
        response = client.get("/test/conflict")
        assert response.status_code == 409

    def test_business_logic_error_status_code(self, client):
        """Test 422 status code for business logic errors."""
        response = client.get("/test/business-logic")
        assert response.status_code == 422

    def test_internal_error_status_code(self, client):
        """Test 500 status code for internal errors."""
        response = client.get("/test/internal-error")
        assert response.status_code == 500


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
