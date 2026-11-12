-- Print-on-Demand tables
-- Run: docker exec -i l30-database psql -U l30 -d l30_library < /app/migrations/pod_tables.sql

CREATE TABLE IF NOT EXISTS pod_title_configs (
    id SERIAL PRIMARY KEY,
    ebook_id INTEGER NOT NULL UNIQUE REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    list_price_cents INTEGER NOT NULL,
    cost_price_cents INTEGER,
    binding_type VARCHAR(30) NOT NULL DEFAULT 'paperback',
    interior_type VARCHAR(20) NOT NULL DEFAULT 'bw',
    trim_size VARCHAR(20) NOT NULL DEFAULT '6x9',
    paper_type VARCHAR(20) NOT NULL DEFAULT 'cream',
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    lulu_printable_id VARCHAR(100),
    cover_file_url VARCHAR(500),
    page_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_pod_title_configs_ebook_id ON pod_title_configs(ebook_id);
CREATE INDEX IF NOT EXISTS ix_pod_title_configs_author_id ON pod_title_configs(author_id);

CREATE TABLE IF NOT EXISTS pod_orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    ebook_id INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    pod_config_id INTEGER NOT NULL REFERENCES pod_title_configs(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    list_price_cents INTEGER NOT NULL,
    print_cost_cents INTEGER,
    shipping_cost_cents INTEGER,
    author_royalty_cents INTEGER,
    library_share_cents INTEGER,
    lulu_order_id VARCHAR(100),
    tracking_number VARCHAR(200),
    tracking_url VARCHAR(500),
    shipping_address JSONB NOT NULL,
    stripe_payment_intent_id VARCHAR(200),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ,
    shipped_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS ix_pod_orders_user_id ON pod_orders(user_id);
CREATE INDEX IF NOT EXISTS ix_pod_orders_ebook_id ON pod_orders(ebook_id);
CREATE INDEX IF NOT EXISTS ix_pod_orders_status ON pod_orders(status);
