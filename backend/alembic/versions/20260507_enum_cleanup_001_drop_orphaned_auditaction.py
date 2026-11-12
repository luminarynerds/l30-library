# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""drop orphaned privacy_change_strain_list from auditaction enum

The value 'privacy_change_strain_list' exists in the DB enum but not in
the Python AuditAction model (likely a typo of privacy_change_reading_list).
Zero rows reference it. This migration removes it via the standard
rename-recreate dance since PostgreSQL does not support DROP VALUE on enums.

Revision ID: enum_cleanup_001
Revises: sip2_created_at_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "enum_cleanup_001"
down_revision: Union[str, None] = "sip2_created_at_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every value EXCEPT the orphaned 'privacy_change_strain_list'.
_KEEP_VALUES = [
    "create_user",
    "update_user",
    "delete_user",
    "revert_user_update",
    "lock_user",
    "unlock_user",
    "activate_user",
    "deactivate_user",
    "reset_password",
    "change_role",
    "logout",
    "bulk_lock",
    "bulk_unlock",
    "bulk_activate",
    "bulk_deactivate",
    "bulk_delete",
    "revert_lock_user",
    "revert_unlock_user",
    "revert_fine_waive",
    "revert_privacy_change",
    "revert_patron_merge",
    "gdpr_deletion_requested",
    "gdpr_deletion_cancelled",
    "gdpr_deletion_completed",
    "gdpr_data_exported",
    "staff_initiated_deletion",
    "child_to_adult_transition",
    "patron_merge",
    "patron_restoration",
    "patron_restore",
    "patron_suspension_reversed",
    "circulation_undo_checkout",
    "circulation_undo_hold",
    "circulation_undo_renewal",
    "circulation_reverse_return",
    "circulation_revert_item_status",
    "fee_estimated",
    "fee_paid",
    "fee_waived",
    "fine_payment_reversed",
    "check_bounced",
    "check_cleared",
    "card_reported_stolen",
    "card_replaced",
    "waiver_frequency_alert",
    "claims_returned_escalation",
    "extension_granted",
    "privacy_setting_changed",
    "privacy_change_favorites",
    "privacy_change_reading_list",
    "privacy_change_generic",
    "content_flagged",
    "content_moderated",
    "content_removed",
    "board_member_created",
    "committee_created",
    "meeting_created",
    "meeting_updated",
    "meeting_cancelled",
    "motion_created",
    "motion_seconded",
    "minutes_approved",
    "vote_created",
    "vote_opened",
    "vote_cast",
    "vote_closed",
    "action_item_created",
    "action_item_status_changed",
    "request_received",
    "request_acknowledged",
    "request_denied",
    "records_released",
    "appeal_filed",
    "appeal_decided",
    "document_published",
    "strategic_goal_created",
    "status_changed",
    "note_added",
    "viewed",
    "settings_reverted",
    "redaction_started",
    "two_fa_enabled",
    "two_fa_disabled",
    "two_fa_verify_success",
    "two_fa_verify_failed",
    "recovery_code_used",
    "recovery_codes_regenerated",
    "recovery_email_added",
    "recovery_email_verified",
    "recovery_email_removed",
    "security_alert_sent",
    "login_success",
    "login_failed",
    "login_locked",
    "password_changed",
    "session_revoked",
    "all_sessions_revoked",
    "new_device_detected",
]


def upgrade() -> None:
    enum_values = ", ".join(f"'{v}'" for v in _KEEP_VALUES)
    # Rename-recreate dance: PG cannot drop a single enum value.
    op.execute(sa.text("ALTER TYPE auditaction RENAME TO auditaction_old"))
    op.execute(sa.text(f"CREATE TYPE auditaction AS ENUM ({enum_values})"))
    op.execute(
        sa.text(
            "ALTER TABLE audit_logs "
            "ALTER COLUMN action TYPE auditaction "
            "USING action::text::auditaction"
        )
    )
    op.execute(sa.text("DROP TYPE auditaction_old"))


def downgrade() -> None:
    op.execute(
        sa.text(
            "ALTER TYPE auditaction ADD VALUE IF NOT EXISTS "
            "'privacy_change_strain_list'"
        )
    )
