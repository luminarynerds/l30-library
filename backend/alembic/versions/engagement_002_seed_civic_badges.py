# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed civic badges for engagement surveys

Revision ID: engagement_002
Revises: engagement_001
Create Date: 2026-05-07 00:00:01.000000

Data-only migration. Inserts three Badge rows into the existing
``learning_badges`` table so the engagement-survey dispatcher can
successfully award civic badges. Without these rows, every
``award_badge`` action would write a ``status='failed'`` SurveyOutcome.

Idempotent: ON CONFLICT (name) DO NOTHING. Safe to re-run.

Badge.name is treated as a stable slug; that is the value branching
rules pass as ``{"action": "award_badge", "badge": "civic_first_action"}``.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "engagement_002"
down_revision: Union[str, None] = "engagement_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CIVIC_BADGES = [
    {
        "name": "civic_first_action",
        "description": (
            "Took your first concrete civic action after completing an "
            "engagement survey."
        ),
        "badge_type": "achievement",
        "rarity": "common",
        "category": "civic",
        "criteria": '{"trigger": "survey_outcome", "outcome_type": "civic_email_sent"}',
        "xp_value": 25,
    },
    {
        "name": "civic_voter",
        "description": (
            "Reported participating in a local discussion or vote on AI "
            "policy in a longitudinal follow-up."
        ),
        "badge_type": "achievement",
        "rarity": "uncommon",
        "category": "civic",
        "criteria": '{"trigger": "longitudinal_response", "field": "voted_on_ai_policy"}',
        "xp_value": 50,
    },
    {
        "name": "civic_leader",
        "description": (
            "Completed the full engagement arc: Entry Pulse, mid-course "
            "checks, and longitudinal follow-up."
        ),
        "badge_type": "milestone",
        "rarity": "rare",
        "category": "civic",
        "criteria": '{"trigger": "engagement_arc_complete"}',
        "xp_value": 100,
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    stmt = sa.text("""INSERT INTO learning_badges
            (name, description, badge_type, rarity, category,
             criteria, xp_value, is_active, is_secret,
             current_awards, created_at, updated_at)
        VALUES (
            :name, :description, :badge_type, :rarity, :category,
            CAST(:criteria AS jsonb), :xp_value,
            true, false, 0, NOW(), NOW()
        )
        ON CONFLICT (name) DO NOTHING""")
    for badge in CIVIC_BADGES:
        bind.execute(stmt, badge)


def downgrade() -> None:
    names = [b["name"] for b in CIVIC_BADGES]
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "DELETE FROM learning_user_badges"
            " WHERE badge_id IN (SELECT id FROM learning_badges WHERE name = ANY(:names))"
        ),
        {"names": names},
    )
    bind.execute(
        sa.text("DELETE FROM learning_badges WHERE name = ANY(:names)"),
        {"names": names},
    )
