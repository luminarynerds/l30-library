-- Adds activity feed, milestones, and shelf preferences tables
-- Part of My Shelf Redesign (2026-03-19)

-- Reading activity feed
CREATE TABLE IF NOT EXISTS reading_activities (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    catalog_item_id INTEGER REFERENCES catalog_items(id) ON DELETE CASCADE,
    activity_type VARCHAR(50) NOT NULL,
    summary VARCHAR(500) NOT NULL,
    metadata_json TEXT,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_reading_activities_user_id ON reading_activities(user_id);
CREATE INDEX IF NOT EXISTS ix_reading_activities_user_occurred
    ON reading_activities(user_id, occurred_at DESC);

-- Reading milestones
CREATE TABLE IF NOT EXISTS reading_milestones (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    milestone_type VARCHAR(50) NOT NULL,
    milestone_key VARCHAR(100) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description VARCHAR(500),
    earned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    dismissed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_milestone_key UNIQUE (user_id, milestone_key)
);

CREATE INDEX IF NOT EXISTS ix_reading_milestones_user_id ON reading_milestones(user_id);

-- Patron shelf preferences
CREATE TABLE IF NOT EXISTS patron_shelf_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    show_reading_activity BOOLEAN NOT NULL DEFAULT FALSE,
    show_pace_stats BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
