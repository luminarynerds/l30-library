# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create authority_terms and authority_term_relations tables.

Revision ID: authority_terms_001
Revises: search_tsv_generated_001
Create Date: 2026-05-08

Adds an authority-controlled browse layer to the catalog. Patrons browsing by
subject (or author/series/genre) can follow see-also, broader, and narrower
cross-references — the standard MARC 4xx/5xx authority-record relationship
model, distilled to the minimum needed to drive a navigation UI.

  authority_terms          one row per controlled heading
  authority_term_relations directed edges between headings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "authority_terms_001"
down_revision: Union[str, None] = "search_tsv_generated_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "authority_terms",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("term", sa.String(500), nullable=False),
        sa.Column(
            "normalized_term",
            sa.String(500),
            nullable=False,
            comment="Lowercased, whitespace-collapsed term used for prefix lookup.",
        ),
        sa.Column(
            "term_type",
            sa.String(40),
            nullable=False,
            comment="One of: subject, author, series, genre, geographic.",
        ),
        sa.Column("scope_note", sa.Text(), nullable=True),
        sa.Column(
            "is_preferred",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="False for non-preferred terms that exist only as 'use for' targets.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("term_type", "term", name="uq_authority_terms_type_term"),
    )
    op.create_index(
        "ix_authority_terms_type_normalized",
        "authority_terms",
        ["term_type", "normalized_term"],
    )

    op.create_table(
        "authority_term_relations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "term_id",
            sa.Integer(),
            sa.ForeignKey("authority_terms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "related_term_id",
            sa.Integer(),
            sa.ForeignKey("authority_terms.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "relation_type",
            sa.String(20),
            nullable=False,
            comment="One of: see_also, broader, narrower, use_for.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("term_id <> related_term_id", name="ck_authority_relation_no_self_loop"),
        sa.UniqueConstraint(
            "term_id", "related_term_id", "relation_type",
            name="uq_authority_relations_edge",
        ),
    )
    op.create_index(
        "ix_authority_relations_term_type",
        "authority_term_relations",
        ["term_id", "relation_type"],
    )
    op.create_index(
        "ix_authority_relations_related_type",
        "authority_term_relations",
        ["related_term_id", "relation_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_authority_relations_related_type", table_name="authority_term_relations")
    op.drop_index("ix_authority_relations_term_type", table_name="authority_term_relations")
    op.drop_table("authority_term_relations")
    op.drop_index("ix_authority_terms_type_normalized", table_name="authority_terms")
    op.drop_table("authority_terms")
