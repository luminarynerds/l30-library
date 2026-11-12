# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Regret Recovery Service.

Validates that:
- Every destructive action has a mapped recovery timeline
- Recovery timelines are well-formed (valid severity, windows, etc.)
- The endpoint-to-action-key detection works correctly
- The "regret is human" design principles are enforced:
  * Critical actions require typed confirmation
  * Every action has at least one recovery window
  * Soft-delete actions have reassurance messaging
  * The default timeline covers unknown actions gracefully
"""

import pytest
from app.services.regret_recovery_service import (
    get_recovery_timeline,
    get_all_registered_actions,
    get_actions_by_severity,
    detect_action_key,
    ActionSeverity,
    RecoveryDifficulty,
    RegretRecoveryTimeline,
    ENDPOINT_TO_ACTION_KEY,
)


class TestRecoveryTimelineRegistry:
    """Test the recovery timeline registry."""

    def test_registry_is_not_empty(self):
        """At least some destructive actions should be registered."""
        all_actions = get_all_registered_actions()
        assert len(all_actions) > 0, "Registry should have registered actions"

    def test_all_registered_actions_have_valid_fields(self):
        """Every registered action must have all required fields filled out."""
        for key, timeline in get_all_registered_actions().items():
            assert timeline.action_key == key, f"{key}: action_key mismatch"
            assert timeline.action_label, f"{key}: missing action_label"
            assert isinstance(timeline.severity, ActionSeverity), f"{key}: invalid severity"
            assert isinstance(timeline.requires_confirmation, bool), f"{key}: requires_confirmation must be bool"
            assert isinstance(timeline.requires_typed_confirmation, bool), f"{key}: requires_typed_confirmation must be bool"
            assert isinstance(timeline.soft_delete, bool), f"{key}: soft_delete must be bool"
            assert len(timeline.windows) > 0, f"{key}: must have at least one recovery window"

    def test_all_windows_have_valid_fields(self):
        """Every recovery window must have valid difficulty and method."""
        for key, timeline in get_all_registered_actions().items():
            for i, window in enumerate(timeline.windows):
                assert window.timeframe, f"{key} window {i}: missing timeframe"
                assert isinstance(window.difficulty, RecoveryDifficulty), (
                    f"{key} window {i}: invalid difficulty"
                )
                assert window.method, f"{key} window {i}: missing method"
                assert isinstance(window.available, bool), (
                    f"{key} window {i}: available must be bool"
                )

    def test_critical_actions_require_typed_confirmation(self):
        """CRITICAL severity actions must require typed confirmation."""
        critical = get_actions_by_severity(ActionSeverity.CRITICAL)
        for timeline in critical:
            assert timeline.requires_typed_confirmation, (
                f"CRITICAL action '{timeline.action_key}' must require typed confirmation"
            )
            assert timeline.requires_confirmation, (
                f"CRITICAL action '{timeline.action_key}' must require confirmation"
            )

    def test_all_actions_have_reassurance(self):
        """Every action should have reassurance messaging — regret is human."""
        for key, timeline in get_all_registered_actions().items():
            assert timeline.reassurance, (
                f"Action '{key}' is missing reassurance messaging. "
                "Regret is human — every action should offer comfort."
            )

    def test_all_actions_have_what_is_lost(self):
        """Every action should explain what is affected."""
        for key, timeline in get_all_registered_actions().items():
            assert timeline.what_is_lost, (
                f"Action '{key}' is missing what_is_lost description"
            )


class TestRecoveryTimelineLookup:
    """Test looking up specific recovery timelines."""

    def test_known_action_returns_correct_timeline(self):
        """Looking up a known action returns the right timeline."""
        timeline = get_recovery_timeline("delete_catalog_item")
        assert timeline.action_key == "delete_catalog_item"
        assert timeline.severity == ActionSeverity.HIGH
        assert timeline.requires_confirmation is True
        assert len(timeline.windows) > 0

    def test_unknown_action_returns_default_timeline(self):
        """Looking up an unknown action returns a safe default."""
        timeline = get_recovery_timeline("totally_unknown_action_xyz")
        assert timeline.action_key == "totally_unknown_action_xyz"
        assert timeline.requires_confirmation is True  # Safe default
        assert len(timeline.windows) > 0
        assert timeline.reassurance  # Even unknown actions get reassurance

    def test_gdpr_deletion_is_critical(self):
        """GDPR account deletion is the most severe action."""
        timeline = get_recovery_timeline("delete_account_gdpr")
        assert timeline.severity == ActionSeverity.CRITICAL
        assert timeline.requires_typed_confirmation is True
        assert timeline.soft_delete is False

    def test_deactivate_user_is_reversible(self):
        """Deactivating a user should be fully reversible."""
        timeline = get_recovery_timeline("deactivate_user")
        assert timeline.soft_delete is True
        # Should have at least one self-service recovery window
        self_service = [
            w for w in timeline.windows
            if w.difficulty == RecoveryDifficulty.SELF_SERVICE
        ]
        assert len(self_service) > 0, "Deactivation should be self-service undoable"

    def test_remove_favorite_is_low_severity(self):
        """Removing a favorite is low-impact and easily redone."""
        timeline = get_recovery_timeline("remove_favorite")
        assert timeline.severity == ActionSeverity.LOW
        assert timeline.requires_confirmation is False

    def test_bulk_delete_is_critical(self):
        """Bulk delete is a critical operation."""
        timeline = get_recovery_timeline("bulk_delete")
        assert timeline.severity == ActionSeverity.CRITICAL
        assert timeline.requires_typed_confirmation is True


class TestEndpointDetection:
    """Test the HTTP endpoint to action key mapping."""

    def test_detect_user_delete(self):
        """DELETE /api/v1/users/123 -> deactivate_user."""
        key = detect_action_key("DELETE", "/api/v1/users/123")
        assert key == "deactivate_user"

    def test_detect_catalog_delete(self):
        """DELETE /api/v1/catalog/456 -> delete_catalog_item."""
        key = detect_action_key("DELETE", "/api/v1/catalog/456")
        assert key == "delete_catalog_item"

    def test_detect_gdpr_delete(self):
        """DELETE /api/v1/privacy/account -> delete_account_gdpr."""
        key = detect_action_key("DELETE", "/api/v1/privacy/account")
        assert key == "delete_account_gdpr"

    def test_detect_unknown_endpoint(self):
        """Unknown endpoints return 'unknown'."""
        key = detect_action_key("DELETE", "/api/v1/something/nobody/knows")
        assert key == "unknown"

    def test_endpoint_map_covers_key_destructive_operations(self):
        """The endpoint map should cover the most critical destructive operations."""
        critical_endpoints = [
            "DELETE /api/v1/users/{user_id}",
            "DELETE /api/v1/privacy/account",
            "DELETE /api/v1/catalog/{item_id}",
        ]
        for endpoint in critical_endpoints:
            assert endpoint in ENDPOINT_TO_ACTION_KEY, (
                f"Critical endpoint '{endpoint}' is not in the detection map"
            )


class TestTimelineSerialization:
    """Test that timelines serialize correctly for the API."""

    def test_to_dict_has_all_fields(self):
        """Serialized timeline should have all expected fields."""
        timeline = get_recovery_timeline("delete_catalog_item")
        data = timeline.to_dict()

        assert "action_key" in data
        assert "action_label" in data
        assert "severity" in data
        assert "requires_confirmation" in data
        assert "requires_typed_confirmation" in data
        assert "soft_delete" in data
        assert "windows" in data
        assert "what_is_lost" in data
        assert "what_is_kept" in data
        assert "reassurance" in data

    def test_to_dict_windows_are_serializable(self):
        """Window entries should be plain dicts."""
        timeline = get_recovery_timeline("delete_catalog_item")
        data = timeline.to_dict()

        for window in data["windows"]:
            assert isinstance(window, dict)
            assert "timeframe" in window
            assert "seconds" in window
            assert "difficulty" in window
            assert "method" in window
            assert "available" in window
            # Enums should be serialized as strings
            assert isinstance(window["difficulty"], str)

    def test_severity_is_string_in_dict(self):
        """Severity should be serialized as a string, not an enum."""
        timeline = get_recovery_timeline("delete_catalog_item")
        data = timeline.to_dict()
        assert isinstance(data["severity"], str)
        assert data["severity"] in ("low", "medium", "high", "critical")


class TestRecoveryDesignPrinciples:
    """
    Test that the system embodies the design philosophy:
    "Regret is human. Recovery should be possible."
    """

    def test_no_action_has_zero_windows(self):
        """Every action must have at least one recovery window,
        even if that window is 'impossible'."""
        for key, timeline in get_all_registered_actions().items():
            assert len(timeline.windows) >= 1, (
                f"Action '{key}' has no recovery windows. "
                "Even permanent actions should explain WHY recovery isn't possible."
            )

    def test_impossible_windows_explain_why(self):
        """Windows marked 'impossible' should explain the alternative."""
        for key, timeline in get_all_registered_actions().items():
            for window in timeline.windows:
                if window.difficulty == RecoveryDifficulty.IMPOSSIBLE:
                    assert not window.available, (
                        f"Action '{key}': impossible windows must have available=False"
                    )
                    assert len(window.method) > 10, (
                        f"Action '{key}': impossible window needs a helpful explanation, "
                        f"not just '{window.method}'"
                    )

    def test_soft_delete_actions_are_recoverable(self):
        """Actions marked soft_delete=True should have at least one
        available recovery window with self_service or staff_help difficulty."""
        for key, timeline in get_all_registered_actions().items():
            if timeline.soft_delete:
                available = [w for w in timeline.windows if w.available]
                assert len(available) > 0, (
                    f"Soft-delete action '{key}' has no available recovery windows"
                )
                recoverable = [
                    w for w in available
                    if w.difficulty in (
                        RecoveryDifficulty.SELF_SERVICE,
                        RecoveryDifficulty.STAFF_HELP,
                        RecoveryDifficulty.ADMIN_HELP,
                    )
                ]
                assert len(recoverable) > 0, (
                    f"Soft-delete action '{key}' should be recoverable without IT help"
                )

    def test_severity_levels_are_well_distributed(self):
        """The registry should have actions across multiple severity levels."""
        all_actions = get_all_registered_actions()
        severities = {t.severity for t in all_actions.values()}
        assert len(severities) >= 3, (
            f"Expected at least 3 severity levels represented, got {len(severities)}: {severities}"
        )

    def test_high_severity_actions_require_confirmation(self):
        """HIGH and CRITICAL actions must require confirmation."""
        for key, timeline in get_all_registered_actions().items():
            if timeline.severity in (ActionSeverity.HIGH, ActionSeverity.CRITICAL):
                assert timeline.requires_confirmation, (
                    f"HIGH/CRITICAL action '{key}' must require confirmation"
                )
