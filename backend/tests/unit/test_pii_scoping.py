# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for PII scoping, masking, filtering, and audit logging.

Covers:
- Field filtering for each role level
- Masking functions (email, phone, card number)
- Volunteer/patron cannot see SENSITIVE or RESTRICTED fields
- Admin can see all fields
- Audit logging captures accesses correctly
- Edge cases (missing fields, None values, empty strings)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.pii_scope import (
    FIELD_SENSITIVITY,
    PIISensitivity,
    REDACTED,
    ROLE_VISIBILITY,
    filter_patron_data,
    filter_report_response,
    get_field_sensitivity,
    get_max_visibility,
    mask_card_number,
    mask_email,
    mask_field,
    mask_phone,
)
from app.models.user import UserRole


# ==========================================================================
# Fixtures: sample patron data
# ==========================================================================


def _full_patron_dict() -> dict:
    """Return a patron dict with fields at every sensitivity level."""
    return {
        # PUBLIC
        "patron_name": "Jane Doe",
        "patron_id": 42,
        "patron_type": "adult",
        # INTERNAL
        "patron_library_card": "LIB-2024-00042",
        # SENSITIVE
        "patron_email": "jane@example.com",
        "patron_phone": "555-867-5309",
        "date_of_birth": "1990-01-15",
        "notice_preference": "EMAIL",
        # RESTRICTED
        "patron_address": "123 Main St\nSomewhere Up North, ON K0K1K0",
        "emergency_contact_name": "John Doe",
        "emergency_contact_phone": "555-123-4567",
        # Non-PII fields (pass through)
        "checkout_id": 101,
        "item_title": "Moby Dick",
        "due_date": "2025-01-01",
        "days_overdue": 14,
    }


# ==========================================================================
# Tests: sensitivity level ordering
# ==========================================================================


class TestPIISensitivityLevels:
    def test_ordering(self):
        assert PIISensitivity.PUBLIC < PIISensitivity.INTERNAL
        assert PIISensitivity.INTERNAL < PIISensitivity.SENSITIVE
        assert PIISensitivity.SENSITIVE < PIISensitivity.RESTRICTED

    def test_integer_values(self):
        assert int(PIISensitivity.PUBLIC) == 1
        assert int(PIISensitivity.INTERNAL) == 2
        assert int(PIISensitivity.SENSITIVE) == 3
        assert int(PIISensitivity.RESTRICTED) == 4


# ==========================================================================
# Tests: role -> visibility mapping
# ==========================================================================


class TestRoleVisibilityMapping:
    def test_patron_gets_public(self):
        assert get_max_visibility(UserRole.PATRON) == PIISensitivity.PUBLIC

    def test_child_gets_public(self):
        assert get_max_visibility(UserRole.CHILD) == PIISensitivity.PUBLIC

    def test_bookmobile_gets_public(self):
        assert get_max_visibility(UserRole.BOOKMOBILE) == PIISensitivity.PUBLIC

    def test_homebond_gets_public(self):
        assert get_max_visibility(UserRole.HOMEBOND) == PIISensitivity.PUBLIC

    def test_staff_gets_internal(self):
        assert get_max_visibility(UserRole.STAFF) == PIISensitivity.INTERNAL

    def test_director_gets_sensitive(self):
        assert get_max_visibility(UserRole.DIRECTOR) == PIISensitivity.SENSITIVE

    def test_legal_gets_sensitive(self):
        assert get_max_visibility(UserRole.LEGAL) == PIISensitivity.SENSITIVE

    def test_admin_gets_restricted(self):
        assert get_max_visibility(UserRole.ADMIN) == PIISensitivity.RESTRICTED

    def test_super_admin_gets_restricted(self):
        assert get_max_visibility(UserRole.SUPER_ADMIN) == PIISensitivity.RESTRICTED

    def test_all_roles_are_mapped(self):
        """Every UserRole should have an explicit visibility mapping."""
        for role in UserRole:
            vis = get_max_visibility(role)
            assert vis is not None, f"Role {role} has no visibility mapping"
            assert isinstance(vis, PIISensitivity)


