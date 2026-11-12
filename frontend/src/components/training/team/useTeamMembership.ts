/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * useTeamMembership - small hook the dashboard shell uses to decide whether
 * to surface the Team tab.
 *
 * Returns:
 *   - hasReports: true when the current staff user manages at least one
 *     report (StaffOnboarding.manager_id == current_user.id).
 *   - isLoading: true while the underlying query is in-flight.
 *
 * The query is shared (same `['team-progress']` key as TeamTab), so opening
 * the tab does not re-fetch.
 */
import { useQuery } from '@tanstack/react-query';
import { trainingApi, type TeamMemberProgress } from '../api';

export function useTeamMembership(enabled: boolean = true): {
  hasReports: boolean;
  isLoading: boolean;
} {
  const { data, isLoading } = useQuery<TeamMemberProgress[]>({
    queryKey: ['team-progress'],
    queryFn: () => trainingApi.getTeamProgress(),
    enabled,
    retry: 1,
    // 5-minute freshness — tab visibility doesn't change often, and we don't
    // want to flicker the tab in/out as users navigate.
    staleTime: 5 * 60 * 1000,
  });

  return {
    hasReports: Array.isArray(data) && data.length > 0,
    isLoading,
  };
}
