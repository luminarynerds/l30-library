-- Review feedback (2026-05-13):
--
-- 1. Phase 2 backfill missed computer_sessions rows whose branch_location
--    held a sub-room label ("Children's Room", "Main Floor - Reference
--    Area", "Main Floor - Window Bay", "Teen Zone"). All sub-rooms in
--    prod live at Main (branch_id=7); the map needs an explicit catch.
--
-- 2. EOD / check-in / book-drop / branch-shared statistics tables had
--    ON DELETE SET NULL on the new branch_id FK. Losing the branch
--    attribution silently corrupts state-reportable counts. Switch
--    those to ON DELETE RESTRICT so a branch delete fails loud.
--
-- 3. The Phase 2 verification block hand-picked four tables. Replace it
--    with a loop over every Phase 1 (table, label_column) pair so
--    future drift gets caught.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 1)

BEGIN;

-- (1) Fill in the rows the original backfill missed.
UPDATE computer_sessions
   SET branch_id = 7
 WHERE branch_id IS NULL
   AND branch_location IS NOT NULL
   AND (
        branch_location = 'Children''s Room'
        OR branch_location LIKE 'Main Floor%'
        OR branch_location = 'Teen Zone'
   );

-- (2) Switch FK behavior for tables where losing branch attribution
--     would silently corrupt reports. Drop + re-add each FK.
DO $$
DECLARE
    targets TEXT[] := ARRAY[
        'eod_sessions', 'eod_statistics', 'eod_templates',
        'check_in_sessions', 'check_in_statistics',
        'book_drops',
        'circulation_statistics', 'collection_statistics',
        'patron_statistics', 'program_statistics', 'reference_statistics',
        'visit_counts', 'visit_statistics',
        'statistical_reports'
    ];
    t TEXT;
BEGIN
    FOREACH t IN ARRAY targets LOOP
        EXECUTE format(
            'ALTER TABLE %I DROP CONSTRAINT IF EXISTS %I',
            t, t || '_branch_id_fkey'
        );
        EXECUTE format(
            'ALTER TABLE %I ADD CONSTRAINT %I '
            'FOREIGN KEY (branch_id) REFERENCES branches(id) ON DELETE RESTRICT',
            t, t || '_branch_id_fkey'
        );
    END LOOP;
END$$;

-- (3) Widen verification: every Phase 1 (table, label_column) pair.
DO $$
DECLARE
    pair RECORD;
    unmapped INTEGER;
    bad TEXT := '';
BEGIN
    FOR pair IN
        SELECT * FROM (VALUES
            ('bibframe_items',            'library_branch'),
            ('eod_sessions',              'branch_location'),
            ('eod_statistics',            'branch_location'),
            ('eod_templates',             'branch_location'),
            ('check_in_sessions',         'branch_location'),
            ('check_in_statistics',       'branch_location'),
            ('book_drops',                'branch_location'),
            ('circulation_statistics',    'branch_location'),
            ('collection_statistics',     'branch_location'),
            ('computer_sessions',         'branch_location'),
            ('computer_usage_statistics', 'branch_location'),
            ('cipa_compliance_reports',   'branch_location'),
            ('database_access_logs',      'branch_location'),
            ('filter_bypass_requests',    'branch_location'),
            ('internet_policy_acceptances','branch_location'),
            ('lost_damaged_settings',     'branch_location'),
            ('patron_statistics',         'branch_location'),
            ('program_statistics',        'branch_location'),
            ('reference_statistics',      'branch_location'),
            ('statistical_reports',       'branch_location'),
            ('usage_statistics_settings', 'branch_location'),
            ('visit_counts',              'branch_location'),
            ('visit_statistics',          'branch_location'),
            ('found_item_storage_locations','branch'),
            ('item_copies',               'location')
        ) AS t(tbl, col)
    LOOP
        EXECUTE format(
            'SELECT COUNT(*) FROM %I WHERE %I IS NOT NULL AND branch_id IS NULL',
            pair.tbl, pair.col
        ) INTO unmapped;
        IF unmapped > 0 THEN
            bad := bad || format('%s.%s: %s, ', pair.tbl, pair.col, unmapped);
        END IF;
    END LOOP;

    -- check_in_results uses destination_branch / destination_branch_id
    SELECT COUNT(*) INTO unmapped
      FROM check_in_results
     WHERE destination_branch IS NOT NULL AND destination_branch_id IS NULL;
    IF unmapped > 0 THEN
        bad := bad || format('check_in_results.destination_branch: %s, ', unmapped);
    END IF;

    IF length(bad) > 0 THEN
        RAISE EXCEPTION 'unmapped branch labels remain: %', bad;
    END IF;
END$$;

COMMIT;
