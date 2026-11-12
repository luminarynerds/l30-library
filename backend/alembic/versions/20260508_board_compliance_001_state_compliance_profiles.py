# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""board_compliance: state compliance profiles

Revision ID: board_compliance_001
Revises: dbsub_session_ttl_001
Create Date: 2026-05-08

Adds board_state_compliance_profiles table for configuring state-specific
open meeting law and public records requirements. Seeds Utah profile
(Utah Code 52-4, 63G-2).

Schema-only, additive, prod-safe:
  * Creates board_state_compliance_profiles table
  * Seeds Utah compliance profile with is_active=True
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "board_compliance_001"
down_revision: Union[str, None] = "board_retention_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotency check
    if not op.get_context().as_sql:
        bind = op.get_bind()
        result = bind.execute(
            sa.text("SELECT 1 FROM information_schema.tables WHERE table_name='board_state_compliance_profiles'")
        )
        if result.fetchone():
            return

    op.create_table(
        "board_state_compliance_profiles",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("state_code", sa.String(2), nullable=False),
        sa.Column("state_name", sa.String(100), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        # Open meeting law
        sa.Column("notice_lead_hours", sa.Integer(), nullable=False),
        sa.Column("emergency_notice_rule", sa.String(500), nullable=True),
        sa.Column("open_meeting_law_citation", sa.String(500), nullable=True),
        sa.Column("permitted_exec_session_reasons", JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
        # Public records law
        sa.Column("public_records_law_name", sa.String(200), nullable=True),
        sa.Column("public_records_response_days", sa.Integer(), nullable=True),
        sa.Column("public_records_law_citation", sa.String(500), nullable=True),
        # Retention defaults
        sa.Column("minutes_retention", sa.String(50), server_default=sa.text("'permanent'"), nullable=False),
        sa.Column("resolution_retention", sa.String(50), server_default=sa.text("'permanent'"), nullable=False),
        # Configuration audit
        sa.Column("configured_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("configured_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_board_state_compliance_profiles_state_code", "board_state_compliance_profiles", ["state_code"], unique=True)
    op.create_index("ix_board_state_compliance_profiles_is_active", "board_state_compliance_profiles", ["is_active"])

    # Seed Utah profile
    exec_reasons_json = '[{"code": "personnel", "citation": "52-4-205(1)(a)", "description": "Discussion of the character, professional competence, or physical or mental health of an individual"}, {"code": "litigation", "citation": "52-4-205(1)(c)", "description": "Strategy sessions with respect to pending or reasonably imminent litigation"}, {"code": "property", "citation": "52-4-205(1)(d)", "description": "Strategy sessions with respect to the purchase, exchange, or lease of real property"}, {"code": "attorney_client", "citation": "52-4-205(1)(e)", "description": "Strategy sessions with respect to security matters or the deployment of security personnel"}, {"code": "security", "citation": "52-4-205(1)(f)", "description": "Discussion regarding deployment of security personnel, devices, or systems"}, {"code": "investigative", "citation": "52-4-205(1)(g)", "description": "Investigative proceedings regarding allegations of criminal misconduct"}]'
    op.execute(sa.text("""
        INSERT INTO board_state_compliance_profiles (
            state_code, state_name, is_active,
            notice_lead_hours, emergency_notice_rule, open_meeting_law_citation,
            permitted_exec_session_reasons,
            public_records_law_name, public_records_response_days, public_records_law_citation,
            minutes_retention, resolution_retention
        ) VALUES (
            'UT', 'Utah', true,
            24, 'Best notice practicable for emergency meetings (Utah Code 52-4-202(5))',
            'Utah Open and Public Meetings Act, Utah Code 52-4',
            :exec_reasons,
            'Government Records Access and Management Act (GRAMA)',
            10,
            'Utah Code 63G-2',
            'permanent', 'permanent'
        )
    """).bindparams(exec_reasons=exec_reasons_json))


def downgrade() -> None:
    op.drop_index("ix_board_state_compliance_profiles_is_active", table_name="board_state_compliance_profiles")
    op.drop_index("ix_board_state_compliance_profiles_state_code", table_name="board_state_compliance_profiles")
    op.drop_table("board_state_compliance_profiles")
