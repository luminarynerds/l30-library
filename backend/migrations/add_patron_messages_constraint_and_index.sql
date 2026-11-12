
-- Review feedback (2026-05-13):
-- 1. CHECK constraint to prevent (delivered=true, status='failed') drift
--    between the legacy boolean and the new lifecycle enum.
-- 2. Better composite index for the print-queue read pattern:
--    WHERE channel = 'print' AND status = 'queued' ORDER BY sent_at.

BEGIN;

ALTER TABLE patron_messages
    DROP CONSTRAINT IF EXISTS ck_patron_messages_delivered_status;

ALTER TABLE patron_messages
    ADD CONSTRAINT ck_patron_messages_delivered_status
    CHECK (
        (delivered = TRUE  AND status IN ('sent', 'delivered', 'printed'))
        OR
        (delivered = FALSE AND status IN ('queued', 'failed'))
    );

-- Replace the prior (status, channel) index with a tighter one tuned for
-- the print-queue endpoint: filter then sort.
DROP INDEX IF EXISTS ix_patron_messages_status_channel;
CREATE INDEX IF NOT EXISTS ix_patron_messages_channel_status_sent
    ON patron_messages(channel, status, sent_at);

COMMIT;
