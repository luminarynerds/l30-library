-- Migration: Add processing queue support
-- Date: 2026-03-17

BEGIN;

ALTER TABLE item_copies
    ADD COLUMN IF NOT EXISTS processing_step VARCHAR(50);

ALTER TABLE organization_features
    ADD COLUMN IF NOT EXISTS processing_queue_enabled BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS idx_item_copies_processing_step ON item_copies(processing_step)
    WHERE processing_step IS NOT NULL;

COMMIT;
