-- Adds 'print' value to messagechannel enum and a per-message lifecycle
-- status column. Unblocks librarian-agent print_only / email_or_print
-- delivery modes and the staff print queue.
--
-- See: docs/specs/2026-05-13-db-brittleness-reduction-spec.md (Item 3)
--
-- Safe to re-run: every step is idempotent.

BEGIN;

-- 1) Add 'print' to messagechannel enum (lowercase, per L30 enum rules)
ALTER TYPE messagechannel ADD VALUE IF NOT EXISTS 'print';

COMMIT;

-- ALTER TYPE ... ADD VALUE cannot run in the same transaction that uses
-- the new value, so the status enum and column live in their own block.

BEGIN;

-- 2) Create messagestatus enum if it does not already exist
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'messagestatus') THEN
        CREATE TYPE messagestatus AS ENUM (
            'queued',
            'sent',
            'delivered',
            'failed',
            'printed'
        );
    END IF;
END$$;

-- 3) Add status column to patron_messages with safe default
ALTER TABLE patron_messages
    ADD COLUMN IF NOT EXISTS status messagestatus NOT NULL DEFAULT 'sent';

-- 4) Backfill existing rows.
--    - delivered=true  -> 'sent' (the default; no work)
--    - delivered=false -> 'failed'
--    Information is lost either way; we record the best signal available.
UPDATE patron_messages
SET status = 'failed'
WHERE delivered = FALSE
  AND status = 'sent';  -- only touch rows still on the default

-- 5) Index for the print queue view
CREATE INDEX IF NOT EXISTS ix_patron_messages_status_channel
    ON patron_messages(status, channel);

COMMIT;
