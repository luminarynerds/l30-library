-- SPDX-FileCopyrightText: 2026 Luminary Nerds
-- SPDX-License-Identifier: AGPL-3.0-or-later
--
-- Phase 1 addendum — reference_questions was missed in add_branch_id_phase1.sql.
-- Adds branch_id FK and an index, backfills from VARCHAR branch_location using
-- the same canonical-label logic as backfill_branch_id_phase2.sql.
--
-- Unblocks the librarian-agent adapter (slice 4) which writes ReferenceQuestion
-- rows from the staff-reply endpoint.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 1)
--
-- Safe to re-run.

BEGIN;

ALTER TABLE reference_questions
  ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_reference_questions_asked_branch_id
  ON reference_questions (asked_at, branch_id);

-- Backfill using the same canonical map as Phase 2.
UPDATE reference_questions SET branch_id = 7
WHERE branch_id IS NULL AND (
  branch_location IN ('Main', 'Main Library', 'Main Circulation Desk', 'Main Branch')
  OR branch_location LIKE 'Main - %'
);

UPDATE reference_questions SET branch_id = 8
WHERE branch_id IS NULL AND branch_location LIKE 'Elmdale%';

UPDATE reference_questions SET branch_id = 9
WHERE branch_id IS NULL AND (
  branch_location = 'Annex'
  OR branch_location LIKE 'Community Annex%'
  OR branch_location LIKE 'Annex %'
);

UPDATE reference_questions SET branch_id = 10
WHERE branch_id IS NULL AND branch_location = 'Bookmobile';

-- Verification — fail loud if any non-empty label is unmapped.
DO $$
DECLARE unmapped INTEGER;
BEGIN
  SELECT count(*) INTO unmapped
  FROM reference_questions
  WHERE branch_location IS NOT NULL
    AND length(trim(branch_location)) > 0
    AND branch_id IS NULL;
  IF unmapped > 0 THEN
    RAISE EXCEPTION 'reference_questions: % rows have unmapped branch_location. Extend canonical map and re-run.', unmapped;
  END IF;
END $$;

COMMIT;
