-- Migration: Add new feature toggle columns to organization_features
-- PR: #12 - Add comprehensive feature toggle guards
-- Date: 2026-03-17
--
-- Run with:
--   docker exec -i l30-database psql -U l30 -d l30_library < backend/migrations/feature_toggles_new_columns.sql

BEGIN;

ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS legal_services_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS strategic_planning_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS literacy_programs_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS tech_services_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS emergency_services_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS compliance_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS volunteers_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS notifications_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS marketing_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS streaming_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS staff_scheduling_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS beta_features_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS storytime_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS digital_access_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS collection_management_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS patron_engagement_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS staff_wellness_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS faq_chatbot_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS financial_reports_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS book_clubs_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS sip2_rfid_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS signage_enabled BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS printing_enabled BOOLEAN NOT NULL DEFAULT TRUE;

COMMIT;
