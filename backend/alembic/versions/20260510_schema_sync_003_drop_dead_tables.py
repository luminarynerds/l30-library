"""drop dead tables removed from models

Revision ID: schema_sync_003
Revises: schema_sync_002
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "schema_sync_003"
down_revision: Union[str, None] = "schema_sync_002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Pre-beta cleanup: drop 22 tables whose models have been removed.
    # DB backup: /tmp/l30_pre_migration_20260510.sql.gz

    # ── Step 1: child/junction tables (have FKs to other tables being dropped) ──
    op.drop_index("ix_patron_nudge_state_patron_status", table_name="patron_nudge_state")
    op.drop_table("patron_nudge_state")

    op.drop_index("ix_curated_shelf_items_catalog_item_id", table_name="curated_shelf_items")
    op.drop_index("ix_curated_shelf_items_shelf_id", table_name="curated_shelf_items")
    op.drop_table("curated_shelf_items")

    # ── Step 2: parent tables (safe now that children are gone) ──
    op.drop_index("ix_nudges_slug", table_name="nudges")
    op.drop_table("nudges")

    op.drop_table("curated_shelves")

    # ── Step 3: standalone empty tables (0 rows, no FK dependents) ──
    op.drop_index("ix_author_payout_history_author_id", table_name="author_payout_history")
    op.drop_index("ix_author_payout_history_id", table_name="author_payout_history")
    op.drop_index("ix_author_payout_history_status", table_name="author_payout_history")
    op.drop_table("author_payout_history")

    op.drop_index("ix_author_balances_author_id", table_name="author_balances")
    op.drop_index("ix_author_balances_id", table_name="author_balances")
    op.drop_table("author_balances")

    op.drop_table("author_profiles")
    op.drop_table("author_update_types")
    op.drop_table("editorial_feature_types")
    op.drop_table("ebook_submission_reviews")

    op.drop_index("ix_indie_ebook_versions_changed_by_name", table_name="indie_ebook_versions")
    op.drop_index("ix_indie_ebook_versions_ebook_id", table_name="indie_ebook_versions")
    op.drop_index("ix_indie_ebook_versions_id", table_name="indie_ebook_versions")
    op.drop_table("indie_ebook_versions")

    op.drop_table("indie_platform_settings")

    op.drop_index("ix_oauth_accounts_id", table_name="oauth_accounts")
    op.drop_index("ix_oauth_accounts_provider", table_name="oauth_accounts")
    op.drop_index("ix_oauth_accounts_user_id", table_name="oauth_accounts")
    op.drop_table("oauth_accounts")

    op.drop_index("ix_public_domain_hashes_file_hash", table_name="public_domain_hashes")
    op.drop_index("ix_public_domain_hashes_id", table_name="public_domain_hashes")
    op.drop_table("public_domain_hashes")

    op.drop_index("ix_royalty_audit_logs_author_id", table_name="royalty_audit_logs")
    op.drop_index("ix_royalty_audit_logs_change_type", table_name="royalty_audit_logs")
    op.drop_index("ix_royalty_audit_logs_id", table_name="royalty_audit_logs")
    op.drop_table("royalty_audit_logs")

    op.drop_index("ix_patron_reading_lists_patron", table_name="patron_reading_lists")
    op.drop_index(
        "ix_patron_reading_lists_share_token",
        table_name="patron_reading_lists",
        postgresql_where="(share_token IS NOT NULL)",
    )
    op.drop_table("patron_reading_lists")

    # ── Step 4: tables with data but no FK dependents ──
    op.drop_table("library_branding")

    op.drop_index("ix_beta_feedback_id", table_name="beta_feedback")
    op.drop_index("ix_beta_feedback_type", table_name="beta_feedback")
    op.drop_table("beta_feedback")

    op.drop_index("ix_cms_branch", table_name="community_metrics_snapshots")
    op.drop_index("ix_cms_category", table_name="community_metrics_snapshots")
    op.drop_index("ix_cms_period", table_name="community_metrics_snapshots")
    op.drop_index("ix_community_metrics_snapshots_id", table_name="community_metrics_snapshots")
    op.drop_table("community_metrics_snapshots")

    op.drop_index("ix_cookie_of_week_id", table_name="cookie_of_week")
    op.drop_index("ix_cookie_of_week_set_by_id", table_name="cookie_of_week")
    op.drop_index("ix_cookie_of_week_week_of", table_name="cookie_of_week")
    op.drop_table("cookie_of_week")

    op.drop_index("ix_ernie_sightings_id", table_name="ernie_sightings")
    op.drop_index("ix_ernie_sightings_reported_by_id", table_name="ernie_sightings")
    op.drop_table("ernie_sightings")

    op.drop_index("ix_apscheduler_jobs_next_run_time", table_name="apscheduler_jobs")
    op.drop_table("apscheduler_jobs")

    # ── Step 5: orphaned enum types ──
    op.execute("DROP TYPE IF EXISTS beta_feedbacktype")
    op.execute("DROP TYPE IF EXISTS feedbackstatus")
    op.execute("DROP TYPE IF EXISTS feedbackpriority")


def downgrade() -> None:
    # Recreate enums first
    beta_feedbacktype = postgresql.ENUM(
        "bug", "suggestion", "confusion", "praise", "other",
        name="beta_feedbacktype", create_type=False,
    )
    feedbackstatus = postgresql.ENUM(
        "new", "reviewed", "in_progress", "resolved", "wont_fix",
        name="feedbackstatus", create_type=False,
    )
    feedbackpriority = postgresql.ENUM(
        "low", "medium", "high", "critical",
        name="feedbackpriority", create_type=False,
    )
    beta_feedbacktype.create(op.get_bind(), checkfirst=True)
    feedbackstatus.create(op.get_bind(), checkfirst=True)
    feedbackpriority.create(op.get_bind(), checkfirst=True)

    # ── Step 4 reversed: tables with data ──
    op.create_table(
        "apscheduler_jobs",
        sa.Column("id", sa.String(191), nullable=False),
        sa.Column("next_run_time", sa.Float(), nullable=True),
        sa.Column("job_state", sa.LargeBinary(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apscheduler_jobs_next_run_time", "apscheduler_jobs", ["next_run_time"])

    op.create_table(
        "ernie_sightings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("location", sa.String(100), nullable=False),
        sa.Column("activity", sa.String(200), nullable=False),
        sa.Column("spotted_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("reported_by", sa.String(100), nullable=False),
        sa.Column("reported_by_id", sa.Integer(), nullable=True),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["reported_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ernie_sightings_id", "ernie_sightings", ["id"])
    op.create_index("ix_ernie_sightings_reported_by_id", "ernie_sightings", ["reported_by_id"])

    op.create_table(
        "cookie_of_week",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("flavor", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("week_of", sa.Date(), nullable=False),
        sa.Column("next_friday", sa.Date(), nullable=False),
        sa.Column("set_by", sa.String(100), nullable=False),
        sa.Column("set_by_id", sa.Integer(), nullable=True),
        sa.Column("recipe_url", sa.String(500), nullable=True),
        sa.Column("is_classic_recipe", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["set_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_cookie_of_week_id", "cookie_of_week", ["id"])
    op.create_index("ix_cookie_of_week_set_by_id", "cookie_of_week", ["set_by_id"])
    op.create_index("ix_cookie_of_week_week_of", "cookie_of_week", ["week_of"])

    op.create_table(
        "community_metrics_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("metrics", postgresql.JSONB(), nullable=False),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("branch_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "period_start", "period_end", "period_type", "category", "branch_id",
            name="uq_cms_period_category_branch",
        ),
        sa.ForeignKeyConstraint(["branch_id"], ["branches.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_community_metrics_snapshots_id", "community_metrics_snapshots", ["id"])
    op.create_index("ix_cms_branch", "community_metrics_snapshots", ["branch_id"])
    op.create_index("ix_cms_category", "community_metrics_snapshots", ["category"])
    op.create_index("ix_cms_period", "community_metrics_snapshots", ["period_type", "period_start", "period_end"])

    op.create_table(
        "beta_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", postgresql.ENUM(
            "bug", "suggestion", "confusion", "praise", "other",
            name="beta_feedbacktype", create_type=False,
        ), nullable=False),
        sa.Column("status", postgresql.ENUM(
            "new", "reviewed", "in_progress", "resolved", "wont_fix",
            name="feedbackstatus", create_type=False,
        ), nullable=False),
        sa.Column("priority", postgresql.ENUM(
            "low", "medium", "high", "critical",
            name="feedbackpriority", create_type=False,
        ), nullable=False),
        sa.Column("subject", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("page_url", sa.String(500), nullable=True),
        sa.Column("browser_info", sa.String(300), nullable=True),
        sa.Column("screenshot_url", sa.String(500), nullable=True),
        sa.Column("submitted_by_id", sa.Integer(), nullable=True),
        sa.Column("email", sa.String(254), nullable=True),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.Integer(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["submitted_by_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resolved_by_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_beta_feedback_id", "beta_feedback", ["id"])
    op.create_index("ix_beta_feedback_type", "beta_feedback", ["type"])

    op.create_table(
        "library_branding",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("library_name", sa.String(255), nullable=False),
        sa.Column("library_short_name", sa.String(50), nullable=True),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("privacy_email", sa.String(255), nullable=True),
        sa.Column("indie_email", sa.String(255), nullable=True),
        sa.Column("giving_email", sa.String(255), nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column("address_line1", sa.String(255), nullable=True),
        sa.Column("address_line2", sa.String(255), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=True),
        sa.Column("accent_color", sa.String(7), nullable=True),
        sa.Column("card_prefix", sa.String(10), nullable=True),
        sa.Column("hero_title", sa.String(500), nullable=True),
        sa.Column("hero_subtitle", sa.String(500), nullable=True),
        sa.Column("tagline", sa.String(255), nullable=True),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("id = 1", name="singleton_branding"),
    )

    # ── Step 3 reversed: standalone tables ──
    op.create_table(
        "patron_reading_lists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patron_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("share_token", postgresql.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["patron_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_patron_reading_lists_patron", "patron_reading_lists", ["patron_id"])
    op.create_index(
        "ix_patron_reading_lists_share_token",
        "patron_reading_lists",
        ["share_token"],
        unique=True,
        postgresql_where=sa.text("share_token IS NOT NULL"),
    )

    op.create_table(
        "royalty_audit_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(50), nullable=False),
        sa.Column("old_value", sa.Float(), nullable=True),
        sa.Column("new_value", sa.Float(), nullable=True),
        sa.Column("withholding_type", sa.String(50), nullable=True),
        sa.Column("withholding_amount", sa.Float(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("changed_by_name", sa.String(200), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_royalty_audit_logs_id", "royalty_audit_logs", ["id"])
    op.create_index("ix_royalty_audit_logs_author_id", "royalty_audit_logs", ["author_id"])
    op.create_index("ix_royalty_audit_logs_change_type", "royalty_audit_logs", ["change_type"])

    op.create_table(
        "public_domain_hashes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("author", sa.String(255), nullable=True),
        sa.Column("source", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("file_hash"),
    )
    op.create_index("ix_public_domain_hashes_id", "public_domain_hashes", ["id"])
    op.create_index("ix_public_domain_hashes_file_hash", "public_domain_hashes", ["file_hash"])

    op.create_table(
        "oauth_accounts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("provider_email", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_oauth_provider_user"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_oauth_accounts_id", "oauth_accounts", ["id"])
    op.create_index("ix_oauth_accounts_provider", "oauth_accounts", ["provider"])
    op.create_index("ix_oauth_accounts_user_id", "oauth_accounts", ["user_id"])

    op.create_table(
        "indie_platform_settings",
        sa.Column("key", sa.String(100), nullable=False),
        sa.Column("value", postgresql.JSONB(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
        sa.ForeignKeyConstraint(["updated_by_id"], ["users.id"], ondelete="SET NULL"),
    )

    op.create_table(
        "indie_ebook_versions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ebook_id", sa.Integer(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("changed_fields", sa.JSON(), nullable=False),
        sa.Column("changed_by_name", sa.String(200), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("change_reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_indie_ebook_versions_id", "indie_ebook_versions", ["id"])
    op.create_index("ix_indie_ebook_versions_ebook_id", "indie_ebook_versions", ["ebook_id"])
    op.create_index("ix_indie_ebook_versions_changed_by_name", "indie_ebook_versions", ["changed_by_name"])

    op.create_table(
        "ebook_submission_reviews",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "editorial_feature_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "author_update_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("icon", sa.String(50), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("requires_linked_ebook", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("max_body_length", sa.Integer(), nullable=False, server_default=sa.text("500")),
        sa.Column("allow_image", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    op.create_table(
        "author_profiles",
        sa.Column("indie_author_id", sa.Integer(), nullable=False),
        sa.Column("photo_url", sa.String(500), nullable=True),
        sa.Column("website", sa.String(500), nullable=True),
        sa.Column("social_links", postgresql.JSONB(), nullable=True),
        sa.Column("featured_quote", sa.Text(), nullable=True),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("indie_author_id"),
    )

    op.create_table(
        "author_balances",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("available_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_balance", sa.Numeric(12, 2), nullable=False),
        sa.Column("pending_payout_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("total_transactions", sa.Integer(), nullable=False),
        sa.Column("total_checkouts", sa.Integer(), nullable=False),
        sa.Column("last_payout_date", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("available_balance >= 0", name="ck_author_balance_available_non_negative"),
        sa.CheckConstraint("paid_balance >= 0", name="ck_author_balance_paid_non_negative"),
        sa.CheckConstraint("pending_payout_amount >= 0", name="ck_author_balance_pending_non_negative"),
    )
    op.create_index("ix_author_balances_id", "author_balances", ["id"])
    op.create_index("ix_author_balances_author_id", "author_balances", ["author_id"], unique=True)

    op.create_table(
        "author_payout_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("stripe_transfer_id", sa.String(255), nullable=True),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("transaction_count", sa.Integer(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stripe_transfer_id"),
    )
    op.create_index("ix_author_payout_history_id", "author_payout_history", ["id"])
    op.create_index("ix_author_payout_history_author_id", "author_payout_history", ["author_id"])
    op.create_index("ix_author_payout_history_status", "author_payout_history", ["status"])

    # ── Step 2 reversed: parent tables ──
    op.create_table(
        "curated_shelves",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "nudges",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(100), nullable=False),
        sa.Column("trigger_conditions", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("content_title", sa.String(200), nullable=True),
        sa.Column("content_body", sa.Text(), nullable=False),
        sa.Column("content_cta_label", sa.String(100), nullable=True),
        sa.Column("content_cta_route", sa.String(200), nullable=True),
        sa.Column("delivery_type", sa.String(20), nullable=False),
        sa.Column("delivery_placement", sa.String(50), nullable=False, server_default=sa.text("'global'")),
        sa.Column("priority", sa.SmallInteger(), nullable=False, server_default=sa.text("5")),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=False, server_default=sa.text("604800")),
        sa.Column("max_impressions", sa.SmallInteger(), nullable=False, server_default=sa.text("3")),
        sa.Column("tags", postgresql.ARRAY(sa.String(50)), nullable=False, server_default=sa.text("'{}'::varchar[]")),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_nudges_slug", "nudges", ["slug"], unique=True)

    # ── Step 1 reversed: child/junction tables ──
    op.create_table(
        "curated_shelf_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("shelf_id", sa.Integer(), nullable=False),
        sa.Column("catalog_item_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("shelf_id", "catalog_item_id"),
        sa.ForeignKeyConstraint(["shelf_id"], ["curated_shelves.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["catalog_item_id"], ["catalog_items.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_curated_shelf_items_shelf_id", "curated_shelf_items", ["shelf_id"])
    op.create_index("ix_curated_shelf_items_catalog_item_id", "curated_shelf_items", ["catalog_item_id"])

    op.create_table(
        "patron_nudge_state",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("patron_id", sa.Integer(), nullable=False),
        sa.Column("nudge_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default=sa.text("'shown'")),
        sa.Column("impressions", sa.SmallInteger(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_shown_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_shown_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("patron_id", "nudge_id", name="uq_patron_nudge"),
        sa.ForeignKeyConstraint(["nudge_id"], ["nudges.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["patron_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_patron_nudge_state_patron_status", "patron_nudge_state", ["patron_id", "status"])
