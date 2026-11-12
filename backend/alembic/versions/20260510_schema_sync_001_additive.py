"""add download_events, watermark_records tables and missing indexes

Revision ID: schema_sync_001
Revises: catalog_state_events_001
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "schema_sync_001"
down_revision: Union[str, None] = "catalog_state_events_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── New tables ──────────────────────────────────────────────
    op.create_table(
        "download_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("borrow_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ebook_id", sa.Integer(), nullable=False),
        sa.Column("ip_hash", sa.String(length=64), nullable=False),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("file_format", sa.String(length=20), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("watermark_id", sa.String(length=64), nullable=True),
        sa.Column("is_range_request", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["borrow_id"], ["indie_ebook_borrows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ebook_id"], ["indie_ebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_download_events_borrow_id", "download_events", ["borrow_id"])
    op.create_index("ix_download_events_created_at", "download_events", ["created_at"])
    op.create_index("ix_download_events_ebook_id", "download_events", ["ebook_id"])
    op.create_index("ix_download_events_id", "download_events", ["id"])
    op.create_index("ix_download_events_ip_hash", "download_events", ["ip_hash"])
    op.create_index("ix_download_events_user_id", "download_events", ["user_id"])

    op.create_table(
        "watermark_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("borrow_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ebook_id", sa.Integer(), nullable=False),
        sa.Column("watermark_id", sa.String(length=64), nullable=False),
        sa.Column("patron_hash", sa.String(length=64), nullable=False),
        sa.Column("library_id", sa.String(length=64), nullable=True),
        sa.Column("file_sha256", sa.String(length=64), nullable=False),
        sa.Column("original_sha256", sa.String(length=64), nullable=False),
        sa.Column("file_format", sa.String(length=10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("borrow_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["borrow_id"], ["indie_ebook_borrows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ebook_id"], ["indie_ebooks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_watermark_records_borrow_id", "watermark_records", ["borrow_id"])
    op.create_index("ix_watermark_records_ebook_id", "watermark_records", ["ebook_id"])
    op.create_index("ix_watermark_records_id", "watermark_records", ["id"])
    op.create_index("ix_watermark_records_user_id", "watermark_records", ["user_id"])
    op.create_index("ix_watermark_records_watermark_id", "watermark_records", ["watermark_id"], unique=True)

    # ── New column ──────────────────────────────────────────────
    op.add_column(
        "reading_ambassador_certifications",
        sa.Column("certification_number", sa.String(length=50), nullable=True),
    )
    op.create_index(
        "ix_reading_ambassador_certifications_certification_number",
        "reading_ambassador_certifications",
        ["certification_number"],
        unique=True,
    )

    # ── Missing indexes ─────────────────────────────────────────
    op.create_index("ix_api_keys_id", "api_keys", ["id"])
    op.create_index("ix_catalog_state_events_id", "catalog_state_events", ["id"])
    op.create_index("ix_board_coi_disclosures_id", "board_coi_disclosures", ["id"])
    op.create_index("ix_board_legal_holds_id", "board_legal_holds", ["id"])
    op.create_index("ix_board_minutes_amendments_id", "board_minutes_amendments", ["id"])
    op.create_index("ix_board_record_dispositions_id", "board_record_dispositions", ["id"])
    op.create_index("ix_board_record_retention_schedules_id", "board_record_retention_schedules", ["id"])
    op.create_index("ix_board_recusal_declarations_id", "board_recusal_declarations", ["id"])
    op.create_index("ix_board_state_compliance_profiles_id", "board_state_compliance_profiles", ["id"])
    op.create_index("ix_indie_authors_id", "indie_authors", ["id"])
    op.create_index("ix_indie_bookmarks_id", "indie_bookmarks", ["id"])
    op.create_index("ix_indie_ebook_borrows_id", "indie_ebook_borrows", ["id"])
    op.create_index("ix_indie_ebook_waitlist_id", "indie_ebook_waitlist", ["id"])
    op.create_index("ix_indie_ebooks_id", "indie_ebooks", ["id"])
    op.create_index("ix_page_meta_tags_id", "page_meta_tags", ["id"])
    op.create_index("ix_notification_history_notification_type", "notification_history", ["notification_type"])
    op.create_index("ix_notification_queue_notification_type", "notification_queue", ["notification_type"])
    op.create_index("ix_notifications_notification_type", "notifications", ["notification_type"])
    op.create_index("ix_shift_swap_notifications_notification_type", "shift_swap_notifications", ["notification_type"])
    op.create_index("ix_shift_swap_notifications_type", "shift_swap_notifications", ["notification_type"])
    op.create_index("ix_legal_documents_status", "legal_documents", ["status"])
    op.create_index("ix_legal_docs_status_category", "legal_documents", ["status", "category"])

    # ── Missing constraints ─────────────────────────────────────
    op.create_unique_constraint("uq_audit_scan_item", "audit_scans", ["audit_id", "item_copy_id"])
    op.create_unique_constraint("uq_blog_post_tags_post_tag", "blog_post_tags", ["post_id", "tag_id"])

    # ── Missing FK constraints ──────────────────────────────────
    op.create_foreign_key(
        "fk_event_registrations_event_id",
        "event_registrations", "events",
        ["event_id"], ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_overflow_purchases_royalty_transaction_id",
        "overflow_purchases", "royalty_transactions",
        ["royalty_transaction_id"], ["id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade() -> None:
    # FK constraints
    op.drop_constraint("fk_overflow_purchases_royalty_transaction_id", "overflow_purchases", type_="foreignkey")
    op.drop_constraint("fk_event_registrations_event_id", "event_registrations", type_="foreignkey")

    # Unique constraints
    op.drop_constraint("uq_blog_post_tags_post_tag", "blog_post_tags", type_="unique")
    op.drop_constraint("uq_audit_scan_item", "audit_scans", type_="unique")

    # Indexes
    op.drop_index("ix_legal_docs_status_category", table_name="legal_documents")
    op.drop_index("ix_legal_documents_status", table_name="legal_documents")
    op.drop_index("ix_shift_swap_notifications_type", table_name="shift_swap_notifications")
    op.drop_index("ix_shift_swap_notifications_notification_type", table_name="shift_swap_notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notification_queue_notification_type", table_name="notification_queue")
    op.drop_index("ix_notification_history_notification_type", table_name="notification_history")
    op.drop_index("ix_page_meta_tags_id", table_name="page_meta_tags")
    op.drop_index("ix_indie_ebooks_id", table_name="indie_ebooks")
    op.drop_index("ix_indie_ebook_waitlist_id", table_name="indie_ebook_waitlist")
    op.drop_index("ix_indie_ebook_borrows_id", table_name="indie_ebook_borrows")
    op.drop_index("ix_indie_bookmarks_id", table_name="indie_bookmarks")
    op.drop_index("ix_indie_authors_id", table_name="indie_authors")
    op.drop_index("ix_board_state_compliance_profiles_id", table_name="board_state_compliance_profiles")
    op.drop_index("ix_board_recusal_declarations_id", table_name="board_recusal_declarations")
    op.drop_index("ix_board_record_retention_schedules_id", table_name="board_record_retention_schedules")
    op.drop_index("ix_board_record_dispositions_id", table_name="board_record_dispositions")
    op.drop_index("ix_board_minutes_amendments_id", table_name="board_minutes_amendments")
    op.drop_index("ix_board_legal_holds_id", table_name="board_legal_holds")
    op.drop_index("ix_board_coi_disclosures_id", table_name="board_coi_disclosures")
    op.drop_index("ix_catalog_state_events_id", table_name="catalog_state_events")
    op.drop_index("ix_api_keys_id", table_name="api_keys")

    # Column
    op.drop_index("ix_reading_ambassador_certifications_certification_number", table_name="reading_ambassador_certifications")
    op.drop_column("reading_ambassador_certifications", "certification_number")

    # Tables
    op.drop_index("ix_watermark_records_watermark_id", table_name="watermark_records")
    op.drop_index("ix_watermark_records_user_id", table_name="watermark_records")
    op.drop_index("ix_watermark_records_id", table_name="watermark_records")
    op.drop_index("ix_watermark_records_ebook_id", table_name="watermark_records")
    op.drop_index("ix_watermark_records_borrow_id", table_name="watermark_records")
    op.drop_table("watermark_records")

    op.drop_index("ix_download_events_user_id", table_name="download_events")
    op.drop_index("ix_download_events_ip_hash", table_name="download_events")
    op.drop_index("ix_download_events_id", table_name="download_events")
    op.drop_index("ix_download_events_ebook_id", table_name="download_events")
    op.drop_index("ix_download_events_created_at", table_name="download_events")
    op.drop_index("ix_download_events_borrow_id", table_name="download_events")
    op.drop_table("download_events")
