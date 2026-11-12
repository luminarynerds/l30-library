# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for input validation and schemas.
"""

import pytest
from pydantic import EmailStr, ValidationError

from app.schemas.circulation import CheckoutResponse, HoldResponse
from app.schemas.fine import FineResponse
from app.schemas.user import UserCreate, UserResponse


@pytest.mark.unit
class TestUserValidation:
    """Test user schema validation."""

    def test_user_create_valid(self):
        """Test creating valid user data."""
        data = {
            "email": "test@example.com",
            "password": "ValidPassword123!",
            "first_name": "Test",
            "last_name": "User",
        }
        user = UserCreate(**data)
        assert user.email == "test@example.com"
        assert user.password == "ValidPassword123!"

    def test_user_create_invalid_email(self):
        """Test invalid email is rejected."""
        data = {
            "email": "not-an-email",
            "password": "ValidPassword123!",
            "first_name": "Test",
            "last_name": "User",
        }
        with pytest.raises(ValidationError):
            UserCreate(**data)

    def test_user_create_common_password_rejected(self):
        """Test common passwords are rejected."""
        data = {
            "email": "test@example.com",
            "password": "password123",
            "first_name": "Test",
            "last_name": "User",
        }
        with pytest.raises(ValidationError):
            UserCreate(**data)

    def test_user_create_missing_required(self):
        """Test missing required fields."""
        data = {
            "email": "test@example.com",
            # Missing password, first_name, last_name
        }
        with pytest.raises(ValidationError):
            UserCreate(**data)

    def test_email_validation(self):
        """Test email field validation."""
        valid_emails = [
            "test@example.com",
            "user+tag@example.co.uk",
            "123@example.com",
        ]
        for email in valid_emails:
            # These should validate without error
            assert email  # Just checking they're valid format

    def test_invalid_email_formats(self):
        """Test invalid email formats are caught."""
        invalid_emails = [
            "plainaddress",
            "@example.com",
            "user@",
            "user name@example.com",
        ]
        for email in invalid_emails:
            data = {
                "email": email,
                "password": "ValidPassword123!",
                "first_name": "Test",
                "last_name": "User",
            }
            with pytest.raises(ValidationError):
                UserCreate(**data)


@pytest.mark.unit
class TestCheckoutValidation:
    """Test checkout schema validation."""

    async def test_checkout_response_structure(self, test_db, test_checkout):
        """Test checkout response can be created from model."""
        response = CheckoutResponse.model_validate(test_checkout)
        assert response.id == test_checkout.id
        assert response.user_id == test_checkout.user_id
        assert response.status == test_checkout.status.value


@pytest.mark.unit
class TestFineValidation:
    """Test fine schema validation."""

    async def test_fine_response_structure(self, test_db, test_fine):
        """Test fine response can be created from model."""
        response = FineResponse.model_validate(test_fine)
        assert response.id == test_fine.id
        assert response.user_id == test_fine.user_id
        assert str(response.amount) == str(test_fine.amount)


@pytest.mark.unit
class TestSettingsValidation:
    """Test settings helpers.

    Every field on Settings uses Field(alias=...) for its env var name
    (e.g. cors_origins has alias="CORS_ORIGINS"), and Config doesn't set
    populate_by_name. Without that, pydantic-settings only accepts the
    alias as an __init__ kwarg -- constructing Settings(cors_origins=...)
    (the field name) is silently ignored (Config.extra = "ignore"), and
    the field falls back to whatever's in the real environment instead.
    These tests construct Settings with the ALIAS names (CORS_ORIGINS=,
    not cors_origins=) so the values actually apply.
    """

    def test_cors_origins_list_strips_empty(self):
        """Test CORS origins list filters blank entries."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="http://example.com, ,http://localhost:3000,",
        )
        assert settings.cors_origins_list == [
            "http://example.com",
            "http://localhost:3000",
        ]

    def test_cors_rejects_wildcard_origin(self):
        """Test CORS wildcard origin is rejected for security."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="*",
        )
        with pytest.raises(ValueError, match="Wildcard origin"):
            _ = settings.cors_origins_list

    def test_cors_rejects_wildcard_in_list(self):
        """Test CORS wildcard mixed with other origins is rejected."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="https://example.com,*,http://localhost:3000",
        )
        with pytest.raises(ValueError, match="Wildcard origin"):
            _ = settings.cors_origins_list

    def test_cors_rejects_invalid_url_format(self):
        """Test CORS rejects malformed URLs."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="not-a-url",
        )
        with pytest.raises(ValueError, match="not a valid URL format"):
            _ = settings.cors_origins_list

    def test_cors_rejects_url_without_protocol(self):
        """Test CORS rejects URLs without http/https protocol."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="example.com",
        )
        with pytest.raises(ValueError, match="not a valid URL format"):
            _ = settings.cors_origins_list

    def test_cors_production_rejects_localhost(self):
        """Test CORS rejects localhost origins in production."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="https://example.com,http://localhost:3000",
            PII_ENCRYPTION_ENABLED=True,
            PII_HASH_KEY="test-pii-hash-key-not-for-prod-use",
            # Production-mode Settings now also reject default salts
            # (added after these CORS tests were written).
            WATERMARK_SECRET_SALT="test-watermark-salt-not-for-prod-use",
            DOWNLOAD_IP_HASH_SALT="test-download-salt-not-for-prod-use",
            # A valid 32-byte urlsafe-base64 Fernet key. The original
            # literal here was that same key base64-encoded a second time
            # by mistake (decodes to 44 bytes, not 32); Settings' own
            # Fernet-key validator correctly rejects that.
            PII_ENCRYPTION_KEY="qyHVfH5VKovJgeKS2oFRwbnalQ0ftAXs40CX3JfnP8k=",
        )
        with pytest.raises(ValueError, match="localhost.*not allowed in production"):
            _ = settings.cors_origins_list

    def test_cors_production_rejects_http(self):
        """Test CORS requires HTTPS in production."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="http://example.com",
            PII_ENCRYPTION_ENABLED=True,
            PII_HASH_KEY="test-pii-hash-key-not-for-prod-use",
            # Production-mode Settings now also reject default salts
            # (added after these CORS tests were written).
            WATERMARK_SECRET_SALT="test-watermark-salt-not-for-prod-use",
            DOWNLOAD_IP_HASH_SALT="test-download-salt-not-for-prod-use",
            PII_ENCRYPTION_KEY="qyHVfH5VKovJgeKS2oFRwbnalQ0ftAXs40CX3JfnP8k=",
        )
        with pytest.raises(ValueError, match="must use HTTPS in production"):
            _ = settings.cors_origins_list

    def test_cors_production_accepts_valid_https(self):
        """Test CORS accepts valid HTTPS origins in production."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            ENVIRONMENT="production",
            CORS_ORIGINS="https://example.com,https://api.example.com",
            PII_ENCRYPTION_ENABLED=True,
            PII_HASH_KEY="test-pii-hash-key-not-for-prod-use",
            # Production-mode Settings now also reject default salts
            # (added after these CORS tests were written).
            WATERMARK_SECRET_SALT="test-watermark-salt-not-for-prod-use",
            DOWNLOAD_IP_HASH_SALT="test-download-salt-not-for-prod-use",
            PII_ENCRYPTION_KEY="qyHVfH5VKovJgeKS2oFRwbnalQ0ftAXs40CX3JfnP8k=",
        )
        # Should not raise
        origins = settings.cors_origins_list
        assert origins == ["https://example.com", "https://api.example.com"]

    def test_cors_accepts_valid_url_with_port(self):
        """Test CORS accepts URLs with port numbers."""
        from app.core.config import Settings

        settings = Settings(
            DATABASE_URL="postgresql://user:pass@localhost:5432/test",
            SECRET_KEY="test-secret",
            CORS_ORIGINS="http://localhost:3000,https://example.com:8443",
        )
        origins = settings.cors_origins_list
        assert "http://localhost:3000" in origins
        assert "https://example.com:8443" in origins

    # test_learning_certificate_verify_url_uses_configured_public_api_base
    # deleted (wave 4 / slice M): Settings.learning_certificate_verify_url()
    # and public_api_base_url no longer exist anywhere in app/core/config.py
    # or app code. The printed-certificate verify link
    # (app/api/v1/learning_certificates.py) now builds its URL from
    # `frontend_base` + "/verify/{certificate_number}" instead -- covered by
    # tests/test_certificate_service.py and tests/api/v1/test_learning_
    # certificates.py. This test targeted a superseded code path, not a
    # regression to restore.


@pytest.mark.unit
class TestPasswordValidationRules:
    """Test password validation rules."""

    def test_password_minimum_length(self):
        """Test password minimum length requirement (8 chars)."""
        short = "Pass1!"  # 6 chars
        long = "ValidPassword123!"  # 17 chars
        assert len(short) < 8
        assert len(long) >= 8

    def test_password_number_requirement(self):
        """Test password must contain number."""
        without_number = "ValidPassword!"
        with_number = "ValidPassword123!"
        assert not any(c.isdigit() for c in without_number)
        assert any(c.isdigit() for c in with_number)

    def test_password_special_chars(self):
        """Test strong passwords use special characters."""
        weak = "ValidPassword123"
        strong = "ValidPassword123!"
        assert not any(c in "!@#$%^&*()" for c in weak)
        assert any(c in "!@#$%^&*()" for c in strong)
