-- Migration: Create donation_records table
-- Date: 2026-03-18

BEGIN;

DO $$ BEGIN
    CREATE TYPE donation_status AS ENUM ('pending', 'under_review', 'accepted', 'declined', 'processed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS donation_records (
    id SERIAL PRIMARY KEY,
    donor_name VARCHAR(255),
    donor_email VARCHAR(255),
    donor_phone VARCHAR(50),
    donor_address TEXT,
    is_anonymous BOOLEAN NOT NULL DEFAULT FALSE,
    tax_receipt_requested BOOLEAN NOT NULL DEFAULT FALSE,
    tax_receipt_sent BOOLEAN NOT NULL DEFAULT FALSE,
    title VARCHAR(500),
    author VARCHAR(500),
    isbn VARCHAR(20),
    material_type VARCHAR(50),
    quantity INTEGER NOT NULL DEFAULT 1,
    condition_notes TEXT,
    estimated_value INTEGER,
    status donation_status NOT NULL DEFAULT 'pending',
    received_date DATE NOT NULL DEFAULT CURRENT_DATE,
    received_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP,
    decline_reason TEXT,
    staff_notes TEXT,
    catalog_item_id INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
    item_copy_id INTEGER REFERENCES item_copies(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_donation_records_status ON donation_records(status);
CREATE INDEX IF NOT EXISTS idx_donation_records_received_date ON donation_records(received_date);

COMMIT;
