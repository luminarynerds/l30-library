-- Known Devices table for new-device detection and 2FA trusted devices
-- Date: 2026-03-13

BEGIN;

CREATE TABLE IF NOT EXISTS known_devices (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    device_hash VARCHAR(64) NOT NULL,
    friendly_name VARCHAR(255),
    ip_address VARCHAR(45),
    first_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    trusted_until TIMESTAMPTZ
);

CREATE UNIQUE INDEX IF NOT EXISTS ix_known_devices_user_device ON known_devices(user_id, device_hash);
CREATE INDEX IF NOT EXISTS ix_known_devices_user_id ON known_devices(user_id);

COMMIT;
