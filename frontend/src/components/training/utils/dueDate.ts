/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Training due-date helpers.
 *
 * Wave 1: swapped the simulated `enrolled_at + 30 days` shim for the real
 * configured deadline that the backend now stores on `Enrollment.due_at`.
 *
 * Semantics:
 *   - `due_at` is null when the course has no `duration_days` configured —
 *     i.e. there is no deadline, and the enrollment can never be "overdue".
 *   - `due_at` is a wall-clock instant (TIMESTAMP WITH TIME ZONE on the
 *     backend, ISO-8601 on the wire). All comparisons here are in that
 *     absolute timeline; we never re-derive due from enrolled_at.
 */
import type { CourseProgress } from '../api';

export type StatusFilter =
  | 'all'
  | 'completed'
  | 'in_progress'
  | 'not_started'
  | 'overdue'
  | 'due_soon';
export type SortField = 'title' | 'progress' | 'enrolled_at' | 'status';
export type SortDirection = 'asc' | 'desc';
export type TrainingTab = 'courses' | 'skills' | 'team';

export interface Alert {
  id: string;
  type: 'overdue' | 'due_soon';
  courseTitle: string;
  courseId: number;
  message: string;
  dueDate?: Date;
}

export interface MonthlyCompletion {
  month: string;
  year: number;
  count: number;
  label: string;
}

export function getDueDate(enrollment: { due_at: string | null }): Date | null {
  if (!enrollment?.due_at) return null;
  try {
    const d = new Date(enrollment.due_at);
    return Number.isNaN(d.getTime()) ? null : d;
  } catch (_err) {
    return null;
  }
}

export function getTrainingStatus(
  progress: CourseProgress,
): 'completed' | 'in_progress' | 'not_started' | 'overdue' {
  try {
    if (!progress?.enrollment) return 'not_started';
    if (progress.enrollment.completed_at) return 'completed';
    if (progress.progress_percentage > 0) {
      const dueDate = getDueDate(progress.enrollment);
      // No deadline configured -> can never be overdue.
      if (dueDate && new Date() > dueDate) return 'overdue';
      return 'in_progress';
    }
    return 'not_started';
  } catch (_err) {
    return 'not_started';
  }
}

export function getDaysUntilDue(enrollment: { due_at: string | null }): number | null {
  const dueDate = getDueDate(enrollment);
  if (!dueDate) return null;
  try {
    const now = new Date();
    return Math.ceil((dueDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  } catch (_err) {
    return null;
  }
}
