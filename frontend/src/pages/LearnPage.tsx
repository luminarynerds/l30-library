/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */

/* eslint-disable react-refresh/only-export-components */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { usePreferences } from '../contexts/PreferencesContext';
import api from '../api/api';
import { learningApi } from '@/components/training';
import { logger } from '@/utils/logger';
import { GentleProgress } from '../components/training';
import { API_BASE } from '@/api/types'
import { useTranslation } from '@/i18n'
import type { EnrolledCourse, RecommendedCourse, LearningPath, LastLesson } from '../types/learning';
import { getLastLesson, RECENTLY_VIEWED_KEY, LAST_LESSON_KEY } from '../services/learning-storage';
import { usePageTitle } from '@/hooks/usePageTitle'
import { useBranding } from '@/contexts/BrandingContext'
import {
  LearnHeader,
  QuickResumeBanner,
  QuickPicks,
  CourseSearchBar,
  InProgressCourses,
  CompletedCourses,
  RecommendedCourses,
  LearningPathsSection,
  EmptyState,
  LearnSidebar,
} from './learn/components';

export { addToRecentlyViewed, setLastLesson } from '../services/learning-storage';

// Motivational messages based on progress and streak state
type MotivationalMessage = { key: string; fallback: string };
const getMotivationalMessage = (
  completedLessons: number,
  _totalLessons: number,
  completedCourses: number,
  currentStreak: number,
): MotivationalMessage => {
  if (completedCourses >= 5) return { key: 'learn.motivationalChampion', fallback: "You've finished five courses. That's real." };
  if (completedCourses >= 3) return { key: 'learn.motivationalThreeComplete', fallback: "Three courses done. You're building something here." };
  if (completedCourses >= 1) return { key: 'learn.motivationalFirstDone', fallback: "First course complete. The hard part was starting." };
  if (completedLessons >= 10) return { key: 'learn.motivationalTenLessons', fallback: "Ten lessons in. You know more today than you did last week." };
  if (completedLessons >= 5) return { key: 'learn.motivationalGreatProgress', fallback: "Five lessons down. Keep going at your own pace." };
  // Streak-aware: returning patron with gap vs active streak vs brand new
  if (completedLessons > 0 && currentStreak === 0) {
    return { key: 'learn.motivationalReturning', fallback: "Welcome back. Pick up where you left off." };
  }
  if (completedLessons > 0 && currentStreak > 0) {
    return { key: 'learn.motivationalActiveStreak', fallback: "You're on a streak. Each lesson builds on the last." };
  }
  if (completedLessons >= 1) return { key: 'learn.motivationalStarted', fallback: "You've taken the first step. Every lesson counts." };
  return { key: 'learn.motivationalReady', fallback: "Pick a course that looks interesting. That's the only rule." };
};

