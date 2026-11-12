-- Adds users.last_activity_at as a materialized signal of patron engagement,
-- backfilled from existing checkouts/holds/messages/last_login.
-- Used by outreach criteria (lapsed_days) and lapsed-patron queries that
-- currently fan out across four tables.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 4)
--
-- Safe to re-run.

BEGIN;

-- 1) Column
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS ix_users_last_activity_at
    ON users(last_activity_at);

-- 2) Backfill: greatest of last checkout, last hold, last message-sent,
--    last_login, account creation. Conservative — never lower than created_at.
WITH activity AS (
    SELECT
        u.id AS user_id,
        GREATEST(
            COALESCE(MAX(c.checked_out_at), u.created_at),
            COALESCE(MAX(c.returned_at),    u.created_at),
            COALESCE(MAX(h.created_at),     u.created_at),
            COALESCE(MAX(pm.sent_at),       u.created_at),
            COALESCE(u.last_login,          u.created_at),
            u.created_at
        ) AS latest
    FROM users u
    LEFT JOIN checkouts c        ON c.user_id   = u.id
    LEFT JOIN holds h            ON h.user_id   = u.id
    LEFT JOIN patron_messages pm ON pm.patron_id = u.id
    GROUP BY u.id, u.created_at, u.last_login
)
UPDATE users u
SET last_activity_at = a.latest
FROM activity a
WHERE a.user_id = u.id
  AND (u.last_activity_at IS NULL OR u.last_activity_at < a.latest);

-- 3) Trigger function: bump users.last_activity_at when a checkout, hold,
--    or message references the patron. Keep the function permissive
--    (does nothing if the user no longer exists).
CREATE OR REPLACE FUNCTION bump_user_last_activity()
RETURNS TRIGGER AS $$
DECLARE
    target_user_id INTEGER;
    activity_time  TIMESTAMPTZ;
BEGIN
    IF TG_TABLE_NAME = 'checkouts' THEN
        target_user_id := NEW.user_id;
        activity_time  := COALESCE(NEW.returned_at, NEW.checked_out_at, NOW());
    ELSIF TG_TABLE_NAME = 'holds' THEN
        target_user_id := NEW.user_id;
        activity_time  := COALESCE(NEW.updated_at, NEW.created_at, NOW());
    ELSIF TG_TABLE_NAME = 'patron_messages' THEN
        target_user_id := NEW.patron_id;
        activity_time  := COALESCE(NEW.sent_at, NOW());
    ELSE
        RETURN NEW;
    END IF;

    IF target_user_id IS NULL THEN
        RETURN NEW;
    END IF;

    UPDATE users
    SET last_activity_at = activity_time
    WHERE id = target_user_id
      AND (last_activity_at IS NULL OR last_activity_at < activity_time);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_bump_last_activity_checkouts        ON checkouts;
DROP TRIGGER IF EXISTS trg_bump_last_activity_holds            ON holds;
DROP TRIGGER IF EXISTS trg_bump_last_activity_patron_messages  ON patron_messages;

CREATE TRIGGER trg_bump_last_activity_checkouts
    AFTER INSERT OR UPDATE OF returned_at, checked_out_at
    ON checkouts
    FOR EACH ROW
    EXECUTE FUNCTION bump_user_last_activity();

CREATE TRIGGER trg_bump_last_activity_holds
    AFTER INSERT OR UPDATE OF updated_at, created_at
    ON holds
    FOR EACH ROW
    EXECUTE FUNCTION bump_user_last_activity();

CREATE TRIGGER trg_bump_last_activity_patron_messages
    AFTER INSERT OR UPDATE OF sent_at
    ON patron_messages
    FOR EACH ROW
    EXECUTE FUNCTION bump_user_last_activity();

COMMIT;
