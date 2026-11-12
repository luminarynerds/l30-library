-- Migration: Add household support for family-linked accounts
-- Date: 2026-02-22
-- Description: Adds household linking functionality to support parent-child account relationships

-- 1. Add household_id column to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS household_id INTEGER;
CREATE INDEX IF NOT EXISTS idx_users_household_id ON users(household_id);

-- 2. Create household_link_status enum type
DO $$ BEGIN
    CREATE TYPE householdlinkstatus AS ENUM ('pending', 'approved', 'declined');
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;

-- 3. Create household_links table
CREATE TABLE IF NOT EXISTS household_links (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_parent_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status householdlinkstatus NOT NULL DEFAULT 'pending',
    decline_reason VARCHAR(500),
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 4. Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_household_links_requester_id ON household_links(requester_id);
CREATE INDEX IF NOT EXISTS idx_household_links_target_parent_id ON household_links(target_parent_id);
CREATE INDEX IF NOT EXISTS idx_household_links_status ON household_links(status);
CREATE INDEX IF NOT EXISTS idx_household_links_created_at ON household_links(created_at);

-- 5. Create trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_household_links_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS household_links_updated_at_trigger ON household_links;
CREATE TRIGGER household_links_updated_at_trigger
    BEFORE UPDATE ON household_links
    FOR EACH ROW
    EXECUTE FUNCTION update_household_links_updated_at();
