-- Migration: Add data integrity constraints (CHECK constraints + FK ondelete fixes)
-- Date: 2026-03-18
-- Description: Adds database-level CHECK constraints for business logic validation
--              and fixes missing ON DELETE behaviors on foreign keys.
--
-- This migration addresses gaps where invalid data could be inserted via
-- direct SQL, admin scripts, or application bugs bypassing validation.

BEGIN;

-- ============================================================================
-- CHECK CONSTRAINTS - Date ordering
-- ============================================================================

-- Checkouts: due_date must be >= checked_out_at
ALTER TABLE checkouts
    ADD CONSTRAINT ck_checkout_due_after_checkout
    CHECK (due_date >= checked_out_at);

-- Checkouts: returned_at must be >= checked_out_at (when set)
ALTER TABLE checkouts
    ADD CONSTRAINT ck_checkout_return_after_checkout
    CHECK (returned_at IS NULL OR returned_at >= checked_out_at);

-- Users: suspended_until must be after suspended_at
ALTER TABLE users
    ADD CONSTRAINT ck_user_suspended_until_after_suspended_at
    CHECK (suspended_until IS NULL OR suspended_at IS NULL OR suspended_until > suspended_at);

-- Inventory audits: completed_at must be >= started_at
ALTER TABLE inventory_audits
    ADD CONSTRAINT ck_inventory_audit_completed_after_started
    CHECK (completed_at IS NULL OR completed_at >= started_at);

-- Insurance policies: expiration_date must be after effective_date
ALTER TABLE insurance_policies
    ADD CONSTRAINT ck_insurance_policy_expiration_after_effective
    CHECK (expiration_date > effective_date);

-- Indie ebook borrows: returned_at must be >= borrowed_at
ALTER TABLE indie_ebook_borrows
    ADD CONSTRAINT ck_indie_ebook_borrow_return_after_borrow
    CHECK (returned_at IS NULL OR returned_at >= borrowed_at);

-- ============================================================================
-- CHECK CONSTRAINTS - Positive integers / valid ranges
-- ============================================================================

-- Catalog items
ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_publication_year_range
    CHECK (publication_year IS NULL OR (publication_year >= 1000 AND publication_year <= 2100));

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_page_count_positive
    CHECK (page_count IS NULL OR page_count > 0);

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_runtime_positive
    CHECK (runtime_minutes IS NULL OR runtime_minutes > 0);

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_disc_count_positive
    CHECK (disc_count IS NULL OR disc_count > 0);

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_track_count_positive
    CHECK (track_count IS NULL OR track_count > 0);

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_total_checkouts_non_negative
    CHECK (total_checkouts >= 0);

ALTER TABLE catalog_items
    ADD CONSTRAINT ck_catalog_item_share_count_non_negative
    CHECK (share_count >= 0);

-- Item copies
ALTER TABLE item_copies
    ADD CONSTRAINT ck_item_copy_copy_number_positive
    CHECK (copy_number > 0);

ALTER TABLE item_copies
    ADD CONSTRAINT ck_item_copy_replacement_cost_non_negative
    CHECK (replacement_cost IS NULL OR replacement_cost >= 0);

-- Holds
ALTER TABLE holds
    ADD CONSTRAINT ck_hold_position_positive
    CHECK (position > 0);

ALTER TABLE holds
    ADD CONSTRAINT ck_hold_no_show_count_non_negative
    CHECK (no_show_count >= 0);

-- Checkouts
ALTER TABLE checkouts
    ADD CONSTRAINT ck_checkout_renewal_count_non_negative
    CHECK (renewal_count >= 0);

-- Inventory audits
ALTER TABLE inventory_audits
    ADD CONSTRAINT ck_inventory_audit_items_expected_non_negative
    CHECK (items_expected >= 0);

ALTER TABLE inventory_audits
    ADD CONSTRAINT ck_inventory_audit_items_found_non_negative
    CHECK (items_found >= 0);

ALTER TABLE inventory_audits
    ADD CONSTRAINT ck_inventory_audit_items_missing_non_negative
    CHECK (items_missing >= 0);

ALTER TABLE inventory_audits
    ADD CONSTRAINT ck_inventory_audit_items_misplaced_non_negative
    CHECK (items_misplaced >= 0);

-- Users
ALTER TABLE users
    ADD CONSTRAINT ck_user_reading_minutes_owed_non_negative
    CHECK (reading_minutes_owed >= 0);

ALTER TABLE users
    ADD CONSTRAINT ck_user_reading_minutes_logged_non_negative
    CHECK (reading_minutes_logged >= 0);

ALTER TABLE users
    ADD CONSTRAINT ck_user_failed_login_attempts_non_negative
    CHECK (failed_login_attempts >= 0);

ALTER TABLE users
    ADD CONSTRAINT ck_user_room_no_show_count_non_negative
    CHECK (room_reservation_no_show_count >= 0);

