-- Migration: Add reading shelf expansion feature toggle columns
-- Feature: Reading Shelf Expansion (Phase 1)
-- Date: 2026-03-17
--
-- Run with:
--   docker exec -i l30-database psql -U l30 -d l30 < backend/migrations/reading_shelf_feature_toggles.sql

BEGIN;

ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS reading_shelf_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS reading_goals_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS reading_challenges_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS shelf_recommendations_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS shelf_data_export_enabled BOOLEAN NOT NULL DEFAULT TRUE;

COMMIT;
