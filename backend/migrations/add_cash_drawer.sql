-- Cash Drawer / Petty Cash Management tables
-- Created: 2026-03-03

-- Enum types (prefixed to avoid conflicts with existing enums)
DO $$ BEGIN
    CREATE TYPE cash_drawer_mode AS ENUM ('shift_based', 'day_based');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE cash_session_status AS ENUM ('open', 'pending_approval', 'closed');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE cash_transaction_direction AS ENUM ('inflow', 'outflow');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE cash_transaction_category AS ENUM ('fine_payment', 'print_fee', 'copy_fee', 'room_fee', 'card_replacement', 'makerspace_fee', 'petty_cash', 'other');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Cash Drawers
CREATE TABLE IF NOT EXISTS cash_drawers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    default_float NUMERIC(10,2) NOT NULL DEFAULT 100.00,
    mode cash_drawer_mode NOT NULL DEFAULT 'day_based',
    discrepancy_threshold NUMERIC(10,2) NOT NULL DEFAULT 5.00,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Cash Drawer Sessions
CREATE TABLE IF NOT EXISTS cash_drawer_sessions (
    id SERIAL PRIMARY KEY,
    drawer_id INTEGER NOT NULL REFERENCES cash_drawers(id),
    opened_by INTEGER NOT NULL REFERENCES users(id),
    closed_by INTEGER REFERENCES users(id),
    approved_by INTEGER REFERENCES users(id),
    status cash_session_status NOT NULL DEFAULT 'open',
    opening_float NUMERIC(10,2) NOT NULL,
    expected_total NUMERIC(10,2),
    counted_total NUMERIC(10,2),
    discrepancy NUMERIC(10,2),
    denomination_breakdown JSONB,
    notes TEXT,
    opened_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cash_drawer_sessions_drawer_id ON cash_drawer_sessions(drawer_id);
CREATE INDEX IF NOT EXISTS idx_cash_drawer_sessions_status ON cash_drawer_sessions(status);

-- Cash Transactions
CREATE TABLE IF NOT EXISTS cash_transactions (
    id SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES cash_drawer_sessions(id),
    staff_id INTEGER NOT NULL REFERENCES users(id),
    direction cash_transaction_direction NOT NULL,
    category cash_transaction_category NOT NULL,
    amount NUMERIC(10,2) NOT NULL,
    amount_tendered NUMERIC(10,2),
    change_given NUMERIC(10,2),
    description TEXT,
    reference_type VARCHAR(50),
    reference_id INTEGER,
    voided BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cash_transactions_session_id ON cash_transactions(session_id);