-- Reading logs
ALTER TABLE reading_logs
    ADD CONSTRAINT ck_reading_log_minutes_positive
    CHECK (minutes > 0);

-- Indie ebooks
ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_total_copies_non_negative
    CHECK (total_copies >= 0);

ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_current_borrows_non_negative
    CHECK (current_borrows >= 0);

ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_borrow_duration_positive
    CHECK (borrow_duration_days > 0);

ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_publication_year_range
    CHECK (publication_year IS NULL OR (publication_year >= 1000 AND publication_year <= 2100));

ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_rating_count_non_negative
    CHECK (rating_count >= 0);

ALTER TABLE indie_ebooks
    ADD CONSTRAINT ck_indie_ebook_total_borrows_non_negative
    CHECK (total_borrows >= 0);

-- Indie ebook borrows
ALTER TABLE indie_ebook_borrows
    ADD CONSTRAINT ck_indie_ebook_borrow_rating_range
    CHECK (rating IS NULL OR (rating >= 1 AND rating <= 5));

ALTER TABLE indie_ebook_borrows
    ADD CONSTRAINT ck_indie_ebook_borrow_download_count_non_negative
    CHECK (download_count >= 0);

ALTER TABLE indie_ebook_borrows
    ADD CONSTRAINT ck_indie_ebook_borrow_max_downloads_positive
    CHECK (max_downloads > 0);

-- Insurance policies
ALTER TABLE insurance_policies
    ADD CONSTRAINT ck_insurance_policy_coverage_non_negative
    CHECK (coverage_amount >= 0);

ALTER TABLE insurance_policies
    ADD CONSTRAINT ck_insurance_policy_deductible_non_negative
    CHECK (deductible >= 0);

ALTER TABLE insurance_policies
    ADD CONSTRAINT ck_insurance_policy_claims_filed_non_negative
    CHECK (claims_filed >= 0);

-- ============================================================================
-- FOREIGN KEY ON DELETE fixes
-- ============================================================================
-- These ALTER statements fix ForeignKeys that were missing ON DELETE behavior.
-- The default PostgreSQL behavior (RESTRICT/NO ACTION) prevents cleanup of
-- parent records, which can lead to orphaned data when bypassing the ORM.
--
-- Strategy:
--   CASCADE: child record has no meaning without the parent
--   SET NULL: audit/reference trail should be preserved even if referent is removed

-- item_copies.catalog_item_id: CASCADE (copies are meaningless without catalog item)
ALTER TABLE item_copies
    DROP CONSTRAINT IF EXISTS item_copies_catalog_item_id_fkey,
    ADD CONSTRAINT item_copies_catalog_item_id_fkey
    FOREIGN KEY (catalog_item_id) REFERENCES catalog_items(id) ON DELETE CASCADE;

