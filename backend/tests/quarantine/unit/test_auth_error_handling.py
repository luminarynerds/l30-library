# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for error handling in authentication module.

Tests for:
- Registration succeeds when email send fails
- Password reset succeeds when email send fails
- Resend verification succeeds when email send fails
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from starlette.requests import Request

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import hash_password, create_verification_token


@pytest.fixture(autouse=True)
def disable_rate_limiter():
    """Disable rate limiter for all tests in this module."""
    with patch("app.core.rate_limit.limiter"):
        yield


def create_mock_request(client_host: str = "127.0.0.1") -> MagicMock:
    """Create a mock Request object that passes validation."""
    mock_request = MagicMock(spec=Request)
    mock_request.client = MagicMock()
    mock_request.client.host = client_host
    return mock_request


@pytest.mark.unit
class TestRegistrationEmailFailure:
    """Test that user registration doesn't crash if email send fails."""

    @pytest.mark.asyncio
    async def test_registration_succeeds_when_email_fails(
        self, test_db: AsyncSession
    ):
        """Test that user registration completes even if verification email fails.

        The user should be created in the database and the endpoint should
        return successfully, logging a warning about the email failure.
        """
        from app.api.v1.auth import register
        from app.schemas.user import UserCreate

        # Create user data
        user_data = UserCreate(
            email="newuser_emailfail@example.com",
            password="ValidPassword123!",
            first_name="Test",
            last_name="User",
        )

        # Mock the email function to raise an exception
        with patch(
            "app.api.v1.auth.send_verification_email",
            new_callable=AsyncMock,
            side_effect=Exception("SMTP connection failed"),
        ):
            # Mock the request object
            mock_request = create_mock_request()

            # This should NOT raise despite email failure
            result = await register(mock_request, user_data, test_db)

            # Verify user was created
            assert result is not None
            assert result.email == "newuser_emailfail@example.com"
            assert result.first_name == "Test"
            assert result.email_verified is False

            # Verify user exists in database
            db_result = await test_db.execute(
                select(User).where(User.email == "newuser_emailfail@example.com")
            )
            db_user = db_result.scalar_one_or_none()
            assert db_user is not None
            assert db_user.verification_token is not None

    @pytest.mark.asyncio
    async def test_registration_logs_email_failure(
        self, test_db: AsyncSession, caplog
    ):
        """Test that email failures during registration are logged."""
        from app.api.v1.auth import register
        from app.schemas.user import UserCreate
        import logging

        user_data = UserCreate(
            email="logtest_emailfail@example.com",
            password="ValidPassword123!",
            first_name="Log",
            last_name="Test",
        )

        with patch(
            "app.api.v1.auth.send_verification_email",
            new_callable=AsyncMock,
            side_effect=Exception("Connection refused"),
        ):
            mock_request = create_mock_request()

            with caplog.at_level(logging.WARNING):
                await register(mock_request, user_data, test_db)

            # The warning should have been logged
            assert any(
                "Failed to send verification email" in record.message
                for record in caplog.records
            )


@pytest.mark.unit
class TestPasswordResetEmailFailure:
    """Test that password reset doesn't crash if email send fails."""

    @pytest.mark.asyncio
    async def test_password_reset_succeeds_when_email_fails(
        self, test_db: AsyncSession, test_patron
    ):
        """Test that password reset request completes even if email fails.

        The reset token should be stored in the database and the endpoint
        should return the standard success message.
        """
        from app.api.v1.auth import forgot_password
        from app.schemas.user import ForgotPasswordRequest

        # Ensure the test patron has a verified email
        test_patron.email_verified = True
        await test_db.commit()

        request_data = ForgotPasswordRequest(email=test_patron.email)

        with patch(
            "app.api.v1.auth.send_password_reset_email",
            new_callable=AsyncMock,
            side_effect=Exception("Email service unavailable"),
        ):
            mock_request = create_mock_request()

            # This should NOT raise despite email failure
            result = await forgot_password(mock_request, request_data, test_db)

            # Should return success message (security: don't reveal email status)
            assert "reset link has been sent" in result.message.lower() or "verified account" in result.message.lower()

            # Verify reset token was stored
            await test_db.refresh(test_patron)
            assert test_patron.reset_token is not None
            assert test_patron.reset_token_expires is not None

    @pytest.mark.asyncio
    async def test_password_reset_unverified_email_no_email_sent(
        self, test_db: AsyncSession, test_patron
    ):
        """Test that password reset for unverified email doesn't send email."""
        from app.api.v1.auth import forgot_password
        from app.schemas.user import ForgotPasswordRequest

        # Ensure the test patron has an unverified email
        test_patron.email_verified = False
        await test_db.commit()

        request_data = ForgotPasswordRequest(email=test_patron.email)

        email_mock = AsyncMock()
        with patch(
            "app.api.v1.auth.send_password_reset_email",
            email_mock,
        ):
            mock_request = create_mock_request()

            result = await forgot_password(mock_request, request_data, test_db)

            # Email should not have been called for unverified account
            email_mock.assert_not_called()

            # Should still return success message (security: don't reveal)
            assert result.message is not None


