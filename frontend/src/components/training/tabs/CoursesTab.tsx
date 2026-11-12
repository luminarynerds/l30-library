/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable no-case-declarations */
/**
 * CoursesTab - Compliance / course training tab.
 *
 * Self-contained: owns search/filter/sort/dismissed-alert state and all the
 * derived useMemo blocks. Future waves will swap the simulated due-date
 * implementation in `../utils/dueDate` and add badges/chips to `CourseRow`
 * without touching this component.
 */
import React, { useCallback, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Loader2,
  AlertTriangle,
  Clock,
  Calendar,
  Search,
  X,
  TrendingUp,
  BookOpen,
  Filter,
  BarChart3,
  Plus,
  GraduationCap,
} from 'lucide-react';
import toast from 'react-hot-toast';
import clsx from 'clsx';
import { useTranslation, getCurrentLocale } from '@/i18n';
import { useAuth } from '@/contexts/AuthContext';
import { learningApi, type CourseProgress, type CourseListItem } from '../api';
import {
  getDueDate,
  getTrainingStatus,
  getDaysUntilDue,
  type StatusFilter,
  type SortField,
  type SortDirection,
  type Alert,
  type MonthlyCompletion,
} from '../utils/dueDate';
import { CourseRow } from './CourseRow';
import { SortableTh } from './SortableTh';

