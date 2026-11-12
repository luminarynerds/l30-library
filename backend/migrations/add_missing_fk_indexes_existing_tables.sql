-- LSC Missing Foreign Key Indexes - For Existing Tables Only
-- Generated: 2026-02-11
-- Adds indexes for foreign keys in tables that actually exist in littleschitt_library database
--
-- This script creates indexes for FK columns that don't already have them
-- Safe to run multiple times (uses IF NOT EXISTS)

BEGIN;

-- =============================================================================
-- Board System Tables
-- =============================================================================

-- agenda_items
CREATE INDEX IF NOT EXISTS idx_agenda_items_created_by_id ON agenda_items(created_by_id);
CREATE INDEX IF NOT EXISTS idx_agenda_items_meeting_id ON agenda_items(meeting_id);
CREATE INDEX IF NOT EXISTS idx_agenda_items_parent_item_id ON agenda_items(parent_item_id);

-- ai_tools
CREATE INDEX IF NOT EXISTS idx_ai_tools_created_by_id ON ai_tools(created_by_id);
CREATE INDEX IF NOT EXISTS idx_ai_tools_updated_by_id ON ai_tools(updated_by_id);

-- announcements
CREATE INDEX IF NOT EXISTS idx_announcements_created_by_id ON announcements(created_by_id);