# ==========================================================================
# Tests: field sensitivity classification
# ==========================================================================


class TestFieldSensitivity:
    def test_patron_name_is_public(self):
        assert get_field_sensitivity("patron_name") == PIISensitivity.PUBLIC

    def test_library_card_is_internal(self):
        assert get_field_sensitivity("patron_library_card") == PIISensitivity.INTERNAL

    def test_email_is_sensitive(self):
        assert get_field_sensitivity("patron_email") == PIISensitivity.SENSITIVE

    def test_phone_is_sensitive(self):
        assert get_field_sensitivity("patron_phone") == PIISensitivity.SENSITIVE

    def test_address_is_restricted(self):
        assert get_field_sensitivity("patron_address") == PIISensitivity.RESTRICTED

    def test_unknown_field_returns_none(self):
        assert get_field_sensitivity("checkout_id") is None
        assert get_field_sensitivity("nonexistent_field") is None

    def test_date_of_birth_is_sensitive(self):
        assert get_field_sensitivity("date_of_birth") == PIISensitivity.SENSITIVE

    def test_ssn_is_restricted(self):
        assert get_field_sensitivity("ssn") == PIISensitivity.RESTRICTED


# ==========================================================================
# Tests: masking functions
# ==========================================================================


class TestMaskEmail:
    def test_normal_email(self):
        assert mask_email("jane@example.com") == "j***@example.com"

    def test_short_local(self):
        assert mask_email("a@example.com") == "a***@example.com"

    def test_long_local(self):
        result = mask_email("longusername@domain.org")
        assert result == "l***@domain.org"

    def test_none_returns_none(self):
        assert mask_email(None) is None

    def test_empty_string_returns_empty(self):
        assert mask_email("") == ""

    def test_no_at_sign(self):
        assert mask_email("invalid-email") == "***"


class TestMaskPhone:
    def test_dashed_format(self):
        assert mask_phone("555-867-5309") == "***-***-5309"

    def test_parenthesized_format(self):
        assert mask_phone("(555) 867-5309") == "***-***-5309"

    def test_digits_only(self):
        assert mask_phone("5558675309") == "***-***-5309"

    def test_international_format(self):
        assert mask_phone("+1-555-867-5309") == "***-***-5309"

    def test_short_number(self):
        assert mask_phone("123") == "***"

    def test_four_digits(self):
        assert mask_phone("1234") == "***-***-1234"

    def test_none_returns_none(self):
        assert mask_phone(None) is None

    def test_empty_string_returns_empty(self):
        assert mask_phone("") == ""


class TestMaskCardNumber:
    def test_standard_card(self):
        assert mask_card_number("LIB-2024-00042") == "***0042"

    def test_numeric_card(self):
        assert mask_card_number("1234567890") == "***7890"

    def test_short_card(self):
        assert mask_card_number("1234") == "1234"

    def test_very_short_card(self):
        assert mask_card_number("12") == "12"

    def test_none_returns_none(self):
        assert mask_card_number(None) is None

    def test_empty_string_returns_empty(self):
        assert mask_card_number("") == ""


class TestMaskField:
    def test_email_type(self):
        assert mask_field("jane@example.com", "email") == "j***@example.com"

    def test_phone_type(self):
        assert mask_field("555-867-5309", "phone") == "***-***-5309"

    def test_card_number_type(self):
        assert mask_field("LIB-2024-00042", "card_number") == "***0042"

    def test_unknown_type_passes_through(self):
        assert mask_field("hello", "unknown") == "hello"


# ==========================================================================
# Tests: filter_patron_data by role
# ==========================================================================


