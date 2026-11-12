# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive unit tests for email service functions.

Tests cover:
- Email sending with Resend API
- CAN-SPAM compliance
- Email content generation
- Error handling (timeouts, network failures)
- Email templates and rendering
- Unsubscribe and preference URLs
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from app.core.email import (
    send_email,
    send_password_reset_email,
    send_verification_email,
    send_hold_ready_notification,
    get_can_spam_footer,
    get_physical_address,
    COLORS,
)
from app.core.config import get_settings


@pytest.mark.unit
class TestCanSpamFooter:
    """Test CAN-SPAM compliance footer generation."""

    def test_can_spam_footer_includes_physical_address(self):
        """Test that footer includes required physical address."""
        address = get_physical_address()
        footer = get_can_spam_footer(is_transactional=False)
        assert address["name"] in footer
        assert address["street"] in footer
        assert address["city"] in footer
        assert address["state"] in footer
        assert address["zip"] in footer
        assert address["country"] in footer

    def test_can_spam_footer_includes_unsubscribe_link(self):
        """Test that non-transactional emails include unsubscribe link."""
        unsubscribe_url = "https://example.com/unsubscribe"
        footer = get_can_spam_footer(unsubscribe_url=unsubscribe_url, is_transactional=False)
        assert unsubscribe_url in footer
        assert "Unsubscribe" in footer or "unsubscribe" in footer.lower()

    def test_can_spam_footer_omits_unsubscribe_for_transactional(self):
        """Test that transactional emails don't require unsubscribe link."""
        footer = get_can_spam_footer(is_transactional=True)
        assert "Unsubscribe" not in footer or "transactional" in footer.lower()

    def test_can_spam_footer_includes_preferences_link(self):
        """Test that footer includes preferences link when provided."""
        preferences_url = "https://example.com/preferences"
        footer = get_can_spam_footer(preferences_url=preferences_url, is_transactional=False)
        assert preferences_url in footer
        assert "preference" in footer.lower()

    def test_can_spam_footer_marks_transactional_emails(self):
        """Test that transactional emails are marked as such."""
        footer = get_can_spam_footer(is_transactional=True)
        assert "transactional" in footer.lower()

    def test_can_spam_footer_html_format(self):
        """Test that footer returns valid HTML."""
        footer = get_can_spam_footer()
        assert "<div" in footer
        assert "</div>" in footer
        assert "<table" in footer or "<p" in footer

    def test_can_spam_footer_copyright_notice(self):
        """Test that footer includes copyright notice."""
        _ = get_settings()
        footer = get_can_spam_footer()
        assert "©" in footer or "(c)" in footer.lower() or "copyright" in footer.lower()

    def test_can_spam_footer_respects_color_scheme(self):
        """Test that footer uses defined color scheme."""
        footer = get_can_spam_footer()
        # Should use colors from COLORS dict
        assert COLORS["heading"] in footer or COLORS["text_light"] in footer


