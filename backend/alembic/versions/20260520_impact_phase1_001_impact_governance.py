# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""impact measurement layer — Phase 1 governance

Revision ID: impact_phase1_001
Revises: bc_waitlist_001
Create Date: 2026-05-20 00:00:00.000000+00:00

Adds the two governance tables that scaffold the impact-measurement
layer:

  * ``outcome_indicators`` — catalog of community-level outcomes the
    library is willing to claim contribution to. Approval-gated.
  * ``theory_of_change_claims`` — links a program or strategic
    initiative to an outcome indicator with mechanism + evidence ladder
    + annual review. CHECK constraint enforces exactly-one of
    ``contributing_program_id`` / ``contributing_initiative_id``.

Plus:
  * ``strategic_kpis.outcome_indicator_id`` — nullable FK so a KPI can
    point at a community outcome.
  * ``organization_features.impact_measurement_enabled`` — feature
    flag, default false (opt-in per library).
  * Seven new ``auditaction`` enum values for governance state changes
    (created / approved / retired for indicators; created / reviewed /
    promoted / retired for claims).

Idempotent: every step uses ``IF [NOT] EXISTS`` because L30's
``init_db.py`` may have already created the tables from the SQLAlchemy
models by the time alembic runs. See ``feedback_l30_init_db_vs_alembic_new_table``.

