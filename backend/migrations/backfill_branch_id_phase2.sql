-- Item 1 Phase 2 — backfill branch_id from VARCHAR branch labels using the
-- canonical name map. Strings observed in prod (audit 2026-05-13):
--   - 'Bookmobile'                                    -> id 10
--   - 'Main', 'Main Library', 'Main Circulation Desk',
--     'Main - <anything>'                             -> id 7
--
-- No 'Elmdale' or 'Community Annex' string variants were found in the
-- VARCHAR columns, so the map below is complete for the current dataset.
-- Any future drift will surface as NULL branch_id rows; the verification
-- block at the end fails the migration if that happens.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 1)
--
-- Safe to re-run.

BEGIN;

CREATE TEMP TABLE _branch_label_map (
    pattern    TEXT PRIMARY KEY,
    branch_id  INTEGER NOT NULL
) ON COMMIT DROP;

INSERT INTO _branch_label_map(pattern, branch_id) VALUES
    ('Bookmobile',            10),
    ('Main',                   7),
    ('Main Library',           7),
    ('Main Circulation Desk',  7);

-- map_label(label) returns the branch_id, also handling 'Main - <shelving>'.
CREATE OR REPLACE FUNCTION pg_temp.map_label(label TEXT) RETURNS INTEGER AS $$
DECLARE
    bid INTEGER;
BEGIN
    IF label IS NULL OR length(trim(label)) = 0 THEN
        RETURN NULL;
    END IF;

    SELECT branch_id INTO bid FROM _branch_label_map WHERE pattern = label;
    IF bid IS NOT NULL THEN
        RETURN bid;
    END IF;

    -- Handle compound shelving labels like 'Main - Tech', 'Main - Children'
    IF label LIKE 'Main - %' THEN
        RETURN 7;
    END IF;
    IF label LIKE 'Elmdale%' THEN
        RETURN 8;
    END IF;
    IF label LIKE 'Community Annex%' OR label LIKE 'Annex%' THEN
        RETURN 9;
    END IF;

    RETURN NULL;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Backfill every Phase 1 branch_id column from its companion VARCHAR.
UPDATE bibframe_items      SET branch_id = pg_temp.map_label(library_branch)    WHERE branch_id IS NULL AND library_branch    IS NOT NULL;
UPDATE eod_sessions        SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE eod_statistics      SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE eod_templates       SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE check_in_sessions   SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE check_in_statistics SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE check_in_results    SET destination_branch_id = pg_temp.map_label(destination_branch)
    WHERE destination_branch_id IS NULL AND destination_branch IS NOT NULL;
UPDATE book_drops          SET branch_id = pg_temp.map_label(branch_location)   WHERE branch_id IS NULL AND branch_location   IS NOT NULL;
UPDATE circulation_statistics      SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE collection_statistics       SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE computer_sessions           SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE computer_usage_statistics   SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE cipa_compliance_reports     SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE database_access_logs        SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE filter_bypass_requests      SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE internet_policy_acceptances SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE lost_damaged_settings       SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE patron_statistics           SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE program_statistics          SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE reference_statistics        SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE statistical_reports         SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE usage_statistics_settings   SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE visit_counts                SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE visit_statistics            SET branch_id = pg_temp.map_label(branch_location) WHERE branch_id IS NULL AND branch_location IS NOT NULL;
UPDATE found_item_storage_locations SET branch_id = pg_temp.map_label(branch) WHERE branch_id IS NULL AND branch IS NOT NULL;
UPDATE item_copies                 SET branch_id = pg_temp.map_label(location) WHERE branch_id IS NULL AND location IS NOT NULL;

-- Verification: fail the migration if any non-null label remained unmapped.
DO $$
DECLARE
    unmapped INTEGER;
    msg TEXT;
BEGIN
    msg := '';

    SELECT COUNT(*) INTO unmapped FROM bibframe_items
        WHERE library_branch IS NOT NULL AND branch_id IS NULL;
    IF unmapped > 0 THEN msg := msg || format('bibframe_items: %s rows, ', unmapped); END IF;

    SELECT COUNT(*) INTO unmapped FROM eod_sessions
        WHERE branch_location IS NOT NULL AND branch_id IS NULL;
    IF unmapped > 0 THEN msg := msg || format('eod_sessions: %s rows, ', unmapped); END IF;

    SELECT COUNT(*) INTO unmapped FROM check_in_sessions
        WHERE branch_location IS NOT NULL AND branch_id IS NULL;
    IF unmapped > 0 THEN msg := msg || format('check_in_sessions: %s rows, ', unmapped); END IF;

    SELECT COUNT(*) INTO unmapped FROM item_copies
        WHERE location IS NOT NULL AND branch_id IS NULL;
    IF unmapped > 0 THEN msg := msg || format('item_copies: %s rows, ', unmapped); END IF;

    IF length(msg) > 0 THEN
        RAISE EXCEPTION 'branch_id backfill left unmapped rows: %', msg;
    END IF;
END $$;

DROP FUNCTION pg_temp.map_label(TEXT);

COMMIT;