@pytest.mark.unit
class TestSendEmail:
    """Test the generic send_email function."""

    @pytest.mark.asyncio
    async def test_send_email_without_api_key_configured(self):
        """Test that send_email returns True when no API key is configured."""
        with patch("app.core.email.settings") as mock_settings:
            mock_settings.resend_api_key = None
            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>"
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_builds_correct_payload(self):
        """Test that email payload is correctly constructed."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            await send_email(
                to_email="test@mockmail.dev",
                subject="Test Subject",
                html_content="<p>Test Content</p>"
            )

            # Verify post was called
            assert mock_post.called
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert payload["to"][0] == "test@mockmail.dev"
            assert payload["subject"] == "Test Subject"
            assert payload["html"] == "<p>Test Content</p>"

    @pytest.mark.asyncio
    async def test_send_email_includes_authorization_header(self):
        """Test that API key is included in Authorization header."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key-123"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>"
            )

            call_args = mock_post.call_args
            headers = call_args.kwargs["headers"]
            assert headers["Authorization"] == "Bearer test-key-123"
            assert headers["Content-Type"] == "application/json"

    @pytest.mark.asyncio
    async def test_send_email_handles_timeout(self):
        """Test that send_email handles httpx timeout gracefully."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_handles_request_error(self):
        """Test that send_email handles network errors gracefully."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.side_effect = httpx.RequestError("Network error")

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_with_attachment(self):
        """Test that email attachments are correctly encoded and included."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            attachment_data = b"PDF_CONTENT_HERE"

            await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
                attachment_data=attachment_data,
                attachment_filename="document.pdf"
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert "attachments" in payload
            assert payload["attachments"][0]["filename"] == "document.pdf"
            assert payload["attachments"][0]["content_type"] == "application/pdf"
            assert "content" in payload["attachments"][0]  # Base64 encoded

    @pytest.mark.asyncio
    async def test_send_email_with_list_unsubscribe_header(self):
        """Test that List-Unsubscribe header is included."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            unsubscribe_url = "https://example.com/unsubscribe"

            await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
                unsubscribe_url=unsubscribe_url
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert "headers" in payload
            assert "List-Unsubscribe" in payload["headers"]
            assert unsubscribe_url in payload["headers"]["List-Unsubscribe"]
            assert payload["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"

    @pytest.mark.asyncio
    async def test_send_email_with_categories(self):
        """Test that categories are included for analytics."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            categories = ["newsletter", "weekly-digest"]

            await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
                categories=categories
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert payload["tags"] == [{"name": c, "value": "1"} for c in categories]

    @pytest.mark.asyncio
    async def test_send_email_success_codes(self):
        """Test that 200, 201, and 202 status codes indicate success."""
        for status_code in [200, 201, 202]:
            with patch("app.core.email.settings") as mock_settings, \
                 patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_settings.resend_api_key = "test-key"
                mock_settings.resend_min_interval_s = 0
                mock_settings.from_email = "noreply@library.local"
                mock_settings.app_name = "Test Library"
                mock_post.return_value.status_code = status_code

                result = await send_email(
                    to_email="test@mockmail.dev",
                    subject="Test",
                    html_content="<p>Test</p>"
                )

                assert result is True

    @pytest.mark.asyncio
    async def test_send_email_failure_codes(self):
        """Test that non-success status codes indicate failure."""
        for status_code in [400, 401, 403, 429, 500, 503]:
            with patch("app.core.email.settings") as mock_settings, \
                 patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_settings.resend_api_key = "test-key"
                mock_settings.resend_min_interval_s = 0
                mock_settings.from_email = "noreply@library.local"
                mock_settings.app_name = "Test Library"
                mock_post.return_value.status_code = status_code

                result = await send_email(
                    to_email="test@mockmail.dev",
                    subject="Test",
                    html_content="<p>Test</p>"
                )

                assert result is False


@pytest.mark.unit
class TestPasswordResetEmail:
    """Test password reset email generation."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_includes_token(self):
        """Test that password reset email includes reset token."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            reset_token = "test-reset-token-12345"
            await send_password_reset_email(
                to_email="test@mockmail.dev",
                reset_token=reset_token,
                first_name="John"
            )

            # Verify send_email was called
            assert mock_send.called
            call_args = mock_send.call_args
            html_content = call_args.args[2]

            assert reset_token in html_content
            assert "reset-password" in html_content.lower()

    @pytest.mark.asyncio
    async def test_send_password_reset_email_includes_name(self):
        """Test that password reset email includes patron name."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_password_reset_email(
                to_email="test@mockmail.dev",
                reset_token="token",
                first_name="John"
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert "John" in html_content

    @pytest.mark.asyncio
    async def test_send_password_reset_email_includes_expiry_info(self):
        """Test that password reset email indicates token expiry."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_password_reset_email(
                to_email="test@mockmail.dev",
                reset_token="token",
                first_name="John"
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert "hour" in html_content.lower() or "1 hour" in html_content

    @pytest.mark.asyncio
    async def test_send_password_reset_email_subject(self):
        """Test that password reset email has appropriate subject."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_password_reset_email(
                to_email="test@mockmail.dev",
                reset_token="token",
                first_name="John"
            )

            call_args = mock_send.call_args
            subject = call_args.args[1]
            assert "password" in subject.lower() or "reset" in subject.lower()


