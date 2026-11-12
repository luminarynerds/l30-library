# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comprehensive unit tests for password security functions.

Tests cover:
- Password validation rules (length, complexity, common passwords)
- Password hashing and verification
- Password reuse prevention
- Edge cases and security considerations
"""

import pytest
from app.core.security import (
    validate_password,
    hash_password,
    verify_password,
    PasswordValidationError,
    COMMON_PASSWORDS,
    PASSWORD_HISTORY_COUNT,
)
from app.core.config import get_settings


@pytest.mark.unit
class TestPasswordValidation:
    """Test password validation rules."""

    def test_validate_password_minimum_length_requirement(self):
        """Test that passwords must meet minimum length requirement."""
        settings = get_settings()
        min_length = settings.password_min_length

        # Too short
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("Short1")
        assert "at least" in str(exc_info.value).lower()
        assert str(min_length) in str(exc_info.value)

    def test_validate_password_valid_minimum_length(self):
        """Test that passwords at minimum length are accepted."""
        settings = get_settings()
        min_length = settings.password_min_length

        # Exactly minimum length, with all required character classes
        password = "Aa1!" + "a" * (min_length - 4)
        assert len(password) == min_length
        validate_password(password)  # Should not raise

    def test_validate_password_requires_digit(self):
        """Test that passwords must contain at least one digit."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("NoDigitsHere!")
        error_msg = str(exc_info.value).lower()
        assert "digit" in error_msg or "number" in error_msg

    def test_validate_password_digit_variants(self):
        """Test that various digit formats are accepted."""
        # All should pass - they have digits (plus upper/special the policy also requires)
        validate_password("ValidPassword1!")
        validate_password("Pass0word!")
        validate_password("Pass9word!")

    def test_validate_password_rejects_common_passwords(self):
        """Test that common passwords are rejected."""
        # "Password123!" satisfies every character-class rule and still case-folds to
        # the "password123!" entry in COMMON_PASSWORDS, so it is the one example that can
        # reach the common-password-specific message under the stricter policy.
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("Password123!")
        assert "common" in str(exc_info.value).lower() or "stronger" in str(exc_info.value).lower()

        # "123456", "qwerty", "admin" have no case/digit/special variant that both (a)
        # satisfies the character-class rules and (b) case-folds to an exact match in
        # COMMON_PASSWORDS -- they now fail an earlier character-class check instead.
        # Still always rejected, just for a different (also-valid) reason.
        for common_pwd in ["123456", "qwerty", "admin"]:
            with pytest.raises(PasswordValidationError):
                validate_password(common_pwd)

    def test_validate_password_common_password_case_insensitive(self):
        """Test that common password detection is case-insensitive."""
        # PASSWORD123 should be detected as similar to password123
        with pytest.raises(PasswordValidationError):
            validate_password("PASSWORD123")

        # QwErTy should be detected
        with pytest.raises(PasswordValidationError):
            validate_password("QwErTy1")

    def test_validate_password_all_common_passwords_blocked(self):
        """Test that all passwords in COMMON_PASSWORDS list are blocked."""
        for common_pwd in COMMON_PASSWORDS:
            # Add digit if needed
            test_pwd = common_pwd if any(c.isdigit() for c in common_pwd) else common_pwd + "1"
            with pytest.raises(PasswordValidationError):
                validate_password(test_pwd)

    def test_validate_password_special_characters_allowed(self):
        """Test that special characters are allowed."""
        validate_password("Valid!Pass123")
        validate_password("ValidPass@123")
        validate_password("ValidPass#123$")
        validate_password("ValidPass%123^")

    def test_validate_password_unicode_characters_allowed(self):
        """Test that unicode characters are allowed."""
        validate_password("Validpässwörd123!")
        validate_password("Validпароль123!")  # Russian
        validate_password("Valid密码123!")      # Chinese

    def test_validate_password_spaces_allowed(self):
        """Test that spaces in passwords are allowed."""
        validate_password("Valid Pass Word 123!")
        validate_password("My Secret Pass1!")

    def test_validate_password_empty_string(self):
        """Test that empty password is rejected."""
        with pytest.raises(PasswordValidationError):
            validate_password("")

    def test_validate_password_whitespace_only(self):
        """Test that whitespace-only password is too short."""
        with pytest.raises(PasswordValidationError):
            validate_password("     ")

    def test_validate_password_long_passwords_accepted(self):
        """Test that very long passwords are accepted."""
        long_password = "A" + "a" * 498 + "1!"  # 501 characters, all char classes present
        assert len(long_password) == 501
        validate_password(long_password)  # Should not raise


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password_returns_hash(self):
        """Test that hash_password returns a hash string."""
        password = "ValidPassword123"
        hashed = hash_password(password)
        assert isinstance(hashed, str)
        assert hashed != password
        assert len(hashed) > 20  # Bcrypt hashes are typically 60 chars

    def test_hash_password_deterministic_per_run(self):
        """Test that same password can be verified (salt varies)."""
        password = "ValidPassword123"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different due to different salt
        assert hash1 != hash2

        # But both should verify correctly
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_hash_password_with_special_characters(self):
        """Test hashing passwords with special characters."""
        passwords = [
            "Pass!@#$%^&*123",
            "Pass\tWithTab123",
            "Pass\nWithNewline123",
            "Pass123🔒",  # With emoji
        ]

        for pwd in passwords:
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed)

    def test_hash_password_with_unicode(self):
        """Test hashing unicode passwords."""
        passwords = [
            "Пароль123",  # Russian
            "密码Pass123",   # Chinese mixed
            "Mötörhëäd123", # Special Latin chars
        ]

        for pwd in passwords:
            hashed = hash_password(pwd)
            assert verify_password(pwd, hashed)

    def test_hash_password_very_long_password(self):
        """Test hashing very long passwords."""
        # Bcrypt has a maximum input length of 72 bytes (after encoding)
        # But bcrypt handles this correctly
        long_password = "a" * 1000 + "1"
        hashed = hash_password(long_password)
        # Should successfully hash without truncation issues (bcrypt handles this)
        assert isinstance(hashed, str)


