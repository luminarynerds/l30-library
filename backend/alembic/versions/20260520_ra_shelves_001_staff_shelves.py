"""create staff_shelves table + seed initial 7 RA shelves

Revision ID: ra_shelves_001
Revises: df85cac32c74
Create Date: 2026-05-20

Adds the staff_shelves table used by the /discover chip row and
/catalog?shelf=<slug> view. Seeds 7 initial readers'-advisory shelves.

Uses CREATE TABLE IF NOT EXISTS so init_db.py auto-create at startup does
not collide with alembic (see feedback_l30_init_db_vs_alembic_new_table).

Items seeded by id reflect the live catalog at 2026-05-20 (n=156 cataloged).
Empty item_ids on adult-learners, new-parents and spanish-language-picks
where the catalog has no matching items today; shelves still appear in the
admin list so curators can fill them later.
"""
from typing import Union

from alembic import op
import sqlalchemy as sa


revision: str = "ra_shelves_001"
down_revision: Union[str, None] = "df85cac32c74"
branch_labels = None
depends_on = None


SEED_SHELVES = [
    # (slug, title, description, audience, display_order, item_ids)
    (
        "new-parents",
        "New parents",
        "Board books, parenting guides, and lullaby kits for the bleary-eyed first year.",
        "adults",
        10,
        [],
    ),
    (
        "local-ohio-authors",
        "Local Ohio authors",
        "Fiction, history, and field guides rooted in Ohio.",
        "all",
        20,
        [4, 26, 27, 30, 34, 55, 66, 78],
    ),
    (
        "teens-after-hunger-games",
        "Teens who liked Hunger Games",
        "Dystopian, climate-future, and high-stakes adventure picks. Pairs YA reads with adult crossovers your teen can handle.",
        "teens",
        30,
        [55, 11, 13, 14, 15],
    ),
    (
        "first-chapter-books",
        "First chapter books",
        "Short, illustrated chapter books for newly-independent readers.",
        "kids",
        40,
        [117, 120, 122, 124],
    ),
    (
        "adult-learners",
        "Adult learners",
        "ESL, GED prep, and adult literacy supports. Curated when titles arrive.",
        "adults",
        50,
        [],
    ),
    (
        "cozy-mysteries",
        "Cozy mysteries",
        "Small-town sleuths, gentle stakes, no graphic content.",
        "adults",
        60,
        [58, 133, 134],
    ),
    (
        "spanish-language-picks",
        "Spanish-language picks",
        "Bilingual and Spanish-language reads for kids and families. Growing collection.",
        "all",
        70,
        [118],
    ),
]


def upgrade() -> None:
    # Idempotent enum + table create -- init_db.py may have already created
    # them at backend startup.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE shelfaudience AS ENUM ('kids', 'teens', 'adults', 'all');
        EXCEPTION WHEN duplicate_object THEN null; END $$
    """)
    op.execute("""
        CREATE TABLE IF NOT EXISTS staff_shelves (
            id SERIAL PRIMARY KEY,
            slug VARCHAR(80) NOT NULL UNIQUE,
            title VARCHAR(200) NOT NULL,
            description TEXT,
            item_ids JSON NOT NULL DEFAULT '[]'::json,
            audience shelfaudience,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            display_order INTEGER NOT NULL DEFAULT 0,
            created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
    """)
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_staff_shelves_slug ON staff_shelves(slug)"
    )

    # Seed shelves. Use ON CONFLICT DO NOTHING so re-running upgrade after a
    # downgrade-then-upgrade cycle (or partial init_db state) is safe.
    import json
    conn = op.get_bind()
    for slug, title, description, audience, display_order, item_ids in SEED_SHELVES:
        conn.execute(
            sa.text(
                """
                INSERT INTO staff_shelves
                    (slug, title, description, item_ids, audience, is_active, display_order)
                VALUES
                    (:slug, :title, :description, CAST(:item_ids AS JSON),
                     CAST(:audience AS shelfaudience), TRUE, :display_order)
                ON CONFLICT (slug) DO NOTHING
                """
            ),
            {
                "slug": slug,
                "title": title,
                "description": description,
                "item_ids": json.dumps(item_ids),
                "audience": audience,
                "display_order": display_order,
            },
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS staff_shelves")
    op.execute("DROP TYPE IF EXISTS shelfaudience")