-- condition_changes.reported_by_id: SET NULL (preserve audit trail)
ALTER TABLE condition_changes
    DROP CONSTRAINT IF EXISTS condition_changes_reported_by_id_fkey,
    ADD CONSTRAINT condition_changes_reported_by_id_fkey
    FOREIGN KEY (reported_by_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE condition_changes ALTER COLUMN reported_by_id DROP NOT NULL;

-- inventory_audits.created_by_id: SET NULL (preserve audit trail)
ALTER TABLE inventory_audits
    DROP CONSTRAINT IF EXISTS inventory_audits_created_by_id_fkey,
    ADD CONSTRAINT inventory_audits_created_by_id_fkey
    FOREIGN KEY (created_by_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE inventory_audits ALTER COLUMN created_by_id DROP NOT NULL;

-- audit_scans.item_copy_id: CASCADE (scans are meaningless without item copy)
ALTER TABLE audit_scans
    DROP CONSTRAINT IF EXISTS audit_scans_item_copy_id_fkey,
    ADD CONSTRAINT audit_scans_item_copy_id_fkey
    FOREIGN KEY (item_copy_id) REFERENCES item_copies(id) ON DELETE CASCADE;

-- audit_scans.scanned_by_id: SET NULL (preserve audit trail)
ALTER TABLE audit_scans
    DROP CONSTRAINT IF EXISTS audit_scans_scanned_by_id_fkey,
    ADD CONSTRAINT audit_scans_scanned_by_id_fkey
    FOREIGN KEY (scanned_by_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE audit_scans ALTER COLUMN scanned_by_id DROP NOT NULL;

-- reading_logs.user_id: CASCADE (reading logs belong to user)
ALTER TABLE reading_logs
    DROP CONSTRAINT IF EXISTS reading_logs_user_id_fkey,
    ADD CONSTRAINT reading_logs_user_id_fkey
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE;

-- DMCA models
ALTER TABLE dmca_notices
    DROP CONSTRAINT IF EXISTS dmca_notices_ebook_id_fkey,
    ADD CONSTRAINT dmca_notices_ebook_id_fkey
    FOREIGN KEY (ebook_id) REFERENCES indie_ebooks(id) ON DELETE CASCADE;

ALTER TABLE dmca_notices
    DROP CONSTRAINT IF EXISTS dmca_notices_reviewed_by_id_fkey,
    ADD CONSTRAINT dmca_notices_reviewed_by_id_fkey
    FOREIGN KEY (reviewed_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE dmca_counter_notices
    DROP CONSTRAINT IF EXISTS dmca_counter_notices_notice_id_fkey,
    ADD CONSTRAINT dmca_counter_notices_notice_id_fkey
    FOREIGN KEY (notice_id) REFERENCES dmca_notices(id) ON DELETE CASCADE;

ALTER TABLE dmca_counter_notices
    DROP CONSTRAINT IF EXISTS dmca_counter_notices_author_id_fkey,
    ADD CONSTRAINT dmca_counter_notices_author_id_fkey
    FOREIGN KEY (author_id) REFERENCES indie_authors(id) ON DELETE CASCADE;

ALTER TABLE dmca_strikes
    DROP CONSTRAINT IF EXISTS dmca_strikes_author_id_fkey,
    ADD CONSTRAINT dmca_strikes_author_id_fkey
    FOREIGN KEY (author_id) REFERENCES indie_authors(id) ON DELETE CASCADE;

ALTER TABLE dmca_strikes
    DROP CONSTRAINT IF EXISTS dmca_strikes_notice_id_fkey,
    ADD CONSTRAINT dmca_strikes_notice_id_fkey
    FOREIGN KEY (notice_id) REFERENCES dmca_notices(id) ON DELETE CASCADE;

ALTER TABLE dmca_audit_logs
    DROP CONSTRAINT IF EXISTS dmca_audit_logs_notice_id_fkey,
    ADD CONSTRAINT dmca_audit_logs_notice_id_fkey
    FOREIGN KEY (notice_id) REFERENCES dmca_notices(id) ON DELETE CASCADE;

ALTER TABLE dmca_audit_logs
    DROP CONSTRAINT IF EXISTS dmca_audit_logs_actor_id_fkey,
    ADD CONSTRAINT dmca_audit_logs_actor_id_fkey
    FOREIGN KEY (actor_id) REFERENCES users(id) ON DELETE SET NULL;

-- Indie author audit trail references
ALTER TABLE indie_authors
    DROP CONSTRAINT IF EXISTS indie_authors_verified_by_id_fkey,
    ADD CONSTRAINT indie_authors_verified_by_id_fkey
    FOREIGN KEY (verified_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE indie_authors
    DROP CONSTRAINT IF EXISTS indie_authors_application_decided_by_id_fkey,
    ADD CONSTRAINT indie_authors_application_decided_by_id_fkey
    FOREIGN KEY (application_decided_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE indie_ebooks
    DROP CONSTRAINT IF EXISTS indie_ebooks_staff_reviewer_id_fkey,
    ADD CONSTRAINT indie_ebooks_staff_reviewer_id_fkey
    FOREIGN KEY (staff_reviewer_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE indie_ebooks
    DROP CONSTRAINT IF EXISTS indie_ebooks_cataloged_by_id_fkey,
    ADD CONSTRAINT indie_ebooks_cataloged_by_id_fkey
    FOREIGN KEY (cataloged_by_id) REFERENCES users(id) ON DELETE SET NULL;

-- Compliance tracking user references
ALTER TABLE ada_compliance
    DROP CONSTRAINT IF EXISTS ada_compliance_ada_coordinator_id_fkey,
    ADD CONSTRAINT ada_compliance_ada_coordinator_id_fkey
    FOREIGN KEY (ada_coordinator_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE state_library_requirements
    DROP CONSTRAINT IF EXISTS state_library_requirements_responsible_person_id_fkey,
    ADD CONSTRAINT state_library_requirements_responsible_person_id_fkey
    FOREIGN KEY (responsible_person_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE staff_certifications
    DROP CONSTRAINT IF EXISTS staff_certifications_verified_by_id_fkey,
    ADD CONSTRAINT staff_certifications_verified_by_id_fkey
    FOREIGN KEY (verified_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE policy_reviews
    DROP CONSTRAINT IF EXISTS policy_reviews_approved_by_id_fkey,
    ADD CONSTRAINT policy_reviews_approved_by_id_fkey
    FOREIGN KEY (approved_by_id) REFERENCES users(id) ON DELETE SET NULL;

ALTER TABLE policy_reviews
    DROP CONSTRAINT IF EXISTS policy_reviews_owner_id_fkey,
    ADD CONSTRAINT policy_reviews_owner_id_fkey
    FOREIGN KEY (owner_id) REFERENCES users(id) ON DELETE SET NULL;

COMMIT;