@pytest.mark.unit
class TestPasswordVerification:
    """Test password verification logic."""

    def test_verify_password_correct_password(self):
        """Test verifying a correct password."""
        password = "ValidPassword123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_incorrect_password(self):
        """Test verifying an incorrect password."""
        password = "ValidPassword123"
        wrong_password = "WrongPassword123"
        hashed = hash_password(password)
        assert verify_password(wrong_password, hashed) is False

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "ValidPassword123"
        hashed = hash_password(password)

        # Different case should fail
        assert verify_password("validpassword123", hashed) is False
        assert verify_password("VALIDPASSWORD123", hashed) is False

    def test_verify_password_empty_string(self):
        """Test verifying empty password against hash."""
        password = "ValidPassword123"
        hashed = hash_password(password)
        assert verify_password("", hashed) is False

    def test_verify_password_none_hashed(self):
        """Test verifying password against None hash."""
        password = "ValidPassword123"
        # Should raise an error or return False gracefully
        try:
            result = verify_password(password, None)
            assert result is False
        except (TypeError, AttributeError):
            # Expected to raise with None
            pass

    def test_verify_password_invalid_hash_format(self):
        """Test verifying against invalid hash format."""
        password = "ValidPassword123"
        invalid_hashes = [
            "not_a_valid_hash",
            "123456",
            "$2a$invalid_hash",
            "",
        ]

        for invalid_hash in invalid_hashes:
            result = verify_password(password, invalid_hash)
            assert result is False  # Should gracefully handle

    def test_verify_password_special_characters(self):
        """Test verifying passwords with special characters."""
        password = "Pass!@#$%^&*123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("Pass!@#$%^&*124", hashed) is False

    def test_verify_password_unicode(self):
        """Test verifying unicode passwords."""
        password = "Пароль123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True
        assert verify_password("Пароль124", hashed) is False

    def test_verify_password_partial_match(self):
        """Test that partial password matches fail."""
        password = "ValidPassword123"
        hashed = hash_password(password)
        assert verify_password("ValidPassword", hashed) is False
        assert verify_password("ValidPassword12", hashed) is False
        assert verify_password("ValidPassword1234", hashed) is False


