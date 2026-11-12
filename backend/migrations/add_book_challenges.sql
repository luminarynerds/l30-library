-- Book Challenges and Intellectual Freedom Resources tables
-- Created: 2026-03-26

-- Enum types for book challenges
DO $$ BEGIN
    CREATE TYPE challengestatus AS ENUM (
        'RECEIVED',
        'UNDER_REVIEW',
        'COMMITTEE_REVIEW',
        'BOARD_REVIEW',
        'RESOLVED_RETAINED',
        'RESOLVED_RESTRICTED',
        'RESOLVED_REMOVED',
        'WITHDRAWN'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE challengeoutcome AS ENUM (
        'RETAINED',
        'RETAINED_WITH_CHANGES',
        'RESTRICTED',
        'REMOVED',
        'WITHDRAWN',
        'PENDING'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE challengereason AS ENUM (
        'SEXUAL_CONTENT',
        'LGBTQ_CONTENT',
        'VIOLENCE',
        'LANGUAGE',
        'RELIGIOUS_VIEWPOINT',
        'POLITICAL_VIEWPOINT',
        'AGE_INAPPROPRIATE',
        'RACISM',
        'DRUGS_ALCOHOL',
        'ANTI_FAMILY',
        'OCCULT_SUPERNATURAL',
        'OTHER'
    );
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Book Challenges table
CREATE TABLE IF NOT EXISTS book_challenges (
    id                  SERIAL PRIMARY KEY,
    catalog_item_id     INTEGER REFERENCES catalog_items(id) ON DELETE SET NULL,
    title               VARCHAR(500) NOT NULL,
    author              VARCHAR(255),
    isbn                VARCHAR(20),
    status              challengestatus NOT NULL DEFAULT 'RECEIVED',
    primary_reason      challengereason NOT NULL,
    additional_reasons  TEXT,
    challenger_complaint TEXT,
    challenger_name     VARCHAR(255),
    challenger_is_patron BOOLEAN DEFAULT TRUE,
    challenger_contact  VARCHAR(255),
    date_received       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    date_resolved       TIMESTAMPTZ,
    outcome             challengeoutcome NOT NULL DEFAULT 'PENDING',
    resolution_summary  TEXT,
    committee_notes     TEXT,
    is_public           BOOLEAN DEFAULT FALSE,
    public_title        VARCHAR(255),
    public_summary      TEXT,
    lessons_learned     TEXT,
    assigned_staff_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    resolved_by_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_book_challenges_catalog_item_id ON book_challenges(catalog_item_id);
CREATE INDEX IF NOT EXISTS ix_book_challenges_status ON book_challenges(status);
CREATE INDEX IF NOT EXISTS ix_book_challenges_is_public ON book_challenges(is_public);
CREATE INDEX IF NOT EXISTS ix_book_challenges_id ON book_challenges(id);

-- Book Challenge Notes table
CREATE TABLE IF NOT EXISTS book_challenge_notes (
    id              SERIAL PRIMARY KEY,
    challenge_id    INTEGER NOT NULL REFERENCES book_challenges(id) ON DELETE CASCADE,
    note            TEXT NOT NULL,
    is_internal     BOOLEAN DEFAULT TRUE,
    created_by_id   INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_book_challenge_notes_challenge_id ON book_challenge_notes(challenge_id);
CREATE INDEX IF NOT EXISTS ix_book_challenge_notes_id ON book_challenge_notes(id);

-- Intellectual Freedom Resources table
CREATE TABLE IF NOT EXISTS intellectual_freedom_resources (
    id              SERIAL PRIMARY KEY,
    title           VARCHAR(255) NOT NULL,
    description     TEXT,
    content         TEXT,
    url             VARCHAR(500),
    resource_type   VARCHAR(50) NOT NULL,
    display_order   INTEGER DEFAULT 0,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_intellectual_freedom_resources_is_active ON intellectual_freedom_resources(is_active);
CREATE INDEX IF NOT EXISTS ix_intellectual_freedom_resources_id ON intellectual_freedom_resources(id);
