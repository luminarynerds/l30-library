/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import React, { useState } from 'react';
import { useOrganizationFeatures, type OrganizationFeatures } from '@/contexts/OrganizationFeaturesContext';
import api from '@/api/api';
import { AlertCircle, CheckCircle, Loader, ToggleLeft, ToggleRight, RefreshCw } from 'lucide-react';
import { StaffLayout } from './StaffLayout'
import { SUCCESS_FEEDBACK_DURATION_MS } from '@/constants/timeouts';
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'

export const StaffFeatureFlagsPage: React.FC = () => {
  const { t } = useTranslation()
  const { features, refetch, loading: featuresLoading } = useOrganizationFeatures();
  const [updating, setUpdating] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const featureGroups = [
    {
      title: 'Sidebar Modules',
      features: [
        {
          key: 'front_desk_enabled' as const,
          label: 'Front Desk',
          description: 'Public-facing entry (get-a-card CTA, branches/hours, mobile menu). UI-only — staff circulation endpoints stay live.',
        },
        {
          key: 'collection_management_enabled' as const,
          label: 'Collection Management',
          description: 'Cataloging, acquisitions, inventory, shelf reading, weeding',
        },
        {
          key: 'community_features_enabled' as const,
          label: 'Library Programs & Services',
          description: 'Events, reading programs, ILL, makerspace, rooms, training',
        },
        {
          key: 'board_features_enabled' as const,
          label: 'Board & Governance',
          description: 'Board members, meetings, motions, committees, treasurer',
        },
        {
          key: 'marketing_enabled' as const,
          label: 'Marketing & Outreach',
          description: 'Campaigns, outreach, social sharing, analytics',
        },
      ],
    },
    {
      title: 'Patron Services',
      features: [
        {
          key: 'patron_portal_enabled' as const,
          label: 'Patron Portal',
          description: t('components.staff.staffFeatureFlags.publicFacingPortalAndServices'),
        },
        {
          key: 'patron_engagement_enabled' as const,
          label: 'Patron Engagement',
          description: 'Patron messaging, badges, reactions, and engagement tracking',
        },
        {
          key: 'parent_onboarding_enabled' as const,
          label: 'Parent Onboarding',
          description: 'Family-services onboarding flow: connection groups, childcare check-in, home visits, weekly export',
        },
        {
          key: 'self_checkout_enabled' as const,
          label: 'Self-Checkout',
          description: t('components.staff.staffFeatureFlags.patronSelfCheckoutFunctionalityAt'),
        },
        {
          key: 'for_teachers_enabled' as const,
          label: 'For Teachers',
          description: 'Patron-side teacher portal: reading dashboard, reading lists, PD, consultations, family challenges, library visits',
        },
        {
          key: 'customer_display_enabled' as const,
          label: 'Customer Display',
          description: 'Patron-facing second-monitor display mirroring desk activity. Default off — opt in if your desk has a second monitor.',
        },
        {
          key: 'saved_searches_enabled' as const,
          label: 'Saved Searches & Alerts',
          description: 'Patron saved catalog searches with new-arrival alerts. Default off — opt in after notifier delivery is verified.',
        },
        {
          key: 'faq_chatbot_enabled' as const,
          label: 'FAQ Chatbot',
          description: 'Patron-facing FAQ chatbot widget',
        },
      ],
    },
    {
      title: 'Circulation Desk',
      features: [
        {
          key: 'circulation_print_slip_enabled' as const,
          label: 'Checkout Slip',
          description: 'Printable + emailable receipt toolbar after a staff-desk checkout.',
        },
        {
          key: 'circulation_hold_trap_card_enabled' as const,
          label: 'Hold Trap Card',
          description: 'Surface hold-trap card on check-in when the returned item fills the next active hold.',
        },
        {
          key: 'sip2_rfid_enabled' as const,
          label: 'SIP2 / RFID',
          description: 'SIP2 + RFID self-service hardware integration',
        },
      ],
    },
    {
      title: 'Programs & Events',
      features: [
        {
          key: 'events_enabled' as const,
          label: 'Events',
          description: 'Library events calendar, registration, attendance',
        },
        {
          key: 'storytime_enabled' as const,
          label: 'Storytime',
          description: 'Storytime sessions, schedules, attendance tracking',
        },
        {
          key: 'literacy_programs_enabled' as const,
          label: 'Literacy Programs',
          description: 'Adult literacy, tutoring, ESL, basic-skills programs',
        },
        {
          key: 'gamification_enabled' as const,
          label: 'Gamification',
          description: t('components.staff.staffFeatureFlags.badgesPointsAchievementsAndLeaderboards2'),
        },
        {
          key: 'banned_books_tracking_enabled' as const,
          label: 'Banned Books Tracking',
          description: t('components.staff.staffFeatureFlags.trackingOfFrequentlyChallengedAnd'),
        },
      ],
    },
    {
      title: 'Reading Programs',
      features: [
        {
          key: 'reading_programs_enabled' as const,
          label: 'Reading Programs',
          description: t('components.staff.staffFeatureFlags.patronReadingChallengesAndProgress'),
        },
        {
          key: 'reading_programs_booklist_enabled' as const,
          label: 'Reading Programs: Booklist',
          description: 'Recommended reads (curated booklist) tab on program detail',
        },
        {
          key: 'reading_programs_paper_log_enabled' as const,
          label: 'Reading Programs: Paper Log',
          description: 'Printable paper reading log with kiosk/desk claim-code redemption',
        },
      ],
    },
    {
      title: 'Book Clubs',
      features: [
        {
          key: 'book_clubs_enabled' as const,
          label: 'Book Clubs',
          description: 'Book club groups, schedules, current reads',
        },
        {
          key: 'book_club_history_enabled' as const,
          label: 'Book Club Discussion Archive',
          description: 'Postgres FTS search across past book-club discussions. Default off — opt in while feature bakes in.',
        },
        {
          key: 'book_club_waitlist_enabled' as const,
          label: 'Book Club Waitlist',
          description: 'FIFO waitlist + capacity signals on book clubs. Default off — opt in while feature bakes in.',
        },
      ],
    },
    {
      title: 'Learning & Training',
      features: [
        {
          key: 'learning_platform_enabled' as const,
          label: 'Learning Platform',
          description: 'Learning paths, courses, and sessions',
        },
        {
          key: 'training_modules_enabled' as const,
          label: 'Training Modules',
          description: t('components.staff.staffFeatureFlags.onlineCoursesAndTrainingContent'),
        },
        {
          key: 'cohort_enabled' as const,
          label: 'Learning Cohorts',
          description: 'Learning-path cohorts: opt-in pair-up + shared discussion wall. Default off — opt in while feature bakes in.',
        },
      ],
    },
    {
      title: 'Discovery & Shelves',
      features: [
        {
          key: 'reading_shelf_enabled' as const,
          label: 'Reading Shelf',
          description: 'Patron personal reading shelf (currently/finished/want-to-read)',
        },
        {
          key: 'reading_goals_enabled' as const,
          label: 'Reading Goals',
          description: 'Patron annual reading goals + progress tracking. Default off.',
        },
        {
          key: 'shelf_data_export_enabled' as const,
          label: 'Shelf Data Export',
          description: 'Patron data export for personal reading shelf',
        },
        {
          key: 'aggregate_trending_enabled' as const,
          label: 'Aggregate Trending Rails',
          description: 'Trending rails on /discover ("what neighbors are reading"). Aggregate-only with k-anon floor + per-patron opt-out.',
        },
      ],
    },
    {
      title: 'Spaces & Equipment',
      features: [
        {
          key: 'meeting_rooms_enabled' as const,
          label: 'Meeting Rooms',
          description: 'Room reservations, scheduling, equipment',
        },
        {
          key: 'makerspace_enabled' as const,
          label: 'Makerspace',
          description: 'Makerspace equipment booking, certifications, projects',
        },
        {
          key: 'printing_enabled' as const,
          label: 'Printing',
          description: 'Patron print management + print-release stations',
        },
        {
          key: 'signage_enabled' as const,
          label: 'Digital Signage',
          description: 'In-library digital signage / display boards',
        },
      ],
    },
    {
      title: 'Outreach & Community',
      features: [
        {
          key: 'outreach_enabled' as const,
          label: 'Outreach',
          description: 'External outreach campaigns + community partnerships',
        },
        {
          key: 'volunteers_enabled' as const,
          label: 'Volunteers',
          description: 'Volunteer roster, scheduling, hour tracking',
        },
        {
          key: 'family_card_enabled' as const,
          label: 'Family card',
          description: 'Family / household linked accounts. Disable for libraries that do not run a family-card program.',
        },
        {
          key: 'ill_enabled' as const,
          label: 'Interlibrary Loan',
          description: 'ILL requests, lending, and tracking',
        },
        {
          key: 'home_delivery_enabled' as const,
          label: 'Home Delivery',
          description: 'Books-by-mail / homebound delivery service',
        },
      ],
    },
    {
      title: 'Collection',
      features: [
        {
          key: 'acquisition_enabled' as const,
          label: 'Acquisitions',
          description: 'Acquisitions workflow: vendor orders, receiving, invoicing',
        },
        {
          key: 'serials_enabled' as const,
          label: 'Serials',
          description: 'Periodicals + serials check-in and issue tracking',
        },
        {
          key: 'migration_enabled' as const,
          label: 'Catalog Migration',
          description: 'Catalog import / data migration tooling',
        },
        {
          key: 'free_ebooks_enabled' as const,
          label: 'Free Ebooks',
          description: 'Patron-facing free ebook collections (public domain, open access)',
        },
        {
          key: 'indie_platform_enabled' as const,
          label: 'Indie Platform',
          description: 'Independent author / indie catalog integration',
        },
        {
          key: 'digital_access_enabled' as const,
          label: 'Digital Access',
          description: 'Patron digital resources + database access pages',
        },
        {
          key: 'streaming_enabled' as const,
          label: 'Streaming',
          description: 'Patron streaming media (video / audio) access',
        },
      ],
    },
    {
      title: 'Specialty Services',
      features: [
        {
          key: 'genealogy_enabled' as const,
          label: 'Genealogy',
          description: 'Genealogy collection, research tools, family-history programs',
        },
        {
          key: 'legal_services_enabled' as const,
          label: 'Legal Services',
          description: 'Legal-aid clinics, law-enforcement liaison, court resources',
        },
        {
          key: 'tech_services_enabled' as const,
          label: 'Tech Services',
          description: 'Patron tech help, device clinics, digital-literacy support',
        },
        {
          key: 'emergency_services_enabled' as const,
          label: 'Emergency Services',
          description: 'Cooling/warming centers, disaster response, emergency resources',
        },
        {
          key: 'ai_tools_enabled' as const,
          label: 'AI Tools',
          description: 'Staff- and patron-facing AI assistants and tooling',
        },
        {
          key: 'ama_enabled' as const,
          label: 'Ask-Me-Anything',
          description: 'Staff Ask-Me-Anything Q&A widget. Default off.',
        },
      ],
    },
    {
      title: 'Communications',
      features: [
        {
          key: 'email_notifications_enabled' as const,
          label: 'Email Notifications',
          description: t('components.staff.staffFeatureFlags.automatedPatronNotificationsForHolds'),
        },
        {
          key: 'notifications_enabled' as const,
          label: 'Notifications (general)',
          description: 'In-app notifications center + push delivery (separate from email)',
        },
      ],
    },
    {
      title: 'Governance & Reports',
      features: [
        {
          key: 'compliance_enabled' as const,
          label: 'Compliance',
          description: 'Compliance tracking, policies, regulatory reporting',
        },
        {
          key: 'impact_measurement_enabled' as const,
          label: 'Impact Measurement',
          description: 'Phase-1 governance scaffolding for impact measurement. Default off — opt-in per library.',
        },
        {
          key: 'strategic_planning_enabled' as const,
          label: 'Strategic Planning',
          description: 'Strategic plans, goals, KPI tracking',
        },
        {
          key: 'community_outcomes_enabled' as const,
          label: 'Community Outcomes',
          description: 'Community-outcomes dashboards and reporting',
        },
        {
          key: 'financial_reports_enabled' as const,
          label: 'Financial Reports',
          description: 'Financial reporting + treasurer dashboards',
        },
      ],
    },
    {
      title: 'Operations',
      features: [
        {
          key: 'staff_scheduling_enabled' as const,
          label: 'Staff Scheduling',
          description: 'Staff schedules, shift swaps, time-off requests',
        },
        {
          key: 'staff_wellness_enabled' as const,
          label: 'Staff Wellness',
          description: 'Staff wellness check-ins, resources, and burnout signals',
        },
        {
          key: 'processing_queue_enabled' as const,
          label: 'Processing Queue',
          description: 'Item-processing queue (catalog-to-shelf workflow)',
        },
        {
          key: 'beta_features_enabled' as const,
          label: 'Beta Features',
          description: 'Enable early-access / beta features. Default off.',
        },
        {
          key: 'home_visit_safety_enabled' as const,
          label: 'Home-Visit Lone-Worker Check-In',
          description: 'Staff safe-arrival / safe-departure check-in on home visits, with overdue-checkout alerting to a buddy + supervisors. Default off — opt in once the supervisor notification path is in place.',
        },
        {
          key: 'home_visit_day_plan_enabled' as const,
          label: 'Home-Visit Day Plan (Map + Access Notes)',
          description: 'Map-aware "Today\'s route" view for staff home visitors -- ordered stops, geocoded pins, drive/walk ETAs, per-patron accessibility notes (steps, dog, language, parking), manual sort, and a print-friendly mode. Geocoding uses the public Nominatim instance; confirm volume is low-volume before enabling. Default off.',
        },
      ],
    },
  ];

  const handleToggleFeature = async (featureKey: keyof OrganizationFeatures) => {
    if (!features) return;

    const currentValue = features[featureKey];
    if (typeof currentValue !== 'boolean') return;

    setUpdating(featureKey);
    setError(null);
    setSuccess(null);

    try {
      await api.patch(`${API_BASE}/organization-features`, {
        [featureKey]: !currentValue,
      });

      const featureName = featureKey
        .replace(/_enabled$/, '')
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase());

      setSuccess(`${featureName} ${!currentValue ? 'enabled' : 'disabled'} successfully`);
      await refetch();

      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(null), SUCCESS_FEEDBACK_DURATION_MS);
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : 'Failed to update feature flag';
      setError(errorMessage);
      if (import.meta.env.DEV) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      }
    } finally {
      setUpdating(null);
    }
  };

  const handleRefresh = async () => {
    setIsRefreshing(true);
    try {
      await refetch();
      setSuccess('Feature flags refreshed successfully');
      setTimeout(() => setSuccess(null), SUCCESS_FEEDBACK_DURATION_MS);
    } catch (err: unknown) {
      setError(
        err instanceof Error ? err.message : 'Failed to refresh feature flags'
      );
    } finally {
      setIsRefreshing(false);
    }
  };

  if (featuresLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="flex flex-col items-center gap-4">
          <Loader className="w-8 h-8 text-lsc-rose motion-safe:animate-spin" />
          <p className="text-lsc-dark dark:text-lsc-cream">Loading feature flags...</p>
        </div>
      </div>
    );
  }

  return (
    <StaffLayout title="Feature Flags">
      <div className="min-h-screen bg-lsc-cream dark:bg-earth-900 p-4 sm:p-6 lg:p-8">
        <div className="max-w-6xl mx-auto space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Feature Flags
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Manage organization-wide feature settings
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-2 px-3 py-2 rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white/50 dark:bg-earth-800/30 hover:bg-lsc-white/70 dark:hover:bg-earth-800/50 text-lsc-dark dark:text-lsc-cream transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'motion-safe:animate-spin' : ''}`} />
            Refresh
          </button>
        </div>

        {/* Alert Messages */}
        {error && (
          <div
            className="flex items-start gap-3 p-4 bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-700 rounded-lg"
            role="alert"
          >
            <AlertCircle className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h2 className="font-serif font-semibold text-status-danger-800 dark:text-status-danger-200">Error</h2>
              <p className="text-sm text-status-danger-700 dark:text-status-danger-300 mt-1">{error}</p>
            </div>
          </div>
        )}

        {success && (
          <div
            className="flex items-start gap-3 p-4 bg-status-success-50 dark:bg-status-success-900/20 border border-status-success-200 dark:border-status-success-700 rounded-lg"
            role="status"
          >
            <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400 flex-shrink-0 mt-0.5" />
            <p className="text-sm text-status-success-700 dark:text-status-success-300">{success}</p>
          </div>
        )}

        {/* Feature Groups */}
        <div className="space-y-6">
          {featureGroups.map((group) => (
            <div key={group.title} className="border border-lsc-border dark:border-earth-700 rounded-lg p-6">
              <div className="mb-4">
                <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
                  {group.title}
                </h2>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{group.features.length} features</p>
              </div>
              <div className="space-y-4">
                {group.features.map(({ key, label, description }) => {
                  const isEnabled = features?.[key] === true;
                  const isUpdating = updating === key;

                  return (
                    <div
                      key={key}
                      className="flex items-center justify-between p-4 rounded-lg border border-lsc-border/50 dark:border-earth-700/50 hover:border-lsc-border dark:hover:border-earth-700 bg-lsc-white/50 dark:bg-earth-800/30 transition-colors"
                    >
                      <div className="flex-1">
                        <h3 className="font-serif font-semibold text-lsc-dark dark:text-lsc-cream">
                          {label}
                        </h3>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                          {description}
                        </p>
                      </div>

                      {/* Toggle Button */}
                      <button
                        onClick={() => handleToggleFeature(key)}
                        disabled={isUpdating}
                        aria-label={`Toggle ${label}`}
                        aria-checked={isEnabled}
                        role="switch"
                        className={`relative ml-4 inline-flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900 ${
                          isEnabled
                            ? 'bg-lsc-rose/15 text-lsc-rose hover:bg-lsc-rose/25'
                            : 'bg-lsc-dark/10 text-lsc-dark/70 dark:bg-lsc-cream/10 dark:text-lsc-cream/70 hover:bg-lsc-dark/15 dark:hover:bg-lsc-cream/15'
                        } ${isUpdating ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'}`}
                      >
                        {isUpdating ? (
                          <>
                            <Loader className="w-4 h-4 motion-safe:animate-spin" />
                            <span className="text-sm">Updating...</span>
                          </>
                        ) : isEnabled ? (
                          <>
                            <ToggleRight className="w-4 h-4" />
                            <span className="text-sm">Enabled</span>
                          </>
                        ) : (
                          <>
                            <ToggleLeft className="w-4 h-4" />
                            <span className="text-sm">Disabled</span>
                          </>
                        )}
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>

        {/* Configuration Info Card */}
        <div className="border border-lsc-border dark:border-earth-700 bg-lsc-cream/50 dark:bg-earth-800/50 rounded-lg p-6">
          <div className="mb-4">
            <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
              Configuration Values
            </h2>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{t('components.staff.staffFeatureFlags.systemWideLimitsAndDefaults')}</p>
          </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="p-4 bg-lsc-white/50 dark:bg-earth-800/30 rounded-lg border border-lsc-border/50 dark:border-earth-700/50">
                <p className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Max Holds per Patron
                </p>
                <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-2">
                  {features?.max_holds_per_patron ?? 'N/A'}
                </p>
              </div>
              <div className="p-4 bg-lsc-white/50 dark:bg-earth-800/30 rounded-lg border border-lsc-border/50 dark:border-earth-700/50">
                <p className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Max Checkouts per Patron
                </p>
                <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-2">
                  {features?.max_checkouts_per_patron ?? 'N/A'}
                </p>
              </div>
              <div className="p-4 bg-lsc-white/50 dark:bg-earth-800/30 rounded-lg border border-lsc-border/50 dark:border-earth-700/50">
                <p className="text-sm font-semibold text-lsc-dark/70 dark:text-lsc-cream/70">
                  Default Daily Goal (minutes)
                </p>
                <p className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mt-2">
                  {features?.default_daily_goal_minutes ?? 'N/A'}
                </p>
              </div>
            </div>
        </div>

        {/* Help Info Card */}
        <div className="border border-lsc-border dark:border-earth-700 rounded-lg p-6">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-4">
            About Feature Flags
          </h2>
          <div className="space-y-3 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            <p>
              Feature flags allow you to enable or disable functionality across the entire
              organization without deploying code.
            </p>
            <p>
              Changes are applied immediately and affect all users. Staff members may need to
              refresh their sessions or browser to see the changes reflected in their UI.
            </p>
            <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 pt-2 border-t border-lsc-border/30 dark:border-earth-700/30">
              Last updated: {features?.updated_at ? new Date(features.updated_at).toLocaleString() : 'Never'}
            </p>
          </div>
        </div>
        </div>
      </div>
    </StaffLayout>
  );
};

export default StaffFeatureFlagsPage;