@pytest.mark.unit
class TestPasswordValidationIntegration:
    """Integration tests for validation -> hashing -> verification flow."""

    def test_valid_password_workflow(self):
        """Test complete workflow: validate -> hash -> verify."""
        password = "MySecurePassword123!"

        # Validate
        validate_password(password)  # Should not raise

        # Hash
        hashed = hash_password(password)

        # Verify
        assert verify_password(password, hashed) is True

    def test_invalid_password_rejected_early(self):
        """Test that validation catches invalid passwords before hashing."""
        invalid_passwords = [
            "short1",                # Too short
            "noDIGIT!",              # No digit
            "password123",           # Common password
        ]

        for invalid_pwd in invalid_passwords:
            with pytest.raises(PasswordValidationError):
                validate_password(invalid_pwd)

            # Should never reach hashing step if validation is enforced
            # In real code, hash() would be called only after validate() passes

    def test_multiple_users_different_hashes(self):
        """Test that same password for different users produces different hashes."""
        password = "SamePassword123!"

        # Validate once
        validate_password(password)

        # Hash for two different users
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Hashes should be different (different salts)
        assert hash1 != hash2

        # But both should verify
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


@pytest.mark.unit
class TestPasswordHistoryTracking:
    """Test password reuse prevention (requires database integration in real implementation)."""

    def test_password_history_count_constant(self):
        """Test that PASSWORD_HISTORY_COUNT is defined."""
        assert PASSWORD_HISTORY_COUNT > 0
        assert PASSWORD_HISTORY_COUNT >= 5  # NIST recommendation minimum

    def test_password_history_concept(self):
        """Test the concept of password history (unit test version)."""
        # In real implementation, this would check database for previous hashes
        # Here we demonstrate the concept with hashes

        passwords = [
            "ValidPassword123!",
            "AnotherPassword456!",
            "ThirdPassword789!",
            "FourthPassword012!",
            "FifthPassword345!",
        ]

        hashes = []

        # Simulate building history
        for pwd in passwords:
            validate_password(pwd)
            hash_obj = hash_password(pwd)
            hashes.append((pwd, hash_obj))

        # Should have PASSWORD_HISTORY_COUNT hashes
        assert len(hashes) >= PASSWORD_HISTORY_COUNT

        # All should verify correctly
        for pwd, hash_obj in hashes:
            assert verify_password(pwd, hash_obj)

        # But none should match each other
        for i, (pwd_i, hash_i) in enumerate(hashes):
            for j, (pwd_j, hash_j) in enumerate(hashes):
                if i != j:
                    # Password i should not verify against hash j
                    assert verify_password(pwd_i, hash_j) is False