export function CoursesTab(): React.ReactElement {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuth();

  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [sortField, setSortField] = useState<SortField>('enrolled_at');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [dismissedAlerts, setDismissedAlerts] = useState<Set<string>>(new Set());

  const { data: courses = [], isLoading: coursesLoading } = useQuery({
    queryKey: ['my-courses'],
    queryFn: learningApi.getMyCourses,
    retry: 1,
  });

  const { data: allCourses = [], isLoading: allCoursesLoading } = useQuery({
    queryKey: ['all-courses'],
    queryFn: learningApi.getAllCourses,
    retry: 1,
  });

  const {
    data: certCountData,
    isLoading: certCountLoading,
    isError: certCountError,
  } = useQuery({
    queryKey: ['my-cert-count'],
    queryFn: learningApi.getMyCertCount,
    enabled: isAuthenticated,
    retry: 1,
  });

  const {
    data: skillsSummaryData,
    isLoading: skillsSummaryLoading,
    isError: skillsSummaryError,
  } = useQuery({
    queryKey: ['my-skills-summary'],
    queryFn: learningApi.getMySkillsSummary,
    enabled: isAuthenticated,
    retry: 1,
  });

  /**
   * Real progress metrics that replaced the fake-XP footer.
   *
   * - hoursLabel: derived from existing `courses` (no extra fetch). Sums each
   *   enrollment's proportional minutes — `course.estimated_minutes *
   *   (completed_lessons / total_lessons)` — across all enrollments. Shows
   *   minutes if total < 60, else hours rounded to one decimal.
   * - certCount / skillsCovered: from the new queries above. While loading we
   *   render an em dash to keep the tile width stable for ND users; we never
   *   show 0 mid-load since that would be misleading.
   */
  const stats = useMemo(() => {
    let totalMinutes = 0;
    for (const c of courses) {
      const total = c.total_lessons || 0;
      const completed = c.completed_lessons || 0;
      const minutes = c.course?.estimated_minutes || 0;
      if (total > 0 && minutes > 0 && completed > 0) {
        totalMinutes += minutes * (completed / total);
      }
    }
    let hoursLabel: string;
    if (totalMinutes <= 0) {
      hoursLabel = '0 hours';
    } else if (totalMinutes < 60) {
      const mins = Math.round(totalMinutes);
      hoursLabel = `${mins} minute${mins === 1 ? '' : 's'}`;
    } else {
      const hours = Math.round((totalMinutes / 60) * 10) / 10;
      hoursLabel = `${hours} hour${hours === 1 ? '' : 's'}`;
    }
    return { hoursLabel };
  }, [courses]);

  const certCountDisplay = certCountError
    ? '—'
    : certCountLoading || !certCountData
      ? '—'
      : String(certCountData.count);
  const skillsCoveredDisplay = skillsSummaryError
    ? '—'
    : skillsSummaryLoading || !skillsSummaryData
      ? '—'
      : String(skillsSummaryData.skills_covered);

  const enrollMutation = useMutation({
    mutationFn: (courseId: number) => learningApi.enrollInCourse(courseId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['my-courses'] });
      queryClient.invalidateQueries({ queryKey: ['all-courses'] });
      toast.success(t('toast.staffTrainingDashboard.enrolledSuccessfully'));
    },
    onError: (err: unknown) => {
      const message = err instanceof Error ? err.message : t('toast.staffTrainingDashboard.failedToEnroll');
      toast.error(message, { duration: 5000 });
    },
  });

  const availableCourses = useMemo(() => {
    try {
      if (!allCourses?.length || !courses?.length) return [];
      const enrolledIds = new Set(courses.map((c: CourseProgress) => c.course?.id).filter(Boolean));
      return allCourses.filter((c: CourseListItem) => !enrolledIds.has(c.id));
    } catch (_err) {
      return [];
    }
  }, [allCourses, courses]);

  const kpis = useMemo(() => {
    if (!courses?.length) {
      return { completionRate: 0, overdueCount: 0, dueSoonCount: 0, nextDeadline: null as Date | null };
    }
    const completed = courses.filter((c) => c.enrollment.completed_at).length;
    const total = courses.length;
    const completionRate = total > 0 ? Math.round((completed / total) * 100) : 0;
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    let overdueCount = 0;
    let dueSoonCount = 0;
    let nextDeadline: Date | null = null;
    courses.forEach((course) => {
      if (course.enrollment.completed_at) return;
      const dueDate = getDueDate(course.enrollment);
      // No deadline configured -> skip (never overdue, never due-soon).
      if (!dueDate) return;
      if (dueDate < now) {
        overdueCount++;
      } else if (dueDate <= sevenDaysFromNow) {
        dueSoonCount++;
      }
      if (dueDate > now) {
        if (!nextDeadline || dueDate < nextDeadline) {
          nextDeadline = dueDate;
        }
      }
    });
    return { completionRate, overdueCount, dueSoonCount, nextDeadline };
  }, [courses]);

  const alerts = useMemo((): Alert[] => {
    if (!courses?.length) return [];
    const now = new Date();
    const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
    const alertsList: Alert[] = [];
    courses.forEach((course) => {
      if (course.enrollment.completed_at) return;
      const dueDate = getDueDate(course.enrollment);
      // No deadline configured -> never alert.
      if (!dueDate) return;
      const daysUntil = getDaysUntilDue(course.enrollment);
      if (dueDate < now) {
        const overdueBy = daysUntil === null ? 0 : Math.abs(daysUntil);
        alertsList.push({
          id: `overdue-${course.course.id}`,
          type: 'overdue',
          courseTitle: course.course.title,
          courseId: course.course.id,
          message: `Training is ${overdueBy} day${overdueBy !== 1 ? 's' : ''} overdue`,
          dueDate,
        });
      } else if (dueDate <= sevenDaysFromNow) {
        const daysLeft = daysUntil ?? 0;
        alertsList.push({
          id: `due-soon-${course.course.id}`,
          type: 'due_soon',
          courseTitle: course.course.title,
          courseId: course.course.id,
          message: `Due in ${daysLeft} day${daysLeft !== 1 ? 's' : ''}`,
          dueDate,
        });
      }
    });
    return alertsList.filter((a) => !dismissedAlerts.has(a.id));
  }, [courses, dismissedAlerts]);

  const completionTimeline = useMemo((): MonthlyCompletion[] => {
    if (!courses?.length) return [];
    const completedCourses = courses.filter((c) => c.enrollment.completed_at);
    const monthlyData: Record<string, MonthlyCompletion> = {};
    const now = new Date();
    for (let i = 5; i >= 0; i--) {
      const date = new Date(now.getFullYear(), now.getMonth() - i, 1);
      const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
      monthlyData[key] = {
        month: date.toLocaleString('default', { month: 'short' }),
        year: date.getFullYear(),
        count: 0,
        label: date.toLocaleString('default', { month: 'short', year: '2-digit' }),
      };
    }
    completedCourses.forEach((course) => {
      if (!course.enrollment.completed_at) return;
      const completedDate = new Date(course.enrollment.completed_at);
      const key = `${completedDate.getFullYear()}-${String(completedDate.getMonth() + 1).padStart(2, '0')}`;
      if (monthlyData[key]) {
        monthlyData[key].count++;
      }
    });
    return Object.values(monthlyData);
  }, [courses]);

  /**
   * Wave 4: split filtered list into Required and Recommended.
   * Search/filter/sort apply uniformly to both sections — we filter+sort
   * once and partition by `enrollment.is_required` after.
   */
  const filteredCourses = useMemo(() => {
    if (!courses?.length) return [];
    let filtered = [...courses];
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(
        (c) =>
          c.course.title.toLowerCase().includes(query) ||
          c.course.description?.toLowerCase().includes(query),
      );
    }
    if (statusFilter !== 'all') {
      const now = new Date();
      const sevenDaysFromNow = new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000);
      filtered = filtered.filter((c) => {
        const status = getTrainingStatus(c);
        if (statusFilter === 'completed') return status === 'completed';
        if (statusFilter === 'in_progress') return status === 'in_progress' || status === 'overdue';
        if (statusFilter === 'not_started') return status === 'not_started';
        if (statusFilter === 'overdue') {
          if (c.enrollment.completed_at) return false;
          const dueDate = getDueDate(c.enrollment);
          return !!dueDate && dueDate < now;
        }
        if (statusFilter === 'due_soon') {
          if (c.enrollment.completed_at) return false;
          const dueDate = getDueDate(c.enrollment);
          return !!dueDate && dueDate >= now && dueDate <= sevenDaysFromNow;
        }
        return true;
      });
    }
    filtered.sort((a, b) => {
      let comparison = 0;
      switch (sortField) {
        case 'title':
          comparison = a.course.title.localeCompare(b.course.title);
          break;
        case 'progress':
          comparison = a.progress_percentage - b.progress_percentage;
          break;
        case 'enrolled_at':
          comparison =
            new Date(a.enrollment.enrolled_at).getTime() - new Date(b.enrollment.enrolled_at).getTime();
          break;
        case 'status':
          const statusOrder = { completed: 0, in_progress: 1, overdue: 2, not_started: 3 };
          comparison = statusOrder[getTrainingStatus(a)] - statusOrder[getTrainingStatus(b)];
          break;
      }
      return sortDirection === 'asc' ? comparison : -comparison;
    });
    return filtered;
  }, [courses, searchQuery, statusFilter, sortField, sortDirection]);

  const requiredCourses = useMemo(
    () => filteredCourses.filter((c) => c.enrollment.is_required),
    [filteredCourses],
  );
  const recommendedCourses = useMemo(
    () => filteredCourses.filter((c) => !c.enrollment.is_required),
    [filteredCourses],
  );

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDirection((prev) => (prev === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDirection('asc');
      }
    },
    [sortField],
  );

  const dismissAlert = useCallback((alertId: string) => {
    setDismissedAlerts((prev) => new Set([...prev, alertId]));
  }, []);

  const getStatusBadge = (course: CourseProgress) => {
    const status = getTrainingStatus(course);
    const styles = {
      completed: 'bg-lsc-cream dark:bg-lsc-brown/30 text-lsc-rose dark:text-lsc-cream/70',
      in_progress: 'bg-lsc-cream dark:bg-lsc-dark/30 text-lsc-rose dark:text-lsc-rose-light',
      not_started: 'bg-lsc-cream dark:bg-lsc-brown/50 text-lsc-dark/70 dark:text-lsc-cream/70',
      overdue: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
    };
    const labels = {
      completed: 'Completed',
      in_progress: 'In Progress',
      not_started: 'Not Started',
      overdue: 'Overdue',
    };
    return (
      <span className={clsx('px-2 py-1 rounded-full text-xs font-medium', styles[status])}>
        {labels[status]}
      </span>
    );
  };

  const isLoading = coursesLoading;
  const maxCount = Math.max(...completionTimeline.map((m) => m.count), 1);

  /**
   * Wave 4: shared table-head renderer so the Required and Recommended
   * sections render identical sortable headers and column widths. Sort
   * controls are shared (one set above both sections) — clicking on either
   * head toggles the same sortField/sortDirection state, so a sort applied
   * in one section is reflected in the other.
   */
  const renderTableHead = () => (
    <thead>
      <tr className="bg-lsc-cream dark:bg-lsc-brown/50">
        <SortableTh
          label="Training"
          sortKey="title"
          currentSort={sortField}
          currentDir={sortDirection}
          onSort={handleSort}
        />
        <SortableTh
          label="Status"
          sortKey="status"
          currentSort={sortField}
          currentDir={sortDirection}
          onSort={handleSort}
        />
        <SortableTh
          label="Progress"
          sortKey="progress"
          currentSort={sortField}
          currentDir={sortDirection}
          onSort={handleSort}
        />
        <SortableTh
          label="Enrolled"
          sortKey="enrolled_at"
          currentSort={sortField}
          currentDir={sortDirection}
          onSort={handleSort}
        />
        <th
          className="px-4 py-3 text-left text-sm font-medium text-lsc-dark/70 dark:text-lsc-cream/70"
          scope="col"
        >
          Due Date
        </th>
      </tr>
    </thead>
  );

  /**
   * Renders one section's table body. Empty section gets an inline
   * empty-state row of the same vertical footprint as a populated row,
   * so layout stays predictable for ND users.
   */
  const renderSectionBody = (
    rows: typeof filteredCourses,
    emptyText: string,
  ) => (
    <tbody className="divide-y divide-lsc-border dark:divide-earth-700">
      {isLoading ? (
        <tr>
          <td colSpan={5} className="px-4 py-12 text-center">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light mx-auto" />
          </td>
        </tr>
      ) : rows.length === 0 ? (
        <tr>
          <td
            colSpan={5}
            className="px-4 py-8 text-center text-lsc-dark/70 dark:text-lsc-cream/70"
          >
            <BookOpen aria-hidden="true" className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>{emptyText}</p>
          </td>
        </tr>
      ) : (
        rows.map((course) => (
          <CourseRow
            key={course.course.id}
            course={course}
            onOpen={(id) => navigate(`/learn/course/${id}`)}
            getStatusBadge={getStatusBadge}
          />
        ))
      )}
    </tbody>
  );

  return (
    <>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overall Completion</p>
              <p className="text-3xl font-bold text-lsc-rose dark:text-lsc-rose-light mt-1">
                {isLoading ? '-' : `${kpis.completionRate}%`}
              </p>
            </div>
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <TrendingUp aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          </div>
          <div className="mt-3 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden">
            <div
              className="h-full bg-lsc-rose dark:bg-sage-400 rounded-full transition-all duration-500"
              style={{ width: `${kpis.completionRate}%` }}
            />
          </div>
        </div>

        <button
          type="button"
          onClick={() => setStatusFilter(statusFilter === 'overdue' ? 'all' : 'overdue')}
          aria-pressed={statusFilter === 'overdue'}
          aria-label={`Filter by overdue training: ${kpis.overdueCount} ${kpis.overdueCount === 1 ? 'course' : 'courses'}`}
          className={clsx(
            'text-left bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose hover:border-lsc-rose dark:hover:border-lsc-rose-light',
            statusFilter === 'overdue'
              ? 'border-lsc-rose dark:border-lsc-rose-light ring-2 ring-lsc-rose/30'
              : 'border-lsc-border dark:border-earth-700',
          )}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Overdue</p>
              <p
                className={clsx(
                  'text-3xl font-bold mt-1',
                  kpis.overdueCount > 0 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark dark:text-lsc-cream',
                )}
              >
                {isLoading ? '-' : kpis.overdueCount}
              </p>
            </div>
            <div
              className={clsx(
                'w-10 h-10 rounded-xl flex items-center justify-center',
                kpis.overdueCount > 0 ? 'bg-status-danger-100 dark:bg-status-danger-900/30' : 'bg-lsc-cream dark:bg-lsc-brown',
              )}
            >
              <AlertTriangle
                aria-hidden="true"
                className={clsx(
                  'w-5 h-5',
                  kpis.overdueCount > 0 ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark/70 dark:text-lsc-cream/70',
                )}
              />
            </div>
          </div>
        </button>

        <button
          type="button"
          onClick={() => setStatusFilter(statusFilter === 'due_soon' ? 'all' : 'due_soon')}
          aria-pressed={statusFilter === 'due_soon'}
          aria-label={`Filter by due soon: ${kpis.dueSoonCount} ${kpis.dueSoonCount === 1 ? 'course' : 'courses'} due in 7 days`}
          className={clsx(
            'text-left bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose hover:border-lsc-rose dark:hover:border-lsc-rose-light',
            statusFilter === 'due_soon'
              ? 'border-lsc-rose dark:border-lsc-rose-light ring-2 ring-lsc-rose/30'
              : 'border-lsc-border dark:border-earth-700',
          )}
        >
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Due Soon (7 days)</p>
              <p
                className={clsx(
                  'text-3xl font-bold mt-1',
                  kpis.dueSoonCount > 0
                    ? 'text-lsc-rose dark:text-lsc-rose-light'
                    : 'text-lsc-dark dark:text-lsc-cream',
                )}
              >
                {isLoading ? '-' : kpis.dueSoonCount}
              </p>
            </div>
            <div
              className={clsx(
                'w-10 h-10 rounded-xl flex items-center justify-center',
                kpis.dueSoonCount > 0 ? 'bg-lsc-cream dark:bg-lsc-dark/30' : 'bg-lsc-cream dark:bg-lsc-brown',
              )}
            >
              <Clock
                aria-hidden="true"
                className={clsx(
                  'w-5 h-5',
                  kpis.dueSoonCount > 0
                    ? 'text-lsc-rose dark:text-lsc-rose-light'
                    : 'text-lsc-dark/70 dark:text-lsc-cream/70',
                )}
              />
            </div>
          </div>
        </button>

        <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-5 shadow-sm border border-lsc-border dark:border-earth-700">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Next Deadline</p>
              <p className="text-lg font-semibold text-lsc-dark dark:text-lsc-cream mt-1">
                {isLoading
                  ? '-'
                  : kpis.nextDeadline
                    ? kpis.nextDeadline.toLocaleDateString(getCurrentLocale(), { month: 'short', day: 'numeric' })
                    : 'No deadlines'}
              </p>
            </div>
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown rounded-xl flex items-center justify-center">
              <Calendar aria-hidden="true" className="w-5 h-5 text-lsc-dark/70 dark:text-lsc-cream/70" />
            </div>
          </div>
        </div>
      </div>

      {alerts.length > 0 && (
        <div className="space-y-3">
          <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2">
            <AlertTriangle aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            Action Required
          </h2>
          <div className="space-y-2">
            {alerts.map((alert) => (
              <div
                key={alert.id}
                className={clsx(
                  'flex items-center justify-between p-4 rounded-xl border',
                  alert.type === 'overdue'
                    ? 'bg-status-danger-50 dark:bg-status-danger-900/20 border-status-danger-200 dark:border-status-danger-800'
                    : 'bg-lsc-cream dark:bg-lsc-dark/20 border-lsc-border dark:border-earth-800',
                )}
              >
                <div className="flex items-center gap-3">
                  {alert.type === 'overdue' ? (
                    <AlertTriangle aria-hidden="true" className="w-5 h-5 text-status-danger-600 dark:text-status-danger-400" />
                  ) : (
                    <Clock aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
                  )}
                  <div>
                    <p
                      className={clsx(
                        'font-medium',
                        alert.type === 'overdue'
                          ? 'text-status-danger-800 dark:text-status-danger-200'
                          : 'text-lsc-dark dark:text-lsc-rose-light/50',
                      )}
                    >
                      {alert.courseTitle}
                    </p>
                    <p
                      className={clsx(
                        'text-sm',
                        alert.type === 'overdue'
                          ? 'text-status-danger-600 dark:text-status-danger-300'
                          : 'text-lsc-rose dark:text-lsc-rose-light',
                      )}
                    >
                      {alert.message}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => navigate(`/learn/course/${alert.courseId}`)}
                    className={clsx(
                      'px-3 py-1.5 text-sm font-medium rounded-xl transition-colors',
                      alert.type === 'overdue'
                        ? 'bg-status-danger-600 hover:bg-status-danger-700 text-white'
                        : 'bg-lsc-rose hover:bg-lsc-rose/90 text-white',
                    )}
                  >
                    Resume
                  </button>
                  <button
                    onClick={() => dismissAlert(alert.id)}
                    className="p-1.5 text-lsc-dark/70 dark:text-lsc-cream/70 hover:text-lsc-dark/70 dark:text-lsc-cream/70 dark:hover:text-lsc-cream rounded-xl hover:bg-lsc-cream dark:hover:bg-lsc-brown"
                    aria-label={t('aria.staff.dismissAlert')}
                  >
                    <X aria-hidden="true" className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/*
        Wave 4: shared search + filter controls apply to BOTH the Required
        and Recommended tables below. Sort state is also shared (clicking a
        column header in either table sorts both).
      */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden">
        <div className="p-4 border-b border-lsc-border dark:border-earth-700">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <input
                type="text"
                placeholder={t('placeholder.staffTrainingDashboard.searchTrainings')}
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label={t('aria.staffTrainingDashboard.searchTrainings')}
                className="w-full pl-10 pr-4 py-2 bg-lsc-cream dark:bg-lsc-brown border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream placeholder-earth-500 dark:placeholder-earth-500 focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              />
            </div>
            <div className="flex items-center gap-2">
              <label htmlFor="status-filter" className="sr-only">
                Filter by status
              </label>
              <Filter aria-hidden="true" className="w-4 h-4 text-lsc-dark/70 dark:text-lsc-cream/70" />
              <select
                id="status-filter"
                aria-label={t('aria.acquisition.filterByStatus')}
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
                className="px-3 py-2 bg-lsc-cream dark:bg-lsc-brown border border-lsc-border dark:border-earth-700 rounded-xl text-lsc-dark dark:text-lsc-cream focus:outline-none focus:ring-2 focus:ring-lsc-rose"
              >
                <option value="all">All Status</option>
                <option value="overdue">Overdue</option>
                <option value="due_soon">Due Soon (7 days)</option>
                <option value="completed">Completed</option>
                <option value="in_progress">In Progress</option>
                <option value="not_started">Not Started</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Required trainings section. Collapses to a single line when empty so
          ND users aren't scanning empty tables. */}
      {!isLoading && requiredCourses.length === 0 ? (
        <section
          aria-labelledby="required-trainings-heading"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center gap-2"
        >
          <AlertTriangle
            aria-hidden="true"
            className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400 flex-shrink-0"
          />
          <h2
            id="required-trainings-heading"
            className="font-serif text-sm font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            Required:
          </h2>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            No required training assigned.
          </span>
        </section>
      ) : (
        <section
          aria-labelledby="required-trainings-heading"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden"
        >
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 flex items-center gap-2">
            <AlertTriangle
              aria-hidden="true"
              className="w-4 h-4 text-status-danger-600 dark:text-status-danger-400"
            />
            <h2
              id="required-trainings-heading"
              className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              Required
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              {renderTableHead()}
              {renderSectionBody(
                requiredCourses,
                'No required training assigned.',
              )}
            </table>
          </div>
        </section>
      )}

      {/* Recommended trainings section. Collapses to a single line when empty;
          the message points users at the Available Courses card below. */}
      {!isLoading && recommendedCourses.length === 0 ? (
        <section
          aria-labelledby="recommended-trainings-heading"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 px-4 py-3 flex items-center gap-2"
        >
          <BookOpen
            aria-hidden="true"
            className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light flex-shrink-0"
          />
          <h2
            id="recommended-trainings-heading"
            className="font-serif text-sm font-semibold text-lsc-dark dark:text-lsc-cream"
          >
            Recommended:
          </h2>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
            No recommended training - browse Available Courses below.
          </span>
        </section>
      ) : (
        <section
          aria-labelledby="recommended-trainings-heading"
          className="bg-lsc-white dark:bg-earth-800 rounded-xl shadow-sm border border-lsc-border dark:border-earth-700 overflow-hidden"
        >
          <div className="px-4 py-3 border-b border-lsc-border dark:border-earth-700 flex items-center gap-2">
            <BookOpen
              aria-hidden="true"
              className="w-4 h-4 text-lsc-rose dark:text-lsc-rose-light"
            />
            <h2
              id="recommended-trainings-heading"
              className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream"
            >
              Recommended
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              {renderTableHead()}
              {renderSectionBody(
                recommendedCourses,
                'No recommended training enrolled.',
              )}
            </table>
          </div>
        </section>
      )}

      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
          <BarChart3 className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Completion Timeline
        </h2>
        {isLoading ? (
          <div className="h-32 flex items-center justify-center">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose dark:text-lsc-rose-light" />
          </div>
        ) : (
          <figure>
            <div
              role="img"
              aria-label={`Completion timeline: ${completionTimeline
                .map((m) => `${m.label}: ${m.count}`)
                .join(', ')}`}
              className="flex items-end justify-between gap-2 h-32"
            >
              {completionTimeline.map((month, index) => (
                <div key={index} className="flex-1 flex flex-col items-center">
                  <div
                    className="w-full max-w-[40px] bg-lsc-rose dark:bg-sage-400 rounded-t transition-all hover:bg-lsc-rose dark:hover:bg-sage-300"
                    style={{
                      height: month.count > 0 ? `${(month.count / maxCount) * 80 + 20}%` : '4px',
                      minHeight: month.count > 0 ? '20px' : '4px',
                    }}
                    title={`${month.count} completed`}
                  />
                  <p className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mt-2 text-center">{month.label}</p>
                  {month.count > 0 && (
                    <p className="text-xs font-medium text-lsc-rose dark:text-lsc-rose-light">{month.count}</p>
                  )}
                </div>
              ))}
            </div>
            <figcaption className="sr-only">
              <table>
                <caption>Modules completed per month</caption>
                <thead>
                  <tr>
                    <th scope="col">Month</th>
                    <th scope="col">Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {completionTimeline.map((month, index) => (
                    <tr key={index}>
                      <th scope="row">{month.label}</th>
                      <td>{month.count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </figcaption>
          </figure>
        )}
        {!isLoading && (
          <div className="mt-6 pt-4 border-t border-lsc-border dark:border-earth-700 grid grid-cols-3 gap-4 text-center">
            <div
              className="motion-safe:transition-opacity"
              aria-label={`Hours of training completed: ${stats.hoursLabel}`}
            >
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {stats.hoursLabel}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Hours of training completed
              </p>
            </div>
            <div
              className="motion-safe:transition-opacity"
              aria-label={
                certCountError
                  ? 'Certifications data unavailable'
                  : `Certifications earned: ${certCountDisplay}`
              }
            >
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {certCountDisplay}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                Certifications earned
              </p>
            </div>
            <div
              className="motion-safe:transition-opacity"
              aria-label={
                skillsSummaryError
                  ? 'Skills data unavailable'
                  : `Skills covered: ${skillsCoveredDisplay}`
              }
            >
              <p className="text-2xl font-bold text-lsc-rose dark:text-lsc-rose-light">
                {skillsCoveredDisplay}
              </p>
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">Skills covered</p>
            </div>
          </div>
        )}
      </div>

      {/* Available Courses */}
      <div className="bg-lsc-white dark:bg-earth-800 rounded-xl p-6 shadow-sm border border-lsc-border dark:border-earth-700">
        <h2 className="font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream flex items-center gap-2 mb-4">
          <GraduationCap aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
          Available Courses
        </h2>
        {allCoursesLoading ? (
          <div className="h-32 flex items-center justify-center">
            <Loader2 className="w-6 h-6 motion-safe:animate-spin text-lsc-rose" />
          </div>
        ) : availableCourses.length === 0 ? (
          <p className="text-lsc-dark/70 dark:text-lsc-cream/70 text-center py-8">
            {t('staffTrainingDashboard.youAreEnrolledInAll')}
          </p>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {availableCourses.map((course: CourseListItem) => (
              <div
                key={course.id}
                className="border border-lsc-border dark:border-earth-700 rounded-xl p-4 hover:border-earth-400 dark:hover:border-lsc-rose transition-colors"
              >
                <h3 className="font-medium text-lsc-dark dark:text-lsc-cream mb-2">{course.title}</h3>
                <p
                  className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 line-clamp-2 mb-3"
                  title={course.description || 'No description'}
                >
                  {course.description || 'No description'}
                </p>
                <div className="flex items-center justify-between text-xs text-lsc-dark/70 dark:text-lsc-cream/70 mb-3">
                  <span>{course.lesson_count} lessons</span>
                  <span>{course.estimated_minutes || 0} min</span>
                </div>
                <button
                  onClick={() => enrollMutation.mutate(course.id)}
                  disabled={enrollMutation.isPending}
                  className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-lsc-rose hover:bg-lsc-rose/90 disabled:bg-lsc-rose text-white rounded-xl font-medium text-sm transition-colors"
                >
                  <Plus aria-hidden="true" className="w-4 h-4" />
                  Enroll Now
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