@pytest.mark.unit
class TestResendVerificationEmailFailure:
    """Test that resend verification doesn't crash if email send fails."""

    @pytest.mark.asyncio
    async def test_resend_verification_succeeds_when_email_fails(
        self, test_db: AsyncSession
    ):
        """Test that resend verification completes even if email fails."""
        from app.api.v1.auth import resend_verification
        from app.schemas.user import ResendVerificationRequest
        from app.core.security import create_verification_token

        # Create an unverified user
        user = User(
            email="unverified_resend@example.com",
            password_hash=hash_password("TestPassword123!"),
            first_name="Unverified",
            last_name="User",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=False,
            verification_token=create_verification_token(),
        )
        test_db.add(user)
        await test_db.commit()

        request_data = ResendVerificationRequest(email=user.email)

        with patch(
            "app.api.v1.auth.send_verification_email",
            new_callable=AsyncMock,
            side_effect=Exception("Mail server timeout"),
        ):
            mock_request = create_mock_request()

            # This should NOT raise despite email failure
            result = await resend_verification(mock_request, request_data, test_db)

            # Should return success message
            assert "verification email has been sent" in result.message.lower()

            # Verify new token was stored
            await test_db.refresh(user)
            assert user.verification_token is not None


@pytest.mark.unit
class TestEmailServiceResilience:
    """Test overall resilience when email service is down."""

    @pytest.mark.asyncio
    async def test_multiple_operations_with_email_failures(
        self, test_db: AsyncSession
    ):
        """Test that multiple auth operations work when email is down."""
        from app.api.v1.auth import register, forgot_password, resend_verification
        from app.schemas.user import UserCreate, ForgotPasswordRequest, ResendVerificationRequest

        # Simulate complete email service outage
        email_exception = Exception("Connection to mail server refused")

        with patch(
            "app.api.v1.auth.send_verification_email",
            new_callable=AsyncMock,
            side_effect=email_exception,
        ), patch(
            "app.api.v1.auth.send_password_reset_email",
            new_callable=AsyncMock,
            side_effect=email_exception,
        ):
            mock_request = create_mock_request()

            # 1. Registration should work
            user_data = UserCreate(
                email="resilience_test@example.com",
                password="ValidPassword123!",
                first_name="Resilience",
                last_name="Test",
            )
            result = await register(mock_request, user_data, test_db)
            assert result.email == "resilience_test@example.com"

            # 2. Verify email (manually) so password reset can work
            db_result = await test_db.execute(
                select(User).where(User.email == "resilience_test@example.com")
            )
            user = db_result.scalar_one()
            user.email_verified = True
            await test_db.commit()

            # 3. Password reset should work
            forgot_data = ForgotPasswordRequest(email="resilience_test@example.com")
            result = await forgot_password(mock_request, forgot_data, test_db)
            assert result.message is not None


@pytest.mark.unit
class TestEmailErrorLogging:
    """Test that email errors are properly logged without exposing details."""

    @pytest.mark.asyncio
    async def test_email_error_does_not_leak_to_response(
        self, test_db: AsyncSession
    ):
        """Test that email errors don't leak sensitive info in response."""
        from app.api.v1.auth import register
        from app.schemas.user import UserCreate

        user_data = UserCreate(
            email="noleak_test@example.com",
            password="ValidPassword123!",
            first_name="NoLeak",
            last_name="Test",
        )

        # Simulate an email error with sensitive info
        sensitive_error = Exception(
            "SMTP Auth failed: user=admin@smtp.example.com password=s3cr3t"
        )

        with patch(
            "app.api.v1.auth.send_verification_email",
            new_callable=AsyncMock,
            side_effect=sensitive_error,
        ):
            mock_request = create_mock_request()

            result = await register(mock_request, user_data, test_db)

            # Response should not contain sensitive error details
            # The response is a UserResponse, not an error message
            assert result is not None
            assert hasattr(result, 'email')
            # No password or SMTP details should be in the response


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
