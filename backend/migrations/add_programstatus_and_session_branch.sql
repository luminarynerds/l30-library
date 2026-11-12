-- Adds a real programstatus enum and converts programs.status to use it.
-- Adds branch_id to program_sessions so per-session counts are FK-safe.
-- Unblocks board-packet queries that need programs_held + program_attendance
-- without falling back to the events/EventRegistration path.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 5)

BEGIN;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'programstatus') THEN
        CREATE TYPE programstatus AS ENUM (
            -- All values up-front: keeping every enum member in the
            -- initial CREATE means the subsequent ALTER COLUMN below
            -- never depends on the transactional ADD VALUE order.
            'planned',
            'scheduled',
            'active',
            'in_progress',
            'completed',
            'cancelled',
            'postponed',
            'rescheduled'
        );
    END IF;
END$$;

ALTER TABLE programs
    ALTER COLUMN status TYPE programstatus
    USING status::programstatus;

ALTER TABLE program_sessions
    ADD COLUMN IF NOT EXISTS branch_id INTEGER REFERENCES branches(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS ix_program_sessions_branch_id
    ON program_sessions(branch_id);

COMMIT;