-- audit_scans
CREATE INDEX IF NOT EXISTS idx_audit_scans_audit_id ON audit_scans(audit_id);
CREATE INDEX IF NOT EXISTS idx_audit_scans_item_copy_id ON audit_scans(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_audit_scans_scanned_by_id ON audit_scans(scanned_by_id);

-- board_documents
CREATE INDEX IF NOT EXISTS idx_board_documents_created_by_id ON board_documents(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_documents_meeting_id ON board_documents(meeting_id);
CREATE INDEX IF NOT EXISTS idx_board_documents_previous_version_id ON board_documents(previous_version_id);
CREATE INDEX IF NOT EXISTS idx_board_documents_published_by_id ON board_documents(published_by_id);

-- board_meeting_briefs
CREATE INDEX IF NOT EXISTS idx_board_meeting_briefs_created_by_id ON board_meeting_briefs(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_meeting_briefs_meeting_id ON board_meeting_briefs(meeting_id);

-- board_meetings
CREATE INDEX IF NOT EXISTS idx_board_meetings_agenda_published_by_id ON board_meetings(agenda_published_by_id);
CREATE INDEX IF NOT EXISTS idx_board_meetings_created_by_id ON board_meetings(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_meetings_minutes_approved_by_id ON board_meetings(minutes_approved_by_id);

-- board_members
CREATE INDEX IF NOT EXISTS idx_board_members_user_id ON board_members(user_id);

-- board_minutes
CREATE INDEX IF NOT EXISTS idx_board_minutes_approved_by_id ON board_minutes(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_board_minutes_created_by_id ON board_minutes(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_minutes_meeting_id ON board_minutes(meeting_id);
CREATE INDEX IF NOT EXISTS idx_board_minutes_prepared_by_id ON board_minutes(prepared_by_id);

-- board_votes
CREATE INDEX IF NOT EXISTS idx_board_votes_closed_by_id ON board_votes(closed_by_id);
CREATE INDEX IF NOT EXISTS idx_board_votes_created_by_id ON board_votes(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_votes_meeting_id ON board_votes(meeting_id);

-- board_votes_cast
CREATE INDEX IF NOT EXISTS idx_board_votes_cast_board_member_id ON board_votes_cast(board_member_id);
CREATE INDEX IF NOT EXISTS idx_board_votes_cast_vote_id ON board_votes_cast(vote_id);

-- =============================================================================
-- Catalog & Circulation Tables
-- =============================================================================

-- catalog_items
CREATE INDEX IF NOT EXISTS idx_catalog_items_cataloged_by_id ON catalog_items(cataloged_by_id);

-- cataloging_queue
CREATE INDEX IF NOT EXISTS idx_cataloging_queue_assigned_to_id ON cataloging_queue(assigned_to_id);

-- checkouts
CREATE INDEX IF NOT EXISTS idx_checkouts_patron_id ON checkouts(patron_id);
CREATE INDEX IF NOT EXISTS idx_checkouts_item_copy_id ON checkouts(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_checkouts_checked_out_by_id ON checkouts(checked_out_by_id);
CREATE INDEX IF NOT EXISTS idx_checkouts_checked_in_by_id ON checkouts(checked_in_by_id);

-- holds
CREATE INDEX IF NOT EXISTS idx_holds_patron_id ON holds(patron_id);
CREATE INDEX IF NOT EXISTS idx_holds_catalog_item_id ON holds(catalog_item_id);
CREATE INDEX IF NOT EXISTS idx_holds_filled_item_copy_id ON holds(filled_item_copy_id);
CREATE INDEX IF NOT EXISTS idx_holds_cancelled_by_id ON holds(cancelled_by_id);

-- item_copies
CREATE INDEX IF NOT EXISTS idx_item_copies_catalog_item_id ON item_copies(catalog_item_id);
CREATE INDEX IF NOT EXISTS idx_item_copies_current_location_id ON item_copies(current_location_id);

-- favorites
CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_favorites_catalog_item_id ON favorites(catalog_item_id);

-- =============================================================================
-- Learning & Courses Tables
-- =============================================================================

-- courses
CREATE INDEX IF NOT EXISTS idx_courses_created_by_id ON courses(created_by_id);
CREATE INDEX IF NOT EXISTS idx_courses_instructor_id ON courses(instructor_id);

-- enrollments
CREATE INDEX IF NOT EXISTS idx_enrollments_user_id ON enrollments(user_id);
CREATE INDEX IF NOT EXISTS idx_enrollments_course_id ON enrollments(course_id);

-- learning_paths
CREATE INDEX IF NOT EXISTS idx_learning_paths_created_by_id ON learning_paths(created_by_id);

-- learning_labs
CREATE INDEX IF NOT EXISTS idx_learning_labs_created_by_id ON learning_labs(created_by_id);

-- lab_completions
CREATE INDEX IF NOT EXISTS idx_lab_completions_user_id ON lab_completions(user_id);
CREATE INDEX IF NOT EXISTS idx_lab_completions_lab_id ON lab_completions(lab_id);

-- lesson_progress
CREATE INDEX IF NOT EXISTS idx_lesson_progress_user_id ON lesson_progress(user_id);
CREATE INDEX IF NOT EXISTS idx_lesson_progress_lesson_id ON lesson_progress(lesson_id);

-- certificates
CREATE INDEX IF NOT EXISTS idx_certificates_user_id ON certificates(user_id);
CREATE INDEX IF NOT EXISTS idx_certificates_course_id ON certificates(course_id);

-- =============================================================================
-- Financial Tables
-- =============================================================================

-- fines
CREATE INDEX IF NOT EXISTS idx_fines_patron_id ON fines(patron_id);
CREATE INDEX IF NOT EXISTS idx_fines_checkout_id ON fines(checkout_id);
CREATE INDEX IF NOT EXISTS idx_fines_waived_by_id ON fines(waived_by_id);

-- =============================================================================
-- Event Tables
-- =============================================================================

-- events
CREATE INDEX IF NOT EXISTS idx_events_created_by_id ON events(created_by_id);
CREATE INDEX IF NOT EXISTS idx_events_facilitator_id ON events(facilitator_id);

-- event_registrations
CREATE INDEX IF NOT EXISTS idx_event_registrations_event_id ON event_registrations(event_id);
CREATE INDEX IF NOT EXISTS idx_event_registrations_user_id ON event_registrations(user_id);

-- =============================================================================
-- Indie Author Tables
-- =============================================================================

-- indie_authors
CREATE INDEX IF NOT EXISTS idx_indie_authors_user_id ON indie_authors(user_id);

-- indie_ebooks
CREATE INDEX IF NOT EXISTS idx_indie_ebooks_author_id ON indie_ebooks(author_id);
CREATE INDEX IF NOT EXISTS idx_indie_ebooks_submitted_by_id ON indie_ebooks(submitted_by_id);

-- indie_ebook_versions
CREATE INDEX IF NOT EXISTS idx_indie_ebook_versions_ebook_id ON indie_ebook_versions(ebook_id);
CREATE INDEX IF NOT EXISTS idx_indie_ebook_versions_uploaded_by_id ON indie_ebook_versions(uploaded_by_id);

-- indie_ebook_borrows
CREATE INDEX IF NOT EXISTS idx_indie_ebook_borrows_ebook_id ON indie_ebook_borrows(ebook_id);
CREATE INDEX IF NOT EXISTS idx_indie_ebook_borrows_patron_id ON indie_ebook_borrows(patron_id);

-- indie_ebook_waitlist
CREATE INDEX IF NOT EXISTS idx_indie_ebook_waitlist_ebook_id ON indie_ebook_waitlist(ebook_id);
CREATE INDEX IF NOT EXISTS idx_indie_ebook_waitlist_patron_id ON indie_ebook_waitlist(patron_id);

-- ebook_submission_reviews
CREATE INDEX IF NOT EXISTS idx_ebook_submission_reviews_ebook_id ON ebook_submission_reviews(ebook_id);
CREATE INDEX IF NOT EXISTS idx_ebook_submission_reviews_reviewer_id ON ebook_submission_reviews(reviewer_id);

-- =============================================================================
-- Knowledge Base Tables
-- =============================================================================

-- knowledge_entries
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_added_by_id ON knowledge_entries(added_by_id);
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_category_id ON knowledge_entries(category_id);

-- =============================================================================
-- Cohort Tables
-- =============================================================================

-- cohorts
CREATE INDEX IF NOT EXISTS idx_cohorts_created_by_id ON cohorts(created_by_id);

-- cohort_members
CREATE INDEX IF NOT EXISTS idx_cohort_members_cohort_id ON cohort_members(cohort_id);
CREATE INDEX IF NOT EXISTS idx_cohort_members_user_id ON cohort_members(user_id);

-- cohort_trainings
CREATE INDEX IF NOT EXISTS idx_cohort_trainings_cohort_id ON cohort_trainings(cohort_id);
CREATE INDEX IF NOT EXISTS idx_cohort_trainings_trainer_id ON cohort_trainings(trainer_id);

-- =============================================================================
-- Inventory Tables
-- =============================================================================

-- inventory_audits
CREATE INDEX IF NOT EXISTS idx_inventory_audits_initiated_by_id ON inventory_audits(initiated_by_id);
CREATE INDEX IF NOT EXISTS idx_inventory_audits_completed_by_id ON inventory_audits(completed_by_id);

-- item_lifecycle_events
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_item_copy_id ON item_lifecycle_events(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_performed_by_id ON item_lifecycle_events(performed_by_id);

-- condition_changes
CREATE INDEX IF NOT EXISTS idx_condition_changes_item_copy_id ON condition_changes(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_condition_changes_reported_by_id ON condition_changes(reported_by_id);

COMMIT;

-- =============================================================================
-- Run ANALYZE to update statistics
-- =============================================================================

ANALYZE agenda_items;
ANALYZE board_documents;
ANALYZE board_meetings;
ANALYZE board_minutes;
ANALYZE board_votes;
ANALYZE catalog_items;
ANALYZE checkouts;
ANALYZE holds;
ANALYZE item_copies;
ANALYZE fines;
ANALYZE events;
ANALYZE courses;
ANALYZE indie_ebooks;
ANALYZE knowledge_entries;

-- End of migration
