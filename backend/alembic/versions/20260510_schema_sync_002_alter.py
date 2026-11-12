"""alter FK constraints, enum types, nullable, and column changes

Revision ID: schema_sync_002
Revises: schema_sync_001
Create Date: 2026-05-10
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "schema_sync_002"
down_revision: Union[str, None] = "schema_sync_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── 1. FK constraint changes ──────────────────────────────────────────
    op.drop_constraint("checkouts_item_id_fkey", "checkouts", type_="foreignkey")
    op.create_foreign_key(None, "checkouts", "catalog_items", ["item_id"], ["id"], ondelete="RESTRICT")

    op.drop_constraint("holds_item_id_fkey", "holds", type_="foreignkey")
    op.create_foreign_key(None, "holds", "catalog_items", ["item_id"], ["id"], ondelete="RESTRICT")

    # ── 2. Blog posts changes ────────────────────────────────────────────
    op.drop_constraint("blog_posts_slug_key", "blog_posts", type_="unique")
    op.drop_index("ix_blog_posts_series", table_name="blog_posts")
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=True)

    op.alter_column("blog_posts", "status",
        existing_type=sa.VARCHAR(length=20),
        type_=sa.Enum("draft", "published", "scheduled", name="blog_post_status_enum", native_enum=False),
        existing_nullable=False,
        existing_server_default=sa.text("'draft'::character varying"))

    # ── 3. Board table nullable changes ───────────────────────────────────
    op.alter_column("board_legal_holds", "is_active",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true"))
    op.alter_column("board_legal_holds", "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False)

    op.alter_column("board_members", "is_chair",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("false"))

    op.alter_column("board_minutes", "is_sealed",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("false"))
    op.alter_column("board_minutes", "is_permanent",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true"))

    op.alter_column("board_record_dispositions", "record_metadata",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
        existing_server_default=sa.text("'{}'::jsonb"))
    op.alter_column("board_record_dispositions", "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False)

    op.alter_column("board_record_retention_schedules", "is_permanent",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true"))
    # Backfill nulls before NOT NULL constraint
    op.execute("UPDATE board_record_retention_schedules SET updated_at = created_at WHERE updated_at IS NULL")
    op.alter_column("board_record_retention_schedules", "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False)
    op.drop_constraint("board_record_retention_schedules_record_type_key",
        "board_record_retention_schedules", type_="unique")

    op.alter_column("board_recusal_declarations", "is_active",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true"))
    op.alter_column("board_recusal_declarations", "updated_at",
        existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False)

    op.alter_column("board_resolutions", "is_permanent",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("true"))

    op.alter_column("board_state_compliance_profiles", "is_active",
        existing_type=sa.BOOLEAN(), nullable=True, existing_server_default=sa.text("false"))
    op.alter_column("board_state_compliance_profiles", "permitted_exec_session_reasons",
        existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=True,
        existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column("board_state_compliance_profiles", "minutes_retention",
        existing_type=sa.VARCHAR(length=50), nullable=True,
        existing_server_default=sa.text("'permanent'::character varying"))
    op.alter_column("board_state_compliance_profiles", "resolution_retention",
        existing_type=sa.VARCHAR(length=50), nullable=True,
        existing_server_default=sa.text("'permanent'::character varying"))
    op.alter_column("board_state_compliance_profiles", "configured_at",
        existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True,
        existing_server_default=sa.text("now()"))

    op.alter_column("board_votes", "final_tally_recusal",
        existing_type=sa.INTEGER(), nullable=True, existing_server_default=sa.text("0"))

    # ── 4. Enum type renames ──────────────────────────────────────────────
    op.execute("ALTER TYPE alertseverity RENAME TO monitoringalertseverity")
    op.execute("ALTER TYPE shifttype RENAME TO fairnessshifttype")

    op.alter_column("legal_documents", "status",
        existing_type=postgresql.ENUM("draft", "in_review", "approved", "active",
            "archived", "superseded", "obsolete", name="legaldocumentstatus"),
        nullable=False)

    # ── 5. Column drops ──────────────────────────────────────────────────
    op.drop_index("ix_catalog_items_author_trgm", table_name="catalog_items",
        postgresql_ops={"author": "gin_trgm_ops"}, postgresql_using="gin")
    op.drop_index("ix_catalog_items_safety_category", table_name="catalog_items")
    op.drop_index("ix_catalog_items_safety_cert", table_name="catalog_items")
    op.drop_index("ix_catalog_items_search_tsv", table_name="catalog_items", postgresql_using="gin")
    op.drop_index("ix_catalog_items_title_trgm", table_name="catalog_items",
        postgresql_ops={"title": "gin_trgm_ops"}, postgresql_using="gin")
    op.drop_column("catalog_items", "search_tsv")

    op.drop_column("organization_features", "ernie_sightings_enabled")
    op.drop_column("organization_features", "seed_library_enabled")
    op.drop_column("organization_features", "cookie_of_week_enabled")

    op.drop_column("reading_registrations", "opt_out_leaderboard")

    op.drop_index("ix_royalty_transactions_borrow_id", table_name="royalty_transactions")
    op.drop_constraint("uq_royalty_transactions_access_record_id", "royalty_transactions", type_="unique")

    # ── 6. Notification type: make non-nullable ──────────────────────────
    _nt = postgresql.ENUM(
        "checkout_receipt", "due_date_reminder", "overdue_notice", "hold_ready",
        "hold_expiring", "hold_cancelled", "fine_notice", "account_locked",
        "account_transitioned", "event_reminder", "event_cancelled", "event_updated",
        "training_new_course", "training_course_completed", "training_milestone_reached",
        "training_certificate_earned", "training_streak_reminder", "training_new_content",
        "training_skill_assessment_due", "training_weekly_digest",
        "board_meeting_scheduled", "board_agenda_published", "panic_alert",
        "purchase_request_submitted", "purchase_request_ordered",
        "purchase_request_received", "purchase_request_declined",
        "welcome_email", "fine_assessment_notice", "fine_payment_confirmation",
        "event_registration_confirmation", "staff_daily_alert",
        "new_match", "match_accepted", "match_rejected",
        "swap_claimed", "swap_expiring", "claim_approved", "claim_rejected",
        name="notificationtype",
    )
    op.alter_column("notifications", "notification_type", existing_type=_nt, nullable=False)
    op.alter_column("shift_swap_notifications", "notification_type", existing_type=_nt, nullable=False)


def downgrade() -> None:
    _nt = postgresql.ENUM(
        "checkout_receipt", "due_date_reminder", "overdue_notice", "hold_ready",
        "hold_expiring", "hold_cancelled", "fine_notice", "account_locked",
        "account_transitioned", "event_reminder", "event_cancelled", "event_updated",
        "training_new_course", "training_course_completed", "training_milestone_reached",
        "training_certificate_earned", "training_streak_reminder", "training_new_content",
        "training_skill_assessment_due", "training_weekly_digest",
        "board_meeting_scheduled", "board_agenda_published", "panic_alert",
        "purchase_request_submitted", "purchase_request_ordered",
        "purchase_request_received", "purchase_request_declined",
        "welcome_email", "fine_assessment_notice", "fine_payment_confirmation",
        "event_registration_confirmation", "staff_daily_alert",
        "new_match", "match_accepted", "match_rejected",
        "swap_claimed", "swap_expiring", "claim_approved", "claim_rejected",
        name="notificationtype",
    )

    # 6. Revert notification nullable
    op.alter_column("shift_swap_notifications", "notification_type", existing_type=_nt, nullable=True)
    op.alter_column("notifications", "notification_type", existing_type=_nt, nullable=True)

    # 5. Recreate dropped columns/indexes
    op.create_unique_constraint("uq_royalty_transactions_access_record_id", "royalty_transactions", ["access_record_id"])
    op.create_index("ix_royalty_transactions_borrow_id", "royalty_transactions", ["borrow_id"])
    op.add_column("reading_registrations", sa.Column("opt_out_leaderboard", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False))
    op.add_column("organization_features", sa.Column("cookie_of_week_enabled", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False))
    op.add_column("organization_features", sa.Column("seed_library_enabled", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False))
    op.add_column("organization_features", sa.Column("ernie_sightings_enabled", sa.BOOLEAN(), server_default=sa.text("false"), nullable=False))
    op.add_column("catalog_items", sa.Column("search_tsv", postgresql.TSVECTOR(), nullable=True))
    op.create_index("ix_catalog_items_title_trgm", "catalog_items", ["title"],
        postgresql_ops={"title": "gin_trgm_ops"}, postgresql_using="gin")
    op.create_index("ix_catalog_items_search_tsv", "catalog_items", ["search_tsv"], postgresql_using="gin")
    op.create_index("ix_catalog_items_safety_cert", "catalog_items", ["safety_certification_required"])
    op.create_index("ix_catalog_items_safety_category", "catalog_items", ["safety_category"])
    op.create_index("ix_catalog_items_author_trgm", "catalog_items", ["author"],
        postgresql_ops={"author": "gin_trgm_ops"}, postgresql_using="gin")

    # 4. Revert enum renames
    op.alter_column("legal_documents", "status",
        existing_type=postgresql.ENUM("draft", "in_review", "approved", "active",
            "archived", "superseded", "obsolete", name="legaldocumentstatus"),
        nullable=True)
    op.execute("ALTER TYPE fairnessshifttype RENAME TO shifttype")
    op.execute("ALTER TYPE monitoringalertseverity RENAME TO alertseverity")

    # 3. Revert board nullable
    op.alter_column("board_votes", "final_tally_recusal", existing_type=sa.INTEGER(), nullable=False, existing_server_default=sa.text("0"))
    op.alter_column("board_state_compliance_profiles", "configured_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=False, existing_server_default=sa.text("now()"))
    op.alter_column("board_state_compliance_profiles", "resolution_retention", existing_type=sa.VARCHAR(length=50), nullable=False, existing_server_default=sa.text("'permanent'::character varying"))
    op.alter_column("board_state_compliance_profiles", "minutes_retention", existing_type=sa.VARCHAR(length=50), nullable=False, existing_server_default=sa.text("'permanent'::character varying"))
    op.alter_column("board_state_compliance_profiles", "permitted_exec_session_reasons", existing_type=postgresql.JSONB(astext_type=sa.Text()), nullable=False, existing_server_default=sa.text("'[]'::jsonb"))
    op.alter_column("board_state_compliance_profiles", "is_active", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("false"))
    op.alter_column("board_resolutions", "is_permanent", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true"))
    op.alter_column("board_recusal_declarations", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True)
    op.alter_column("board_recusal_declarations", "is_active", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true"))
    op.create_unique_constraint("board_record_retention_schedules_record_type_key", "board_record_retention_schedules", ["record_type"])
    op.alter_column("board_record_retention_schedules", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True)
    op.alter_column("board_record_retention_schedules", "is_permanent", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true"))
    op.alter_column("board_record_dispositions", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True)
    op.alter_column("board_record_dispositions", "record_metadata",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True, existing_server_default=sa.text("'{}'::jsonb"))
    op.alter_column("board_minutes", "is_permanent", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true"))
    op.alter_column("board_minutes", "is_sealed", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("false"))
    op.alter_column("board_members", "is_chair", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("false"))
    op.alter_column("board_legal_holds", "updated_at", existing_type=postgresql.TIMESTAMP(timezone=True), nullable=True)
    op.alter_column("board_legal_holds", "is_active", existing_type=sa.BOOLEAN(), nullable=False, existing_server_default=sa.text("true"))

    # 2. Revert blog posts
    op.alter_column("blog_posts", "status",
        existing_type=sa.Enum("draft", "published", "scheduled", name="blog_post_status_enum", native_enum=False),
        type_=sa.VARCHAR(length=20),
        existing_nullable=False, existing_server_default=sa.text("'draft'::character varying"))
    op.drop_index("ix_blog_posts_slug", table_name="blog_posts")
    op.create_index("ix_blog_posts_slug", "blog_posts", ["slug"], unique=False)
    op.create_index("ix_blog_posts_series", "blog_posts", ["series_name"])
    op.create_unique_constraint("blog_posts_slug_key", "blog_posts", ["slug"])

    # 1. Revert FK constraints
    op.drop_constraint("holds_item_id_fkey", "holds", type_="foreignkey")
    op.create_foreign_key("holds_item_id_fkey", "holds", "catalog_items", ["item_id"], ["id"], ondelete="SET NULL")
    op.drop_constraint("checkouts_item_id_fkey", "checkouts", type_="foreignkey")
    op.create_foreign_key("checkouts_item_id_fkey", "checkouts", "catalog_items", ["item_id"], ["id"], ondelete="SET NULL")
