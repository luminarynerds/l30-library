# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests: reversal state-integrity fixes (sweep 2026-07-01).

H1 — _revert_privacy_setting_changed must return success=False when the
     user does not have the target attribute (was: silently skipping the
     write and returning success=True).

H2 — _revert_note_added must soft-delete the PatronNote record (was:
     logging a retraction audit entry and returning success=True while
     leaving the note record intact).
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.audit_log import AuditAction, AuditLog
from app.services.reversal.audit_strategy import AuditReversalStrategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_db(execute_return=None):
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = execute_return
    db.execute.return_value = mock_result
    return db


def _audit_log_privacy_setting(target_user_id, setting_name, old_value):
    log = MagicMock(spec=AuditLog)
    log.action = AuditAction.PRIVACY_SETTING_CHANGED
    log.target_user_id = target_user_id
    log.details = {
        "setting_name": setting_name,
        "old_value": old_value,
        "new_value": "public",
    }
    log.created_at = None
    log.id = 1
    return log


def _audit_log_note_added(note_id):
    log = MagicMock(spec=AuditLog)
    log.action = AuditAction.NOTE_ADDED
    log.target_user_id = 10
    log.details = {"note_id": note_id}
    log.created_at = None
    log.id = 2
    return log


# ---------------------------------------------------------------------------
# H1 — _revert_privacy_setting_changed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revert_privacy_setting_fails_when_no_user_id():
    """Return success=False when audit log has no target_user_id."""
    db = _make_db()
    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_privacy_setting(
        target_user_id=None,
        setting_name="show_reading_history",
        old_value=False,
    )

    result = await strategy._revert_privacy_setting_changed(audit_log, 1, None, None)

    assert not result.success, "Must fail: no target user ID"


@pytest.mark.asyncio
async def test_revert_privacy_setting_fails_when_user_not_found():
    """Return success=False when the target user no longer exists."""
    db = _make_db(execute_return=None)  # user fetch returns None
    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_privacy_setting(
        target_user_id=99,
        setting_name="show_reading_history",
        old_value=False,
    )

    result = await strategy._revert_privacy_setting_changed(audit_log, 1, None, None)

    assert not result.success, "Must fail: user not found"


@pytest.mark.asyncio
async def test_revert_privacy_setting_fails_when_attr_missing():
    """Return success=False when user model lacks the setting attribute."""
    user = MagicMock(spec=[])  # empty spec: hasattr returns False for everything
    db = _make_db(execute_return=user)
    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_privacy_setting(
        target_user_id=5,
        setting_name="nonexistent_setting_xyz",
        old_value=False,
    )

    result = await strategy._revert_privacy_setting_changed(audit_log, 1, None, None)

    assert not result.success, (
        "Must fail: user has no 'nonexistent_setting_xyz' attribute — "
        "was silently skipping the write and returning success=True"
    )


@pytest.mark.asyncio
async def test_revert_privacy_setting_succeeds_when_attr_present():
    """Happy path: attr exists — setattr is called and success=True."""
    user = MagicMock()
    user.id = 5
    user.email = "patron@example.com"
    user.reading_list_privacy = "public"

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user
    db.execute.return_value = mock_result

    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_privacy_setting(
        target_user_id=5,
        setting_name="reading_list_privacy",
        old_value="private",  # truthy so the `or`-chain resolves correctly
    )

    result = await strategy._revert_privacy_setting_changed(audit_log, 1, None, None)

    assert result.success, "Must succeed: setting exists and is reverted"
    assert user.reading_list_privacy == "private", "setattr must have applied the old_value"


# ---------------------------------------------------------------------------
# H2 — _revert_note_added
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_revert_note_added_fails_when_no_note_id():
    """Return success=False when audit log has no note_id."""
    db = AsyncMock()
    strategy = AuditReversalStrategy(db)
    audit_log = MagicMock(spec=AuditLog)
    audit_log.action = AuditAction.NOTE_ADDED
    audit_log.target_user_id = 10
    audit_log.details = {}  # no note_id
    audit_log.created_at = None
    audit_log.id = 3

    result = await strategy._revert_note_added(audit_log, 1, None, None)

    assert not result.success, "Must fail: no note_id in audit log"


@pytest.mark.asyncio
async def test_revert_note_added_fails_when_note_not_found():
    """Return success=False when the PatronNote no longer exists."""
    db = _make_db(execute_return=None)  # note query returns None
    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_note_added(note_id=42)

    result = await strategy._revert_note_added(audit_log, 1, None, None)

    assert not result.success, "Must fail: note 42 not found"


@pytest.mark.asyncio
async def test_revert_note_added_soft_deletes_note():
    """Actual note record must be soft-deleted, not just flagged in the audit trail."""
    note = MagicMock()
    note.id = 77
    note.is_deleted = False

    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = note
    db.execute.return_value = mock_result

    strategy = AuditReversalStrategy(db)
    audit_log = _audit_log_note_added(note_id=77)

    result = await strategy._revert_note_added(audit_log, 1, None, None)

    assert result.success, "Must succeed when note exists"
    note.soft_delete.assert_called_once_with(
        user_id=1,
        reason="Admin reversal of NOTE_ADDED action",
    )
