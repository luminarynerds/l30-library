# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""create subjects + catalog_item_subjects join tables and backfill

Revision ID: subjects_join_001
Revises: lexile_001
Create Date: 2026-05-16

Replaces substring filtering against the denormalized
``catalog_items.subjects`` text column (capped 500 chars) with a normalized
join. The old column is intentionally *not dropped* in this migration -- we
keep it for one release cycle for rollback safety. Drop in a follow-up once
the join table is the canonical source of truth in prod.

Backfill is delimiter-tolerant: production data uses semicolons (newer rows)
and commas (legacy MARC imports), and a handful of rows still carry Postgres
array literal syntax (``{a,b,c}``). The ``backfill_subjects`` helper is
extracted so tests can exercise it without invoking Alembic.
"""
import re
from typing import Iterable

import sqlalchemy as sa
from alembic import op
from sqlalchemy.sql import column, table

revision = "subjects_join_001"
down_revision = "lexile_001"
branch_labels = None
depends_on = None


# ---------------------------------------------------------------------------
# Backfill helper (exported for tests)
# ---------------------------------------------------------------------------

_ARRAY_LITERAL_RE = re.compile(r"^\{(.*)\}$")
_SPLIT_RE = re.compile(r"[;,]")


def parse_subjects(raw: str | None) -> list[str]:
    """Split a free-text subjects string into a deduped, ordered list.

    Handles three observed formats in prod:

    * ``"Mystery; Holocaust; Memoir"`` -- semicolon-delimited (most common)
    * ``"Mystery, Cozy mystery, Small town"`` -- comma-delimited (legacy MARC)
    * ``"{astronaut,space,nasa}"`` -- Postgres array literal (a handful of rows)

    Strips whitespace + surrounding quotes, drops empties, preserves first-seen
    order so the join row ``position`` column reflects the source ordering.
    """
    if not raw:
        return []
    s = raw.strip()
    if not s:
        return []
    m = _ARRAY_LITERAL_RE.match(s)
    if m:
        s = m.group(1)
    out: list[str] = []
    seen: set[str] = set()
    for part in _SPLIT_RE.split(s):
        label = part.strip().strip('"').strip("'").strip()
        if not label:
            continue
        key = label.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(label)
    return out


def slugify(label: str) -> str:
    """Lowercase, collapse whitespace, strip non-alphanum-ish chars."""
    s = label.lower().strip()
    s = re.sub(r"\s+", "-", s)
    s = re.sub(r"[^a-z0-9\-]+", "", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "subject"


def backfill_subjects(connection) -> tuple[int, int]:
    """Backfill subjects + catalog_item_subjects from catalog_items.subjects.

    Returns ``(subjects_inserted, links_inserted)``. Idempotent: re-running
    is a no-op against rows already present (uses UNIQUE on label + composite
    PK on the join). Safe to call from a SQLAlchemy connection in tests.
    """
    subjects_tbl = table(
        "subjects",
        column("id", sa.Integer),
        column("label", sa.String),
        column("slug", sa.String),
        column("authority", sa.String),
    )
    join_tbl = table(
        "catalog_item_subjects",
        column("catalog_item_id", sa.Integer),
        column("subject_id", sa.Integer),
        column("position", sa.Integer),
    )

    # Pull every row with a non-empty subjects string.
    rows = connection.execute(
        sa.text(
            "SELECT id, subjects FROM catalog_items "
            "WHERE subjects IS NOT NULL AND length(trim(subjects)) > 0"
        )
    ).fetchall()

    # Pass 1: collect distinct labels.
    label_to_id: dict[str, int] = {}
    parsed_per_item: list[tuple[int, list[str]]] = []
    for row in rows:
        labels = parse_subjects(row[1])
        if not labels:
            continue
        parsed_per_item.append((row[0], labels))
        for label in labels:
            label_to_id.setdefault(label, 0)

    # Pre-load existing subjects so we don't duplicate-insert.
    if label_to_id:
        existing = connection.execute(
            sa.select(subjects_tbl.c.id, subjects_tbl.c.label).where(
                subjects_tbl.c.label.in_(list(label_to_id.keys()))
            )
        ).fetchall()
        for sid, lbl in existing:
            label_to_id[lbl] = sid

    # Insert any new subjects, then refetch to learn their IDs.
    to_insert = [
        {"label": lbl, "slug": slugify(lbl), "authority": None}
        for lbl, sid in label_to_id.items()
        if sid == 0
    ]
    subjects_inserted = 0
    if to_insert:
        connection.execute(subjects_tbl.insert(), to_insert)
        subjects_inserted = len(to_insert)
        refetch = connection.execute(
            sa.select(subjects_tbl.c.id, subjects_tbl.c.label).where(
                subjects_tbl.c.label.in_([r["label"] for r in to_insert])
            )
        ).fetchall()
        for sid, lbl in refetch:
            label_to_id[lbl] = sid

    # Pre-load existing join rows to make the backfill idempotent.
    existing_links: set[tuple[int, int]] = set()
    if parsed_per_item:
        item_ids = [item_id for item_id, _ in parsed_per_item]
        link_rows = connection.execute(
            sa.select(
                join_tbl.c.catalog_item_id, join_tbl.c.subject_id
            ).where(join_tbl.c.catalog_item_id.in_(item_ids))
        ).fetchall()
        existing_links = {(c, s) for c, s in link_rows}

    link_inserts: list[dict] = []
    for item_id, labels in parsed_per_item:
        for position, label in enumerate(labels):
            sid = label_to_id[label]
            if (item_id, sid) in existing_links:
                continue
            link_inserts.append(
                {
                    "catalog_item_id": item_id,
                    "subject_id": sid,
                    "position": position,
                }
            )

    if link_inserts:
        connection.execute(join_tbl.insert(), link_inserts)

    return subjects_inserted, len(link_inserts)


# ---------------------------------------------------------------------------
# Schema operations
# ---------------------------------------------------------------------------


def upgrade() -> None:
    op.create_table(
        "subjects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("label", sa.String(length=300), nullable=False),
        sa.Column("slug", sa.String(length=300), nullable=False),
        sa.Column("authority", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("label", name="uq_subjects_label"),
    )
    op.create_index("ix_subjects_label", "subjects", ["label"])
    op.create_index("ix_subjects_slug", "subjects", ["slug"])
    op.create_index("ix_subjects_authority", "subjects", ["authority"])

    op.create_table(
        "catalog_item_subjects",
        sa.Column(
            "catalog_item_id",
            sa.Integer(),
            sa.ForeignKey("catalog_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "subject_id",
            sa.Integer(),
            sa.ForeignKey("subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "position", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.PrimaryKeyConstraint(
            "catalog_item_id", "subject_id", name="pk_catalog_item_subjects"
        ),
    )
    op.create_index(
        "ix_catalog_item_subjects_catalog_item_id",
        "catalog_item_subjects",
        ["catalog_item_id"],
    )
    op.create_index(
        "ix_catalog_item_subjects_subject_id",
        "catalog_item_subjects",
        ["subject_id"],
    )
    op.create_index(
        "ix_catalog_item_subjects_subject_item",
        "catalog_item_subjects",
        ["subject_id", "catalog_item_id"],
    )

    # Backfill from the legacy text column. Skipped automatically on a fresh
    # DB where catalog_items is empty (the SELECT just returns no rows).
    if op.get_context().as_sql:
        # Per-row backfill depends on runtime catalog_items rows; cannot be
        # previewed offline.
        return
    bind = op.get_bind()
    backfill_subjects(bind)


def downgrade() -> None:
    op.drop_index(
        "ix_catalog_item_subjects_subject_item",
        table_name="catalog_item_subjects",
    )
    op.drop_index(
        "ix_catalog_item_subjects_subject_id",
        table_name="catalog_item_subjects",
    )
    op.drop_index(
        "ix_catalog_item_subjects_catalog_item_id",
        table_name="catalog_item_subjects",
    )
    op.drop_table("catalog_item_subjects")
    op.drop_index("ix_subjects_authority", table_name="subjects")
    op.drop_index("ix_subjects_slug", table_name="subjects")
    op.drop_index("ix_subjects_label", table_name="subjects")
    op.drop_table("subjects")
