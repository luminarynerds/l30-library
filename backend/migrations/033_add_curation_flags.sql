-- Add staff curation columns to indie_ebooks
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS is_staff_pick BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS featured_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS staff_pick_order INTEGER NOT NULL DEFAULT 0;
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS curated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE indie_ebooks ADD COLUMN IF NOT EXISTS curated_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_featured ON indie_ebooks(is_featured) WHERE is_featured = true;
CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_staff_pick ON indie_ebooks(is_staff_pick) WHERE is_staff_pick = true;
