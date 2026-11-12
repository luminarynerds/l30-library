-- Migration: Add status and purchase_request_id to selection_list_items
-- Date: 2026-03-17

BEGIN;

-- Note: Using native_enum=False in SQLAlchemy, so the column is VARCHAR.
-- No need to create a native enum type.

ALTER TABLE selection_list_items
    ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS purchase_request_id INTEGER REFERENCES patron_purchase_requests(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_selection_list_status ON selection_list_items(status);
CREATE INDEX IF NOT EXISTS idx_selection_list_purchase_request_id ON selection_list_items(purchase_request_id);

COMMIT;
