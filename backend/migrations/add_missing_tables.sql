-- =============================================================================
-- Migration: Add all missing tables
-- Generated: 2026-03-26
-- Covers:
--   1. All learning platform tables (courses, modules, lessons, etc.)
--   2. Indie author sub-tables (borrows, waitlist, versions, reviews, etc.)
--   3. royalty_transactions
--   4. Deferred FK from overflow_purchases -> royalty_transactions
-- =============================================================================

-- ============================================================================
-- SECTION 1: LEARNING PLATFORM TABLES (from app/models/learning.py)
-- ============================================================================

-- courses
CREATE TABLE IF NOT EXISTS courses (
    id                      SERIAL PRIMARY KEY,
    title                   VARCHAR(200) NOT NULL,
    description             TEXT,
    thumbnail_url           VARCHAR(500),
    access_level            VARCHAR(20) NOT NULL DEFAULT 'patron',
    is_published            BOOLEAN NOT NULL DEFAULT FALSE,
    estimated_minutes       INTEGER,
    difficulty              VARCHAR(20) DEFAULT 'beginner',
    sensory_warning         TEXT,
    quiz_passing_threshold  INTEGER DEFAULT 70,
    xp_reward               INTEGER DEFAULT 100,
    prerequisite_course_ids JSONB DEFAULT '[]'::jsonb,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_courses_id ON courses (id);

-- modules
CREATE TABLE IF NOT EXISTS modules (
    id          SERIAL PRIMARY KEY,
    course_id   INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    title       VARCHAR(200) NOT NULL,
    description TEXT,
    sort_order  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_modules_id ON modules (id);
CREATE INDEX IF NOT EXISTS ix_modules_course_id ON modules (course_id);

-- lessons
CREATE TABLE IF NOT EXISTS lessons (
    id                       SERIAL PRIMARY KEY,
    module_id                INTEGER NOT NULL REFERENCES modules(id) ON DELETE CASCADE,
    title                    VARCHAR(200) NOT NULL,
    lesson_type              VARCHAR(20) NOT NULL,
    content                  JSONB NOT NULL,
    estimated_minutes        INTEGER,
    sensory_notes            TEXT,
    xp_reward                INTEGER DEFAULT 10,
    sort_order               INTEGER DEFAULT 0,
    summary                  TEXT,
    visual_aid_url           VARCHAR(500),
    audio_narration_url      VARCHAR(500),
    preferred_break_interval INTEGER
);
CREATE INDEX IF NOT EXISTS ix_lessons_id ON lessons (id);
CREATE INDEX IF NOT EXISTS ix_lessons_module_id ON lessons (module_id);

-- lesson_resources
CREATE TABLE IF NOT EXISTS lesson_resources (
    id            SERIAL PRIMARY KEY,
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    title         VARCHAR(200) NOT NULL,
    description   TEXT,
    resource_type VARCHAR(20) NOT NULL,
    url           VARCHAR(500) NOT NULL,
    sort_order    INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_lesson_resources_id ON lesson_resources (id);
CREATE INDEX IF NOT EXISTS ix_lesson_resources_lesson_id ON lesson_resources (lesson_id);

-- lesson_variants
CREATE TABLE IF NOT EXISTS lesson_variants (
    id           SERIAL PRIMARY KEY,
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    variant_type VARCHAR(20) NOT NULL,
    content      JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_lesson_variants_id ON lesson_variants (id);
CREATE INDEX IF NOT EXISTS ix_lesson_variants_lesson_id ON lesson_variants (lesson_id);

-- quiz_questions
CREATE TABLE IF NOT EXISTS quiz_questions (
    id            SERIAL PRIMARY KEY,
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    question_type VARCHAR(20) DEFAULT 'multiple_choice',
    options       JSONB,
    explanation   TEXT,
    sort_order    INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_id ON quiz_questions (id);
CREATE INDEX IF NOT EXISTS ix_quiz_questions_lesson_id ON quiz_questions (lesson_id);

-- enrollments
CREATE TABLE IF NOT EXISTS enrollments (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id    INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    enrolled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ,
    CONSTRAINT uq_enrollment UNIQUE (user_id, course_id)
);
CREATE INDEX IF NOT EXISTS ix_enrollments_id ON enrollments (id);
CREATE INDEX IF NOT EXISTS ix_enrollments_user_id ON enrollments (user_id);
CREATE INDEX IF NOT EXISTS ix_enrollments_course_id ON enrollments (course_id);

-- lesson_progress
CREATE TABLE IF NOT EXISTS lesson_progress (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id       INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    status          VARCHAR(20) DEFAULT 'not_started',
    quiz_score      INTEGER,
    variants_viewed JSONB DEFAULT '[]'::jsonb,
    scroll_position DOUBLE PRECISION,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    CONSTRAINT uq_lesson_progress UNIQUE (user_id, lesson_id)
);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_id ON lesson_progress (id);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_user_id ON lesson_progress (user_id);
CREATE INDEX IF NOT EXISTS ix_lesson_progress_lesson_id ON lesson_progress (lesson_id);

-- certificates
CREATE TABLE IF NOT EXISTS certificates (
    id                 SERIAL PRIMARY KEY,
    user_id            INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id          INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    certificate_number VARCHAR(50) NOT NULL UNIQUE,
    issued_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_certificate UNIQUE (user_id, course_id)
);
CREATE INDEX IF NOT EXISTS ix_certificates_id ON certificates (id);
CREATE INDEX IF NOT EXISTS ix_certificates_user_id ON certificates (user_id);
CREATE INDEX IF NOT EXISTS ix_certificates_course_id ON certificates (course_id);

-- quiz_attempts
CREATE TABLE IF NOT EXISTS quiz_attempts (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id    INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    score        INTEGER DEFAULT 0,
    passed       BOOLEAN DEFAULT FALSE,
    answers      JSONB DEFAULT '[]'::jsonb,
    started_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_quiz_attempts_id ON quiz_attempts (id);
CREATE INDEX IF NOT EXISTS ix_quiz_attempts_user_id ON quiz_attempts (user_id);
CREATE INDEX IF NOT EXISTS ix_quiz_attempts_lesson_id ON quiz_attempts (lesson_id);

-- skills
CREATE TABLE IF NOT EXISTS skills (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    category    VARCHAR(50) NOT NULL,
    is_active   BOOLEAN DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS ix_skills_id ON skills (id);
CREATE INDEX IF NOT EXISTS ix_skills_category ON skills (category);

-- user_skills
CREATE TABLE IF NOT EXISTS user_skills (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill_id      INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    current_level INTEGER DEFAULT 1,
    assessed_at   TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uq_user_skill UNIQUE (user_id, skill_id)
);
CREATE INDEX IF NOT EXISTS ix_user_skills_id ON user_skills (id);
CREATE INDEX IF NOT EXISTS ix_user_skills_user_id ON user_skills (user_id);
CREATE INDEX IF NOT EXISTS ix_user_skills_skill_id ON user_skills (skill_id);

-- role_required_skills
CREATE TABLE IF NOT EXISTS role_required_skills (
    id             SERIAL PRIMARY KEY,
    role           VARCHAR(50) NOT NULL,
    skill_id       INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    required_level INTEGER DEFAULT 3,
    is_mandatory   BOOLEAN DEFAULT TRUE,
    CONSTRAINT uq_role_skill UNIQUE (role, skill_id)
);
CREATE INDEX IF NOT EXISTS ix_role_required_skills_id ON role_required_skills (id);
CREATE INDEX IF NOT EXISTS ix_role_required_skills_role ON role_required_skills (role);

-- skill_assessment_questions
CREATE TABLE IF NOT EXISTS skill_assessment_questions (
    id               SERIAL PRIMARY KEY,
    skill_id         INTEGER NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
    question_text    TEXT NOT NULL,
    question_type    VARCHAR(20) DEFAULT 'multiple_choice',
    options          JSONB,
    difficulty_level INTEGER DEFAULT 1,
    explanation      TEXT,
    sort_order       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_skill_assessment_questions_id ON skill_assessment_questions (id);
CREATE INDEX IF NOT EXISTS ix_skill_assessment_questions_skill_id ON skill_assessment_questions (skill_id);

-- external_resources
CREATE TABLE IF NOT EXISTS external_resources (
    id                  SERIAL PRIMARY KEY,
    title               VARCHAR(255) NOT NULL,
    description         TEXT,
    source_url          VARCHAR(500) NOT NULL UNIQUE,
    thumbnail_url       VARCHAR(500),
    provider            VARCHAR(100) DEFAULT 'data.org',
    resource_type       VARCHAR(50),
    difficulty          VARCHAR(20) DEFAULT 'beginner',
    topics              JSONB DEFAULT '[]'::jsonb,
    access_level        VARCHAR(20) DEFAULT 'patron',
    estimated_minutes   INTEGER,
    is_featured         BOOLEAN DEFAULT FALSE,
    source_organization VARCHAR(200),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_external_resources_id ON external_resources (id);
CREATE INDEX IF NOT EXISTS ix_external_resources_source_url ON external_resources (source_url);
CREATE INDEX IF NOT EXISTS ix_external_resources_provider ON external_resources (provider);
CREATE INDEX IF NOT EXISTS ix_external_resources_is_featured ON external_resources (is_featured);

-- external_resource_enrollments
CREATE TABLE IF NOT EXISTS external_resource_enrollments (
    id                   SERIAL PRIMARY KEY,
    user_id              INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    external_resource_id INTEGER NOT NULL REFERENCES external_resources(id) ON DELETE CASCADE,
    clicked_at           TIMESTAMPTZ,
    completed            BOOLEAN DEFAULT FALSE,
    completion_date      TIMESTAMPTZ,
    rating               INTEGER,
    notes                TEXT,
    created_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_external_resource_enrollment UNIQUE (user_id, external_resource_id)
);
CREATE INDEX IF NOT EXISTS ix_external_resource_enrollments_id ON external_resource_enrollments (id);
CREATE INDEX IF NOT EXISTS ix_external_resource_enrollments_user_id ON external_resource_enrollments (user_id);
CREATE INDEX IF NOT EXISTS ix_external_resource_enrollments_ext_id ON external_resource_enrollments (external_resource_id);

-- course_views
CREATE TABLE IF NOT EXISTS course_views (
    id        SERIAL PRIMARY KEY,
    user_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_id INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    viewed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_course_view UNIQUE (user_id, course_id)
);
CREATE INDEX IF NOT EXISTS ix_course_views_id ON course_views (id);
CREATE INDEX IF NOT EXISTS ix_course_views_user_id ON course_views (user_id);
CREATE INDEX IF NOT EXISTS ix_course_views_course_id ON course_views (course_id);

-- lesson_bookmarks
CREATE TABLE IF NOT EXISTS lesson_bookmarks (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lesson_id  INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_lesson_bookmark UNIQUE (user_id, lesson_id)
);
CREATE INDEX IF NOT EXISTS ix_lesson_bookmarks_id ON lesson_bookmarks (id);
CREATE INDEX IF NOT EXISTS ix_lesson_bookmarks_user_id ON lesson_bookmarks (user_id);
CREATE INDEX IF NOT EXISTS ix_lesson_bookmarks_lesson_id ON lesson_bookmarks (lesson_id);

-- course_feedback
CREATE TABLE IF NOT EXISTS course_feedback (
    id             SERIAL PRIMARY KEY,
    user_id        INTEGER REFERENCES users(id) ON DELETE SET NULL,
    course_id      INTEGER NOT NULL REFERENCES courses(id) ON DELETE CASCADE,
    lesson_id      INTEGER REFERENCES lessons(id) ON DELETE SET NULL,
    feedback_type  VARCHAR(30) NOT NULL,
    rating         DOUBLE PRECISION,
    comment        TEXT,
    status         VARCHAR(20) NOT NULL DEFAULT 'pending',
    admin_notes    TEXT,
    reviewed_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at    TIMESTAMPTZ,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_course_feedback_id ON course_feedback (id);
CREATE INDEX IF NOT EXISTS idx_course_feedback_course ON course_feedback (course_id);
CREATE INDEX IF NOT EXISTS idx_course_feedback_lesson ON course_feedback (lesson_id);
CREATE INDEX IF NOT EXISTS idx_course_feedback_user ON course_feedback (user_id);
CREATE INDEX IF NOT EXISTS idx_course_feedback_status ON course_feedback (status);
CREATE INDEX IF NOT EXISTS idx_course_feedback_type ON course_feedback (feedback_type);

-- ============================================================================
-- SECTION 2: INDIE AUTHOR SUB-TABLES (from app/models/indie_author.py)
-- These must come before royalty_transactions which FKs into indie_ebook_borrows.
-- ============================================================================

-- ebook_submission_reviews
CREATE TABLE IF NOT EXISTS ebook_submission_reviews (
    id               SERIAL PRIMARY KEY,
    ebook_id         INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    review_type      reviewtype NOT NULL,
    reviewer_id      INTEGER REFERENCES users(id) ON DELETE SET NULL,
    decision         reviewdecision NOT NULL,
    notes            TEXT,
    ai_analysis      JSON,
    flagged_content  JSON,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_ebook_submission_reviews_id ON ebook_submission_reviews (id);
CREATE INDEX IF NOT EXISTS ix_ebook_submission_reviews_ebook_id ON ebook_submission_reviews (ebook_id);

-- indie_ebook_borrows
CREATE TABLE IF NOT EXISTS indie_ebook_borrows (
    id                    SERIAL PRIMARY KEY,
    ebook_id              INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    user_id               INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    borrowed_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at                TIMESTAMPTZ NOT NULL,
    returned_at           TIMESTAMPTZ,
    status                borrowstatus NOT NULL DEFAULT 'active',
    access_token          VARCHAR(64) NOT NULL UNIQUE,
    download_count        INTEGER NOT NULL DEFAULT 0,
    max_downloads         INTEGER NOT NULL DEFAULT 5,
    rating                INTEGER,
    review_text           TEXT,
    review_submitted_at   TIMESTAMPTZ,
    is_review_deleted     BOOLEAN NOT NULL DEFAULT FALSE,
    review_deleted_at     TIMESTAMPTZ,
    review_deleted_by_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    deletion_reason       VARCHAR(500),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_indie_ebook_borrow_return_after_borrow CHECK (returned_at IS NULL OR returned_at >= borrowed_at),
    CONSTRAINT ck_indie_ebook_borrow_rating_range CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5)),
    CONSTRAINT ck_indie_ebook_borrow_download_count_non_negative CHECK (download_count >= 0),
    CONSTRAINT ck_indie_ebook_borrow_max_downloads_positive CHECK (max_downloads > 0)
);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_id ON indie_ebook_borrows (id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_ebook_id ON indie_ebook_borrows (ebook_id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_user_id ON indie_ebook_borrows (user_id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_status ON indie_ebook_borrows (status);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_access_token ON indie_ebook_borrows (access_token);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_borrows_is_review_deleted ON indie_ebook_borrows (is_review_deleted);

-- indie_ebook_waitlist
CREATE TABLE IF NOT EXISTS indie_ebook_waitlist (
    id                     SERIAL PRIMARY KEY,
    ebook_id               INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    user_id                INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    position               INTEGER NOT NULL,
    notified_at            TIMESTAMPTZ,
    notification_expires_at TIMESTAMPTZ,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_waitlist_id ON indie_ebook_waitlist (id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_waitlist_ebook_id ON indie_ebook_waitlist (ebook_id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_waitlist_user_id ON indie_ebook_waitlist (user_id);

-- indie_ebook_versions
CREATE TABLE IF NOT EXISTS indie_ebook_versions (
    id             SERIAL PRIMARY KEY,
    ebook_id       INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    version_number INTEGER NOT NULL,
    snapshot       JSON NOT NULL,
    changed_fields JSON NOT NULL,
    changed_by_id  INTEGER REFERENCES users(id) ON DELETE SET NULL,
    changed_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    change_reason  VARCHAR(500),
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_versions_id ON indie_ebook_versions (id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_versions_ebook_id ON indie_ebook_versions (ebook_id);
CREATE INDEX IF NOT EXISTS ix_indie_ebook_versions_changed_by_id ON indie_ebook_versions (changed_by_id);

-- public_domain_hashes
CREATE TABLE IF NOT EXISTS public_domain_hashes (
    id        SERIAL PRIMARY KEY,
    file_hash VARCHAR(64) NOT NULL UNIQUE,
    title     VARCHAR(500) NOT NULL,
    author    VARCHAR(255),
    source    VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_public_domain_hashes_id ON public_domain_hashes (id);
CREATE INDEX IF NOT EXISTS ix_public_domain_hashes_file_hash ON public_domain_hashes (file_hash);

-- ============================================================================
-- SECTION 3: royalty_transactions (depends on indie_authors, indie_ebooks,
--            and indie_ebook_borrows — all must exist first)
-- ============================================================================

-- Ensure enum exists (no-op if already present)
DO $$ BEGIN
    CREATE TYPE royaltytransactionstatus AS ENUM ('pending', 'earned', 'paid', 'clawed_back');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS royalty_transactions (
    id               SERIAL PRIMARY KEY,
    author_id        INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    ebook_id         INTEGER NOT NULL REFERENCES indie_ebooks(id) ON DELETE CASCADE,
    borrow_id        INTEGER UNIQUE REFERENCES indie_ebook_borrows(id) ON DELETE CASCADE,
    amount           DOUBLE PRECISION NOT NULL,
    royalty_rate     DOUBLE PRECISION NOT NULL,
    status           royaltytransactionstatus NOT NULL DEFAULT 'pending',
    transaction_date TIMESTAMPTZ NOT NULL DEFAULT now(),
    paid_date        TIMESTAMPTZ,
    notes            TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_royalty_transactions_id ON royalty_transactions (id);
CREATE INDEX IF NOT EXISTS ix_royalty_transactions_author_id ON royalty_transactions (author_id);
CREATE INDEX IF NOT EXISTS ix_royalty_transactions_ebook_id ON royalty_transactions (ebook_id);
CREATE INDEX IF NOT EXISTS ix_royalty_transactions_borrow_id ON royalty_transactions (borrow_id);
CREATE INDEX IF NOT EXISTS ix_royalty_transactions_status ON royalty_transactions (status);

-- author_balances (depends on indie_authors — already exists; listed after royalty_transactions
-- for logical grouping)
CREATE TABLE IF NOT EXISTS author_balances (
    id                     SERIAL PRIMARY KEY,
    author_id              INTEGER NOT NULL UNIQUE REFERENCES indie_authors(id) ON DELETE CASCADE,
    available_balance      DOUBLE PRECISION NOT NULL DEFAULT 0,
    paid_balance           DOUBLE PRECISION NOT NULL DEFAULT 0,
    pending_payout_amount  DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_transactions     INTEGER NOT NULL DEFAULT 0,
    total_checkouts        INTEGER NOT NULL DEFAULT 0,
    last_payout_date       TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS ix_author_balances_id ON author_balances (id);
CREATE INDEX IF NOT EXISTS ix_author_balances_author_id ON author_balances (author_id);

-- author_payout_history
CREATE TABLE IF NOT EXISTS author_payout_history (
    id                SERIAL PRIMARY KEY,
    author_id         INTEGER NOT NULL REFERENCES indie_authors(id) ON DELETE CASCADE,
    amount            DOUBLE PRECISION NOT NULL,
    stripe_transfer_id VARCHAR(255) UNIQUE,
    status            VARCHAR(50) NOT NULL,
    error_message     TEXT,
    requested_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at      TIMESTAMPTZ,
    transaction_count INTEGER DEFAULT 1,
    notes             TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_author_payout_history_id ON author_payout_history (id);
CREATE INDEX IF NOT EXISTS ix_author_payout_history_author_id ON author_payout_history (author_id);
CREATE INDEX IF NOT EXISTS ix_author_payout_history_status ON author_payout_history (status);

-- ============================================================================
-- SECTION 4: Deferred FK — overflow_purchases -> royalty_transactions
-- The model uses use_alter=True, meaning the FK was meant to be added after
-- both tables exist. Add it now if missing.
-- ============================================================================

DO $$ BEGIN
    ALTER TABLE overflow_purchases
        ADD CONSTRAINT fk_overflow_purchases_royalty_transaction_id
        FOREIGN KEY (royalty_transaction_id)
        REFERENCES royalty_transactions(id)
        ON DELETE SET NULL;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
