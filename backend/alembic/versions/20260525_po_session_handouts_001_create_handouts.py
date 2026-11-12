# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Create resource_handouts + parent_onboarding_session_handouts.

Revision ID: po_session_handouts_001
Revises: po_followup_referrals_001
Create Date: 2026-05-25

Adds the structured resource-catalog tables that replace the freeform
``resources_provided`` string on the Complete Session form. Two tables:

  - resource_handouts                    catalog of localized PDF handouts
  - parent_onboarding_session_handouts   join row recording what a coordinator
                                         gave to a family during a session

Either ``resource_handout_id`` (catalog PDF) or ``community_resource_link_id``
(URL-only sibling table) is populated on each join row, enforced by a CHECK
constraint at the SQL layer.

Idempotency: ``CREATE TABLE IF NOT EXISTS`` is used throughout because
init_db.py at container startup auto-creates tables from SQLAlchemy model
metadata BEFORE alembic runs (see feedback_l30_init_db_vs_alembic_new_table).
The CHECK constraint adds via a catalog probe so re-runs are safe.
"""
from alembic import op
import sqlalchemy as sa


revision = "po_session_handouts_001"
down_revision = "po_followup_referrals_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # resource_handouts (catalog, seeded empty -- admin CRUD is a
    # separate spec)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS resource_handouts (
            id SERIAL PRIMARY KEY,
            slug VARCHAR(128) NOT NULL,
            title VARCHAR(255) NOT NULL,
            category VARCHAR(64) NOT NULL,
            language VARCHAR(8) NOT NULL,
            description TEXT,
            file_path VARCHAR(500) NOT NULL,
            file_size_bytes INTEGER,
            page_count INTEGER,
            preview_thumbnail_path VARCHAR(500),
            tags VARCHAR[] DEFAULT ARRAY[]::VARCHAR[],
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_resource_handouts_slug_language UNIQUE (slug, language)
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resource_handouts_slug "
        "ON resource_handouts(slug)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resource_handouts_category "
        "ON resource_handouts(category)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resource_handouts_language "
        "ON resource_handouts(language)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_resource_handouts_is_active "
        "ON resource_handouts(is_active)"
    )
    # Composite for the typical "spanish + active wic" picker filter.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_resource_handouts_category_language_active "
        "ON resource_handouts(category, language, is_active)"
    )

    # ------------------------------------------------------------------
    # parent_onboarding_session_handouts (join)
    # ------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS parent_onboarding_session_handouts (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL
                REFERENCES parent_onboarding_sessions(id) ON DELETE CASCADE,
            resource_handout_id INTEGER
                REFERENCES resource_handouts(id) ON DELETE SET NULL,
            community_resource_link_id INTEGER
                REFERENCES community_resource_links(id) ON DELETE SET NULL,
            given_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            given_by_id INTEGER
                REFERENCES users(id) ON DELETE SET NULL,
            given_in_language VARCHAR(8) NOT NULL,
            delivery_method VARCHAR(32) NOT NULL DEFAULT 'printed',
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_session_handouts_session_id "
        "ON parent_onboarding_session_handouts(session_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_parent_onboarding_session_handouts_resource_handout_id "
        "ON parent_onboarding_session_handouts(resource_handout_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_handouts_language_given_at "
        "ON parent_onboarding_session_handouts(given_in_language, given_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_session_handouts_given_by_given_at "
        "ON parent_onboarding_session_handouts(given_by_id, given_at)"
    )

    # CHECK constraint: exactly one of (resource_handout_id,
    # community_resource_link_id) is populated. Probe pg_constraint to
    # stay idempotent across re-runs (alembic stamp + replay during dev
    # cycles).
    has_check = False
    if not op.get_context().as_sql:
        bind = op.get_bind()
        has_check = bind.execute(sa.text(
            "SELECT 1 FROM pg_constraint "
            "WHERE conname = 'ck_session_handouts_target' AND conrelid = "
            "'parent_onboarding_session_handouts'::regclass"
        )).first() is not None
    if not has_check:
        op.execute(
            "ALTER TABLE parent_onboarding_session_handouts "
            "ADD CONSTRAINT ck_session_handouts_target "
            "CHECK ("
            "  (resource_handout_id IS NOT NULL AND community_resource_link_id IS NULL)"
            "  OR (resource_handout_id IS NULL AND community_resource_link_id IS NOT NULL)"
            ")"
        )


def downgrade() -> None:
    """Drop the two tables in reverse FK order.

    Best-effort: we don't expect to roll this forward-and-back in prod, but
    the reverse path keeps the migration replayable on a fresh dev DB.
    """
    if op.get_context().as_sql:
        existing = {"parent_onboarding_session_handouts", "resource_handouts"}
    else:
        bind = op.get_bind()
        inspector = sa.inspect(bind)
        existing = set(inspector.get_table_names())

    if "parent_onboarding_session_handouts" in existing:
        op.execute(
            "ALTER TABLE parent_onboarding_session_handouts "
            "DROP CONSTRAINT IF EXISTS ck_session_handouts_target"
        )
        op.drop_table("parent_onboarding_session_handouts")

    if "resource_handouts" in existing:
        op.drop_table("resource_handouts")
