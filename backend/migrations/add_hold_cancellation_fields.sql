-- Add cancellation metadata fields to holds table
-- These fields track who cancelled a hold, when, and why

ALTER TABLE holds ADD COLUMN IF NOT EXISTS cancelled_at TIMESTAMPTZ;
ALTER TABLE holds ADD COLUMN IF NOT EXISTS cancellation_reason VARCHAR(500);
ALTER TABLE holds ADD COLUMN IF NOT EXISTS cancelled_by VARCHAR(50);
