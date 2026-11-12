-- Schema drift fix: add columns that exist in models but not in existing tables
-- Generated 2026-03-26

BEGIN;

-- === announcements: new columns ===
ALTER TABLE announcements
  ADD COLUMN IF NOT EXISTS summary VARCHAR(500),
  ADD COLUMN IF NOT EXISTS category VARCHAR(50) NOT NULL DEFAULT 'general',
  ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS published_at TIMESTAMP WITH TIME ZONE;

-- announcements.status requires an enum type
DO $$ BEGIN
    CREATE TYPE announcementstatus AS ENUM ('draft', 'published', 'archived');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
ALTER TABLE announcements
  ADD COLUMN IF NOT EXISTS status announcementstatus NOT NULL DEFAULT 'draft';

-- === indie_authors: pinned_ebook_id ===
ALTER TABLE indie_authors
  ADD COLUMN IF NOT EXISTS pinned_ebook_id INTEGER REFERENCES indie_ebooks(id) ON DELETE SET NULL;

-- === indie_ebooks: new columns ===
ALTER TABLE indie_ebooks
  ADD COLUMN IF NOT EXISTS is_preorder BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS preorder_release_date TIMESTAMP WITH TIME ZONE,
  ADD COLUMN IF NOT EXISTS catalog_item_id INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS is_featured BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS is_staff_pick BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS featured_order INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS staff_pick_order INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS curated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
  ADD COLUMN IF NOT EXISTS curated_at TIMESTAMP WITH TIME ZONE;

CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_preorder ON indie_ebooks(is_preorder);
CREATE INDEX IF NOT EXISTS ix_indie_ebooks_catalog_item_id ON indie_ebooks(catalog_item_id);
CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_featured ON indie_ebooks(is_featured);
CREATE INDEX IF NOT EXISTS ix_indie_ebooks_is_staff_pick ON indie_ebooks(is_staff_pick);

-- === organization_features: many new boolean columns ===
ALTER TABLE organization_features
  ADD COLUMN IF NOT EXISTS legal_services_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS strategic_planning_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS literacy_programs_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS tech_services_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS emergency_services_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS compliance_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS volunteers_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS marketing_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS streaming_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS staff_scheduling_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS beta_features_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS storytime_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS digital_access_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS collection_management_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS patron_engagement_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS staff_wellness_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS faq_chatbot_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS financial_reports_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS book_clubs_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS sip2_rfid_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS signage_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS printing_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS ama_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS processing_queue_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS reading_shelf_enabled BOOLEAN NOT NULL DEFAULT true,
  ADD COLUMN IF NOT EXISTS reading_goals_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS reading_challenges_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS shelf_recommendations_enabled BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS shelf_data_export_enabled BOOLEAN NOT NULL DEFAULT true;

COMMIT;
