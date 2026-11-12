/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CourseRow - Single training table row.
 *
 * Extracted so future waves (4 + 5) can add badges / chips without touching
 * the surrounding CoursesTab. Uses `role="link"` per the existing markup; per
 * ARIA spec, links activate on Enter only (not Space), so we keep Enter-only
 * keyboard handling here intentionally.
 *
 * Wave 1: due-date column now reads the real `enrollment.due_at` and renders
 * "No deadline" predictably (same column width, no layout shift) when the
 * course has no configured `duration_days`. Date cells use `<time dateTime>`
 * with full plain-language `aria-label` so screen readers + crawlers don't
 * have to parse "5/12/26" or rely on red text alone for overdue state.
 */
import React from 'react';
import clsx from 'clsx';
import { AlertCircle, BookOpen, CheckCircle2 } from 'lucide-react';
import type { CourseProgress } from '../api';
import { CourseSkillChips } from '../CourseSkillChips';
import { getDueDate } from '../utils/dueDate';
import { getCurrentLocale } from '@/i18n'

export interface CourseRowProps {
  course: CourseProgress;
  onOpen: (id: number) => void;
  getStatusBadge: (course: CourseProgress) => React.ReactNode;
}

const FULL_DATE_FORMAT: Intl.DateTimeFormatOptions = {
  weekday: 'long',
  month: 'long',
  day: 'numeric',
};

const SHORT_DATE_FORMAT: Intl.DateTimeFormatOptions = {
  weekday: 'short',
  month: 'short',
  day: 'numeric',
};

export function CourseRow({ course, onOpen, getStatusBadge }: CourseRowProps): React.ReactElement {
  const dueDate = getDueDate(course.enrollment);
  const isCompleted = !!course.enrollment.completed_at;
  const courseId = course.course.id;
  const isOverdue = !!dueDate && !isCompleted && dueDate < new Date();
  const overdueDays = isOverdue && dueDate
    ? Math.ceil((new Date().getTime() - dueDate.getTime()) / (1000 * 60 * 60 * 24))
    : 0;

  let dueCell: React.ReactNode;
  if (isCompleted) {
    dueCell = (
      <span className="flex items-center gap-1 text-lsc-rose dark:text-lsc-rose-light">
        <CheckCircle2 aria-hidden="true" className="w-4 h-4" />
        Done
      </span>
    );
  } else if (dueDate) {
    const fullLabel = dueDate.toLocaleDateString(getCurrentLocale(), FULL_DATE_FORMAT);
    const shortLabel = dueDate.toLocaleDateString(getCurrentLocale(), SHORT_DATE_FORMAT);
    const ariaLabel = isOverdue
      ? `Overdue by ${overdueDays} day${overdueDays !== 1 ? 's' : ''}, was due ${fullLabel}, ${course.course.title}`
      : `Due ${fullLabel}`;
    dueCell = (
      <time
        dateTime={dueDate.toISOString()}
        aria-label={ariaLabel}
        className={clsx(
          isOverdue ? 'text-status-danger-600 dark:text-status-danger-400' : 'text-lsc-dark/70 dark:text-lsc-cream/70',
        )}
      >
        Due {shortLabel}
      </time>
    );
  } else {
    dueCell = (
      <span
        aria-label="No deadline set"
        className="text-lsc-dark/70 dark:text-lsc-cream/70"
      >
        No deadline
      </span>
    );
  }

  return (
    <tr
      className="hover:bg-lsc-cream dark:hover:bg-lsc-brown/50 cursor-pointer transition-colors"
      onClick={() => onOpen(courseId)}
      onKeyDown={(e) => {
        if (e.key === 'Enter') onOpen(courseId);
      }}
      tabIndex={0}
      role="link"
      aria-label={`Open training: ${course.course.title}`}
    >
      <td className="px-4 py-4">
        <div className="flex items-center gap-3">
          {course.course.thumbnail_url ? (
            <img
              src={course.course.thumbnail_url}
              alt={`Thumbnail for ${course.course.title}`}
              className="w-10 h-10 rounded-xl object-cover"
            />
          ) : (
            <div className="w-10 h-10 bg-lsc-cream dark:bg-lsc-brown/30 rounded-xl flex items-center justify-center">
              <BookOpen aria-hidden="true" className="w-5 h-5 text-lsc-rose dark:text-lsc-rose-light" />
            </div>
          )}
          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <p className="font-medium text-lsc-dark dark:text-lsc-cream">{course.course.title}</p>
              {course.enrollment.is_required && (
                /*
                 * Wave 4: Required badge. Icon + text — never colour alone
                 * (WCAG 1.4.1). The section landmark already conveys
                 * "Required" for screen-reader skim, so the aria-label here
                 * just labels the badge itself.
                 */
                <span
                  aria-label="Required training"
                  className="inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-medium bg-status-danger-100 text-status-danger-700 dark:bg-status-danger-900/30 dark:text-status-danger-300"
                >
                  <AlertCircle aria-hidden="true" className="w-3.5 h-3.5" />
                  Required
                </span>
              )}
            </div>
            {/*
             * Wave 5: skill chips for this course. Visual-only inside the
             * table row — the row itself is `role="link"`, so a button
             * inside would create nested interactives. Deeper navigation
             * lives on the Skills tab disclosure instead.
             */}
            <CourseSkillChips
              skills={course.course.skills ?? []}
              className="mt-1"
            />
            {course.course.estimated_minutes && (
              <p className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
                ~{course.course.estimated_minutes} min
              </p>
            )}
          </div>
        </div>
      </td>
      <td className="px-4 py-4">{getStatusBadge(course)}</td>
      <td className="px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-lsc-cream dark:bg-lsc-brown rounded-full overflow-hidden max-w-[100px]">
            <div
              className={clsx(
                'h-full rounded-full transition-all',
                isCompleted ? 'bg-lsc-rose dark:bg-sage-400' : 'bg-lsc-rose dark:bg-lsc-rose-light',
              )}
              style={{ width: `${course.progress_percentage}%` }}
            />
          </div>
          <span className="text-sm text-lsc-dark/70 dark:text-lsc-cream/70 w-10">
            {course.progress_percentage}%
          </span>
        </div>
      </td>
      <td className="px-4 py-4 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
        <time dateTime={course.enrollment.enrolled_at}>
          {new Date(course.enrollment.enrolled_at).toLocaleDateString()}
        </time>
      </td>
      <td className="px-4 py-4 text-sm">{dueCell}</td>
    </tr>
  );
}
