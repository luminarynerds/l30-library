/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * TeamTab — manager view of direct reports' training progress.
 *
 * Wave 2: read-only table. Wave 4 will wire `TeamMemberRow.onAssignClick` to
 * an "Assign training" workflow without changes here.
 *
 * Data source: GET /api/v1/learning/team/progress, which reuses
 * StaffOnboarding.manager_id to find reports (no users.manager_id column).
 *
 * The Team tab is hidden entirely for non-managers (handled in
 * StaffTrainingDashboard) — predictable layout for ND users.
 */
import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Users } from 'lucide-react';
import { trainingApi, type TeamMemberProgress } from '../api';
import { TeamMemberRow } from '../team/TeamMemberRow';
import { AssignCourseModal } from '../team/AssignCourseModal';

export function TeamTab(): React.ReactElement {
  const queryClient = useQueryClient();
  /**
   * Wave 4: opening the AssignCourseModal stashes the target member here.
   * Modal `isOpen` is derived from this being non-null, so closing the
   * modal naturally clears the selection — single source of truth.
   */
  const [selectedMember, setSelectedMember] =
    useState<TeamMemberProgress | null>(null);

  const {
    data: members = [],
    isLoading,
    isError,
    error,
  } = useQuery<TeamMemberProgress[]>({
    queryKey: ['team-progress'],
    queryFn: () => trainingApi.getTeamProgress(),
    retry: 1,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[240px]">
        <Loader2
          aria-hidden="true"
          className="w-8 h-8 motion-safe:animate-spin text-lsc-rose"
        />
        <span className="sr-only">Loading your team's training progress</span>
      </div>
    );
  }

  if (isError) {
    const message =
      error instanceof Error
        ? error.message
        : "We couldn't load your team's training progress. Please try again in a moment.";
    return (
      <div
        role="alert"
        className="rounded-xl border border-status-danger-300 dark:border-status-danger-800 bg-lsc-white dark:bg-earth-800 p-4 text-lsc-dark dark:text-lsc-cream"
      >
        <p className="font-serif text-lg font-semibold">
          Couldn't load team progress
        </p>
        <p className="mt-1 text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          {message}
        </p>
      </div>
    );
  }

  if (members.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center text-center py-12 px-4">
        <Users
          aria-hidden="true"
          className="w-12 h-12 opacity-50 text-lsc-dark dark:text-lsc-cream"
        />
        <h2 className="mt-3 font-serif text-lg font-semibold text-lsc-dark dark:text-lsc-cream">
          No direct reports
        </h2>
        <p className="mt-1 max-w-md text-sm text-lsc-dark/70 dark:text-lsc-cream/70">
          Ask your admin to update your onboarding profile to link reports to you.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 overflow-hidden">
      {/*
        aria-live region announces the result count to AT users. Browsers
        only re-announce when the text content changes, so refetches that
        return the same N do not re-announce — no per-render dedup needed.
      */}
      <p className="sr-only" role="status" aria-live="polite">
        Showing {members.length}{' '}
        {members.length === 1 ? 'direct report' : 'direct reports'}.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <caption className="sr-only">
            Direct reports' training progress
          </caption>
          <thead className="bg-lsc-cream/60 dark:bg-earth-900/40 text-left">
            <tr>
              <th
                scope="col"
                className="px-4 py-2 font-serif text-xs uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                Team member
              </th>
              <th
                scope="col"
                className="px-4 py-2 font-serif text-xs uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                Courses completed
              </th>
              <th
                scope="col"
                className="px-4 py-2 font-serif text-xs uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                Overdue
              </th>
              <th
                scope="col"
                className="px-4 py-2 font-serif text-xs uppercase tracking-wide text-lsc-dark/70 dark:text-lsc-cream/70"
              >
                Due soon
              </th>
              {/*
                Wave 4: per-row "Assign training" actions column. Header
                visually hidden — the per-row buttons carry their own
                contextual aria-label ("Assign training to {name}").
              */}
              <th scope="col" className="px-4 py-2">
                <span className="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {members.map((member) => (
              <TeamMemberRow
                key={member.user_id}
                member={member}
                onAssignClick={setSelectedMember}
              />
            ))}
          </tbody>
        </table>
      </div>

      <AssignCourseModal
        isOpen={selectedMember !== null}
        member={selectedMember}
        onClose={() => setSelectedMember(null)}
        onSuccess={() => {
          // Invalidate so counts (overdue / due_soon / total) reflect the
          // freshly assigned enrollment. The modal closes itself.
          queryClient.invalidateQueries({ queryKey: ['team-progress'] });
        }}
      />
    </div>
  );
}