export default function LearnPage() {
  const branding = useBranding()
  usePageTitle('Learning Center', `Free courses, workshops, and learning paths at ${branding.library_short_name}. From digital literacy to professional development.`)
  const { t } = useTranslation()
  const { user, isAuthenticated } = useAuth();
  const { preferences } = usePreferences();
  const [enrolledCourses, setEnrolledCourses] = useState<EnrolledCourse[]>([]);
  const [allCourses, setAllCourses] = useState<RecommendedCourse[]>([]);
  const [learningPaths, setLearningPaths] = useState<LearningPath[]>([]);
  const [lastLesson, setLastLessonState] = useState<LastLesson | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [_error, setError] = useState<string | null>(null);

  useEffect(() => {
    // Load last lesson position (localStorage now, API when available)
    getLastLesson().then(setLastLessonState);

    // Fetch courses and learning paths (public endpoint)
    const fetchPromises: Promise<unknown>[] = [
      api.get(`${API_BASE}/learning/courses`).catch((error) => {
        logger.error('Failed to fetch learning courses:', error);
        return [];
      }),
      api.get(`${API_BASE}/learning-paths`).catch((error) => {
        logger.error('Failed to fetch learning paths:', error);
        return [];
      }),
    ];

    // Only fetch enrolled courses for authenticated users
    if (isAuthenticated) {
      fetchPromises.push(api.get(`${API_BASE}/learning/my-courses`).catch((error) => {
        logger.error('Failed to fetch enrolled courses:', error);
        return [];
      }));
    }

    Promise.all(fetchPromises).then(([courses, paths, enrolled]) => {
      setAllCourses(courses as RecommendedCourse[]);
      setLearningPaths(paths as LearningPath[]);
      if (enrolled) {
        setEnrolledCourses(enrolled as EnrolledCourse[]);
      }
    }).catch((err) => {
      Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      setError('Unable to load learning data. Please try again later.');
    }).finally(() => setLoading(false));
  }, [isAuthenticated]);

  // Anon -> auth handoff: one-shot replay of localStorage views + last lesson position
  useEffect(() => {
    if (!isAuthenticated) return;
    if (typeof window === 'undefined') return;
    if (sessionStorage.getItem('lsc_handoff_done')) return;

    let cancelled = false;
    (async () => {
      let allSucceeded = true;
      try {
        const viewsRaw = localStorage.getItem(RECENTLY_VIEWED_KEY);
        const views: { id: number }[] = viewsRaw ? JSON.parse(viewsRaw) : [];
        for (const v of views) {
          try {
            await api.post(`${API_BASE}/learning/courses/${v.id}/view`);
          } catch (err) {
            allSucceeded = false;
            Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
          }
        }

        const lastRaw = localStorage.getItem(LAST_LESSON_KEY);
        if (lastRaw) {
          try {
            const last: LastLesson = JSON.parse(lastRaw);
            if (last?.lessonId) {
              await api.put(`${API_BASE}/learning/lessons/${last.lessonId}/position`, { position: 0 });
            }
          } catch (err) {
            allSucceeded = false;
            Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
          }
        }

        if (!cancelled && allSucceeded) {
          localStorage.removeItem(RECENTLY_VIEWED_KEY);
          localStorage.removeItem(LAST_LESSON_KEY);
        }
      } catch (err) {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
      } finally {
        // Set guard in both success and failure paths so we don't retry within this tab.
        if (!cancelled) sessionStorage.setItem('lsc_handoff_done', '1');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isAuthenticated]);

  // Generate recommendations based on completed courses
  const recommendations = useMemo(() => {
    const completedIds = new Set(enrolledCourses.filter(e => e.enrollment.completed_at).map(e => e.course.id));
    const enrolledIds = new Set(enrolledCourses.map(e => e.course.id));
    const completedDifficulties = new Set(
      enrolledCourses.filter(e => e.enrollment.completed_at && e.course.difficulty).map(e => e.course.difficulty)
    );

    return allCourses
      .filter(c => !enrolledIds.has(c.id))
      .map(c => {
        let reason = 'Popular course';
        if (completedDifficulties.has('beginner') && c.difficulty === 'intermediate') {
          reason = 'Ready for the next level';
        } else if (completedDifficulties.has('intermediate') && c.difficulty === 'advanced') {
          reason = 'Challenge yourself';
        } else if (completedIds.size === 0) {
          reason = 'Great for beginners';
        }
        return { ...c, reason };
      })
      .slice(0, 3);
  }, [enrolledCourses, allCourses]);

  // Filter enrolled courses by search
  const filteredEnrolled = useMemo(() => {
    if (!searchTerm) return enrolledCourses;
    const term = searchTerm.toLowerCase();
    return enrolledCourses.filter(e =>
      e.course.title.toLowerCase().includes(term) ||
      e.course.description?.toLowerCase().includes(term)
    );
  }, [enrolledCourses, searchTerm]);

  // "Got X minutes?" - time-based course suggestions
  const quickPicks = useMemo(() => {
    const enrolledIds = new Set(enrolledCourses.map(e => e.course.id));
    const availableCourses = allCourses.filter(c => !enrolledIds.has(c.id) && c.estimated_minutes);

    return {
      fiveMin: availableCourses.filter(c => c.estimated_minutes && c.estimated_minutes <= 10).slice(0, 2),
      fifteenMin: availableCourses.filter(c => c.estimated_minutes && c.estimated_minutes > 10 && c.estimated_minutes <= 20).slice(0, 2),
      thirtyMin: availableCourses.filter(c => c.estimated_minutes && c.estimated_minutes > 20 && c.estimated_minutes <= 35).slice(0, 2),
    };
  }, [enrolledCourses, allCourses]);

  // Unstarted enrolled courses (enrolled but no lessons completed yet, not finished)
  const unstartedCourses = useMemo(
    () =>
      enrolledCourses.filter(
        e => e.completed_lessons === 0 && !e.enrollment.completed_at,
      ),
    [enrolledCourses],
  );

  // Gamification stats (same query key as UserStatsCard — no extra request when authenticated)
  const { data: gamificationStats } = useQuery({
    queryKey: ['my-stats'],
    queryFn: learningApi.getMyStats,
    enabled: isAuthenticated,
  });

  // Motivational message
  const motivationalMessage = useMemo(() => {
    const completedCourses = enrolledCourses.filter(e => e.enrollment.completed_at).length;
    const completedLessons = enrolledCourses.reduce((sum, c) => sum + c.completed_lessons, 0);
    const totalLessons = enrolledCourses.reduce((sum, c) => sum + c.total_lessons, 0);
    const currentStreak = gamificationStats?.current_streak ?? 0;
    const msg = getMotivationalMessage(completedLessons, totalLessons, completedCourses, currentStreak);
    return t(msg.key, msg.fallback);
  }, [enrolledCourses, gamificationStats, t]);

  if (loading) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4" aria-busy="true" aria-label="Loading learning center">
        <div className="max-w-6xl mx-auto motion-safe:animate-pulse">
          {/* Header bar */}
          <div className="h-8 w-64 bg-lsc-cream dark:bg-lsc-brown rounded mb-6" />
          {/* Quick-pick cards */}
          <div className="grid sm:grid-cols-2 gap-4 mb-8">
            <div className="h-32 bg-lsc-cream dark:bg-lsc-brown rounded-xl" />
            <div className="h-32 bg-lsc-cream dark:bg-lsc-brown rounded-xl" />
          </div>
          {/* Course grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="h-24 bg-lsc-cream dark:bg-lsc-brown rounded-xl" />
            <div className="h-24 bg-lsc-cream dark:bg-lsc-brown rounded-xl" />
            <div className="h-24 bg-lsc-cream dark:bg-lsc-brown rounded-xl" />
          </div>
        </div>
      </div>
    );
  }

  const inProgress = filteredEnrolled.filter(c => !c.enrollment.completed_at);
  const completed = filteredEnrolled.filter(c => c.enrollment.completed_at);
  const totalLessons = enrolledCourses.reduce((sum, c) => sum + c.total_lessons, 0);
  const completedLessons = enrolledCourses.reduce((sum, c) => sum + c.completed_lessons, 0);

  return (
    <main className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-6xl mx-auto">
        <LearnHeader isAuthenticated={isAuthenticated} firstName={user?.first_name} />

        {lastLesson && !searchTerm && (
          <QuickResumeBanner lastLesson={lastLesson} />
        )}

        {!searchTerm && (
          <QuickPicks quickPicks={quickPicks} />
        )}

        {enrolledCourses.length > 0 && (
          <CourseSearchBar searchTerm={searchTerm} onSearchChange={setSearchTerm} />
        )}

        <div className="grid lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {enrolledCourses.length > 0 && (
              <div>
                <GentleProgress completed={completedLessons} total={totalLessons} showPercentage />
                <p className="mt-2 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">{motivationalMessage}</p>
              </div>
            )}

            {unstartedCourses.length > 0 && !searchTerm && (
              <section
                aria-labelledby="unstarted-nudge-heading"
                className="bg-lsc-rose/10 dark:bg-lsc-rose/20 border border-lsc-rose/30 dark:border-lsc-rose/40 rounded-xl p-5"
              >
                <div className="flex items-start gap-3">
                  <Sparkles aria-hidden="true" className="w-5 h-5 text-lsc-rose flex-shrink-0 mt-0.5" />
                  <div className="flex-1 min-w-0">
                    <h2
                      id="unstarted-nudge-heading"
                      className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream mb-1"
                    >
                      {t('learn.unstartedNudgeHeading', 'Saved for you')}
                    </h2>
                    <p className="text-sm text-lsc-dark/80 dark:text-lsc-cream/80 mb-3">
                      {t(
                        'learn.unstartedNudgeBody',
                        'You enrolled in these but have not started yet. No pressure to finish, just here when you are ready.',
                      )}
                    </p>
                    <ul className="space-y-2 mb-4">
                      {unstartedCourses.slice(0, 3).map(e => {
                        const lessonCount = e.total_lessons;
                        const hrs = e.course.estimated_minutes ? Math.round(e.course.estimated_minutes / 60 * 10) / 10 : null;
                        const timePart = hrs
                          ? (hrs >= 1 ? `~${hrs} ${t('learn.hrs', 'hrs')}` : `~${e.course.estimated_minutes} ${t('learn.min', 'min')}`)
                          : null;
                        const meta = [
                          lessonCount ? `${lessonCount} ${t('learn.lessons', 'lessons')}` : null,
                          timePart,
                        ].filter(Boolean).join(' · ');
                        return (
                          <li key={e.course.id} className="text-sm text-lsc-dark dark:text-lsc-cream">
                            <Link
                              to={`/learn/course/${e.course.id}`}
                              className="font-medium hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose rounded"
                            >
                              {e.course.title}
                            </Link>
                            {meta && (
                              <span className="block text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">{meta}</span>
                            )}
                          </li>
                        );
                      })}
                    </ul>
                    {unstartedCourses[0] && (
                      <Link
                        to={`/learn/course/${unstartedCourses[0].course.id}`}
                        className="inline-flex items-center gap-1 px-4 py-2 bg-lsc-rose text-white rounded-xl font-medium text-sm hover:bg-lsc-rose/90 focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2 transition-colors"
                      >
                        {t('learn.pickUpWhereYouStarted', 'Pick up where you started')}
                      </Link>
                    )}
                  </div>
                </div>
              </section>
            )}

            {inProgress.length > 0 && (
              <InProgressCourses courses={inProgress} />
            )}

            {completed.length > 0 && (
              <CompletedCourses courses={completed} />
            )}

            {recommendations.length > 0 && !searchTerm && (
              <RecommendedCourses courses={recommendations} />
            )}

            {learningPaths.length > 0 && !searchTerm && (
              <LearningPathsSection paths={learningPaths} />
            )}

            {isAuthenticated && enrolledCourses.length === 0 && (
              <EmptyState
                isAuthenticated={isAuthenticated}
                searchTerm={searchTerm}
                hasEnrolledCourses={false}
                onClearSearch={() => setSearchTerm('')}
              />
            )}

            {searchTerm && filteredEnrolled.length === 0 && enrolledCourses.length > 0 && (
              <EmptyState
                isAuthenticated={isAuthenticated}
                searchTerm={searchTerm}
                hasEnrolledCourses={true}
                onClearSearch={() => setSearchTerm('')}
              />
            )}
          </div>

          <LearnSidebar
            isAuthenticated={isAuthenticated}
            hideGamification={preferences.hide_gamification}
          />
        </div>
      </div>
    </main>
  );
}
