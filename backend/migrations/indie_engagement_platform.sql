-- Indie Engagement Platform Migration
-- Design doc: docs/plans/2026-03-20-indie-engagement-platform-design.md

-- ============================================================================
-- System 1: Patron Engagement
-- ============================================================================

CREATE TABLE IF NOT EXISTS patron_author_follows (
    id SERIAL PRIMARY KEY,
    patron_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    metislib_author_id VARCHAR(255),
    followed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (patron_id, author_id)
);
CREATE INDEX IF NOT EXISTS ix_patron_author_follows_patron ON patron_author_follows (patron_id);
CREATE INDEX IF NOT EXISTS ix_patron_author_follows_author ON patron_author_follows (author_id);

CREATE TABLE IF NOT EXISTS patron_favorites (
    id SERIAL PRIMARY KEY,
    patron_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ebook_id INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    metislib_content_id VARCHAR(255),
    favorited_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (patron_id, ebook_id)
);
CREATE INDEX IF NOT EXISTS ix_patron_favorites_patron ON patron_favorites (patron_id);
CREATE INDEX IF NOT EXISTS ix_patron_favorites_ebook ON patron_favorites (ebook_id);

CREATE TABLE IF NOT EXISTS patron_reading_lists (
    id SERIAL PRIMARY KEY,
    patron_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    is_public BOOLEAN NOT NULL DEFAULT FALSE,
    share_token UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_patron_reading_lists_patron ON patron_reading_lists (patron_id);
CREATE UNIQUE INDEX IF NOT EXISTS ix_patron_reading_lists_share_token ON patron_reading_lists (share_token) WHERE share_token IS NOT NULL;

CREATE TABLE IF NOT EXISTS reading_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES patron_reading_lists(id) ON DELETE CASCADE,
    ebook_id INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    metislib_content_id VARCHAR(255),
    source_type VARCHAR(20) NOT NULL DEFAULT 'indie',
    added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE (list_id, ebook_id)
);
CREATE INDEX IF NOT EXISTS ix_reading_list_items_list ON reading_list_items (list_id);

-- ============================================================================
-- System 2: Author Presence — Updates
-- ============================================================================

