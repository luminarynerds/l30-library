-- Migration: Ensure order_templates table exists
-- Date: 2026-03-18

BEGIN;

CREATE TABLE IF NOT EXISTS order_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    vendor_id INTEGER REFERENCES vendors(id) ON DELETE SET NULL,
    fund_id INTEGER REFERENCES funds(id) ON DELETE SET NULL,
    created_by_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    is_shared BOOLEAN NOT NULL DEFAULT FALSE,
    template_items TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_order_templates_created_by ON order_templates(created_by_id);

COMMIT;
