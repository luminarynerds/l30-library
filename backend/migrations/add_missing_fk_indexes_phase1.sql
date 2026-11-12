-- LSC Missing Foreign Key Indexes - Phase 1 (Critical Tables)
-- Generated: 2026-02-11
-- Adds indexes for top 10 most critical tables by missing index count
--
-- Execution time estimate: 5-15 minutes depending on table sizes
--
-- IMPORTANT:
-- - Run this during low-traffic period
-- - Consider using CONCURRENTLY for large tables (no locks)
-- - Run ANALYZE after creating indexes
--
-- Tables covered in Phase 1:
-- 1. lost_item_records (28 indexes)
-- 3. offline_modes (28 indexes)
-- 4. makerspace_resources (27 indexes)
-- 5. staff_onboarding (26 indexes)
-- 6. outreach_partners (26 indexes)
-- 7. signage_display (25 indexes)
-- 8. strategic_plans (22 indexes)
-- 9. shared_events (22 indexes)
-- 10. library_systems (22 indexes)

BEGIN;

-- =============================================================================
-- Table: lost_item_records (28 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_lost_item_records_approved_by_id ON lost_item_records(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_item_copy_id ON lost_item_records(item_copy_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_patron_id ON lost_item_records(patron_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_processed_by_id ON lost_item_records(processed_by_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_reported_by_id ON lost_item_records(reported_by_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_resolved_by_id ON lost_item_records(resolved_by_id);
CREATE INDEX IF NOT EXISTS idx_lost_item_records_user_id ON lost_item_records(user_id);

-- =============================================================================
-- Table: offline_modes (28 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_offline_modes_activated_by_id ON offline_modes(activated_by_id);
CREATE INDEX IF NOT EXISTS idx_offline_modes_approved_by_id ON offline_modes(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_offline_modes_deactivated_by_id ON offline_modes(deactivated_by_id);
CREATE INDEX IF NOT EXISTS idx_offline_modes_initiated_by_id ON offline_modes(initiated_by_id);
CREATE INDEX IF NOT EXISTS idx_offline_modes_user_id ON offline_modes(user_id);

-- =============================================================================
-- Table: makerspace_resources (27 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_makerspace_resources_approved_by_id ON makerspace_resources(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_category_id ON makerspace_resources(category_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_created_by_id ON makerspace_resources(created_by_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_parent_project_id ON makerspace_resources(parent_project_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_project_id ON makerspace_resources(project_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_reservation_id ON makerspace_resources(reservation_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_resource_id ON makerspace_resources(resource_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_reviewed_by_id ON makerspace_resources(reviewed_by_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_user_id ON makerspace_resources(user_id);
CREATE INDEX IF NOT EXISTS idx_makerspace_resources_waiver_id ON makerspace_resources(waiver_id);

-- =============================================================================
-- Table: staff_onboarding (26 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_staff_onboarding_acknowledged_by_id ON staff_onboarding(acknowledged_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_assigned_to_id ON staff_onboarding(assigned_to_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_buddy_mentor_id ON staff_onboarding(buddy_mentor_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_completed_by_id ON staff_onboarding(completed_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_created_by_id ON staff_onboarding(created_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_facilitator_id ON staff_onboarding(facilitator_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_onboarding_id ON staff_onboarding(onboarding_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_policy_id ON staff_onboarding(policy_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_provided_by_id ON staff_onboarding(provided_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_provisioned_by_id ON staff_onboarding(provisioned_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_published_by_id ON staff_onboarding(published_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_requested_by_id ON staff_onboarding(requested_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_revoked_by_id ON staff_onboarding(revoked_by_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_scheduled_with_id ON staff_onboarding(scheduled_with_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_supersedes_policy_id ON staff_onboarding(supersedes_policy_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_system_access_id ON staff_onboarding(system_access_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_training_module_id ON staff_onboarding(training_module_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_user_id ON staff_onboarding(user_id);
CREATE INDEX IF NOT EXISTS idx_staff_onboarding_verified_by_id ON staff_onboarding(verified_by_id);

-- =============================================================================
-- Table: outreach_partners (26 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_outreach_partners_approved_by_id ON outreach_partners(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_created_by_id ON outreach_partners(created_by_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_event_id ON outreach_partners(event_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_partner_id ON outreach_partners(partner_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_primary_contact_id ON outreach_partners(primary_contact_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_program_id ON outreach_partners(program_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_updated_by_id ON outreach_partners(updated_by_id);
CREATE INDEX IF NOT EXISTS idx_outreach_partners_visit_id ON outreach_partners(visit_id);

-- =============================================================================
-- Table: signage_display (25 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_signage_display_content_id ON signage_display(content_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_created_by_user_id ON signage_display(created_by_user_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_default_content_id ON signage_display(default_content_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_display_id ON signage_display(display_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_display_template_id ON signage_display(display_template_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_event_id ON signage_display(event_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_reviewed_by_user_id ON signage_display(reviewed_by_user_id);
CREATE INDEX IF NOT EXISTS idx_signage_display_template_id ON signage_display(template_id);

-- =============================================================================
-- Table: strategic_plans (22 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_strategic_plans_approved_by_id ON strategic_plans(approved_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_created_by_id ON strategic_plans(created_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_goal_id ON strategic_plans(goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_metric_id ON strategic_plans(metric_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_milestone_id ON strategic_plans(milestone_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_owner_id ON strategic_plans(owner_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_parent_goal_id ON strategic_plans(parent_goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_parent_id ON strategic_plans(parent_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_plan_id ON strategic_plans(plan_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_recorded_by_id ON strategic_plans(recorded_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_related_goal_id ON strategic_plans(related_goal_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_related_milestone_id ON strategic_plans(related_milestone_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_uploaded_by_id ON strategic_plans(uploaded_by_id);
CREATE INDEX IF NOT EXISTS idx_strategic_plans_user_id ON strategic_plans(user_id);

-- =============================================================================
-- Table: shared_events (22 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_shared_events_backup_coordinator_id ON shared_events(backup_coordinator_id);
CREATE INDEX IF NOT EXISTS idx_shared_events_event_id ON shared_events(event_id);
CREATE INDEX IF NOT EXISTS idx_shared_events_lead_organizer_id ON shared_events(lead_organizer_id);
CREATE INDEX IF NOT EXISTS idx_shared_events_originating_library_id ON shared_events(originating_library_id);
CREATE INDEX IF NOT EXISTS idx_shared_events_parent_event_id ON shared_events(parent_event_id);
CREATE INDEX IF NOT EXISTS idx_shared_events_participant_library_id ON shared_events(participant_library_id);

-- =============================================================================
-- Table: library_systems (22 missing indexes)
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_library_systems_created_by_id ON library_systems(created_by_id);
CREATE INDEX IF NOT EXISTS idx_library_systems_parent_system_id ON library_systems(parent_system_id);
CREATE INDEX IF NOT EXISTS idx_library_systems_system_id ON library_systems(system_id);
CREATE INDEX IF NOT EXISTS idx_library_systems_updated_by_id ON library_systems(updated_by_id);

COMMIT;

-- =============================================================================
-- Post-Index Creation Tasks
-- =============================================================================

-- Run ANALYZE to update statistics
ANALYZE lost_item_records;
ANALYZE offline_modes;
ANALYZE makerspace_resources;
ANALYZE staff_onboarding;
ANALYZE outreach_partners;
ANALYZE signage_display;
ANALYZE strategic_plans;
ANALYZE shared_events;
ANALYZE library_systems;

-- End of Phase 1
