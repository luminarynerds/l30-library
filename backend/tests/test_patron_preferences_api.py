# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for patron preferences API endpoints (patron_preferences.py).

Tests the FastAPI route handlers for patron accessibility preferences.
Covers:
- GET  /patron/preferences (get own preferences, defaults if none)
- PUT  /patron/preferences (upsert own preferences)
- GET  /patron/preferences/{patron_id} (staff-only view)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException

from app.api.v1.patron_preferences import (
    PatronPreferenceResponse,
    PatronPreferenceUpdateRequest,
    get_my_preferences,
    get_patron_preferences_staff,
    update_my_preferences,
)
from app.models.patron_communication import PatronPreference
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_user(user_id: int = 1, role: UserRole = UserRole.PATRON) -> MagicMock:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = f"user{user_id}@example.com"
    user.role = role
    user.is_active = True
    return user


def _make_preference(patron_id: int = 1, **overrides) -> MagicMock:
    defaults = {
        "id": 10,
        "patron_id": patron_id,
        "prefers_large_print": False,
        "prefers_audio_format": False,
        "prefers_braille": False,
        "handle_fragile_items_with_care": False,
        "limited_mobility_assistance_needed": False,
        "needs_extra_time_checkout": False,
        "preference_notes": None,
        "set_by_id": patron_id,
    }
    defaults.update(overrides)
    pref = MagicMock(spec=PatronPreference)
    for k, v in defaults.items():
        setattr(pref, k, v)
    return pref


