-- Migration: Add preorder columns to indie_ebooks table
-- Feature: Indie Ebook Preorder System
-- Date: 2026-03-17
-- Branch: claude/add-preorder-images-marc-VFM7e
--
-- Adds columns for preorder functionality: flag, release date, and catalog item link.

ALTER TABLE indie_ebooks
    ADD COLUMN IF NOT EXISTS is_preorder BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS preorder_release_date TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS catalog_item_id INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_preorder ON indie_ebooks (is_preorder);
CREATE INDEX IF NOT EXISTS ix_indie_ebooks_catalog_item_id ON indie_ebooks (catalog_item_id);
