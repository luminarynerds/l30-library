# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Aggressive input validation security tests for LSC Library Management System.

These tests attempt SQL injection, XSS, path traversal, and command injection attacks
against the backend's input validation mechanisms.
"""

import pytest
from pydantic import ValidationError

from app.core.input_validation import InputValidator, ValidationResult
from app.schemas.user import UserCreate


@pytest.mark.unit
class TestSQLInjectionAttacks:
    """Test SQL injection attack detection and prevention."""

    def test_basic_sql_injection_select(self):
        """Test detection of basic SELECT statement injection."""
        validator = InputValidator()
        payload = "Test' OR '1'='1"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_union_select(self):
        """Test detection of UNION-based SQL injection."""
        validator = InputValidator()
        payload = "'; UNION SELECT * FROM users--"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_update_statement(self):
        """Test detection of UPDATE statement injection."""
        validator = InputValidator()
        payload = "test'; UPDATE users SET admin=true WHERE '1'='1"
        result = validator._validate_string_field("description", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_delete_statement(self):
        """Test detection of DELETE statement injection."""
        validator = InputValidator()
        payload = "test'; DELETE FROM users WHERE '1'='1"
        result = validator._validate_string_field("note", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_drop_table(self):
        """Test detection of DROP TABLE injection."""
        validator = InputValidator()
        payload = "test'; DROP TABLE users--"
        result = validator._validate_string_field("query", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_comment_based(self):
        """Test detection of comment-based SQL injection."""
        validator = InputValidator()
        payload = "test-- SQL injection"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_block_comment(self):
        """Test detection of block comment-based SQL injection."""
        validator = InputValidator()
        payload = "test/* SQL injection */malicious"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_or_and_logic(self):
        """Test detection of OR/AND logic-based SQL injection."""
        validator = InputValidator()
        payload = "' OR 1=1 AND '"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_exec_execute(self):
        """Test detection of EXEC/EXECUTE statement injection."""
        validator = InputValidator()
        payload = "'; EXEC xp_cmdshell 'dir'; --"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("SQL injection" in error for error in (result.errors or []))

    def test_sql_injection_case_insensitive(self):
        """Test that SQL injection detection is case-insensitive."""
        validator = InputValidator()
        payload = "test' sElEcT * from users--"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid


@pytest.mark.unit
class TestXSSAttacks:
    """Test XSS (Cross-Site Scripting) attack detection and prevention."""

    def test_xss_script_tag(self):
        """Test detection of script tag injection."""
        validator = InputValidator()
        payload = "<script>alert('XSS')</script>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_javascript_protocol(self):
        """Test detection of javascript: protocol."""
        validator = InputValidator()
        payload = "<a href='javascript:alert(\"XSS\")'>Click me</a>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_event_handler(self):
        """Test detection of event handler injection."""
        validator = InputValidator()
        payload = "<img src='x' onerror='alert(\"XSS\")'>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_svg_injection(self):
        """Test detection of SVG-based XSS."""
        validator = InputValidator()
        payload = "<svg onload='alert(\"XSS\")'></svg>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_iframe_injection(self):
        """Test detection of iframe injection."""
        validator = InputValidator()
        payload = "<iframe src='http://evil.com'></iframe>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_object_tag(self):
        """Test detection of object tag injection."""
        validator = InputValidator()
        payload = "<object data='http://evil.com/xss.swf'></object>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_embed_tag(self):
        """Test detection of embed tag injection."""
        validator = InputValidator()
        payload = "<embed src='http://evil.com/xss.swf'>"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_xss_event_handler_variations(self):
        """Test various event handler formats."""
        validator = InputValidator()
        payloads = [
            "<div onclick='alert(1)'>Click</div>",
            "<img src=x onload=alert(1)>",
            "<body onload='alert(1)'>",
            "<input autofocus onfocus=alert(1)>",
        ]
        for payload in payloads:
            result = validator._validate_string_field("reason", payload)
            assert not result.is_valid


@pytest.mark.unit
class TestPathTraversalAttacks:
    """Test path traversal attack detection and prevention."""

    def test_path_traversal_double_dot(self):
        """Test detection of ../ path traversal."""
        validator = InputValidator()
        payload = "../../etc/passwd"
        result = validator._validate_string_field("url", payload)
        assert not result.is_valid
        assert any("malicious" in error.lower() for error in (result.errors or []))

    def test_path_traversal_multiple_levels(self):
        """Test detection of multiple-level path traversal."""
        validator = InputValidator()
        payload = "../../../../../../../../etc/passwd"
        result = validator._validate_string_field("url", payload)
        assert not result.is_valid

    def test_path_traversal_backslash(self):
        """Test detection of backslash-based path traversal."""
        validator = InputValidator()
        payload = "..\\..\\windows\\system32"
        result = validator._validate_string_field("url", payload)
        assert not result.is_valid


@pytest.mark.unit
class TestNullByteInjection:
    """Test null byte injection detection."""

    def test_null_byte_injection(self):
        """Test detection of null byte in input."""
        validator = InputValidator()
        payload = "test\x00injection"
        result = validator._validate_string_field("reason", payload)
        assert not result.is_valid
        assert any("null byte" in error.lower() for error in (result.errors or []))

    def test_null_byte_in_challenge_data(self):
        """Test null byte detection in challenge data."""
        validator = InputValidator()
        challenge_data = {"challenger_name": "Test\x00User", "reason": "Valid reason"}
        result = validator.validate_challenge_input(challenge_data)
        assert not result.is_valid


@pytest.mark.unit
class TestLengthValidation:
    """Test input length validation."""

    def test_field_exceeds_max_length(self):
        """Test rejection of input exceeding max length."""
        validator = InputValidator()
        payload = "x" * 1001
        result = validator._validate_string_field("unknown_field", payload)
        assert not result.is_valid
        assert any("exceeds maximum length" in error for error in (result.errors or []))

    def test_title_exceeds_max_length(self):
        """Test title field max length (500 chars)."""
        validator = InputValidator()
        payload = "x" * 501
        result = validator._validate_string_field("title", payload)
        assert not result.is_valid

    def test_email_exceeds_max_length(self):
        """Test email field max length (254 chars)."""
        validator = InputValidator()
        payload = "x" * 250 + "@example.com"
        result = validator._validate_string_field("email", payload)
        assert not result.is_valid

    def test_valid_length_accepted(self):
        """Test that valid length inputs are accepted."""
        validator = InputValidator()
        payload = "x" * 100
        result = validator._validate_string_field("reason", payload)
        assert result.is_valid


@pytest.mark.unit
class TestUserSchemaValidation:
    """Test user schema validation for security."""

    def test_email_validation_prevents_injection(self):
        """Test that email validation prevents injection via email field."""
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com'; DROP TABLE users--",
                password="ValidPassword123!",
                first_name="Test",
                last_name="User",
            )

    def test_password_validation_strength(self):
        """Test password strength validation."""
        weak_passwords = [
            "password",
            "12345678",
            "abcdefgh",
            "Pass1",
        ]
        for pwd in weak_passwords:
            with pytest.raises(ValidationError):
                UserCreate(
                    email="test@example.com",
                    password=pwd,
                    first_name="Test",
                    last_name="User",
                )

    def test_name_field_length_validation(self):
        """Test name field length validation."""
        long_name = "x" * 300
        with pytest.raises(ValidationError):
            UserCreate(
                email="test@example.com",
                password="ValidPassword123!",
                first_name=long_name,
                last_name="User",
            )


@pytest.mark.unit
class TestChallengeInputValidation:
    """Test comprehensive challenge input validation."""

    def test_valid_challenge_input(self):
        """Test valid challenge input is accepted."""
        validator = InputValidator()
        challenge_data = {
            "challenger_name": "John Doe",
            "reason": "Book is not age-appropriate",
        }
        result = validator.validate_challenge_input(challenge_data)
        assert result.is_valid

    def test_missing_required_fields(self):
        """Test that missing required fields are detected."""
        validator = InputValidator()
        challenge_data = {"challenger_name": "John Doe"}
        result = validator.validate_challenge_input(challenge_data)
        assert not result.is_valid
        assert any("reason" in error.lower() for error in (result.errors or []))

    def test_sql_injection_in_multiple_fields(self):
        """Test SQL injection detection across multiple fields."""
        validator = InputValidator()
        challenge_data = {
            "challenger_name": "Test'; DROP TABLE users--",
            "reason": "Valid reason",
        }
        result = validator.validate_challenge_input(challenge_data)
        assert not result.is_valid

    def test_xss_in_multiple_fields(self):
        """Test XSS detection across multiple fields."""
        validator = InputValidator()
        challenge_data = {
            "challenger_name": "Test User",
            "reason": "<script>alert('XSS')</script>",
        }
        result = validator.validate_challenge_input(challenge_data)
        assert not result.is_valid


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