ALTER TYPE ... ADD VALUE: on PG 16 (L30 prod) this runs fine inside a
transaction, but the IF NOT EXISTS guards make it safe to re-run on
any backing version.
"""
from typing import Sequence, Union

from alembic import op


revision: str = "impact_phase1_001"
down_revision: Union[str, None] = "bc_waitlist_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_AUDIT_ACTION_VALUES = (
    "outcome_indicator_created",
    "outcome_indicator_approved",
    "outcome_indicator_retired",
    "claim_created",
    "claim_reviewed",
    "claim_promoted",
    "claim_retired",
)


def upgrade() -> None:
    # -----------------------------------------------------------------
    # 1. outcome_indicators
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS outcome_indicators (
            id SERIAL PRIMARY KEY,
            slug VARCHAR(120) NOT NULL UNIQUE,
            name VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            unit VARCHAR(40) NOT NULL,
            direction_better VARCHAR(8) NOT NULL,
            cadence VARCHAR(16) NOT NULL,
            geographic_scope_type VARCHAR(24) NOT NULL,
            primary_source VARCHAR(255),
            source_url VARCHAR(500),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            requires_board_approval BOOLEAN NOT NULL DEFAULT FALSE,
            approved_at TIMESTAMPTZ,
            approved_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            board_decision_link_id INTEGER REFERENCES board_decision_links(id) ON DELETE SET NULL,
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    # ADD COLUMN IF NOT EXISTS for each — survives init_db pre-creation
    # against an older model version that may be missing newer fields.
    _outcome_indicator_columns = [
        ("slug", "VARCHAR(120) NOT NULL"),
        ("name", "VARCHAR(255) NOT NULL"),
        ("description", "TEXT NOT NULL"),
        ("unit", "VARCHAR(40) NOT NULL"),
        ("direction_better", "VARCHAR(8) NOT NULL"),
        ("cadence", "VARCHAR(16) NOT NULL"),
        ("geographic_scope_type", "VARCHAR(24) NOT NULL"),
        ("primary_source", "VARCHAR(255)"),
        ("source_url", "VARCHAR(500)"),
        ("is_active", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("requires_board_approval", "BOOLEAN NOT NULL DEFAULT FALSE"),
        ("approved_at", "TIMESTAMPTZ"),
        ("approved_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("board_decision_link_id", "INTEGER REFERENCES board_decision_links(id) ON DELETE SET NULL"),
        ("created_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
    ]
    for col, decl in _outcome_indicator_columns:
        op.execute(
            f"ALTER TABLE outcome_indicators ADD COLUMN IF NOT EXISTS {col} {decl}"
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outcome_indicators_slug "
        "ON outcome_indicators (slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_outcome_indicators_active_scope "
        "ON outcome_indicators (is_active, geographic_scope_type)"
    )

    # CHECK constraints. Postgres < 9.x lacks IF NOT EXISTS on ADD
    # CONSTRAINT, so guard via DO block.
    for name, expr in [
        (
            "ck_outcome_indicator_direction_better",
            "direction_better IN ('up', 'down')",
        ),
        (
            "ck_outcome_indicator_cadence",
            "cadence IN ('monthly', 'quarterly', 'semi_annual', 'annual')",
        ),
        (
            "ck_outcome_indicator_geographic_scope_type",
            "geographic_scope_type IN ('census_tract', 'school_district',"
            " 'zip', 'county', 'service_area', 'custom')",
        ),
    ]:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{name}'
                ) THEN
                    ALTER TABLE outcome_indicators
                        ADD CONSTRAINT {name} CHECK ({expr});
                END IF;
            END
            $$
            """
        )

    # -----------------------------------------------------------------
    # 2. theory_of_change_claims
    # -----------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS theory_of_change_claims (
            id SERIAL PRIMARY KEY,
            outcome_indicator_id INTEGER NOT NULL
                REFERENCES outcome_indicators(id) ON DELETE RESTRICT,
            contributing_program_id INTEGER
                REFERENCES programs(id) ON DELETE SET NULL,
            contributing_initiative_id INTEGER
                REFERENCES strategic_initiatives(id) ON DELETE SET NULL,
            mechanism_short VARCHAR(280) NOT NULL,
            mechanism_detail TEXT NOT NULL,
            evidence_strength VARCHAR(24) NOT NULL DEFAULT 'theoretical',
            evidence_citations TEXT,
            intended_dose VARCHAR(255),
            expected_lag VARCHAR(120),
            reviewed_at TIMESTAMPTZ,
            reviewed_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            next_review_due DATE,
            board_decision_link_id INTEGER
                REFERENCES board_decision_links(id) ON DELETE SET NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            retired_at TIMESTAMPTZ,
            retired_reason TEXT,
            created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    _claim_columns = [
        ("outcome_indicator_id", "INTEGER NOT NULL REFERENCES outcome_indicators(id) ON DELETE RESTRICT"),
        ("contributing_program_id", "INTEGER REFERENCES programs(id) ON DELETE SET NULL"),
        ("contributing_initiative_id", "INTEGER REFERENCES strategic_initiatives(id) ON DELETE SET NULL"),
        ("mechanism_short", "VARCHAR(280) NOT NULL"),
        ("mechanism_detail", "TEXT NOT NULL"),
        ("evidence_strength", "VARCHAR(24) NOT NULL DEFAULT 'theoretical'"),
        ("evidence_citations", "TEXT"),
        ("intended_dose", "VARCHAR(255)"),
        ("expected_lag", "VARCHAR(120)"),
        ("reviewed_at", "TIMESTAMPTZ"),
        ("reviewed_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("next_review_due", "DATE"),
        ("board_decision_link_id", "INTEGER REFERENCES board_decision_links(id) ON DELETE SET NULL"),
        ("is_active", "BOOLEAN NOT NULL DEFAULT TRUE"),
        ("retired_at", "TIMESTAMPTZ"),
        ("retired_reason", "TEXT"),
        ("created_by_user_id", "INTEGER REFERENCES users(id) ON DELETE SET NULL"),
        ("created_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
        ("updated_at", "TIMESTAMPTZ NOT NULL DEFAULT NOW()"),
    ]
    for col, decl in _claim_columns:
        op.execute(
            f"ALTER TABLE theory_of_change_claims ADD COLUMN IF NOT EXISTS {col} {decl}"
        )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_theory_of_change_claims_outcome_indicator_id "
        "ON theory_of_change_claims (outcome_indicator_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_theory_of_change_claims_indicator_active "
        "ON theory_of_change_claims (outcome_indicator_id, is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_theory_of_change_claims_next_review "
        "ON theory_of_change_claims (next_review_due) "
        "WHERE is_active = TRUE"
    )

    for name, expr in [
        (
            "ck_claim_program_xor_initiative",
            "(contributing_program_id IS NULL) <> (contributing_initiative_id IS NULL)",
        ),
        (
            "ck_claim_evidence_strength",
            "evidence_strength IN ('theoretical', 'program_aligned',"
            " 'outcome_correlated', 'quasi_experimental', 'experimental')",
        ),
    ]:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint WHERE conname = '{name}'
                ) THEN
                    ALTER TABLE theory_of_change_claims
                        ADD CONSTRAINT {name} CHECK ({expr});
                END IF;
            END
            $$
            """
        )

    # -----------------------------------------------------------------
    # 3. strategic_kpis.outcome_indicator_id (nullable, SET NULL)
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE strategic_kpis "
        "ADD COLUMN IF NOT EXISTS outcome_indicator_id INTEGER "
        "REFERENCES outcome_indicators(id) ON DELETE SET NULL"
    )

    # -----------------------------------------------------------------
    # 4. organization_features.impact_measurement_enabled
    # -----------------------------------------------------------------
    op.execute(
        "ALTER TABLE organization_features "
        "ADD COLUMN IF NOT EXISTS impact_measurement_enabled "
        "BOOLEAN NOT NULL DEFAULT FALSE"
    )

    # -----------------------------------------------------------------
    # 5. AuditAction enum — add governance values
    # -----------------------------------------------------------------
    for value in _AUDIT_ACTION_VALUES:
        op.execute(
            f"ALTER TYPE auditaction ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    # Reverse order; idempotent guards so partial migrations roll back
    # cleanly. PG cannot remove enum values without recreating the
    # type, so the auditaction additions are intentionally left in
    # place — they cost nothing and a fresh upgrade will simply find
    # them already present.

    op.execute(
        "ALTER TABLE organization_features "
        "DROP COLUMN IF EXISTS impact_measurement_enabled"
    )

    op.execute(
        "ALTER TABLE strategic_kpis "
        "DROP COLUMN IF EXISTS outcome_indicator_id"
    )

    op.execute("DROP INDEX IF EXISTS ix_theory_of_change_claims_next_review")
    op.execute("DROP INDEX IF EXISTS ix_theory_of_change_claims_indicator_active")
    op.execute("DROP INDEX IF EXISTS ix_theory_of_change_claims_outcome_indicator_id")
    op.execute("DROP TABLE IF EXISTS theory_of_change_claims")

    op.execute("DROP INDEX IF EXISTS ix_outcome_indicators_active_scope")
    op.execute("DROP INDEX IF EXISTS ix_outcome_indicators_slug")
    op.execute("DROP TABLE IF EXISTS outcome_indicators")
