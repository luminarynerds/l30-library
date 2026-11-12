-- Item 1 Phase 1 — add nullable branch_id FK alongside every VARCHAR branch
-- label so adapters can start writing/reading branch_id without breaking
-- existing string-keyed code paths. Backfill is Phase 2 (separate migration);
-- read switch is Phase 3; VARCHAR drop is Phase 4.
--
-- Scope: Shape B columns from the spec audit. Excluded: columns that are
-- semantically a shelving label rather than a branch reference
-- (catalog_items.location, item_copies.location, events.location), and
-- already-FK columns (Shape A).
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 1)
--
-- Safe to re-run: every step uses IF NOT EXISTS.

BEGIN;

-- bibframe_items: had library_branch VARCHAR; add branch_id FK
ALTER TABLE bibframe_items ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_bibframe_items_branch_id ON bibframe_items(branch_id);

-- EOD workflows
ALTER TABLE eod_sessions    ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE eod_statistics  ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE eod_templates   ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_eod_sessions_branch_id    ON eod_sessions(branch_id);
CREATE INDEX IF NOT EXISTS ix_eod_statistics_branch_id  ON eod_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_eod_templates_branch_id   ON eod_templates(branch_id);

-- Check-in workflows
ALTER TABLE check_in_sessions   ADD COLUMN IF NOT EXISTS branch_id            INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE check_in_statistics ADD COLUMN IF NOT EXISTS branch_id            INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE check_in_results    ADD COLUMN IF NOT EXISTS destination_branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_check_in_sessions_branch_id    ON check_in_sessions(branch_id);
CREATE INDEX IF NOT EXISTS ix_check_in_statistics_branch_id  ON check_in_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_check_in_results_dest_branch   ON check_in_results(destination_branch_id);

-- Book drops
ALTER TABLE book_drops ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_book_drops_branch_id ON book_drops(branch_id);

-- Statistics tables
ALTER TABLE circulation_statistics      ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE collection_statistics       ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE computer_sessions           ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE computer_usage_statistics   ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE cipa_compliance_reports     ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE database_access_logs        ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE filter_bypass_requests      ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE internet_policy_acceptances ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE lost_damaged_settings       ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE patron_statistics           ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE program_statistics          ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE reference_statistics        ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE statistical_reports         ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE usage_statistics_settings   ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE visit_counts                ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
ALTER TABLE visit_statistics            ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_circulation_statistics_branch_id      ON circulation_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_collection_statistics_branch_id       ON collection_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_computer_sessions_branch_id           ON computer_sessions(branch_id);
CREATE INDEX IF NOT EXISTS ix_computer_usage_statistics_branch_id   ON computer_usage_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_cipa_compliance_reports_branch_id     ON cipa_compliance_reports(branch_id);
CREATE INDEX IF NOT EXISTS ix_database_access_logs_branch_id        ON database_access_logs(branch_id);
CREATE INDEX IF NOT EXISTS ix_filter_bypass_requests_branch_id      ON filter_bypass_requests(branch_id);
CREATE INDEX IF NOT EXISTS ix_internet_policy_acceptances_branch_id ON internet_policy_acceptances(branch_id);
CREATE INDEX IF NOT EXISTS ix_lost_damaged_settings_branch_id       ON lost_damaged_settings(branch_id);
CREATE INDEX IF NOT EXISTS ix_patron_statistics_branch_id           ON patron_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_program_statistics_branch_id          ON program_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_reference_statistics_branch_id        ON reference_statistics(branch_id);
CREATE INDEX IF NOT EXISTS ix_statistical_reports_branch_id         ON statistical_reports(branch_id);
CREATE INDEX IF NOT EXISTS ix_usage_statistics_settings_branch_id   ON usage_statistics_settings(branch_id);
CREATE INDEX IF NOT EXISTS ix_visit_counts_branch_id                ON visit_counts(branch_id);
CREATE INDEX IF NOT EXISTS ix_visit_statistics_branch_id            ON visit_statistics(branch_id);

-- found_item_storage_locations uses 'branch' VARCHAR (not branch_location).
ALTER TABLE found_item_storage_locations ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_found_item_storage_locations_branch_id ON found_item_storage_locations(branch_id);

-- item_copies: keep 'location' as a shelving label; add branch_id for the
-- structural branch. Backfill must split the existing 'Main - Tech' style
-- strings on " - ". Phase 2.
ALTER TABLE item_copies ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_item_copies_branch_id ON item_copies(branch_id);

COMMIT;
