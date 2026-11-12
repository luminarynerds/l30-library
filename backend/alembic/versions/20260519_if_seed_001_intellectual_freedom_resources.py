# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""seed baseline intellectual freedom resources

Revision ID: if_seed_001
Revises: bc_waitlist_001
Create Date: 2026-05-19 18:00:00.000000+00:00

Seeds three ALA-authored intellectual freedom resources into
``intellectual_freedom_resources`` so the public Banned Books page
renders meaningful "Learn About Intellectual Freedom" cards out of the
box. Idempotent: each INSERT guarded by NOT EXISTS on ``url`` so re-run
is safe, and we don't add a unique index (schema-stable, low risk).

See ``feedback_l30_init_db_vs_alembic_new_table`` -- the table is
created by SQLAlchemy at startup; this migration only INSERTs rows.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "if_seed_001"
down_revision: Union[str, None] = "bc_waitlist_001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SEEDS = [
    {
        "title": "ALA Freedom to Read Statement",
        "description": (
            "American Library Association joint statement (1953, revised 2004) "
            "affirming the public's right to read and libraries' duty to "
            "resist censorship."
        ),
        "url": "https://www.ala.org/advocacy/intfreedom/statementspols/freedomreadstatement",
        "resource_type": "external_link",
        "display_order": 10,
    },
    {
        "title": "ALA Library Bill of Rights",
        "description": (
            "The Library Bill of Rights sets out the basic policies that "
            "guide service in U.S. libraries, including free access to "
            "information and resistance to abridgment of free expression."
        ),
        "url": "https://www.ala.org/advocacy/intfreedom/librarybill",
        "resource_type": "external_link",
        "display_order": 20,
    },
    {
        "title": "ALA Office for Intellectual Freedom",
        "description": (
            "The Office for Intellectual Freedom (OIF) supports the right "
            "of library users to read, seek information, and speak freely "
            "as guaranteed by the First Amendment."
        ),
        "url": "https://www.ala.org/aboutala/offices/oif",
        "resource_type": "external_link",
        "display_order": 30,
    },
]


_INSERT_SQL = sa.text(
    """
    INSERT INTO intellectual_freedom_resources
        (title, description, url, resource_type, display_order, is_active, created_at, updated_at)
    SELECT
        CAST(:title AS varchar),
        CAST(:description AS text),
        CAST(:url AS varchar),
        CAST(:resource_type AS varchar),
        CAST(:display_order AS integer),
        TRUE,
        NOW(),
        NOW()
    WHERE NOT EXISTS (
        SELECT 1 FROM intellectual_freedom_resources WHERE url = CAST(:url AS varchar)
    )
    """
)

_DELETE_SQL = sa.text(
    "DELETE FROM intellectual_freedom_resources WHERE url = :url"
)


def upgrade() -> None:
    bind = op.get_bind()
    for s in _SEEDS:
        bind.execute(_INSERT_SQL, s)


def downgrade() -> None:
    # Remove only the rows we seeded (matched by url) so we don't blow
    # away any rows a librarian may have curated post-seed.
    bind = op.get_bind()
    for s in _SEEDS:
        bind.execute(_DELETE_SQL, {"url": s["url"]})