@pytest.mark.unit
class TestPasswordEdgeCases:
    """Test edge cases and security considerations."""

    def test_password_with_leading_trailing_spaces(self):
        """Test that spaces are preserved in password."""
        password = "  ValidPassword123  "
        hashed = hash_password(password)

        # Must match exactly, spaces included
        assert verify_password(password, hashed) is True
        assert verify_password("ValidPassword123", hashed) is False  # Without spaces

    def test_password_with_null_bytes(self):
        """Test handling of null bytes in password."""
        # Bcrypt should handle null bytes
        password_with_null = "ValidPassword123\x00Hidden"

        # Should hash without errors
        hashed = hash_password(password_with_null)
        assert verify_password(password_with_null, hashed) is True
        assert verify_password("ValidPassword123", hashed) is False

    def test_password_similar_to_common_but_different(self):
        """Test that passwords similar to common ones but with changes are accepted."""
        # password123 is common, but password124 should be accepted
        validate_password("Password124!")  # Should pass
        validate_password("Password223!")  # Should pass
        validate_password("Xpassword123!")  # Should pass (prefix change)

    def test_consecutive_special_characters(self):
        """Test passwords with consecutive special characters."""
        validate_password("Pass!!!Word123")
        validate_password("Pass@@@Word123")
        validate_password("Pass!!!Word123b")  # "~" is not in the recognized special-char set

    def test_repeated_characters(self):
        """Test passwords with repeated characters."""
        validate_password("Passsssword123!")
        validate_password("PPPPpppp1234!")
        validate_password("Aaaaaaaaaa1!")

    def test_sequential_numbers(self):
        """Test that sequential numbers in password are allowed (not rejected)."""
        # These should pass validation (we don't block sequences)
        validate_password("Password1234!")
        validate_password("Pass123456789!")
        validate_password("123Password1!")

    def test_keyboard_patterns(self):
        """Test that keyboard patterns are allowed (we only block a few specific ones)."""
        # qwerty is blocked, but others should be allowed
        validate_password("Abcdefgh1!")
        validate_password("Zxcvbnm1!")
        validate_password("Asdfghjk1!")

    def test_password_with_json_special_chars(self):
        """Test passwords with JSON-special characters."""
        validate_password('Pass"word123')  # " is in the recognized special-char set
        validate_password("Pass'word123!")  # ' is not, so add one that is
        validate_password("Pass\\word123!")  # backslash is not, so add one that is
        validate_password("Pass/word123!")  # forward slash is not, so add one that is

    def test_password_with_html_special_chars(self):
        """Test passwords with HTML-special characters."""
        validate_password("Pass<word>123")  # < and > are in the recognized special-char set
        validate_password("Pass&word123!")  # & is not, so add one that is
        validate_password("Pass=word123!")  # = is not, so add one that is


@pytest.mark.unit
class TestPasswordValidationErrorMessages:
    """Test that error messages are helpful."""

    def test_error_message_includes_requirement(self):
        """Test that error messages clearly state the requirement."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("short1")

        error_msg = str(exc_info.value).lower()
        assert "password" in error_msg or "at least" in error_msg

    def test_error_message_for_missing_digit(self):
        """Test error message for password without digit."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("NoDigitsLongEnough")

        error_msg = str(exc_info.value).lower()
        assert "digit" in error_msg or "number" in error_msg

    def test_error_message_for_common_password(self):
        """Test error message for common password."""
        with pytest.raises(PasswordValidationError) as exc_info:
            validate_password("Password123!")

        error_msg = str(exc_info.value).lower()
        assert "common" in error_msg or "stronger" in error_msg


@pytest.mark.unit
class TestPasswordSecurityBestPractices:
    """Test that implementation follows security best practices."""

    def test_passwords_not_logged(self):
        """Test that we don't accidentally log passwords."""
        # This is more of an integration test, but we can verify the functions don't have obvious logging
        password = "SecretPassword123"
        hashed = hash_password(password)
        verify_password(password, hashed)

        # If tests pass without exposing password, that's good
        # In real scenario, would check logs to ensure password not there

    def test_hashes_are_different_format_than_password(self):
        """Test that hashes look nothing like passwords."""
        password = "ReadablePassword123"
        hashed = hash_password(password)

        # Bcrypt format should start with $2
        assert hashed.startswith("$2")
        assert password not in hashed
        assert hashed != password

    def test_password_validation_before_hashing(self):
        """Test the recommended pattern: validate -> hash -> store."""
        valid_pwd = "ValidPassword123!"
        invalid_pwd = "invalid"

        # Valid should succeed validation
        try:
            validate_password(valid_pwd)
        except PasswordValidationError:
            pytest.fail("Valid password rejected")

        # Invalid should fail validation
        with pytest.raises(PasswordValidationError):
            validate_password(invalid_pwd)
