# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create partner_agencies + parent_onboarding_followups + parent_onboarding_referrals.

Revision ID: po_followup_referrals_001
Revises: patron_category_001
Create Date: 2026-05-25

Promotes parent-onboarding session follow-ups and referrals from
delimited-string columns (which the prod DB never actually shipped --
the spec was based on a stale FE-TS-types snapshot, the columns don't
exist) to first-class linked records. Adds three tables:

  - partner_agencies              canonical agency lookup (WIC, SNAP, ...)
  - parent_onboarding_followups   tracked tasks with assignee + status
  - parent_onboarding_referrals   per-session referrals, linked or freetext

Idempotency: every CREATE TABLE uses IF NOT EXISTS because init_db.py at
container startup auto-creates from SQLAlchemy model metadata BEFORE
alembic runs (see feedback_l30_init_db_vs_alembic_new_table). The CHECK
constraint on parent_onboarding_referrals is added in a separate ALTER
that is also idempotent (catalog probe before add).
"""
from alembic import op
import sqlalchemy as sa


revision = "po_followup_referrals_001"
down_revision = "patron_category_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # partner_agencies (lookup, seeded empty)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS partner_agencies (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(64) NOT NULL,
            agency_type VARCHAR(64),
            contact_phone VARCHAR(32),
            contact_email VARCHAR(255),
            website_url VARCHAR(500),
            service_area VARCHAR(255),
            languages_served VARCHAR[] DEFAULT ARRAY[]::VARCHAR[],
            notes TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_partner_agencies_slug UNIQUE (slug)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_partner_agencies_slug "
        "ON partner_agencies(slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_partner_agencies_is_active "
        "ON partner_agencies(is_active)"
    )

    # ------------------------------------------------------------------
    # parent_onboarding_followups
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS parent_onboarding_followups (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL
                REFERENCES parent_onboarding_sessions(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            assignee_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL,
            due_date DATE NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'open',
            priority VARCHAR(16) NOT NULL DEFAULT 'normal',
            completed_at TIMESTAMPTZ,
            completed_by_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL,
            completion_note TEXT,
            created_by_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_followups_session_id "
        "ON parent_onboarding_followups(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_followups_assignee_id "
        "ON parent_onboarding_followups(assignee_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_followups_due_date "
        "ON parent_onboarding_followups(due_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_followups_status "
        "ON parent_onboarding_followups(status)"
    )
    # Composite index for the reminder query (assignee_id, status, due_date).
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_followup_assignee_status_due "
        "ON parent_onboarding_followups(assignee_id, status, due_date)"
    )

    # ------------------------------------------------------------------
    # parent_onboarding_referrals
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS parent_onboarding_referrals (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL
                REFERENCES parent_onboarding_sessions(id) ON DELETE CASCADE,
            partner_agency_id INTEGER
                REFERENCES partner_agencies(id) ON DELETE SET NULL,
            agency_name_freetext VARCHAR(255),
            purpose VARCHAR(255) NOT NULL,
            status VARCHAR(32) NOT NULL DEFAULT 'made',
            warm_handoff BOOLEAN NOT NULL DEFAULT FALSE,
            patron_consent_to_share BOOLEAN NOT NULL DEFAULT FALSE,
            notes TEXT,
            made_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            made_by_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_referrals_session_id "
        "ON parent_onboarding_referrals(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_referrals_partner_agency_id "
        "ON parent_onboarding_referrals(partner_agency_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_referrals_status "
        "ON parent_onboarding_referrals(status)"
    )

    # CHECK constraint: at least one of (partner_agency_id, agency_name_freetext)
    # must be populated. Probe the catalog to keep this idempotent across
    # re-runs (alembic stamps + replays do happen during onboarding).
    has_check = False
    if not op.get_context().as_sql:
        bind = op.get_bind()
        has_check = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname = 'ck_referrals_agency_or_freetext' AND conrelid = "
            "'parent_onboarding_referrals'::regclass"
        )).first() is not None
    if not has_check:
        op.execute(
            "ALTER TABLE parent_onboarding_referrals "
            "ADD CONSTRAINT ck_referrals_agency_or_freetext "
            "CHECK (partner_agency_id IS NOT NULL "
            "       OR agency_name_freetext IS NOT NULL)"
        )


def downgrade() -> None:
    """Drop the three tables in reverse FK order.

    Downgrade is best-effort: in production we don't expect to roll this
    forward-and-back, but the reverse path keeps the migration playable
    on a fresh dev DB.
    """
    if op.get_context().as_sql:
        existing = {
            "parent_onboarding_referrals",
            "parent_onboarding_followups",
            "partner_agencies",
        }
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing = set(inspector.get_table_names())

    if "parent_onboarding_referrals" in existing:
        op.execute(
            "ALTER TABLE parent_onboarding_referrals "
            "DROP CONSTRAINT IF EXISTS ck_referrals_agency_or_freetext"
        )
        op.drop_table("parent_onboarding_referrals")

    if "parent_onboarding_followups" in existing:
        op.drop_table("parent_onboarding_followups")

    if "partner_agencies" in existing:
        op.drop_table("partner_agencies")
