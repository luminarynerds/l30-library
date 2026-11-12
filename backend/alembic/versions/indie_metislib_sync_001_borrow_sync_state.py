"""indie borrow metislib sync state

Adds metislib_sync_state to indie_ebook_borrows so a failed L30->MetisLib sync
(borrow/return mirror) is distinguishable from a local-only borrow, enabling the
reconcile job. Backfills existing synced rows (those with a metislib_borrow_id).

Revision ID: indie_metislib_sync_001
Revises: indie_own_data_002
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = "indie_metislib_sync_001"
down_revision = "indie_own_data_002"
branch_labels = None
depends_on = None


def upgrade():
    syncstate = sa.Enum(
        "not_required", "synced", "borrow_failed", "return_failed",
        name="metislibsyncstate",
    )
    syncstate.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "indie_ebook_borrows",
        sa.Column(
            "metislib_sync_state", syncstate,
            nullable=False, server_default="not_required",
        ),
    )
    op.create_index(
        "ix_indie_ebook_borrows_metislib_sync_state",
        "indie_ebook_borrows", ["metislib_sync_state"],
    )
    # Backfill: borrows that already synced (have a metislib_borrow_id) are synced.
    op.execute(
        "UPDATE indie_ebook_borrows SET metislib_sync_state='synced' "
        "WHERE metislib_borrow_id IS NOT NULL"
    )


def downgrade():
    op.drop_index(
        "ix_indie_ebook_borrows_metislib_sync_state",
        table_name="indie_ebook_borrows",
    )
    op.drop_column("indie_ebook_borrows", "metislib_sync_state")
    sa.Enum(name="metislibsyncstate").drop(op.get_bind(), checkfirst=True)
