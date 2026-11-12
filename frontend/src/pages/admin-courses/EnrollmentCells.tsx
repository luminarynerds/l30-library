/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { Users } from 'lucide-react';
import type { CourseListItemAdmin } from '@/api/domains/learning/courses-api';

// Desktop enrollment cell: "X/Y" plus a 5-segment progress bar and an
// "{n} in progress" sub-line. Empty courses show a single em-dash.
export function EnrollmentCell({
  course,
  t,
}: {
  course: CourseListItemAdmin;
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string;
}) {
  if (course.enrollment_count === 0) {
    return (
      <span className="text-sm text-lsc-dark/50 dark:text-lsc-cream/50">
        {t('admin.adminCourses.enrollmentNone')}
      </span>
    );
  }
  const pct = course.enrollment_count
    ? Math.round((course.completion_count / course.enrollment_count) * 100)
    : 0;
  const filledSegments = Math.round((pct / 100) * 5);
  return (
    <div className="text-sm">
      <div className="flex items-center gap-2 text-lsc-dark dark:text-lsc-cream">
        <span className="font-medium tabular-nums">
          {course.completion_count}/{course.enrollment_count}
        </span>
        <span
          aria-hidden="true"
          className="inline-flex items-center gap-0.5"
          title={`${pct}%`}
        >
          {[0, 1, 2, 3, 4].map((i) => (
            <span
              key={i}
              className={`
                inline-block w-1.5 h-3 rounded-sm
                ${
                  i < filledSegments
                    ? 'bg-status-success-500 dark:bg-status-success-400'
                    : 'bg-lsc-border dark:bg-earth-600'
                }
              `}
            />
          ))}
        </span>
      </div>
      <div className="text-xs text-lsc-dark/60 dark:text-lsc-cream/60 mt-0.5">
        {t('admin.adminCourses.enrollmentInProgress', { count: course.in_progress_count })}
      </div>
    </div>
  );
}

// Mobile single-line variant: "<icon> X enrolled · Y% complete" or em-dash.
export function EnrollmentMobileLine({
  course,
  t,
}: {
  course: CourseListItemAdmin;
  t: (key: string, paramsOrFallback?: Record<string, unknown> | string) => string;
}) {
  if (course.enrollment_count === 0) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <Users className="w-4 h-4" aria-hidden="true" />
        {t('admin.adminCourses.enrollmentNone')}
      </span>
    );
  }
  const pct = Math.round((course.completion_count / course.enrollment_count) * 100);
  return (
    <span className="inline-flex items-center gap-1.5">
      <Users className="w-4 h-4" aria-hidden="true" />
      {t('admin.adminCourses.enrollmentMobile', {
        enrolled: course.enrollment_count,
        percent: pct,
      })}
    </span>
  );
}
