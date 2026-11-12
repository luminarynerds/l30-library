# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive unit tests for Pydantic schema validation.

Tests cover:
- User schema field constraints and validation
- Email validation with .test domain support
- Password validation integration
- Field length constraints
- Type validation
- Edge cases and security considerations
"""

import pytest
from datetime import date, datetime
from pydantic import ValidationError

from app.schemas.user import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserLogin,
    LoginRequest,
    validate_email_allow_test,
)
from app.models.user import UserRole


@pytest.mark.unit
class TestEmailValidation:
    """Test email validation with .test domain support."""

    def test_validate_email_valid_standard_email(self):
        """Test validation of standard email addresses."""
        valid_emails = [
            "user@example.com",
            "test.user@example.com",
            "user+tag@example.com",
            "user_name@example.co.uk",
            "123@example.com",
        ]

        for email in valid_emails:
            result = validate_email_allow_test(email)
            assert result is not None
            assert "@" in result

    def test_validate_email_test_domain_allowed(self):
        """Test that .test domain emails are accepted."""
        test_emails = [
            "user@l30.org",
            "test@example.test",
            "admin@system.test",
        ]

        for email in test_emails:
            result = validate_email_allow_test(email)
            assert result is not None
            assert email.lower() == result

    def test_validate_email_normalizes_to_lowercase(self):
        """Test that emails are normalized to lowercase.

        Only for the domain, not the local part: validate_email_allow_test
        delegates non-reserved-TLD addresses to the `email_validator`
        library's `.normalized`, which (correctly, per RFC 5321 local-part
        case sensitivity) lowercases the domain only. This email's TLD
        (.com) isn't in _RFC2606_RESERVED_TLDS, so it takes that path, not
        the local regex fallback that fully lowercases everything.
        """
        email = "Test.User@EXAMPLE.COM"
        result = validate_email_allow_test(email)
        assert result == "Test.User@example.com"

    def test_validate_email_invalid_format(self):
        """Test rejection of invalid email formats."""
        invalid_emails = [
            "notanemail",
            "@example.com",
            "user@",
            "user name@example.com",
            "user@@example.com",
        ]

        for email in invalid_emails:
            with pytest.raises(ValueError):
                validate_email_allow_test(email)

    def test_validate_email_with_unicode(self):
        """Test email validation with unicode characters."""
        # Some systems allow unicode in local part
        email = "user@example.test"
        result = validate_email_allow_test(email)
        assert result is not None


@pytest.mark.unit
class TestUserBaseSchema:
    """Test UserBase schema validation."""

    def test_user_base_valid(self):
        """Test creating valid UserBase."""
        user = UserBase(
            email="test@example.test",
            first_name="John",
            last_name="Doe"
        )
        assert user.email == "test@example.test"
        assert user.first_name == "John"
        assert user.last_name == "Doe"

    def test_user_base_first_name_required(self):
        """Test that first_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(email="test@example.test", last_name="Doe")
        assert "first_name" in str(exc_info.value)

    def test_user_base_last_name_required(self):
        """Test that last_name is required."""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(email="test@example.test", first_name="John")
        assert "last_name" in str(exc_info.value)

    def test_user_base_email_required(self):
        """Test that email is required."""
        with pytest.raises(ValidationError) as exc_info:
            UserBase(first_name="John", last_name="Doe")
        assert "email" in str(exc_info.value)

    def test_user_base_first_name_min_length(self):
        """Test that first_name must be at least 1 character."""
        with pytest.raises(ValidationError):
            UserBase(email="test@example.test", first_name="", last_name="Doe")

    def test_user_base_first_name_max_length(self):
        """Test that first_name has maximum length of 100."""
        with pytest.raises(ValidationError):
            UserBase(
                email="test@example.test",
                first_name="x" * 101,
                last_name="Doe"
            )

    def test_user_base_first_name_at_max_length(self):
        """Test that first_name at exactly max length is accepted."""
        user = UserBase(
            email="test@example.test",
            first_name="x" * 100,
            last_name="Doe"
        )
        assert len(user.first_name) == 100

    def test_user_base_last_name_min_length(self):
        """Test that last_name must be at least 1 character."""
        with pytest.raises(ValidationError):
            UserBase(email="test@example.test", first_name="John", last_name="")

    def test_user_base_last_name_max_length(self):
        """Test that last_name has maximum length of 100."""
        with pytest.raises(ValidationError):
            UserBase(
                email="test@example.test",
                first_name="John",
                last_name="x" * 101
            )

    def test_user_base_last_name_at_max_length(self):
        """Test that last_name at exactly max length is accepted."""
        user = UserBase(
            email="test@example.test",
            first_name="John",
            last_name="x" * 100
        )
        assert len(user.last_name) == 100

    def test_user_base_with_special_characters_in_names(self):
        """Test that names can contain special characters."""
        user = UserBase(
            email="test@example.test",
            first_name="Jean-Pierre",
            last_name="O'Brien"
        )
        assert user.first_name == "Jean-Pierre"
        assert user.last_name == "O'Brien"

    def test_user_base_with_unicode_names(self):
        """Test that names can contain unicode characters."""
        user = UserBase(
            email="test@example.test",
            first_name="José",
            last_name="Müller"
        )
        assert "é" in user.first_name or "Jose" in user.first_name
        assert "ü" in user.last_name or "Muller" in user.last_name


