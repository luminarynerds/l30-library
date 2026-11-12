-- Setup wizard: library branding table + setup_complete flag
-- Applied by: alembic upgrade head (auto-detected) or manual execution

ALTER TABLE system_settings ADD COLUMN IF NOT EXISTS setup_complete BOOLEAN DEFAULT FALSE NOT NULL;

CREATE TABLE IF NOT EXISTS library_branding (
    id INTEGER PRIMARY KEY DEFAULT 1,
    library_name VARCHAR(255) NOT NULL DEFAULT 'My Library',
    library_short_name VARCHAR(50) DEFAULT '',
    domain VARCHAR(255) DEFAULT '',
    contact_email VARCHAR(255) DEFAULT '',
    privacy_email VARCHAR(255) DEFAULT '',
    indie_email VARCHAR(255) DEFAULT '',
    giving_email VARCHAR(255) DEFAULT '',
    phone VARCHAR(50) DEFAULT '',
    address_line1 VARCHAR(255) DEFAULT '',
    address_line2 VARCHAR(255) DEFAULT '',
    primary_color VARCHAR(7) DEFAULT '#E89B44',
    accent_color VARCHAR(7) DEFAULT '#8B5E5E',
    card_prefix VARCHAR(10) DEFAULT 'LIB',
    hero_title VARCHAR(500) DEFAULT '',
    hero_subtitle VARCHAR(500) DEFAULT 'You belong here.',
    tagline VARCHAR(255) DEFAULT '',
    updated_at TIMESTAMP DEFAULT NOW(),
    CONSTRAINT singleton_branding CHECK (id = 1)
);

-- For existing L30 instance: mark setup as already complete
UPDATE system_settings SET setup_complete = TRUE WHERE id = 1;