@pytest.mark.unit
class TestVerificationEmail:
    """Test email verification email generation."""

    @pytest.mark.asyncio
    async def test_send_verification_email_includes_token(self):
        """Test that verification email includes token."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            verify_token = "test-verify-token-12345"
            await send_verification_email(
                to_email="test@mockmail.dev",
                verification_token=verify_token,
                first_name="John"
            )

            assert mock_send.called
            call_args = mock_send.call_args
            html_content = call_args.args[2]

            assert verify_token in html_content
            assert "verify" in html_content.lower()

    @pytest.mark.asyncio
    async def test_send_verification_email_welcome_message(self):
        """Test that verification email includes welcome message."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_verification_email(
                to_email="test@mockmail.dev",
                verification_token="token",
                first_name="John"
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert "welcome" in html_content.lower() or "verify" in html_content.lower()

    @pytest.mark.asyncio
    async def test_send_verification_email_subject(self):
        """Test that verification email has appropriate subject."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_verification_email(
                to_email="test@mockmail.dev",
                verification_token="token",
                first_name="John"
            )

            call_args = mock_send.call_args
            subject = call_args.args[1]
            assert "verify" in subject.lower() or "email" in subject.lower()


@pytest.mark.unit
class TestHoldReadyNotification:
    """Test hold ready notification email generation."""

    @pytest.mark.asyncio
    async def test_send_hold_ready_notification_includes_book_title(self):
        """Test that notification includes book title."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_hold_ready_notification(
                to_email="test@mockmail.dev",
                first_name="John",
                book_title="The Great Gatsby",
                book_author="F. Scott Fitzgerald",
                pickup_location="Main Library",
                expires_at="2026-03-17"
            )

            assert mock_send.called
            call_args = mock_send.call_args
            html_content = call_args.args[2]

            assert "The Great Gatsby" in html_content

    @pytest.mark.asyncio
    async def test_send_hold_ready_notification_includes_author(self):
        """Test that notification includes author information."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_hold_ready_notification(
                to_email="test@mockmail.dev",
                first_name="John",
                book_title="The Great Gatsby",
                book_author="F. Scott Fitzgerald",
                pickup_location="Main Library",
                expires_at="2026-03-17"
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert "F. Scott Fitzgerald" in html_content

    @pytest.mark.asyncio
    async def test_send_hold_ready_notification_handles_missing_author(self):
        """Test that notification works without author information."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_hold_ready_notification(
                to_email="test@mockmail.dev",
                first_name="John",
                book_title="The Great Gatsby",
                book_author=None,
                pickup_location="Main Library",
                expires_at="2026-03-17"
            )

            assert mock_send.called

    @pytest.mark.asyncio
    async def test_send_hold_ready_notification_includes_pickup_location(self):
        """Test that notification includes pickup location."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            await send_hold_ready_notification(
                to_email="test@mockmail.dev",
                first_name="John",
                book_title="The Great Gatsby",
                book_author="F. Scott Fitzgerald",
                pickup_location="Downtown Branch",
                expires_at="2026-03-17"
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert "Downtown Branch" in html_content

    @pytest.mark.asyncio
    async def test_send_hold_ready_notification_includes_expiry_date(self):
        """Test that notification includes expiry/pickup deadline."""
        with patch("app.core.email.send_email", new_callable=AsyncMock) as mock_send, \
             patch("app.core.email.settings") as mock_settings:
            mock_send.return_value = True
            mock_settings.frontend_url = "https://library.local"

            expiry_date = "2026-03-17"
            await send_hold_ready_notification(
                to_email="test@mockmail.dev",
                first_name="John",
                book_title="The Great Gatsby",
                book_author="F. Scott Fitzgerald",
                pickup_location="Main Library",
                expires_at=expiry_date
            )

            call_args = mock_send.call_args
            html_content = call_args.args[2]
            assert expiry_date in html_content


@pytest.mark.unit
class TestEmailSecurityAndCompliance:
    """Test security and compliance features of email service."""

    def test_colors_dictionary_complete(self):
        """Test that COLORS dictionary has all required color definitions."""
        required_colors = ["heading", "body", "button", "button_hover", "border", "divider", "text_light"]
        for color in required_colors:
            assert color in COLORS
            assert isinstance(COLORS[color], str)
            assert COLORS[color].startswith("#")

    def test_physical_address_complete(self):
        """Test that get_physical_address() returns all CAN-SPAM required fields, non-empty."""
        address = get_physical_address()
        required_fields = ["name", "street", "city", "state", "zip", "country"]
        for field in required_fields:
            assert field in address
            # Empty here = CAN-SPAM compliance gap; fix branding.json, not this assertion.
            assert address[field], f"branding produced empty {field}; emails will have an incomplete sender address"

    @pytest.mark.asyncio
    async def test_send_email_handles_encoding_errors(self):
        """Test that send_email handles encoding errors gracefully."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.side_effect = ValueError("Encoding error")

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>"
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_sanitizes_recipient_email(self):
        """Test that recipient email addresses are properly handled."""
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "test-key"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_post.return_value.status_code = 202

            recipient = "test+tag@mockmail.dev"

            await send_email(
                to_email=recipient,
                subject="Test",
                html_content="<p>Test</p>"
            )

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["to"][0] == recipient


