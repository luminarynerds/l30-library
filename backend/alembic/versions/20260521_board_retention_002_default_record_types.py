# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""board_record_retention_schedules: seed 9 additional record types

Extends the defaults seeded by board_retention_001 (which shipped 4 types:
minutes, resolution, motion, document) to cover the record classes the
board admin UI exposes but cannot currently render without retention rules.

Idempotent: inserts each record_type only if missing. The prod DB does not
enforce a unique constraint on record_type (model says unique=True but the
constraint never landed in the schema), so we check existence per row
rather than relying on ON CONFLICT.
"""
from typing import Sequence, Union

import datetime

from alembic import op
import sqlalchemy as sa


_NOW = datetime.datetime.now(datetime.timezone.utc)


revision: str = "board_retention_002"
down_revision: Union[str, None] = "family_card_flag_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


DEFAULTS = [
    # (record_type, retention_years, is_permanent, description, legal_authority)
    ("bylaws", None, True,
     "Bylaws and amendments are permanent governance records.",
     "State public records statutes; nonprofit governance norms."),
    ("policy", None, True,
     "Adopted board policies are permanent governance records.",
     "State public records statutes."),
    ("agenda", 7, False,
     "Meeting agendas retained for 7 years.",
     "State library General Records Schedule."),
    ("audit_report", 7, False,
     "Independent audit reports retained for 7 years.",
     "IRS and state auditor record-retention norms."),
    ("financial_report", 7, False,
     "Board-level financial reports retained for 7 years.",
     "IRS and state auditor norms."),
    ("coi_disclosure", 4, False,
     "Conflict-of-interest disclosures retained 4 years after the member's term ends.",
     "Nonprofit governance and state board norms."),
    ("recusal_declaration", 4, False,
     "Recusal declarations on individual items retained for 4 years.",
     "Nonprofit governance norms; cross-reference state sunshine laws."),
    ("public_comment", 4, False,
     "Submitted public comments on board matters retained for 4 years.",
     "State sunshine and open-meetings law typical retention."),
    ("correspondence", 4, False,
     "Board-related correspondence retained for 4 years.",
     "State public records general schedules."),
]


def upgrade() -> None:
    if op.get_context().as_sql:
        # Offline mode: emit all default rows; the operator decides how to
        # reconcile duplicates against any pre-existing record_type values.
        existing: set[str] = set()
    else:
        bind = op.get_bind()
        existing = {
            row[0] for row in bind.execute(
                sa.text("SELECT record_type FROM board_record_retention_schedules")
            )
        }
    new_rows = [
        {
            "record_type": rt,
            "retention_years": years,
            "is_permanent": perm,
            "description": desc,
            "legal_authority": authority,
            "created_at": _NOW,
            "updated_at": _NOW,
        }
        for rt, years, perm, desc, authority in DEFAULTS
        if rt not in existing
    ]

    if not new_rows:
        return

    schedules_table = sa.table(
        "board_record_retention_schedules",
        sa.column("record_type", sa.String),
        sa.column("retention_years", sa.Integer),
        sa.column("is_permanent", sa.Boolean),
        sa.column("description", sa.Text),
        sa.column("legal_authority", sa.String),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    op.bulk_insert(schedules_table, new_rows)


def downgrade() -> None:
    record_types = ", ".join(f"'{d[0]}'" for d in DEFAULTS)
    op.execute(
        "DELETE FROM board_record_retention_schedules "
        f"WHERE record_type IN ({record_types})"
    )
