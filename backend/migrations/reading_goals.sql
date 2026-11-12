-- Migration: Create reading_goals table
-- Feature: Reading Shelf Expansion (Phase 2 — Reading Goals)
-- Date: 2026-03-17
--
-- Run with:
--   docker exec -i l30-database psql -U l30 -d l30 < backend/migrations/reading_goals.sql

BEGIN;

CREATE TABLE IF NOT EXISTS reading_goals (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    year INTEGER NOT NULL,
    target_books INTEGER NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_user_year_reading_goal UNIQUE (user_id, year)
);

CREATE INDEX IF NOT EXISTS ix_reading_goals_id ON reading_goals(id);
CREATE INDEX IF NOT EXISTS ix_reading_goals_user_id ON reading_goals(user_id);

COMMIT;
