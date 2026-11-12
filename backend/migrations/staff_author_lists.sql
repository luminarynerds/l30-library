-- Create staff_author_lists table
CREATE TABLE IF NOT EXISTS staff_author_lists (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    slug VARCHAR(220) UNIQUE NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT true,
    display_order INTEGER NOT NULL DEFAULT 0,
    created_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_staff_author_lists_slug ON staff_author_lists(slug);
CREATE INDEX idx_staff_author_lists_active ON staff_author_lists(is_active);
CREATE INDEX idx_staff_author_lists_display_order ON staff_author_lists(display_order);

-- Create staff_author_list_items table
CREATE TABLE IF NOT EXISTS staff_author_list_items (
    id SERIAL PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES staff_author_lists(id) ON DELETE CASCADE,
    author_id INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    staff_note TEXT,
    display_order INTEGER NOT NULL DEFAULT 0,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    added_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    UNIQUE(list_id, author_id)
);

CREATE INDEX idx_staff_author_list_items_list_id ON staff_author_list_items(list_id);
CREATE INDEX idx_staff_author_list_items_author_id ON staff_author_list_items(author_id);
CREATE INDEX idx_staff_author_list_items_display_order ON staff_author_list_items(display_order);
