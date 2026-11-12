-- Reference only: tables are auto-created from SQLAlchemy models. This file is for documentation.
-- Staff Message Board tables
-- Internal forum / virtual break room for library staff

CREATE TABLE IF NOT EXISTS staff_board_posts (
    id SERIAL PRIMARY KEY,
    title VARCHAR(300) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(30) NOT NULL DEFAULT 'general',
    pinned BOOLEAN NOT NULL DEFAULT FALSE,
    archived BOOLEAN NOT NULL DEFAULT FALSE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS staff_board_replies (
    id SERIAL PRIMARY KEY,
    content TEXT NOT NULL,
    post_id INTEGER NOT NULL REFERENCES staff_board_posts(id) ON DELETE CASCADE,
    author_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_staff_board_posts_category ON staff_board_posts(category);
CREATE INDEX IF NOT EXISTS idx_staff_board_posts_pinned ON staff_board_posts(pinned);
CREATE INDEX IF NOT EXISTS idx_staff_board_posts_author ON staff_board_posts(author_id);
CREATE INDEX IF NOT EXISTS idx_staff_board_replies_post ON staff_board_replies(post_id);
CREATE INDEX IF NOT EXISTS idx_staff_board_replies_author ON staff_board_replies(author_id);
