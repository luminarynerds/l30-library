/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Staff Training Dashboard - Consolidated training hub.
 *
 * Thin shell after the Wave 0 split: handles auth gating, URL-driven tab
 * state, and the WAI-ARIA tablist + tabpanel scaffolding. Tab content lives
 * in `components/training/tabs/`.
 *
 * Wave 2: adds a manager-only "Team" tab, surfaced only when the current
 * user has at least one direct report linked via StaffOnboarding.manager_id.
 * Non-managers never see the tab; if they navigate to ?tab=team directly,
 * we fall back to the Courses tab.
 */
import React, { Suspense, useEffect, useMemo } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Loader2, BookOpen, Award, Users, RefreshCw } from 'lucide-react';
import toast from 'react-hot-toast';
import { useTranslation } from '@/i18n';
import { useAuth } from '../contexts/AuthContext';
import { AdminShell } from '../components/shells/AdminShell';
import { ErrorBoundary } from '../components/ErrorBoundary';
import {
  TrainingTabNav,
  tabIdFor,
  panelIdFor,
  CoursesTab,
  SkillsTab,
  TeamTab,
  useTeamMembership,
  type TrainingTabDescriptor,
  type TrainingTab,
} from '../components/training';

function TabLoadingSkeleton(): React.ReactElement {
  return (
    <div className="flex items-center justify-center min-h-[200px]">
      <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
    </div>
  );
}

function TabLoadError({ tab }: { tab: TrainingTab }): React.ReactElement {
  const labels: Record<TrainingTab, string> = {
    courses: 'Course Training',
    skills: 'Skills Training',
    team: 'Team',
  };
  return (
    <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 p-6 text-center">
      <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-2">
        {labels[tab]} couldn't load
      </h2>
      <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
        This is often caused by an outdated browser tab after a recent update. Refreshing should fix it.
      </p>
      <button
        type="button"
        onClick={() => window.location.reload()}
        className="inline-flex items-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-xl font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose"
      >
        <RefreshCw aria-hidden="true" className="w-4 h-4" />
        Refresh page
      </button>
    </div>
  );
}

export default function StaffTrainingDashboard(): React.ReactElement {
  const { t } = useTranslation();
  const { user, isLoading: authLoading } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const isStaff = !!user && user.role !== 'patron';

  // Only fetch team progress for staff users — patrons would 403 (handled in
  // the API client by returning [], but we skip the request entirely to be tidy).
  const { hasReports, isLoading: teamLoading } = useTeamMembership(isStaff);

  const requestedTab = (searchParams.get('tab') as TrainingTab) || 'courses';

  // If a non-manager tries to deep-link ?tab=team, fall back to courses.
  // While teamLoading is true we don't yet know — keep the requested tab
  // tentatively so the panel renders once data arrives, but never resolve to
  // 'team' if hasReports turns out false.
  const activeTab: TrainingTab = useMemo(() => {
    if (requestedTab !== 'team') return requestedTab;
    if (teamLoading) return 'team';
    return hasReports ? 'team' : 'courses';
  }, [requestedTab, hasReports, teamLoading]);

  // Sync the URL when we forcibly redirect away from ?tab=team for a non-manager.
  useEffect(() => {
    if (
      requestedTab === 'team' &&
      !teamLoading &&
      !hasReports &&
      activeTab !== 'team'
    ) {
      setSearchParams({ tab: activeTab }, { replace: true });
    }
  }, [requestedTab, teamLoading, hasReports, activeTab, setSearchParams]);

  const setActiveTab = (tab: TrainingTab) => {
    setSearchParams({ tab });
  };

  useEffect(() => {
    if (!authLoading && (!user || user.role === 'patron')) {
      toast.error(t('toast.acquisitionManagement.staffAccessRequired'));
      navigate('/account');
    }
  }, [authLoading, user, navigate, t]);

  if (authLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <Loader2 className="w-8 h-8 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
      </div>
    );
  }

  if (!user || user.role === 'patron') {
    return <></>;
  }

  const tabs: TrainingTabDescriptor[] = [
    { id: 'courses', label: 'Course Training', icon: BookOpen },
    { id: 'skills', label: 'Skills Training', icon: Award },
    ...(hasReports
      ? [{ id: 'team' as const, label: 'Team', icon: Users }]
      : []),
  ];

  return (
    <AdminShell title="Training Center" subtitle={t('staffTrainingDashboard.manageYourTrainingAndSkill')}>
      <TrainingTabNav activeTab={activeTab} onTabChange={setActiveTab} tabs={tabs} />

      {activeTab === 'courses' && (
        <div
          role="tabpanel"
          id={panelIdFor('courses')}
          aria-labelledby={tabIdFor('courses')}
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <ErrorBoundary fallback={<TabLoadError tab="courses" />}>
            <Suspense fallback={<TabLoadingSkeleton />}>
              <CoursesTab />
            </Suspense>
          </ErrorBoundary>
        </div>
      )}

      {activeTab === 'skills' && (
        <div
          role="tabpanel"
          id={panelIdFor('skills')}
          aria-labelledby={tabIdFor('skills')}
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <ErrorBoundary fallback={<TabLoadError tab="skills" />}>
            <Suspense fallback={<TabLoadingSkeleton />}>
              <SkillsTab />
            </Suspense>
          </ErrorBoundary>
        </div>
      )}

      {activeTab === 'team' && hasReports && (
        <div
          role="tabpanel"
          id={panelIdFor('team')}
          aria-labelledby={tabIdFor('team')}
          tabIndex={0}
          className="space-y-6 focus:outline-none"
        >
          <ErrorBoundary fallback={<TabLoadError tab="team" />}>
            <Suspense fallback={<TabLoadingSkeleton />}>
              <TeamTab />
            </Suspense>
          </ErrorBoundary>
        </div>
      )}
    </AdminShell>
  );
}
