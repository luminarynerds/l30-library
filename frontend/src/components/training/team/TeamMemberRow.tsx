/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TeamMemberRow - one row in the manager's Team tab table.
 *
 * Extracted from TeamTab so Wave 4 (assign-training workflow) can drop in an
 * "Assign training" button by adding a single optional `onAssignClick` prop
 * without having to touch TeamTab's table structure.
 *
 * A11y notes:
 *   - Numeric cells with stakes (overdue / due-soon) get an explicit
 *     `aria-label` that includes the user's name + the metric, so a screen
 *     reader announces "Marie Smith: 3 courses overdue" instead of just "3".
 *   - Status badges combine icon + text — never colour alone (WCAG 1.4.1).
 */
import React from 'react';
import { AlertTriangle, Clock, CheckCircle2 } from 'lucide-react';
import type { TeamMemberProgress } from '../api';

export interface TeamMemberRowProps {
  member: TeamMemberProgress;
  /**
   * Reserved for Wave 4 (assign workflow). When provided, a row-level
   * "Assign training" button is rendered. Wave 2 callers leave this undefined.
   */
  onAssignClick?: (member: TeamMemberProgress) => void;
}

export function TeamMemberRow({
  member,
  onAssignClick,
}: TeamMemberRowProps): React.ReactElement {
  const {
    name,
    email,
    courses_total,
    courses_completed,
    overdue_count,
    due_soon_count,
    completion_rate,
  } = member;

  const overdueLabel = `${name}: ${overdue_count} ${
    overdue_count === 1 ? 'course' : 'courses'
  } overdue`;
  const dueSoonLabel = `${name}: ${due_soon_count} ${
    due_soon_count === 1 ? 'course' : 'courses'
  } due soon`;
  const progressLabel = `${name}: ${courses_completed} of ${courses_total} ${
    courses_total === 1 ? 'course' : 'courses'
  } completed (${completion_rate.toFixed(0)} percent)`;

  return (
    <tr className="border-b border-lsc-border dark:border-earth-700 last:border-b-0 focus-within:bg-lsc-cream/40 dark:focus-within:bg-earth-700/40">
      <th
        scope="row"
        className="px-4 py-3 text-left font-normal text-lsc-dark dark:text-lsc-cream align-top"
      >
        <div className="font-medium">{name}</div>
        <div className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 break-all">
          {email}
        </div>
      </th>

      <td
        className="px-4 py-3 text-lsc-dark dark:text-lsc-cream"
        aria-label={progressLabel}
      >
        <div className="flex items-center gap-2">
          <span className="font-medium tabular-nums">
            {courses_completed} / {courses_total}
          </span>
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70 tabular-nums">
            ({completion_rate.toFixed(0)}%)
          </span>
        </div>
        <div
          className="mt-1 h-1.5 w-32 max-w-full bg-lsc-cream dark:bg-earth-700 rounded-full overflow-hidden"
          aria-hidden="true"
        >
          <div
            className="h-full bg-lsc-rose"
            style={{ width: `${Math.min(100, Math.max(0, completion_rate))}%` }}
          />
        </div>
      </td>

      <td className="px-4 py-3">
        {overdue_count > 0 ? (
          <span
            className="inline-flex items-center gap-1 rounded-full bg-status-danger-100 dark:bg-status-danger-900/40 text-status-danger-800 dark:text-status-danger-200 px-2.5 py-1 text-xs font-medium"
            aria-label={overdueLabel}
          >
            <AlertTriangle aria-hidden="true" className="w-3.5 h-3.5" />
            Overdue: {overdue_count}
          </span>
        ) : (
          <span className="inline-flex items-center gap-1 text-xs text-lsc-dark/70 dark:text-lsc-cream/70">
            <CheckCircle2 aria-hidden="true" className="w-3.5 h-3.5" />
            None
          </span>
        )}
      </td>

      <td className="px-4 py-3">
        {due_soon_count > 0 ? (
          <span
            className="inline-flex items-center gap-1 rounded-full bg-lsc-rose/15 dark:bg-lsc-rose/25 text-lsc-rose dark:text-lsc-cream px-2.5 py-1 text-xs font-medium"
            aria-label={dueSoonLabel}
          >
            <Clock aria-hidden="true" className="w-3.5 h-3.5" />
            Due soon: {due_soon_count}
          </span>
        ) : (
          <span className="text-xs text-lsc-dark/70 dark:text-lsc-cream/70">—</span>
        )}
      </td>

      {onAssignClick ? (
        <td className="px-4 py-3 text-right">
          <button
            type="button"
            onClick={() => onAssignClick(member)}
            aria-label={`Assign training to ${name}`}
            className="bg-lsc-rose hover:bg-lsc-rose/90 text-white rounded-lg px-3 py-1.5 text-sm font-medium focus:outline-none focus:ring-2 focus:ring-lsc-rose focus:ring-offset-2"
          >
            Assign training
          </button>
        </td>
      ) : null}
    </tr>
  );
}
