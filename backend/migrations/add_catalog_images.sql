-- Migration: Add catalog_images table for direct image uploads on catalog items
-- Date: 2026-02-28

CREATE TABLE IF NOT EXISTS catalog_images (
    id SERIAL PRIMARY KEY,
    catalog_item_id INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
    image_url VARCHAR(500) NOT NULL,
    image_key VARCHAR(200) NOT NULL,
    is_primary BOOLEAN NOT NULL DEFAULT FALSE,
    caption VARCHAR(255),
    display_order INTEGER NOT NULL DEFAULT 0,
    file_size INTEGER,
    content_type VARCHAR(100),
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    uploaded_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS ix_catalog_images_item_id ON catalog_images(catalog_item_id);
CREATE INDEX IF NOT EXISTS ix_catalog_images_primary ON catalog_images(catalog_item_id, is_primary);