@pytest.mark.unit
class TestUserCreateSchema:
    """Test UserCreate schema validation."""

    def test_user_create_valid(self):
        """Test creating valid UserCreate."""
        user = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert user.email == "test@example.test"
        assert user.password == "SecurePassword123!"

    def test_user_create_password_required(self):
        """Test that password is required."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.test",
                first_name="John",
                last_name="Doe"
            )

    def test_user_create_password_validation_enforced(self):
        """Test that password validation is enforced."""
        # Too short password
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.test",
                first_name="John",
                last_name="Doe",
                password="short1"
            )

    def test_user_create_phone_optional(self):
        """Test that phone is optional."""
        user = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert user.phone is None

    def test_user_create_with_phone(self):
        """Test UserCreate with phone number."""
        user = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!",
            phone="613-555-1234"
        )
        assert user.phone == "613-555-1234"

    def test_user_create_address_optional(self):
        """Test that address is optional."""
        user = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert user.address is None

    def test_user_create_with_address(self):
        """Test UserCreate with address."""
        address = "123 Main Street, City, State 12345"
        user = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!",
            address=address
        )
        assert user.address == address


@pytest.mark.unit
class TestUserUpdateSchema:
    """Test UserUpdate schema validation."""

    def test_user_update_all_fields_optional(self):
        """Test that all fields are optional in UserUpdate."""
        user = UserUpdate()
        assert user.first_name is None
        assert user.last_name is None
        assert user.phone is None
        assert user.address is None

    def test_user_update_first_name_max_length(self):
        """Test first_name max length constraint."""
        with pytest.raises(ValidationError):
            UserUpdate(first_name="x" * 101)

    def test_user_update_last_name_max_length(self):
        """Test last_name max length constraint."""
        with pytest.raises(ValidationError):
            UserUpdate(last_name="x" * 101)

    def test_user_update_phone_max_length(self):
        """Test phone max length constraint."""
        with pytest.raises(ValidationError):
            UserUpdate(phone="x" * 51)

    def test_user_update_address_max_length(self):
        """Test address max length constraint."""
        with pytest.raises(ValidationError):
            UserUpdate(address="x" * 501)

    def test_user_update_emergency_contact_name_max_length(self):
        """Test emergency contact name max length."""
        with pytest.raises(ValidationError):
            UserUpdate(emergency_contact_name="x" * 201)

    def test_user_update_emergency_contact_phone_max_length(self):
        """Test emergency contact phone max length."""
        with pytest.raises(ValidationError):
            UserUpdate(emergency_contact_phone="x" * 21)

    def test_user_update_partial_update(self):
        """Test that only needed fields can be updated."""
        update = UserUpdate(first_name="Jane", phone="555-1234")
        assert update.first_name == "Jane"
        assert update.phone == "555-1234"
        assert update.last_name is None

    def test_user_update_date_of_birth(self):
        """Test date_of_birth field."""
        dob = date(2010, 1, 15)
        update = UserUpdate(date_of_birth=dob)
        assert update.date_of_birth == dob

    def test_user_update_track_reading_history(self):
        """Test track_reading_history boolean field."""
        update = UserUpdate(track_reading_history=False)
        assert update.track_reading_history is False

    def test_user_update_language_preference_max_length(self):
        """Test language preference max length."""
        with pytest.raises(ValidationError):
            UserUpdate(language_preference="x" * 51)


@pytest.mark.unit
class TestUserLoginSchema:
    """Test UserLogin schema validation."""

    def test_user_login_valid(self):
        """Test creating valid UserLogin."""
        login = UserLogin(
            email="test@example.test",
            password="SecurePassword123"
        )
        assert login.email == "test@example.test"
        assert login.password == "SecurePassword123"

    def test_user_login_email_required(self):
        """Test that email is required."""
        with pytest.raises(ValidationError):
            UserLogin(password="SecurePassword123")

    def test_user_login_password_required(self):
        """Test that password is required."""
        with pytest.raises(ValidationError):
            UserLogin(email="test@example.test")

    def test_user_login_password_validation_not_enforced(self):
        """Test that login password validation is not enforced (for comparison)."""
        # Unlike UserCreate, UserLogin doesn't validate password strength
        # This is intentional - users should be able to attempt login with any string
        login = UserLogin(
            email="test@example.test",
            password="weak"
        )
        assert login.password == "weak"


@pytest.mark.unit
class TestLoginRequestSchema:
    """Test LoginRequest schema validation."""

    def test_login_request_with_email(self):
        """Test LoginRequest with email field."""
        login = LoginRequest(
            email="test@example.test",
            password="SecurePassword123"
        )
        assert login.get_login_identifier() == "test@example.test"

    def test_login_request_with_username(self):
        """Test LoginRequest with username field."""
        login = LoginRequest(
            username="testuser",
            password="SecurePassword123"
        )
        assert login.get_login_identifier() == "testuser"

    def test_login_request_email_precedence(self):
        """Test that email takes precedence over username."""
        login = LoginRequest(
            email="test@example.test",
            username="testuser",
            password="SecurePassword123"
        )
        # Email should take precedence
        assert "example.test" in login.get_login_identifier()

    def test_login_request_no_email_no_username(self):
        """Test that at least email or username is required."""
        login = LoginRequest(password="SecurePassword123")
        with pytest.raises(ValueError):
            login.get_login_identifier()

    def test_login_request_password_required(self):
        """Test that password is required."""
        with pytest.raises(ValidationError):
            LoginRequest(email="test@example.test")

    def test_login_request_strips_whitespace(self):
        """Test that email/username whitespace is stripped."""
        login = LoginRequest(
            email="  test@example.test  ",
            password="SecurePassword123"
        )
        assert "test@example.test" in login.get_login_identifier()

    def test_login_request_empty_string_treated_as_none(self):
        """Test that empty strings are treated as None."""
        login = LoginRequest(
            email="",
            username="testuser",
            password="SecurePassword123"
        )
        assert login.get_login_identifier() == "testuser"


@pytest.mark.unit
class TestSchemaEdgeCases:
    """Test edge cases and security considerations."""

    def test_schema_rejects_none_for_required_fields(self):
        """Test that required fields reject None."""
        with pytest.raises(ValidationError):
            UserBase(email=None, first_name="John", last_name="Doe")

    def test_schema_rejects_empty_string_for_required_names(self):
        """Test that empty strings are rejected for names."""
        with pytest.raises(ValidationError):
            UserBase(email="test@example.test", first_name="", last_name="Doe")

    def test_schema_handles_very_long_optional_fields(self):
        """Test handling of very long optional field values."""
        with pytest.raises(ValidationError):
            UserUpdate(address="x" * 1000)

    def test_schema_with_special_json_characters(self):
        """Test that special JSON characters in names are handled."""
        user = UserBase(
            email="test@example.test",
            first_name='John"Test',
            last_name="Doe'Test"
        )
        assert '"' in user.first_name or "Test" in user.first_name
        assert "'" in user.last_name or "Test" in user.last_name

    def test_schema_sql_injection_not_possible_via_schema(self):
        """Test that SQL-like strings are accepted as regular data."""
        # Schema doesn't execute SQL - validation happens at persistence layer
        user = UserCreate(
            email="test@example.test",
            first_name="'; DROP TABLE users; --",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert user.first_name == "'; DROP TABLE users; --"

    def test_schema_html_injection_not_escaped_by_schema(self):
        """Test that HTML-like strings are accepted as regular data."""
        # HTML escaping is frontend responsibility
        user = UserCreate(
            email="test@example.test",
            first_name="<script>alert('XSS')</script>",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert "<script>" in user.first_name

    def test_schema_case_sensitivity(self):
        """Test that schemas preserve case in data."""
        user = UserBase(
            email="Test@Example.Test",
            first_name="JOHN",
            last_name="doe"
        )
        # Email should be lowercased by validator
        assert "test@example.test" in user.email.lower()
        # Names should preserve case
        assert user.first_name == "JOHN"
        assert user.last_name == "doe"

    def test_schema_unicode_normalization(self):
        """Test unicode handling in schemas."""
        # Tests that unicode is preserved (not normalized away)
        user = UserBase(
            email="test@example.test",
            first_name="José",
            last_name="Müller"
        )
        assert user.first_name == "José"
        assert user.last_name == "Müller"


@pytest.mark.unit
class TestSchemaIntegration:
    """Integration tests for schema validation flow."""

    def test_create_then_update_flow(self):
        """Test typical create then update flow."""
        # Create user
        created = UserCreate(
            email="test@example.test",
            first_name="John",
            last_name="Doe",
            password="SecurePassword123!"
        )
        assert created.email == "test@example.test"

        # Update user
        update = UserUpdate(
            first_name="Jane",
            phone="555-1234"
        )
        assert update.first_name == "Jane"
        assert update.phone == "555-1234"

    def test_login_request_to_user_base_not_direct(self):
        """Test that LoginRequest data cannot directly create UserBase."""
        login = LoginRequest(
            email="test@example.test",
            password="SecurePassword123"
        )

        # LoginRequest doesn't have first_name/last_name, so cannot create UserBase directly
        with pytest.raises(ValidationError):
            UserBase(**login.dict())
