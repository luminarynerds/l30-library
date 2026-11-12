# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""drop redundant indexes on catalog_items + job_execution_logs

Revision ID: drop_redundant_indexes_001
Revises: bc_waitlist_001
Create Date: 2026-05-20 00:00:00.000000+00:00

Pre-go-live write-cost reduction. Drops 8 indexes verified redundant via
``pg_stat_user_indexes`` on prod (l30_library) on 2026-05-19:

catalog_items (166 rows at snapshot):
  * ix_catalog_items_subjects        -- idx_scan=0, 40 kB; superseded by
                                        catalog_item_subjects join table +
                                        ix_catalog_items_search_tsv (gin).
  * ix_catalog_items_artist          -- idx_scan=0, 16 kB; rare query path,
                                        and ix_catalog_items_search_tsv
                                        (gin) covers fulltext.
  * ix_catalog_items_binding         -- idx_scan=0, 8 kB; partial index
                                        (WHERE binding IS NOT NULL) but
                                        no observed use.
  * ix_catalog_items_sequence_in_set -- idx_scan=0, 16 kB; superseded by
                                        composite ix_catalog_items_multipart_sequence
                                        (multipart_set_id, sequence_in_set)
                                        for the only realistic query shape.

job_execution_logs (24,180 rows at snapshot):
  * ix_job_execution_logs_id     -- idx_scan=0, 544 kB; structurally
                                    redundant with job_execution_logs_pkey
                                    (btree on id).
  * ix_job_execution_logs_job_id -- idx_scan=0, 280 kB; superseded by
                                    ix_job_exec_job_time (job_id, started_at)
                                    -- leading column identical.
  * ix_job_exec_recent           -- idx_scan=0, 1304 kB; started_at queries
                                    served by ix_job_execution_logs_started_at;
                                    rare (started_at, job_id) shape can
                                    fall back to ix_job_exec_job_time.
  * ix_job_exec_job_success      -- idx_scan=0, 272 kB; (job_id, success);
                                    job_id queries covered by
                                    ix_job_exec_job_time, success column
                                    covered by ix_job_execution_logs_success.

NOT touched (deferred to separate decisions):
  * ix_catalog_items_id          -- structurally redundant with pkey, but
                                    had 3032 scans in window; planner picks
                                    it sometimes. Pkey would serve the
                                    same queries identically; separate PR
                                    with query-plan test.
  * ix_catalog_items_is_large_print -- 2 scans observed; no clear
                                       superseder.
  * Trigram indexes (ix_catalog_items_title_trgm, ix_catalog_items_author_trgm)
    and ix_catalog_items_search_tsv interaction -- needs a deliberate
    query-plan test.

Idempotent via if_exists=True on drop_index; recreate is straight
op.create_index with the original column lists / partial predicate / etc.
"""
from __future__ import annotations

from alembic import op


revision = "drop_redundant_indexes_001"
down_revision = "bc_waitlist_001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # catalog_items -----------------------------------------------------
    # ix_catalog_items_subjects: idx_scan=0; subjects column queried via
    # catalog_item_subjects join + search_tsv gin.
    op.drop_index(
        "ix_catalog_items_subjects",
        table_name="catalog_items",
        if_exists=True,
    )
    # ix_catalog_items_artist: idx_scan=0; search_tsv gin covers fulltext.
    op.drop_index(
        "ix_catalog_items_artist",
        table_name="catalog_items",
        if_exists=True,
    )
    # ix_catalog_items_binding: idx_scan=0; partial index, no use.
    op.drop_index(
        "ix_catalog_items_binding",
        table_name="catalog_items",
        if_exists=True,
    )
    # ix_catalog_items_sequence_in_set: idx_scan=0; superseded by
    # composite ix_catalog_items_multipart_sequence.
    op.drop_index(
        "ix_catalog_items_sequence_in_set",
        table_name="catalog_items",
        if_exists=True,
    )

    # job_execution_logs ------------------------------------------------
    # ix_job_execution_logs_id: idx_scan=0; redundant with pkey on id.
    op.drop_index(
        "ix_job_execution_logs_id",
        table_name="job_execution_logs",
        if_exists=True,
    )
    # ix_job_execution_logs_job_id: idx_scan=0; superseded by
    # ix_job_exec_job_time (job_id, started_at) -- same leading column.
    op.drop_index(
        "ix_job_execution_logs_job_id",
        table_name="job_execution_logs",
        if_exists=True,
    )
    # ix_job_exec_recent: idx_scan=0; (started_at, job_id) -- started_at
    # queries served by ix_job_execution_logs_started_at.
    op.drop_index(
        "ix_job_exec_recent",
        table_name="job_execution_logs",
        if_exists=True,
    )
    # ix_job_exec_job_success: idx_scan=0; (job_id, success) -- job_id
    # covered by ix_job_exec_job_time, success by
    # ix_job_execution_logs_success.
    op.drop_index(
        "ix_job_exec_job_success",
        table_name="job_execution_logs",
        if_exists=True,
    )


def downgrade() -> None:
    # Recreate in reverse order; definitions match initial_schema.sql /
    # 20260507_multipart_sets_001.py / circulation_policy_001_create_table.py.

    # job_execution_logs ------------------------------------------------
    op.create_index(
        "ix_job_exec_job_success",
        "job_execution_logs",
        ["job_id", "success"],
        unique=False,
    )
    op.create_index(
        "ix_job_exec_recent",
        "job_execution_logs",
        ["started_at", "job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_execution_logs_job_id",
        "job_execution_logs",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_job_execution_logs_id",
        "job_execution_logs",
        ["id"],
        unique=False,
    )

    # catalog_items -----------------------------------------------------
    op.create_index(
        "ix_catalog_items_sequence_in_set",
        "catalog_items",
        ["sequence_in_set"],
        unique=False,
    )
    # Partial index: original WHERE binding IS NOT NULL clause preserved.
    op.create_index(
        "ix_catalog_items_binding",
        "catalog_items",
        ["binding"],
        unique=False,
        postgresql_where="binding IS NOT NULL",
    )
    op.create_index(
        "ix_catalog_items_artist",
        "catalog_items",
        ["artist"],
        unique=False,
    )
    op.create_index(
        "ix_catalog_items_subjects",
        "catalog_items",
        ["subjects"],
        unique=False,
    )
