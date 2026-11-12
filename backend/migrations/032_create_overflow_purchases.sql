DO $$ BEGIN
    CREATE TYPE overflowpurchasestatus AS ENUM ('pending', 'completed', 'failed', 'cancelled', 'refunded');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS overflow_purchases (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    metislib_ebook_id INTEGER NOT NULL,
    ebook_title VARCHAR(500) NOT NULL,
    ebook_author VARCHAR(300),
    stripe_checkout_session_id VARCHAR(255) NOT NULL UNIQUE,
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    sale_price_cents INTEGER NOT NULL,
    stripe_fee_cents INTEGER,
    library_kickback_cents INTEGER,
    author_royalty_cents INTEGER,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    library_kickback_percent INTEGER NOT NULL,
    status overflowpurchasestatus NOT NULL DEFAULT 'pending',
    metislib_access_id INTEGER,
    royalty_transaction_id INTEGER REFERENCES royalty_transactions(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    refunded_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_overflow_purchases_user_id ON overflow_purchases(user_id);
CREATE INDEX IF NOT EXISTS ix_overflow_purchases_metislib_ebook_id ON overflow_purchases(metislib_ebook_id);
CREATE INDEX IF NOT EXISTS ix_overflow_purchases_status ON overflow_purchases(status);
CREATE INDEX IF NOT EXISTS ix_overflow_purchases_stripe_session ON overflow_purchases(stripe_checkout_session_id);
CREATE INDEX IF NOT EXISTS ix_overflow_purchases_stripe_pi ON overflow_purchases(stripe_payment_intent_id);
