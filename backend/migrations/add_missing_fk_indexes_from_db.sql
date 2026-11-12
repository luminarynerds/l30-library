-- LSC Missing Foreign Key Indexes - Database-Driven Generation
-- Generated from actual littleschitt_library schema
-- Total missing FK indexes: 77
--
-- Safe to run multiple times (uses IF NOT EXISTS)

-- Table: agenda_items (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_agenda_items_created_by_id ON agenda_items(created_by_id);
CREATE INDEX IF NOT EXISTS idx_agenda_items_parent_item_id ON agenda_items(parent_item_id);

-- Table: ai_tools (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_ai_tools_created_by_id ON ai_tools(created_by_id);
CREATE INDEX IF NOT EXISTS idx_ai_tools_updated_by_id ON ai_tools(updated_by_id);

-- Table: announcements (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_announcements_created_by_id ON announcements(created_by_id);

-- Table: audit_scans (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_audit_scans_item_copy_id ON audit_scans(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_audit_scans_scanned_by_id ON audit_scans(scanned_by_id);

-- Table: board_documents (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_documents_created_by_id ON board_documents(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_documents_previous_version_id ON board_documents(previous_version_id);
CREATE INDEX IF NOT EXISTS idx_board_documents_published_by_id ON board_documents(published_by_id);

-- Table: board_meeting_briefs (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_meeting_briefs_created_by_id ON board_meeting_briefs(created_by_id);

-- Table: board_meetings (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_meetings_agenda_published_by_id ON board_meetings(agenda_published_by_id);
CREATE INDEX IF NOT EXISTS idx_board_meetings_created_by_id ON board_meetings(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_meetings_minutes_approved_by_id ON board_meetings(minutes_approved_by_id);

-- Table: board_minutes (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_minutes_approved_by_id ON board_minutes(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_board_minutes_created_by_id ON board_minutes(created_by_id);
CREATE INDEX IF NOT EXISTS idx_board_minutes_prepared_by_id ON board_minutes(prepared_by_id);

-- Table: board_votes (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_votes_closed_by_id ON board_votes(closed_by_id);
CREATE INDEX IF NOT EXISTS idx_board_votes_created_by_id ON board_votes(created_by_id);

-- Table: board_votes_cast (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_board_votes_cast_board_member_id ON board_votes_cast(board_member_id);

-- Table: cohort_members (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_cohort_members_cohort_id ON cohort_members(cohort_id);
CREATE INDEX IF NOT EXISTS idx_cohort_members_user_id ON cohort_members(user_id);

-- Table: cohort_trainings (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_cohort_trainings_cohort_id ON cohort_trainings(cohort_id);
CREATE INDEX IF NOT EXISTS idx_cohort_trainings_course_id ON cohort_trainings(course_id);

-- Table: cohorts (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_cohorts_created_by ON cohorts(created_by);

-- Table: condition_changes (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_condition_changes_reported_by_id ON condition_changes(reported_by_id);

-- Table: ebook_submission_reviews (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_ebook_submission_reviews_reviewer_id ON ebook_submission_reviews(reviewer_id);

-- Table: fine_policies (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_fine_policies_created_by_id ON fine_policies(created_by_id);

-- Table: fines (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_fines_waived_by_id ON fines(waived_by_id);

-- Table: indie_authors (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_indie_authors_verified_by_id ON indie_authors(verified_by_id);

-- Table: indie_ebooks (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_indie_ebooks_cataloged_by_id ON indie_ebooks(cataloged_by_id);
CREATE INDEX IF NOT EXISTS idx_indie_ebooks_staff_reviewer_id ON indie_ebooks(staff_reviewer_id);

-- Table: inventory_audits (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_inventory_audits_created_by_id ON inventory_audits(created_by_id);

-- Table: item_copies (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_item_copies_purchase_order_item_id ON item_copies(purchase_order_item_id);

-- Table: item_lifecycle_events (5 missing indexes)
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_performed_by_id ON item_lifecycle_events(performed_by_id);
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_related_audit_id ON item_lifecycle_events(related_audit_id);
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_related_checkout_id ON item_lifecycle_events(related_checkout_id);
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_related_po_id ON item_lifecycle_events(related_po_id);
CREATE INDEX IF NOT EXISTS idx_item_lifecycle_events_related_weeding_id ON item_lifecycle_events(related_weeding_id);

-- Table: knowledge_entries (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_knowledge_entries_added_by_id ON knowledge_entries(added_by_id);

-- Table: learning_paths (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_learning_paths_created_by_id ON learning_paths(created_by_id);

-- Table: meeting_action_items (5 missing indexes)
CREATE INDEX IF NOT EXISTS idx_meeting_action_items_agenda_item_id ON meeting_action_items(agenda_item_id);
CREATE INDEX IF NOT EXISTS idx_meeting_action_items_assigned_by_id ON meeting_action_items(assigned_by_id);
CREATE INDEX IF NOT EXISTS idx_meeting_action_items_assigned_to_id ON meeting_action_items(assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_meeting_action_items_board_update_meeting_id ON meeting_action_items(board_update_meeting_id);
CREATE INDEX IF NOT EXISTS idx_meeting_action_items_created_by_id ON meeting_action_items(created_by_id);

-- Table: meeting_attendance (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_meeting_attendance_created_by_id ON meeting_attendance(created_by_id);
CREATE INDEX IF NOT EXISTS idx_meeting_attendance_excused_by_id ON meeting_attendance(excused_by_id);

-- Table: organization_features (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_organization_features_updated_by_id ON organization_features(updated_by_id);

-- Table: refresh_tokens (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id ON refresh_tokens(user_id);

-- Table: role_permissions (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_role_permissions_permission_id ON role_permissions(permission_id);

-- Table: strategic_attachments (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_attachments_goal_id ON strategic_attachments(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_attachments_milestone_id ON strategic_attachments(milestone_id);
CREATE INDEX IF NOT EXISTS idx_strategic_attachments_uploaded_by_id ON strategic_attachments(uploaded_by_id);

-- Table: strategic_audit_logs (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_audit_logs_user_id ON strategic_audit_logs(user_id);

-- Table: strategic_comments (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_comments_goal_id ON strategic_comments(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_comments_parent_id ON strategic_comments(parent_id);
CREATE INDEX IF NOT EXISTS idx_strategic_comments_user_id ON strategic_comments(user_id);

-- Table: strategic_goals (4 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_goals_approved_by_id ON strategic_goals(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_goals_owner_id ON strategic_goals(owner_id);
CREATE INDEX IF NOT EXISTS idx_strategic_goals_parent_goal_id ON strategic_goals(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_goals_plan_id ON strategic_goals(plan_id);

-- Table: strategic_metric_history (2 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_metric_history_metric_id ON strategic_metric_history(metric_id);
CREATE INDEX IF NOT EXISTS idx_strategic_metric_history_recorded_by_id ON strategic_metric_history(recorded_by_id);

-- Table: strategic_metrics (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_metrics_goal_id ON strategic_metrics(goal_id);

-- Table: strategic_milestones (4 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_milestones_approved_by_id ON strategic_milestones(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_milestones_created_by_id ON strategic_milestones(created_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_milestones_goal_id ON strategic_milestones(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_milestones_plan_id ON strategic_milestones(plan_id);

-- Table: strategic_notifications (3 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_notifications_related_goal_id ON strategic_notifications(related_goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_notifications_related_milestone_id ON strategic_notifications(related_milestone_id);
CREATE INDEX IF NOT EXISTS idx_strategic_notifications_user_id ON strategic_notifications(user_id);

-- Table: strategic_plans (1 missing indexes)
CREATE INDEX IF NOT EXISTS idx_strategic_plans_created_by_id ON strategic_plans(created_by_id);

-- Table: weeding_candidates (4 missing indexes)
CREATE INDEX IF NOT EXISTS idx_weeding_candidates_approved_by_id ON weeding_candidates(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_weeding_candidates_created_by_id ON weeding_candidates(created_by_id);
CREATE INDEX IF NOT EXISTS idx_weeding_candidates_rejected_by_id ON weeding_candidates(rejected_by_id);
CREATE INDEX IF NOT EXISTS idx_weeding_candidates_reviewed_by_id ON weeding_candidates(reviewed_by_id);

-- Update table statistics
ANALYZE agenda_items;
ANALYZE ai_tools;
ANALYZE announcements;
ANALYZE audit_scans;
ANALYZE board_documents;
ANALYZE board_meeting_briefs;
ANALYZE board_meetings;
ANALYZE board_minutes;
ANALYZE board_votes;
ANALYZE board_votes_cast;
ANALYZE cohort_members;
ANALYZE cohort_trainings;
ANALYZE cohorts;
ANALYZE condition_changes;
ANALYZE ebook_submission_reviews;
ANALYZE fine_policies;
ANALYZE fines;
ANALYZE indie_authors;
ANALYZE indie_ebooks;
ANALYZE inventory_audits;
ANALYZE item_copies;
ANALYZE item_lifecycle_events;
ANALYZE knowledge_entries;
ANALYZE learning_paths;
ANALYZE meeting_action_items;
ANALYZE meeting_attendance;
ANALYZE organization_features;
ANALYZE refresh_tokens;
ANALYZE role_permissions;
ANALYZE strategic_attachments;
ANALYZE strategic_audit_logs;
ANALYZE strategic_comments;
ANALYZE strategic_goals;
ANALYZE strategic_metric_history;
ANALYZE strategic_metrics;
ANALYZE strategic_milestones;
ANALYZE strategic_notifications;
ANALYZE strategic_plans;
ANALYZE weeding_candidates;