CREATE TABLE IF NOT EXISTS author_update_types (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,
    label VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    requires_linked_ebook BOOLEAN NOT NULL DEFAULT FALSE,
    max_body_length INTEGER NOT NULL DEFAULT 500,
    allow_image BOOLEAN NOT NULL DEFAULT TRUE,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- Seed default update types
INSERT INTO author_update_types (slug, label, icon, description, sort_order) VALUES
    ('announcement', 'Announcement', 'megaphone', 'General announcements to your readers', 0),
    ('new_release', 'New Release', 'sparkles', 'Announce a new book or edition', 1),
    ('event', 'Event', 'calendar', 'Promote an upcoming event', 2),
    ('milestone', 'Milestone', 'trophy', 'Celebrate a milestone (borrows, reviews, etc.)', 3),
    ('behind_the_scenes', 'Behind the Scenes', 'eye', 'Share your writing process or inspiration', 4)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS author_updates (
    id SERIAL PRIMARY KEY,
    author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    metislib_author_id VARCHAR(255),
    update_type_id INTEGER NOT NULL REFERENCES author_update_types(id),
    title VARCHAR(200),
    body TEXT NOT NULL,
    image_url VARCHAR(500),
    linked_ebook_id INTEGER REFERENCES indie_ebooks(id) ON DELETE SET NULL,
    metislib_content_id VARCHAR(255),
    linked_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    is_draft BOOLEAN NOT NULL DEFAULT TRUE,
    staff_approved BOOLEAN NOT NULL DEFAULT FALSE,
    rejection_note TEXT,
    published_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_author_updates_author ON author_updates (author_id);
CREATE INDEX IF NOT EXISTS ix_author_updates_published ON author_updates (published_at) WHERE published_at IS NOT NULL AND is_draft = FALSE;
CREATE INDEX IF NOT EXISTS ix_author_updates_pending ON author_updates (created_at) WHERE is_draft = FALSE AND staff_approved = FALSE AND published_at IS NULL;

CREATE TABLE IF NOT EXISTS update_reactions (
    id SERIAL PRIMARY KEY,
    update_id INTEGER NOT NULL REFERENCES author_updates(id) ON DELETE CASCADE,
    patron_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patron_ref VARCHAR(255),
    reaction_type VARCHAR(50) NOT NULL DEFAULT 'heart',
    reacted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (update_id, patron_id)
);
CREATE INDEX IF NOT EXISTS ix_update_reactions_update ON update_reactions (update_id);

-- ============================================================================
-- System 3: Discovery — Editorial Content
-- ============================================================================

CREATE TABLE IF NOT EXISTS editorial_feature_types (
    id SERIAL PRIMARY KEY,
    slug VARCHAR(50) UNIQUE NOT NULL,
    label VARCHAR(100) NOT NULL,
    icon VARCHAR(50),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0
);

-- Seed default editorial types
INSERT INTO editorial_feature_types (slug, label, icon, description, sort_order) VALUES
    ('author_spotlight', 'Author Spotlight', 'user', 'In-depth feature on an indie author', 0),
    ('staff_interview', 'Staff Interview', 'mic', 'Q&A with an author conducted by staff', 1),
    ('themed_collection', 'Themed Collection', 'library', 'Curated books around a theme', 2),
    ('new_author_welcome', 'New Author Welcome', 'heart', 'Welcome feature for newly approved authors', 3),
    ('seasonal_roundup', 'Seasonal Roundup', 'sun', 'Seasonal reading recommendations', 4)
ON CONFLICT (slug) DO NOTHING;

CREATE TABLE IF NOT EXISTS editorial_features (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    subtitle VARCHAR(500),
    body TEXT NOT NULL,
    feature_type_id INTEGER NOT NULL REFERENCES editorial_feature_types(id),
    cover_image_url VARCHAR(500),
    linked_author_id INTEGER REFERENCES indie_authors(id) ON DELETE SET NULL,
    metislib_author_id VARCHAR(255),
    linked_ebook_ids JSONB DEFAULT '[]'::jsonb,
    metislib_content_ids JSONB DEFAULT '[]'::jsonb,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    published_at TIMESTAMPTZ,
    display_priority INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMPTZ,
    created_by_id INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_editorial_features_published ON editorial_features (display_priority) WHERE is_published = TRUE;
CREATE INDEX IF NOT EXISTS ix_editorial_features_author ON editorial_features (linked_author_id) WHERE linked_author_id IS NOT NULL;

-- ============================================================================
-- Configuration System
-- ============================================================================

CREATE TABLE IF NOT EXISTS indie_platform_settings (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- Seed default settings
INSERT INTO indie_platform_settings (key, value) VALUES
    ('trust_level_auto_approve_updates', '{"0": false, "1": true, "2": true}'::jsonb),
    ('trust_level_create_events', '{"0": false, "1": "staff_approval", "2": true}'::jsonb),
    ('reactions_enabled', 'true'::jsonb),
    ('reaction_types', '[{"slug": "heart", "label": "Love"}]'::jsonb),
    ('follower_counts_public', 'true'::jsonb),
    ('favorite_counts_public', 'true'::jsonb),
    ('happening_now_enabled', 'true'::jsonb),
    ('for_you_feed_enabled', 'true'::jsonb),
    ('update_max_body_length', '500'::jsonb),
    ('editorial_hero_enabled', 'true'::jsonb)
ON CONFLICT (key) DO NOTHING;

-- ============================================================================
-- Alter existing tables
-- ============================================================================

ALTER TABLE events ADD COLUMN IF NOT EXISTS indie_author_id INTEGER REFERENCES indie_authors(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS ix_events_indie_author ON events (indie_author_id) WHERE indie_author_id IS NOT NULL;

ALTER TABLE indie_authors ADD COLUMN IF NOT EXISTS pinned_ebook_id INTEGER REFERENCES indie_ebooks(id) ON DELETE SET NULL;
