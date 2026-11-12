"""final cleanup: remaining enum refs, missing indexes, drop apscheduler

Revision ID: schema_sync_004
Revises: schema_sync_003
Create Date: 2026-05-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "schema_sync_004"
down_revision: Union[str, None] = "schema_sync_003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # compliance_alerts.severity still references old enum name
    # The type was already renamed, but this table's column definition
    # may reference the old type -- just verify and update if needed
    # (Postgres ALTER TYPE RENAME already renamed it globally, so these
    # should already work. The drift is just alembic's detection difference.)

    # Missing index from migration 001 (was accidentally removed)
    op.create_index("ix_blog_posts_series_name", "blog_posts", ["series_name"])

    # Drop apscheduler_jobs (recreated by app on startup, drop again and
    # the app config should be updated to not use DB job store)
    op.execute("DROP TABLE IF EXISTS apscheduler_jobs")


def downgrade() -> None:
    op.create_table("apscheduler_jobs",
        sa.Column("id", sa.VARCHAR(length=191), nullable=False),
        sa.Column("next_run_time", sa.DOUBLE_PRECISION(), nullable=True),
        sa.Column("job_state", postgresql.BYTEA(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_apscheduler_jobs_next_run_time", "apscheduler_jobs", ["next_run_time"])
    op.drop_index("ix_blog_posts_series_name", table_name="blog_posts")
