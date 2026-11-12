/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Single source of truth for the Organization Features admin toggle UI.
 * Backend enforcement lives in backend/app/api/v1/feature_guards.py.
 */

export interface FeatureToggleConfig {
  key: string
  description: string
}

export interface FeatureGroup {
  id: string
  title: string
  toggles: readonly FeatureToggleConfig[]
}

export const FEATURE_GROUPS: readonly FeatureGroup[] = [
  {
    id: 'patron-experience',
    title: 'Patron Experience',
    toggles: [
      { key: 'patron_portal_enabled', description: 'Self-service patron account portal' },
      { key: 'self_checkout_enabled', description: 'Patron self-checkout kiosk support' },
      { key: 'parent_onboarding_enabled', description: 'Wizard for parents to set up child accounts' },
      { key: 'faq_chatbot_enabled', description: 'Patron-facing knowledge base chat' },
      { key: 'ai_tools_enabled', description: 'AI tools hub and patron AI chat' },
    ],
  },
  {
    id: 'reading-engagement',
    title: 'Reading & Engagement',
    toggles: [
      { key: 'reading_shelf_enabled', description: 'Reading status, progress, and activity tracking' },
      { key: 'reading_goals_enabled', description: 'Daily reading-time goals and streaks' },
      { key: 'reading_programs_enabled', description: 'Summer reading, challenges, certificates' },
      { key: 'shelf_data_export_enabled', description: 'Patrons can export their reading history' },
      { key: 'gamification_enabled', description: 'Badges, points, and achievements' },
      { key: 'book_clubs_enabled', description: 'Book club management and discussion' },
      { key: 'book_club_history_enabled', description: 'Soft-archive book club meetings + Postgres FTS search across past discussions' },
      { key: 'ama_enabled', description: 'Author AMA sessions and Q&A' },
    ],
  },
  {
    id: 'discovery-collections',
    title: 'Discovery & Collections',
    toggles: [
      { key: 'collection_management_enabled', description: 'Curation, weeding, collection-metadata tools' },
      { key: 'indie_platform_enabled', description: 'Indie author catalog and MetisLib integration' },
      { key: 'free_ebooks_enabled', description: 'Project Gutenberg and other public-domain ebooks' },
      { key: 'streaming_enabled', description: 'Streaming video and audio collection' },
      { key: 'digital_access_enabled', description: 'Database subscriptions and digital-resources directory' },
      { key: 'serials_enabled', description: 'Magazines, newspapers, and serials management' },
    ],
  },
  {
    id: 'events-spaces',
    title: 'Events & Spaces',
    toggles: [
      { key: 'events_enabled', description: 'Events calendar, registration, iCal export' },
      { key: 'meeting_rooms_enabled', description: 'Room booking and management' },
      { key: 'makerspace_enabled', description: 'Equipment catalog, certifications, workshops' },
      { key: 'storytime_enabled', description: 'Storytime planning and attendance tracking' },
      { key: 'printing_enabled', description: 'Public-printing fees, queue, and settings' },
      { key: 'signage_enabled', description: 'Digital signage management' },
    ],
  },
  {
    id: 'services-outreach',
    title: 'Services & Outreach',
    toggles: [
      { key: 'home_delivery_enabled', description: 'Home delivery enrollment and routing' },
      { key: 'ill_enabled', description: 'ILL borrowing and lending' },
      { key: 'outreach_enabled', description: 'Bookmobile, partnerships, outreach reports' },
      { key: 'volunteers_enabled', description: 'Volunteer scheduling and tracking' },
      { key: 'marketing_enabled', description: 'Email and SMS campaigns, event marketing' },
      { key: 'for_teachers_enabled', description: 'Teacher portal and school reading partnerships' },
      { key: 'learning_platform_enabled', description: 'Courses, lessons, AI literacy labs' },
      { key: 'legal_services_enabled', description: 'Calculators, court directory, document wizard' },
      { key: 'genealogy_enabled', description: 'Family tree, timeline, genealogy workspace' },
      { key: 'tech_services_enabled', description: 'Tech help guides and tech-services portal' },
      { key: 'literacy_programs_enabled', description: 'Literacy program management' },
    ],
  },
  {
    id: 'operations',
    title: 'Operations',
    toggles: [
      { key: 'acquisition_enabled', description: 'Purchase orders, EDI, vendors, selection lists' },
      { key: 'processing_queue_enabled', description: 'New-item processing queue' },
      { key: 'staff_scheduling_enabled', description: 'Shift scheduling, swaps, PTO' },
      { key: 'staff_wellness_enabled', description: 'Focus time and staff wellness tools' },
      { key: 'sip2_rfid_enabled', description: 'SIP2 endpoint and RFID hardware integration' },
      { key: 'emergency_services_enabled', description: 'Panic alert, threat response, safety tools' },
    ],
  },
  {
    id: 'governance-reporting',
    title: 'Governance & Reporting',
    toggles: [
      { key: 'board_features_enabled', description: 'Board meeting tools, motions, voting' },
      { key: 'training_modules_enabled', description: 'Staff training and certification tracking' },
      { key: 'compliance_enabled', description: 'CIPA, public-records, state-compliance tools' },
      { key: 'banned_books_tracking_enabled', description: 'Track book challenges and bans' },
      { key: 'financial_reports_enabled', description: 'Fine collection, payment, financial reports' },
      { key: 'community_outcomes_enabled', description: 'Community outcomes dashboard and reporting' },
      { key: 'community_features_enabled', description: 'Community resources directory' },
      { key: 'patron_engagement_enabled', description: 'Cohorts, segmentation, targeted messaging' },
      { key: 'strategic_planning_enabled', description: 'Strategic goals, milestones, plan analytics' },
    ],
  },
  {
    id: 'communications',
    title: 'Communications',
    toggles: [
      { key: 'email_notifications_enabled', description: 'Automated email notices to patrons' },
      { key: 'notifications_enabled', description: 'Banners, announcements, and system notices' },
    ],
  },
  {
    id: 'advanced',
    title: 'Advanced',
    toggles: [
      { key: 'beta_features_enabled', description: 'Opt in to features still in beta testing' },
    ],
  },
]

export const ALL_FEATURE_KEYS: readonly string[] = FEATURE_GROUPS.flatMap((g) => g.toggles.map((t) => t.key))
