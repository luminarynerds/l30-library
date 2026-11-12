/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { API_BASE } from '@/api/types';
import {
  BarChart3, TrendingUp, Clock, BookOpen, Award, Calendar,
  ChevronRight, Target, Zap, CheckCircle, ArrowLeft, Info
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { usePreferences } from '../contexts/PreferencesContext';
import api from '../api/api';
import { useTranslation } from '@/i18n'

interface EnrolledCourse {
  course: { id: number; title: string; description: string; estimated_minutes: number | null; difficulty?: string; };
  enrollment: { id: number; enrolled_at: string; completed_at: string | null; };
  progress_percentage: number;
  completed_lessons: number;
  total_lessons: number;
}

interface UserStats {
  total_xp: number;
  level: number;
  current_streak: number;
  longest_streak: number;
  badges_earned: number;
  lessons_completed: number;
  courses_completed: number;
}

interface WeeklyProgress {
  day: string;
  lessons: number;
  minutes: number;
}

interface WeeklyActivityResponse {
  activity: WeeklyProgress[];
  total_lessons: number;
  total_minutes: number;
}

interface RecentActivity {
  lesson_id: number;
  lesson_title: string;
  course_id: number;
  course_title: string;
  completed_at: string;
  xp_earned: number;
}

export default function LearningAnalyticsPage() {
  const { t } = useTranslation()
  const { isAuthenticated } = useAuth();
  const { preferences } = usePreferences();
  const [enrolledCourses, setEnrolledCourses] = useState<EnrolledCourse[]>([]);
  const [userStats, setUserStats] = useState<UserStats | null>(null);
  const [weeklyActivity, setWeeklyActivity] = useState<WeeklyActivityResponse | null>(null);
  const [_recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [_error, setError] = useState<string | null>(null);

  // Check if gamification is hidden (pressure-free mode)
  const hideGamification = preferences?.hide_gamification || false;
  const hideStreaks = preferences?.hide_streaks || false;

  useEffect(() => {
    if (isAuthenticated) {
      Promise.all([
        api.get(`${API_BASE}/learning/my-courses`).catch(() => []),
        api.get(`${API_BASE}/learning/gamification/stats`).catch(() => null),
        api.get(`${API_BASE}/learning/gamification/weekly-activity`).catch(() => null),
        api.get(`${API_BASE}/learning/gamification/analytics`).catch(() => null),
      ]).then(([courses, stats, weekly, analytics]) => {
        setEnrolledCourses(courses);
        setUserStats(stats);
        setWeeklyActivity(weekly);
        if (analytics?.recent_activity) {
          setRecentActivity(analytics.recent_activity);
        }
      }).catch((err) => {
        Sentry.captureException(err instanceof Error ? err : new Error(String(err)));
        setError('Unable to load analytics. Please try again later.');
      }).finally(() => setLoading(false));
    } else {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- sync loading reset on unauthenticated branch
      setLoading(false);
    }
  }, [isAuthenticated]);

  // Calculate analytics
  const analytics = useMemo(() => {
    const totalCourses = enrolledCourses.length;
    const completedCourses = enrolledCourses.filter(e => e.enrollment.completed_at).length;
    const inProgressCourses = totalCourses - completedCourses;
    const totalLessons = enrolledCourses.reduce((sum, e) => sum + e.total_lessons, 0);
    const completedLessons = enrolledCourses.reduce((sum, e) => sum + e.completed_lessons, 0);
    const totalMinutes = enrolledCourses.reduce((sum, e) => sum + (e.course.estimated_minutes || 0), 0);
    const estimatedMinutesCompleted = Math.round(
      enrolledCourses.reduce((sum, e) => {
        const courseMinutes = e.course.estimated_minutes || 0;
        return sum + (courseMinutes * e.progress_percentage / 100);
      }, 0)
    );

    // Calculate difficulty distribution
    const difficultyCount = { beginner: 0, intermediate: 0, advanced: 0 };
    enrolledCourses.forEach(e => {
      const diff = e.course.difficulty as keyof typeof difficultyCount;
      if (diff && difficultyCount[diff] !== undefined) {
        difficultyCount[diff]++;
      }
    });

    // Use real weekly activity data from backend, or fallback to empty days
    const weeklyProgress: WeeklyProgress[] = weeklyActivity?.activity || [
      { day: 'Mon', lessons: 0, minutes: 0 },
      { day: 'Tue', lessons: 0, minutes: 0 },
      { day: 'Wed', lessons: 0, minutes: 0 },
      { day: 'Thu', lessons: 0, minutes: 0 },
      { day: 'Fri', lessons: 0, minutes: 0 },
      { day: 'Sat', lessons: 0, minutes: 0 },
      { day: 'Sun', lessons: 0, minutes: 0 },
    ];

    return {
      totalCourses,
      completedCourses,
      inProgressCourses,
      totalLessons,
      completedLessons,
      totalMinutes,
      estimatedMinutesCompleted,
      difficultyCount,
      weeklyProgress,
      completionRate: totalCourses > 0 ? Math.round((completedCourses / totalCourses) * 100) : 0,
      lessonCompletionRate: totalLessons > 0 ? Math.round((completedLessons / totalLessons) * 100) : 0,
    };
  }, [enrolledCourses, weeklyActivity]);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-12 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-lg p-12">
            <BarChart3 className="w-16 h-16 mx-auto text-lsc-rose mb-4" />
            <h2 className="text-xl font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-2">{t('learningAnalytics.signInToViewAnalytics')}</h2>
            <Link to="/account" className="inline-flex items-center gap-2 bg-lsc-rose text-white px-8 py-3 rounded-xl font-medium mt-4">Sign In</Link>
          </div>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
        <div className="max-w-6xl mx-auto motion-safe:animate-pulse">
          <div className="h-8 bg-lsc-white dark:bg-earth-800 rounded w-48 mb-6" />
          <div className="grid md:grid-cols-4 gap-4 mb-8">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-lsc-white dark:bg-earth-800 rounded-xl" />)}
          </div>
        </div>
      </div>
    );
  }

  const maxWeeklyLessons = Math.max(...analytics.weeklyProgress.map(d => d.lessons), 1);

  return (
    <div className="min-h-screen bg-lsc-cream dark:bg-lsc-dark py-8 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link to="/learn" className="inline-flex items-center gap-2 text-lsc-rose hover:underline mb-2">
              <ArrowLeft className="w-4 h-4" />
              Back to Learning
            </Link>
            <h1 className="text-3xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
              Learning Analytics
            </h1>
            <p className="text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              Track your learning journey and progress
            </p>
          </div>
        </div>

        {/* Overview Stats */}
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-earth-100 dark:bg-earth-800/30 flex items-center justify-center">
                <BookOpen className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
              </div>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Courses</span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{analytics.totalCourses}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              {analytics.completedCourses} completed, {analytics.inProgressCourses} in progress
            </p>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-status-success-100 dark:bg-status-success-900/30 flex items-center justify-center">
                <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
              </div>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Lessons Completed</span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{analytics.completedLessons}</p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              of {analytics.totalLessons} total ({analytics.lessonCompletionRate}%)
            </p>
          </div>

          <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-lsc-rose/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-lsc-rose" />
              </div>
              <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Time Invested</span>
            </div>
            <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">
              {Math.floor(analytics.estimatedMinutesCompleted / 60)}h {analytics.estimatedMinutesCompleted % 60}m
            </p>
            <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
              of ~{Math.floor(analytics.totalMinutes / 60)}h total content
            </p>
          </div>

          {/* XP Card - Hidden in pressure-free mode */}
          {!hideGamification ? (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-category-100 dark:bg-category-900/30 flex items-center justify-center">
                  <Zap aria-hidden="true" className="w-5 h-5 text-category-600 dark:text-category-400" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Total XP</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{userStats?.total_xp || 0}</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Level {userStats?.level || 1}
              </p>
            </div>
          ) : (
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
              <div className="flex items-center gap-3 mb-3">
                <div className="w-10 h-10 rounded-full bg-status-success-100 dark:bg-status-success-900/30 flex items-center justify-center">
                  <CheckCircle aria-hidden="true" className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                </div>
                <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Your Progress</span>
              </div>
              <p className="text-3xl font-bold text-lsc-dark dark:text-lsc-cream">{analytics.completionRate}%</p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-1">
                Overall completion
              </p>
            </div>
          )}
        </div>

        <div className="grid lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Weekly Activity Chart */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5 text-lsc-rose" />
                This Week's Activity
              </h2>
              <div className="flex items-end justify-between gap-2 h-40">
                {analytics.weeklyProgress.map((day, _idx) => (
                  <div key={day.day} className="flex-1 flex flex-col items-center">
                    <div
                      className={`w-full rounded-t-lg transition-all ${
                        day.lessons > 0 ? 'bg-lsc-rose' : 'bg-lsc-cream dark:bg-lsc-brown'
                      }`}
                      style={{ height: `${(day.lessons / maxWeeklyLessons) * 100}%`, minHeight: day.lessons > 0 ? '8px' : '4px' }}
                      title={`${day.lessons} lessons, ${day.minutes} minutes`}
                    />
                    <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2">{day.day}</span>
                    <span className="text-xs font-medium text-lsc-dark dark:text-lsc-cream">{day.lessons}</span>
                  </div>
                ))}
              </div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mt-4 text-center">
                {analytics.weeklyProgress.reduce((sum, d) => sum + d.lessons, 0)} lessons completed this week
              </p>
            </div>

            {/* Learning Journey */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
              <h2 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-lsc-rose" />
                Learning Journey
              </h2>
              {enrolledCourses.length === 0 ? (
                <div className="text-center py-8">
                  <BookOpen className="w-12 h-12 mx-auto text-lsc-dark/30 dark:text-lsc-cream/60 mb-3" />
                  <p className="text-lsc-dark/70 dark:text-lsc-cream/70">{t('learningAnalytics.noCoursesEnrolledYet')}</p>
                  <Link to="/learn/catalog" className="text-lsc-rose hover:underline text-sm mt-2 inline-block">
                    Browse courses
                  </Link>
                </div>
              ) : (
                <div className="space-y-4">
                  {enrolledCourses.slice(0, 5).map((enrolled, idx) => (
                    <Link
                      key={enrolled.course.id}
                      to={`/learn/course/${enrolled.course.id}`}
                      className="flex items-center gap-4 p-3 rounded-lg hover:bg-lsc-cream dark:hover:bg-lsc-brown transition-colors group"
                    >
                      <div className="relative">
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                          enrolled.enrollment.completed_at
                            ? 'bg-status-success-100 dark:bg-status-success-900/30'
                            : 'bg-lsc-cream dark:bg-lsc-brown'
                        }`}>
                          {enrolled.enrollment.completed_at ? (
                            <CheckCircle className="w-5 h-5 text-status-success-600 dark:text-status-success-400" />
                          ) : (
                            <span className="text-sm font-bold text-lsc-dark dark:text-lsc-cream">
                              {Math.round(enrolled.progress_percentage)}%
                            </span>
                          )}
                        </div>
                        {idx < enrolledCourses.length - 1 && (
                          <div className="absolute top-full left-1/2 w-0.5 h-4 bg-lsc-border dark:bg-earth-700 -translate-x-1/2" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0">
                        <h3 className="font-medium text-lsc-dark dark:text-lsc-cream truncate group-hover:text-lsc-rose" title={enrolled.course.title}>
                          {enrolled.course.title}
                        </h3>
                        <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                          {enrolled.completed_lessons}/{enrolled.total_lessons} lessons
                          {enrolled.enrollment.completed_at && ' - Completed!'}
                        </p>
                      </div>
                      <ChevronRight className="w-5 h-5 text-lsc-dark/30 dark:text-lsc-cream/60 group-hover:text-lsc-rose" />
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Completion Rate */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
              <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-lsc-rose" />
                Completion Rate
              </h3>
              <div className="relative w-32 h-32 mx-auto mb-4">
                <svg className="w-full h-full transform -rotate-90">
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="12"
                    className="text-lsc-cream dark:text-lsc-brown"
                  />
                  <circle
                    cx="64"
                    cy="64"
                    r="56"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="12"
                    strokeLinecap="round"
                    strokeDasharray={`${analytics.completionRate * 3.52} 352`}
                    className="text-lsc-rose transition-all duration-500"
                  />
                </svg>
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="text-2xl font-bold text-lsc-dark dark:text-lsc-cream">
                    {analytics.completionRate}%
                  </span>
                </div>
              </div>
              <p className="text-center text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Course completion rate
              </p>
            </div>

            {/* Difficulty Distribution */}
            <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
              <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4">
                Difficulty Mix
              </h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-status-success-600 dark:text-status-success-400">Beginner</span>
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {analytics.difficultyCount.beginner}
                  </span>
                </div>
                <div className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                  <div
                    className="h-full bg-status-success-500 rounded-full"
                    style={{ width: `${analytics.totalCourses ? (analytics.difficultyCount.beginner / analytics.totalCourses) * 100 : 0}%` }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-status-warning-600 dark:text-status-warning-400">Intermediate</span>
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {analytics.difficultyCount.intermediate}
                  </span>
                </div>
                <div className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                  <div
                    className="h-full bg-status-warning-500 rounded-full"
                    style={{ width: `${analytics.totalCourses ? (analytics.difficultyCount.intermediate / analytics.totalCourses) * 100 : 0}%` }}
                  />
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-sm text-status-danger-600 dark:text-status-danger-400">Advanced</span>
                  <span className="text-sm font-medium text-lsc-dark dark:text-lsc-cream">
                    {analytics.difficultyCount.advanced}
                  </span>
                </div>
                <div className="h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
                  <div
                    className="h-full bg-status-danger-500 rounded-full"
                    style={{ width: `${analytics.totalCourses ? (analytics.difficultyCount.advanced / analytics.totalCourses) * 100 : 0}%` }}
                  />
                </div>
              </div>
            </div>

            {/* Streaks & Badges - Respects user preferences for pressure-free learning */}
            {userStats && !hideGamification && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
                <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Award aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                  Achievements
                </h3>
                <div className="grid grid-cols-2 gap-4">
                  {!hideStreaks && (
                    <div className="text-center p-3 bg-lsc-cream dark:bg-lsc-brown rounded-lg">
                      <p className="text-2xl font-bold text-lsc-rose">{userStats.current_streak}</p>
                      <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Day Streak</p>
                    </div>
                  )}
                  <div className={`text-center p-3 bg-lsc-cream dark:bg-lsc-brown rounded-lg ${hideStreaks ? 'col-span-2' : ''}`}>
                    <p className="text-2xl font-bold text-lsc-rose">{userStats.badges_earned}</p>
                    <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">Badges</p>
                  </div>
                </div>
                <Link
                  to="/learn/achievements"
                  className="mt-4 block text-center text-sm text-lsc-rose hover:underline"
                >
                  View all achievements
                </Link>
              </div>
            )}

            {/* Pressure-free alternative - shown when gamification is hidden */}
            {hideGamification && (
              <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
                <h3 className="text-lg font-serif font-bold text-lsc-dark dark:text-lsc-cream mb-4 flex items-center gap-2">
                  <Info aria-hidden="true" className="w-5 h-5 text-lsc-rose" />
                  Your Learning Style
                </h3>
                <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 mb-4">
                  You're learning at your own pace, without pressure. Great choice for sustainable progress!
                </p>
                <Link
                  to="/account"
                  className="block text-center text-sm text-lsc-rose hover:underline"
                >
                  Adjust learning preferences
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}