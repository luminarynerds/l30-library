# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create bibframe_local_authorities and add LOCAL to authoritysource enum

Revision ID: local_authorities_001
Revises: catalog_lccn_oclc_001
Create Date: 2026-05-07 02:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "local_authorities_001"
down_revision: Union[str, None] = "catalog_lccn_oclc_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


LOCAL_AUTHORITY_TYPE_VALUES = (
    "name_personal",
    "name_corporate",
    "name_meeting",
    "name_jurisdiction",
    "subject_topic",
    "subject_geographic",
    "subject_temporal",
    "subject_genre",
    "title_uniform",
    "title_series",
    "other",
)

LOCAL_AUTHORITY_STATUS_VALUES = ("provisional", "active", "deprecated")


def upgrade() -> None:
    # ALTER TYPE ... ADD VALUE must run outside a transaction; alembic wraps
    # the migration in one by default, so use IF NOT EXISTS to make this safe
    # to re-run and avoid an explicit autocommit block.
    op.execute("ALTER TYPE authoritysource ADD VALUE IF NOT EXISTS 'local'")

    authority_type = postgresql.ENUM(
        *LOCAL_AUTHORITY_TYPE_VALUES,
        name="localauthoritytype",
        create_type=False,
    )
    authority_status = postgresql.ENUM(
        *LOCAL_AUTHORITY_STATUS_VALUES,
        name="localauthoritystatus",
        create_type=False,
    )
    authority_type.create(op.get_bind(), checkfirst=True)
    authority_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "bibframe_local_authorities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "library_system_id",
            sa.Integer(),
            sa.ForeignKey("library_systems.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "authority_type",
            authority_type,
            nullable=False,
        ),
        sa.Column(
            "status",
            authority_status,
            nullable=False,
        ),
        sa.Column("label", sa.String(length=500), nullable=False),
        sa.Column("label_normalized", sa.String(length=500), nullable=False),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column("source_notes", sa.Text(), nullable=True),
        sa.Column("variants", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("related_authorities", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("external_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "use_instead_id",
            sa.Integer(),
            sa.ForeignKey("bibframe_local_authorities.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "library_system_id",
            "authority_type",
            "label_normalized",
            name="uq_local_authority_heading",
        ),
    )
    op.create_index(
        "ix_bibframe_local_authorities_library_system_id",
        "bibframe_local_authorities",
        ["library_system_id"],
    )
    op.create_index(
        "ix_bibframe_local_authorities_authority_type",
        "bibframe_local_authorities",
        ["authority_type"],
    )
    op.create_index(
        "ix_bibframe_local_authorities_status",
        "bibframe_local_authorities",
        ["status"],
    )
    op.create_index(
        "ix_local_authority_label_normalized",
        "bibframe_local_authorities",
        ["label_normalized"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_local_authority_label_normalized",
        table_name="bibframe_local_authorities",
    )
    op.drop_index(
        "ix_bibframe_local_authorities_status",
        table_name="bibframe_local_authorities",
    )
    op.drop_index(
        "ix_bibframe_local_authorities_authority_type",
        table_name="bibframe_local_authorities",
    )
    op.drop_index(
        "ix_bibframe_local_authorities_library_system_id",
        table_name="bibframe_local_authorities",
    )
    op.drop_table("bibframe_local_authorities")
    op.execute("DROP TYPE IF EXISTS localauthoritystatus")
    op.execute("DROP TYPE IF EXISTS localauthoritytype")
    # Postgres has no clean way to remove a value from an enum; LOCAL stays
    # in authoritysource. AuthorityLink rows pointing at LOCAL would have
    # been deleted by the table drop above (FK cascade) only if links were
    # tracked there — they are not, so removing the enum value is unsafe.
