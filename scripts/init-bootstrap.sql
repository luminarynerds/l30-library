-- SPDX-FileCopyrightText: 2026 Luminary Nerds
-- SPDX-License-Identifier: AGPL-3.0-or-later
-- Bootstrap initialization on first DB startup
-- This creates a marker to prevent re-running the bootstrap

-- Create bootstrap marker table if it doesn't exist
CREATE TABLE IF NOT EXISTS _bootstrap_marker (
    id INTEGER PRIMARY KEY,
    bootstrapped_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
    version VARCHAR(50)
);

-- Note: The actual seed data is populated by run_all_seeds.py
-- which is called from backend startup or manual invocation