class TestFilterPatronDataPatron:
    """PATRON role (PUBLIC visibility) -- most fields should be redacted/masked."""

    def test_public_fields_visible(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_name"] == "Jane Doe"
        assert result["patron_id"] == 42
        assert result["patron_type"] == "adult"

    def test_internal_fields_masked(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        # Full card is masked; last-4 synthetic field is injected
        assert "patron_library_card" in result
        assert result["patron_library_card"] == "***0042"
        assert result.get("library_card_last4") == "***0042"

    def test_sensitive_fields_masked_or_redacted(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        # Email should be masked
        assert "patron_email_masked" in result
        assert result["patron_email_masked"] == "j***@example.com"
        # Raw email should not be present as the original key
        assert (
            result.get("patron_email") is None
            or "patron_email" not in result
            or result.get("patron_email") != "jane@example.com"
        )
        # Phone should be masked
        assert result["patron_phone"] == "***-***-5309"
        # Date of birth should be redacted -- filter_patron_data sets
        # redacted (non-maskable) fields to None, not the REDACTED sentinel,
        # so typed Pydantic response models don't 500 on serialization (see
        # app/core/pii_scope.py filter_patron_data).
        assert result["date_of_birth"] is None
        # Notice preference should be redacted
        assert result["notice_preference"] is None

    def test_restricted_fields_redacted(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_address"] is None
        assert result["emergency_contact_name"] is None
        assert result["emergency_contact_phone"] is None

    def test_non_pii_fields_pass_through(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["checkout_id"] == 101
        assert result["item_title"] == "Moby Dick"
        assert result["due_date"] == "2025-01-01"
        assert result["days_overdue"] == 14


class TestFilterPatronDataStaff:
    """STAFF role (INTERNAL visibility)."""

    def test_public_and_internal_fields_visible(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.STAFF)
        assert result["patron_name"] == "Jane Doe"
        assert result["patron_library_card"] == "LIB-2024-00042"

    def test_sensitive_fields_masked(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.STAFF)
        # Email should be masked
        assert result.get("patron_email_masked") == "j***@example.com"
        # Phone should be masked
        assert result["patron_phone"] == "***-***-5309"

    def test_restricted_fields_redacted(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.STAFF)
        assert result["patron_address"] is None


class TestFilterPatronDataDirector:
    """DIRECTOR role (SENSITIVE visibility)."""

    def test_sensitive_fields_visible(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.DIRECTOR)
        assert result["patron_email"] == "jane@example.com"
        assert result["patron_phone"] == "555-867-5309"
        assert result["date_of_birth"] == "1990-01-15"

    def test_restricted_fields_redacted(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.DIRECTOR)
        assert result["patron_address"] is None
        assert result["emergency_contact_name"] is None


class TestFilterPatronDataAdmin:
    """ADMIN role (RESTRICTED visibility) -- sees everything."""

    def test_all_fields_visible(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.ADMIN)
        assert result["patron_name"] == "Jane Doe"
        assert result["patron_library_card"] == "LIB-2024-00042"
        assert result["patron_email"] == "jane@example.com"
        assert result["patron_phone"] == "555-867-5309"
        assert result["patron_address"] == "123 Main St\nSomewhere Up North, ON K0K1K0"
        assert result["emergency_contact_name"] == "John Doe"
        assert result["emergency_contact_phone"] == "555-123-4567"
        assert result["date_of_birth"] == "1990-01-15"

    def test_no_redacted_fields(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.ADMIN)
        for key, value in result.items():
            assert value != REDACTED, f"Field {key} should not be redacted for ADMIN"


class TestFilterPatronDataSuperAdmin:
    """SUPER_ADMIN role (RESTRICTED visibility) -- sees everything."""

    def test_all_fields_visible(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.SUPER_ADMIN)
        assert result["patron_name"] == "Jane Doe"
        assert result["patron_email"] == "jane@example.com"
        assert result["patron_address"] == "123 Main St\nSomewhere Up North, ON K0K1K0"


# ==========================================================================
# Tests: filter_patron_data does not mutate original
# ==========================================================================


class TestFilterDoesNotMutate:
    def test_original_dict_unchanged(self):
        data = _full_patron_dict()
        original_email = data["patron_email"]
        _ = filter_patron_data(data, UserRole.PATRON)
        assert data["patron_email"] == original_email


# ==========================================================================
# Tests: edge cases
# ==========================================================================


class TestFilterEdgeCases:
    def test_empty_dict(self):
        result = filter_patron_data({}, UserRole.PATRON)
        assert result == {}

    def test_none_values_in_fields(self):
        data = {
            "patron_name": None,
            "patron_email": None,
            "patron_phone": None,
            "patron_library_card": None,
            "patron_address": None,
        }
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_name"] is None  # PUBLIC, None passes through
        # Masked None should still be None
        assert result.get("patron_email_masked") is None
        assert result.get("patron_phone") is None

    def test_empty_string_values(self):
        data = {
            "patron_email": "",
            "patron_phone": "",
            "patron_library_card": "",
        }
        result = filter_patron_data(data, UserRole.PATRON)
        # mask_email("") returns "", mask_phone("") returns ""
        assert result.get("patron_email_masked") == ""
        assert result["patron_phone"] == ""

    def test_only_unknown_fields(self):
        data = {
            "checkout_id": 1,
            "item_title": "Test",
            "random_field": "value",
        }
        result = filter_patron_data(data, UserRole.PATRON)
        assert result == data

    def test_missing_pii_fields_no_error(self):
        """If certain expected PII fields are absent, filtering should not fail."""
        data = {"patron_name": "Test User"}
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_name"] == "Test User"

    def test_library_card_last4_injected_for_public_role(self):
        data = {"patron_library_card": "LIB-2024-99999"}
        result = filter_patron_data(data, UserRole.PATRON)
        assert "library_card_last4" in result
        assert result["library_card_last4"] == "***9999"


# ==========================================================================
# Tests: filter_report_response (recursive structure handling)
# ==========================================================================


class TestFilterReportResponse:
    def test_dict_with_items_list(self):
        data = {
            "items": [_full_patron_dict()],
            "total": 1,
            "page": 1,
        }
        filtered, redacted = filter_report_response(data, UserRole.PATRON)
        assert len(filtered["items"]) == 1
        item = filtered["items"][0]
        assert item["patron_name"] == "Jane Doe"
        assert item["patron_address"] is None

    def test_plain_list(self):
        data = [_full_patron_dict(), _full_patron_dict()]
        filtered, redacted = filter_report_response(data, UserRole.PATRON)
        assert len(filtered) == 2
        assert filtered[0]["patron_address"] is None

    def test_single_dict(self):
        data = _full_patron_dict()
        filtered, redacted = filter_report_response(data, UserRole.PATRON)
        assert filtered["patron_name"] == "Jane Doe"

    def test_redacted_field_names_tracked(self):
        data = {"items": [_full_patron_dict()]}
        _, redacted = filter_report_response(data, UserRole.PATRON)
        # patron_email should have been redacted/masked
        assert "patron_email" in redacted or "patron_address" in redacted

    def test_admin_no_redacted_fields(self):
        data = {"items": [_full_patron_dict()]}
        _, redacted = filter_report_response(data, UserRole.ADMIN)
        assert len(redacted) == 0

    def test_scalar_passthrough(self):
        data = 42
        filtered, redacted = filter_report_response(data, UserRole.PATRON)
        assert filtered == 42
        assert redacted == []

    def test_nested_dict(self):
        data = {
            "report": {
                "patron_email": "test@example.com",
                "patron_name": "Test",
            }
        }
        filtered, _ = filter_report_response(data, UserRole.PATRON)
        # The inner dict should be filtered
        inner = filtered["report"]
        assert inner["patron_name"] == "Test"

    def test_list_of_non_dicts_passthrough(self):
        data = {"values": [1, 2, 3]}
        filtered, _ = filter_report_response(data, UserRole.PATRON)
        assert filtered["values"] == [1, 2, 3]


# ==========================================================================
# Tests: PII audit logging
# ==========================================================================


class TestPIIAuditLogging:
    @pytest.mark.asyncio
    async def test_log_pii_access_structured_log(self):
        """log_pii_access should emit a structured log line."""
        from app.core.pii_audit import log_pii_access

        with patch("app.core.pii_audit.logger") as mock_logger:
            await log_pii_access(
                db=None,
                user_id=1,
                user_role=UserRole.STAFF,
                endpoint="/api/v1/reports/circulation/overdue",
                fields_accessed=["patron_name", "patron_library_card"],
                fields_redacted=["patron_email", "patron_address"],
                patron_ids_accessed=[42, 43],
                ip_address="127.0.0.1",
            )
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            log_json = call_args[0][1]
            parsed = json.loads(log_json)
            assert parsed["user_id"] == 1
            assert parsed["user_role"] == "staff"
            assert parsed["endpoint"] == "/api/v1/reports/circulation/overdue"
            assert "patron_name" in parsed["fields_accessed"]
            assert "patron_email" in parsed["fields_redacted"]
            assert parsed["patron_ids_accessed"] == [42, 43]
            assert parsed["ip_address"] == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_log_pii_access_persists_to_db(self):
        """log_pii_access should persist a record when a db session is provided."""
        from app.core.pii_audit import log_pii_access

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock()

        with patch("app.core.pii_audit.logger"):
            await log_pii_access(
                db=mock_db,
                user_id=1,
                user_role=UserRole.ADMIN,
                endpoint="/api/v1/reports/overdue",
                fields_accessed=["patron_name"],
                fields_redacted=[],
            )
            mock_db.add.assert_called_once()
            mock_db.flush.assert_called_once()
            added_record = mock_db.add.call_args[0][0]
            assert added_record.user_id == 1
            assert added_record.user_role == "admin"

    @pytest.mark.asyncio
    async def test_log_pii_access_db_failure_does_not_raise(self):
        """A database failure in audit logging should not propagate."""
        from app.core.pii_audit import log_pii_access

        mock_db = AsyncMock()
        mock_db.flush = AsyncMock(side_effect=Exception("DB error"))

        with patch("app.core.pii_audit.logger"):
            # Should not raise
            await log_pii_access(
                db=mock_db,
                user_id=1,
                user_role=UserRole.STAFF,
                endpoint="/test",
                fields_accessed=[],
                fields_redacted=[],
            )

    @pytest.mark.asyncio
    async def test_log_pii_access_with_additional_context(self):
        """Additional context dict should be included in the log."""
        from app.core.pii_audit import log_pii_access

        with patch("app.core.pii_audit.logger") as mock_logger:
            await log_pii_access(
                db=None,
                user_id=1,
                user_role=UserRole.STAFF,
                endpoint="/test",
                fields_accessed=["patron_name"],
                fields_redacted=[],
                additional_context={"export_format": "csv"},
            )
            call_args = mock_logger.info.call_args
            log_json = call_args[0][1]
            parsed = json.loads(log_json)
            assert parsed["additional_context"] == {"export_format": "csv"}

    @pytest.mark.asyncio
    async def test_log_pii_access_with_string_role(self):
        """Role passed as a string instead of UserRole enum should work."""
        from app.core.pii_audit import log_pii_access

        with patch("app.core.pii_audit.logger") as mock_logger:
            await log_pii_access(
                db=None,
                user_id=1,
                user_role="STAFF",
                endpoint="/test",
                fields_accessed=[],
                fields_redacted=[],
            )
            call_args = mock_logger.info.call_args
            log_json = call_args[0][1]
            parsed = json.loads(log_json)
            assert parsed["user_role"] == "STAFF"


# ==========================================================================
# Tests: @pii_filtered decorator
# ==========================================================================


class TestPIIFilteredDecorator:
    @pytest.mark.asyncio
    async def test_decorator_filters_dict_response(self):
        from app.middleware.pii_filter import pii_filtered

        @pii_filtered
        async def fake_endpoint(current_user=None, db=None, request=None):
            return {
                "items": [
                    {
                        "patron_name": "Test User",
                        "patron_email": "test@example.com",
                        "patron_address": "123 Elm St",
                    }
                ]
            }

        mock_user = SimpleNamespace(id=1, role=UserRole.PATRON)
        result = await fake_endpoint(current_user=mock_user)
        assert result["items"][0]["patron_name"] == "Test User"
        assert result["items"][0]["patron_address"] is None

    @pytest.mark.asyncio
    async def test_decorator_passes_through_without_user(self):
        from app.middleware.pii_filter import pii_filtered

        @pii_filtered
        async def fake_endpoint(current_user=None):
            return {"patron_email": "test@example.com"}

        result = await fake_endpoint()
        assert result["patron_email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_decorator_passes_through_response_objects(self):
        from starlette.responses import JSONResponse

        from app.middleware.pii_filter import pii_filtered

        @pii_filtered
        async def fake_endpoint(current_user=None):
            return JSONResponse(content={"patron_email": "test@example.com"})

        mock_user = SimpleNamespace(id=1, role=UserRole.PATRON)
        result = await fake_endpoint(current_user=mock_user)
        # Should be a JSONResponse, not filtered
        assert isinstance(result, JSONResponse)

    @pytest.mark.asyncio
    async def test_decorator_logs_pii_access(self):
        from app.middleware.pii_filter import pii_filtered

        @pii_filtered
        async def fake_endpoint(current_user=None, db=None, request=None):
            return {
                "items": [
                    {
                        "patron_name": "Test",
                        "patron_email": "t@example.com",
                    }
                ]
            }

        mock_user = SimpleNamespace(id=1, role=UserRole.STAFF)
        mock_request = MagicMock()
        mock_request.url.path = "/api/v1/reports/overdue"
        mock_request.client.host = "10.0.0.1"

        with patch("app.middleware.pii_filter.log_pii_access", new_callable=AsyncMock) as mock_log:
            await fake_endpoint(current_user=mock_user, request=mock_request)
            mock_log.assert_called_once()
            call_kwargs = mock_log.call_args[1]
            assert call_kwargs["user_id"] == 1
            assert call_kwargs["endpoint"] == "/api/v1/reports/overdue"


# ==========================================================================
# Tests: comprehensive role-level filtering (volunteer scenario from pre-mortem)
# ==========================================================================


class TestVolunteerCannotSeeContactDetails:
    """
    Pre-mortem scenario: a volunteer (PATRON role) exports the overdue report
    and should NOT see phone numbers, email addresses, or full addresses.
    """

    def test_patron_cannot_see_full_email(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        # Should not contain the raw email
        assert "patron_email" not in result or result.get("patron_email") != "jane@example.com"

    def test_patron_cannot_see_full_phone(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result.get("patron_phone") != "555-867-5309"
        # Should be masked
        assert result["patron_phone"] == "***-***-5309"

    def test_patron_cannot_see_address(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_address"] is None

    def test_patron_sees_name_and_card_last4(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.PATRON)
        assert result["patron_name"] == "Jane Doe"
        assert "library_card_last4" in result


class TestAdminSeesAll:
    """Admin sees every field without any redaction."""

    def test_admin_sees_all_fields(self):
        data = _full_patron_dict()
        result = filter_patron_data(data, UserRole.ADMIN)
        for key, value in data.items():
            assert key in result, f"ADMIN should see field {key}"
            assert result[key] == value, f"ADMIN field {key} should be unmodified"


# ==========================================================================
# Tests: PIIAccessLog model
# ==========================================================================


class TestPIIAccessLogModel:
    def test_model_has_required_columns(self):
        from app.core.pii_audit import PIIAccessLog

        assert hasattr(PIIAccessLog, "id")
        assert hasattr(PIIAccessLog, "timestamp")
        assert hasattr(PIIAccessLog, "user_id")
        assert hasattr(PIIAccessLog, "user_role")
        assert hasattr(PIIAccessLog, "endpoint")
        assert hasattr(PIIAccessLog, "fields_accessed")
        assert hasattr(PIIAccessLog, "fields_redacted")
        assert hasattr(PIIAccessLog, "patron_ids_accessed")
        assert hasattr(PIIAccessLog, "ip_address")
        assert hasattr(PIIAccessLog, "additional_context")

    def test_model_tablename(self):
        from app.core.pii_audit import PIIAccessLog

        assert PIIAccessLog.__tablename__ == "pii_access_log"
