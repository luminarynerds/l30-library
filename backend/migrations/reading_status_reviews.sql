-- Migration: Add reading_statuses and reviews tables
-- Feature: Reading Status & Reviews (StoryGraph-like tracking)
-- Date: 2026-03-17
-- Branch: feat/reading-status-reviews
--
-- Run with:
--   docker exec -i l30-database psql -U l30 -d l30 < backend/migrations/reading_status_reviews.sql

BEGIN;

-- 1. Create the shelfstatus enum type
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shelfstatus') THEN
        CREATE TYPE shelfstatus AS ENUM (
            'want_to_read',
            'currently_reading',
            'on_hold',
            'finished',
            'did_not_finish'
        );
    END IF;
END$$;

-- 2. Create reading_statuses table
CREATE TABLE IF NOT EXISTS reading_statuses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    catalog_item_id INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
    status shelfstatus NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    private_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_catalog_reading_status UNIQUE (user_id, catalog_item_id)
);

CREATE INDEX IF NOT EXISTS ix_reading_statuses_id ON reading_statuses(id);
CREATE INDEX IF NOT EXISTS ix_reading_statuses_user_id ON reading_statuses(user_id);
CREATE INDEX IF NOT EXISTS ix_reading_statuses_catalog_item_id ON reading_statuses(catalog_item_id);

-- 3. Create reviews table
CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    catalog_item_id INTEGER NOT NULL REFERENCES catalog_items(id) ON DELETE CASCADE,
    rating INTEGER,
    title VARCHAR(255),
    body TEXT,
    is_staff_review BOOLEAN NOT NULL DEFAULT FALSE,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_catalog_review UNIQUE (user_id, catalog_item_id),
    CONSTRAINT chk_rating_range CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5))
);

CREATE INDEX IF NOT EXISTS ix_reviews_id ON reviews(id);
CREATE INDEX IF NOT EXISTS ix_reviews_user_id ON reviews(user_id);
CREATE INDEX IF NOT EXISTS ix_reviews_catalog_item_id ON reviews(catalog_item_id);

COMMIT;
