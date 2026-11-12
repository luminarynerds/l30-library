-- Adds reading progress tracking and personal tags
-- Part of My Shelf Redesign (2026-03-19)

-- Personal tags on reading_statuses
ALTER TABLE reading_statuses ADD COLUMN IF NOT EXISTS personal_tags JSONB NOT NULL DEFAULT '[]';

-- Reading progress log table
CREATE TABLE IF NOT EXISTS reading_progress (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    catalog_item_id INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
    current_page INTEGER,
    total_pages INTEGER,
    percent INTEGER NOT NULL CHECK (percent >= 0 AND percent <= 100),
    note VARCHAR(280),
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reading_progress_user_id ON reading_progress(user_id);
CREATE INDEX IF NOT EXISTS ix_reading_progress_catalog_item_id ON reading_progress(catalog_item_id);
CREATE INDEX IF NOT EXISTS ix_reading_progress_user_item_logged
    ON reading_progress(user_id, catalog_item_id, logged_at DESC);
