# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""add minor / patron-type gating to ai_tools, ai_guardrails, ai_usage_logs

Revision ID: ai_minor_gating_001
Revises: sip2_created_at_001
Create Date: 2026-05-07
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "ai_minor_gating_001"
down_revision: Union[str, None] = "sip2_created_at_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ai_tools: per-tool minor / patron_type access flags
    op.add_column(
        "ai_tools",
        sa.Column("block_for_minors", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ai_tools",
        sa.Column(
            "requires_parental_consent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "ai_tools",
        sa.Column(
            "block_for_patron_types",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # ai_guardrails: audience scoping for guardrail rules
    op.add_column(
        "ai_guardrails",
        sa.Column(
            "audience_minor",
            sa.String(length=20),
            nullable=False,
            server_default="all",
        ),
    )
    op.add_column(
        "ai_guardrails",
        sa.Column(
            "audience_patron_types",
            JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    # ai_usage_logs: capture audience snapshot for audit
    op.add_column(
        "ai_usage_logs",
        sa.Column("was_minor", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "ai_usage_logs",
        sa.Column("patron_type_at_request", sa.String(length=20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ai_usage_logs", "patron_type_at_request")
    op.drop_column("ai_usage_logs", "was_minor")
    op.drop_column("ai_guardrails", "audience_patron_types")
    op.drop_column("ai_guardrails", "audience_minor")
    op.drop_column("ai_tools", "block_for_patron_types")
    op.drop_column("ai_tools", "requires_parental_consent")
    op.drop_column("ai_tools", "block_for_minors")