@pytest.mark.unit
class TestSendEmailBodyInspection:
    """Test that 2xx responses with error bodies are detected as failures.

    Resend can return a 2xx status code with a JSON body that signals
    failure (rarer but possible). A status-only check therefore silently
    swallows real send failures. Send-side callers retry on False; without this detection,
    transactional email can fail without any visible signal.
    """

    @pytest.mark.asyncio
    async def test_returns_false_on_200_with_errors_array(self):
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = None
            mock_settings.resend_api_key = "sg-test"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_settings.environment = "production"

            mock_post.return_value.status_code = 200
            mock_post.return_value.json = MagicMock(
                return_value={"errors": [{"message": "Invalid sender domain"}]}
            )
            mock_post.return_value.text = '{"errors":[{"message":"Invalid sender domain"}]}'

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_on_resend_200_with_embedded_4xx_statusCode(self):
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "re-test"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_settings.environment = "production"

            mock_post.return_value.status_code = 200
            mock_post.return_value.json = MagicMock(
                return_value={
                    "statusCode": 422,
                    "name": "validation_error",
                    "message": "Missing required field",
                }
            )
            mock_post.return_value.text = (
                '{"statusCode":422,"name":"validation_error","message":"Missing required field"}'
            )

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_on_resend_200_with_id(self):
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = "re-test"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_settings.environment = "production"

            mock_post.return_value.status_code = 200
            mock_post.return_value.json = MagicMock(
                return_value={"id": "550e8400-e29b-41d4-a716-446655440000"}
            )
            mock_post.return_value.text = '{"id":"550e8400-e29b-41d4-a716-446655440000"}'

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_on_202_with_empty_body(self):
        with patch("app.core.email.settings") as mock_settings, \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_settings.resend_api_key = None
            mock_settings.resend_api_key = "sg-test"
            mock_settings.resend_min_interval_s = 0
            mock_settings.from_email = "noreply@library.local"
            mock_settings.app_name = "Test Library"
            mock_settings.environment = "production"

            mock_post.return_value.status_code = 202
            mock_post.return_value.json = MagicMock(side_effect=ValueError("empty body"))
            mock_post.return_value.text = ""

            result = await send_email(
                to_email="test@mockmail.dev",
                subject="Test",
                html_content="<p>Test</p>",
            )

            assert result is True
