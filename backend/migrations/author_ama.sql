-- Author AMA Feature Migration
-- Creates ama_sessions, ama_questions, ama_question_upvotes tables
-- Adds event_type to events, ama_enabled to organization_features

-- Enums
CREATE TYPE amasessionstatus AS ENUM ('upcoming', 'live', 'grace_period', 'archived');
CREATE TYPE questionmoderationstatus AS ENUM ('pending', 'approved', 'rejected');

-- Event type column
ALTER TABLE events ADD COLUMN IF NOT EXISTS event_type VARCHAR(50) NOT NULL DEFAULT 'standard';
CREATE INDEX IF NOT EXISTS ix_events_event_type ON events (event_type);

-- Feature toggle
ALTER TABLE organization_features ADD COLUMN IF NOT EXISTS ama_enabled BOOLEAN NOT NULL DEFAULT FALSE;

-- AMA Sessions
CREATE TABLE IF NOT EXISTS ama_sessions (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL UNIQUE REFERENCES events(id) ON DELETE CASCADE,
    status amasessionstatus NOT NULL DEFAULT 'upcoming',
    indie_author_id INTEGER REFERENCES indie_authors(id) ON DELETE SET NULL,
    guest_author_name VARCHAR(255),
    guest_author_bio TEXT,
    guest_author_photo_url VARCHAR(500),
    guest_author_token VARCHAR(255) UNIQUE,
    guest_author_token_expires_at TIMESTAMPTZ,
    grace_period_hours INTEGER NOT NULL DEFAULT 48,
    grace_period_ends_at TIMESTAMPTZ,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    total_questions INTEGER NOT NULL DEFAULT 0,
    total_answered INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ama_sessions_id ON ama_sessions (id);
CREATE INDEX IF NOT EXISTS ix_ama_sessions_status ON ama_sessions (status);

-- AMA Questions
CREATE TABLE IF NOT EXISTS ama_questions (
    id SERIAL PRIMARY KEY,
    ama_session_id INTEGER NOT NULL REFERENCES ama_sessions(id) ON DELETE CASCADE,
    asked_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    question_text TEXT NOT NULL,
    moderation_status questionmoderationstatus NOT NULL DEFAULT 'pending',
    moderated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    moderated_at TIMESTAMPTZ,
    moderation_reason VARCHAR(500),
    answer_text TEXT,
    answered_at TIMESTAMPTZ,
    upvote_count INTEGER NOT NULL DEFAULT 0,
    display_order INTEGER,
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_ama_questions_id ON ama_questions (id);
CREATE INDEX IF NOT EXISTS ix_ama_questions_session_status ON ama_questions (ama_session_id, moderation_status);

-- AMA Question Upvotes
CREATE TABLE IF NOT EXISTS ama_question_upvotes (
    id SERIAL PRIMARY KEY,
    question_id INTEGER NOT NULL REFERENCES ama_questions(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_ama_question_upvote UNIQUE (question_id, user_id)
);

CREATE INDEX IF NOT EXISTS ix_ama_question_upvotes_id ON ama_question_upvotes (id);
