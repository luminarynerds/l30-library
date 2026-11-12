-- Account Security Enhancement: 2FA, recovery, and alert fields
-- Date: 2026-03-13

BEGIN;

-- 2FA fields on users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret TEXT;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_confirmed_at TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_codes TEXT;

-- Recovery email
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_email VARCHAR(254);
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_email_verified BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_email_token VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS recovery_email_token_expires TIMESTAMPTZ;

-- Security alert preferences
ALTER TABLE users ADD COLUMN IF NOT EXISTS security_alert_new_login BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS security_alert_changes BOOLEAN NOT NULL DEFAULT TRUE;

COMMIT;