def _mock_scalar_one_or_none(value):
    """Create a mock result that returns value from scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# GET /patron/preferences - Get own preferences
# ---------------------------------------------------------------------------


class TestGetMyPreferences:
    """Tests for GET /patron/preferences."""

    @pytest.mark.asyncio
    async def test_returns_defaults_when_no_record(self):
        """New patron with no preferences should get all-false defaults."""
        user = _make_user()
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        response = await get_my_preferences(current_user=user, db=db)

        assert response.prefers_large_print is False
        assert response.prefers_audio_format is False
        assert response.prefers_braille is False
        assert response.handle_fragile_items_with_care is False
        assert response.limited_mobility_assistance_needed is False
        assert response.needs_extra_time_checkout is False
        assert response.preference_notes is None

    @pytest.mark.asyncio
    async def test_returns_existing_preferences(self):
        """Patron with saved preferences should see their values."""
        user = _make_user()
        pref = _make_preference(
            prefers_large_print=True,
            needs_extra_time_checkout=True,
            preference_notes="Needs large print materials",
        )
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(pref)

        with patch.object(PatronPreferenceResponse, "model_validate") as mock_validate:
            mock_validate.return_value = PatronPreferenceResponse(
                prefers_large_print=True,
                needs_extra_time_checkout=True,
                preference_notes="Needs large print materials",
            )
            response = await get_my_preferences(current_user=user, db=db)

        assert response.prefers_large_print is True
        assert response.needs_extra_time_checkout is True
        assert response.preference_notes == "Needs large print materials"


# ---------------------------------------------------------------------------
# PUT /patron/preferences - Update own preferences
# ---------------------------------------------------------------------------


class TestUpdateMyPreferences:
    """Tests for PUT /patron/preferences."""

    @pytest.mark.asyncio
    async def test_creates_new_record_if_none_exists(self):
        """First update should create a new PatronPreference record."""
        user = _make_user()
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        # After commit + refresh, simulate returning the new record
        new_pref = _make_preference(
            prefers_large_print=True,
            prefers_braille=True,
        )
        with patch.object(PatronPreferenceResponse, "model_validate") as mock_validate:
            mock_validate.return_value = PatronPreferenceResponse(
                prefers_large_print=True,
                prefers_braille=True,
            )
            update_data = PatronPreferenceUpdateRequest(
                prefers_large_print=True,
                prefers_braille=True,
            )
            response = await update_my_preferences(
                update_data=update_data, current_user=user, db=db
            )

        assert response.prefers_large_print is True
        assert response.prefers_braille is True
        db.add.assert_called_once()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_updates_existing_record(self):
        """Subsequent updates should modify the existing record."""
        user = _make_user()
        existing_pref = _make_preference(prefers_large_print=False)
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(existing_pref)

        with patch.object(PatronPreferenceResponse, "model_validate") as mock_validate:
            mock_validate.return_value = PatronPreferenceResponse(
                prefers_large_print=True,
            )
            update_data = PatronPreferenceUpdateRequest(prefers_large_print=True)
            response = await update_my_preferences(
                update_data=update_data, current_user=user, db=db
            )

        # Should NOT call db.add (record already exists)
        db.add.assert_not_called()
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rejects_empty_update(self):
        """Update with no fields should return 400."""
        user = _make_user()
        db = AsyncMock()
        update_data = PatronPreferenceUpdateRequest()

        with pytest.raises(HTTPException) as exc_info:
            await update_my_preferences(
                update_data=update_data, current_user=user, db=db
            )

        assert exc_info.value.status_code == 400
        assert "No fields to update" in exc_info.value.detail


# ---------------------------------------------------------------------------
# GET /patron/preferences/{patron_id} - Staff-only view
# ---------------------------------------------------------------------------


class TestGetPatronPreferencesStaff:
    """Tests for GET /patron/preferences/{patron_id}."""

    @pytest.mark.asyncio
    async def test_staff_can_view_patron_preferences(self):
        """Staff user should be able to view any patron's preferences."""
        staff_user = _make_user(user_id=99, role=UserRole.STAFF)
        patron = _make_user(user_id=1, role=UserRole.PATRON)
        pref = _make_preference(
            patron_id=1,
            prefers_audio_format=True,
            limited_mobility_assistance_needed=True,
        )

        db = AsyncMock()
        # First call: find patron, second call: find preferences
        db.execute.side_effect = [
            _mock_scalar_one_or_none(patron),
            _mock_scalar_one_or_none(pref),
        ]

        with patch.object(PatronPreferenceResponse, "model_validate") as mock_validate:
            mock_validate.return_value = PatronPreferenceResponse(
                prefers_audio_format=True,
                limited_mobility_assistance_needed=True,
            )
            response = await get_patron_preferences_staff(
                patron_id=1, current_user=staff_user, db=db
            )

        assert response.prefers_audio_format is True
        assert response.limited_mobility_assistance_needed is True

    @pytest.mark.asyncio
    async def test_patron_cannot_access_staff_endpoint(self):
        """Regular patron should get 403 on staff endpoint."""
        patron_user = _make_user(user_id=1, role=UserRole.PATRON)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_patron_preferences_staff(
                patron_id=2, current_user=patron_user, db=db
            )

        assert exc_info.value.status_code == 403
        assert "Staff access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_staff_gets_defaults_for_patron_without_preferences(self):
        """Staff viewing patron with no preferences should get defaults."""
        staff_user = _make_user(user_id=99, role=UserRole.ADMIN)
        patron = _make_user(user_id=1)

        db = AsyncMock()
        db.execute.side_effect = [
            _mock_scalar_one_or_none(patron),
            _mock_scalar_one_or_none(None),
        ]

        response = await get_patron_preferences_staff(
            patron_id=1, current_user=staff_user, db=db
        )

        assert response.prefers_large_print is False
        assert response.preference_notes is None

    @pytest.mark.asyncio
    async def test_staff_gets_404_for_nonexistent_patron(self):
        """Staff viewing nonexistent patron should get 404."""
        staff_user = _make_user(user_id=99, role=UserRole.STAFF)
        db = AsyncMock()
        db.execute.return_value = _mock_scalar_one_or_none(None)

        with pytest.raises(HTTPException) as exc_info:
            await get_patron_preferences_staff(
                patron_id=9999, current_user=staff_user, db=db
            )

        assert exc_info.value.status_code == 404
        assert "Patron not found" in exc_info.value.detail
