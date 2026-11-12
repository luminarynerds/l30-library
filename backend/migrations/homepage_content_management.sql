-- Homepage Content Management
-- Quick links + library hours, both staff-editable

BEGIN;

-- ======================================================================
-- homepage_quick_links
-- ======================================================================
CREATE TABLE IF NOT EXISTS homepage_quick_links (
    id SERIAL PRIMARY KEY,
    label VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NOT NULL DEFAULT 'link',
    url VARCHAR(255) NOT NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_homepage_quick_links_active_order
    ON homepage_quick_links (is_active, sort_order)
    WHERE is_active = true;

-- Seed with current hardcoded tiles
INSERT INTO homepage_quick_links (label, icon, url, sort_order, is_active) VALUES
    ('Printing', 'printer', '/tech', 1, true),
    ('Job Search', 'compass', '/business?tab=career', 2, true),
    ('Get a Card', 'credit-card', '/card-application', 3, true),
    ('WiFi & Computers', 'wifi', '/tech', 4, true),
    ('Book a Room', 'calendar', '/rooms', 5, true),
    ('Community Help', 'heart', '/community', 6, true),
    ('Ask a Librarian', 'message-circle', '/ask-librarian', 7, true),
    ('Life Situations', 'help-circle', '/help-guide', 8, true);

-- ======================================================================
-- library_hours (weekly schedule — exactly 7 rows)
-- ======================================================================
CREATE TABLE IF NOT EXISTS library_hours (
    id SERIAL PRIMARY KEY,
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    open_time TIME,
    close_time TIME,
    is_closed BOOLEAN NOT NULL DEFAULT false,
    label VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (day_of_week)
);

-- Seed with current hardcoded schedule
-- 0=Sunday, 1=Monday, ..., 6=Saturday
INSERT INTO library_hours (day_of_week, open_time, close_time, is_closed) VALUES
    (0, '09:00', '20:00', false),
    (1, '09:00', '20:00', false),
    (2, '09:00', '20:00', false),
    (3, '09:00', '20:00', false),
    (4, '09:00', '20:00', false),
    (5, '10:00', '18:00', false),
    (6, '10:00', '18:00', false);

-- ======================================================================
-- library_hours_overrides (snow days, holidays, special hours)
-- ======================================================================
CREATE TABLE IF NOT EXISTS library_hours_overrides (
    id SERIAL PRIMARY KEY,
    date DATE NOT NULL UNIQUE,
    open_time TIME,
    close_time TIME,
    is_closed BOOLEAN NOT NULL DEFAULT false,
    reason VARCHAR(200),
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_library_hours_overrides_date
    ON library_hours_overrides (date);

COMMIT;
