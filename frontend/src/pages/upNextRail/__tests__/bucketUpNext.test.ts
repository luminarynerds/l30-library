/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Pure-function tests for the Up Next rail bucketing helper.
 *
 * Notes:
 *   - `now` is injected so we don't depend on system clock or fake timers.
 *   - Datetime strings are local-naive ISO (no Z suffix) so parseDate treats
 *     them as local time and the assertions are timezone-stable.
 *   - Fixtures use the dashboard SUMMARY shapes the backend actually sends
 *     (ParentOnboardingSessionSummary / CareAssignmentSummary /
 *     ParentHomeVisitSummary). Owner scoping: `staff_id` for sessions,
 *     `coordinator_id` for assignments, `visitor_id` for visits.
 *   - `staff_id`/`visitor_id` are optional-and-never-auto-assigned at
 *     creation (unassigned is the common case, not an edge case), so null
 *     there is visible to every coordinator's rail, not excluded from it.
 *     `coordinator_id` is required at assignment creation, so it stays
 *     strict -- see the scoping comment atop bucketUpNext.ts.
 */
import { describe, it, expect } from 'vitest'
import { bucketUpNext } from '../bucketUpNext'
import type {
  ParentOnboardingDashboard,
  ParentOnboardingSessionSummary,
  CareAssignmentSummary,
  ParentHomeVisitSummary,
} from '@/api/parent-onboarding-api'

const ME = 200
const OTHER = 201

// 2026-05-25 is the "today" we anchor every fixture against.
const NOW = new Date('2026-05-25T10:00:00')

function emptyDashboard(): ParentOnboardingDashboard {
  return {
    active_families: 0,
    upcoming_sessions: 0,
    overdue_check_ins: 0,
    active_childcare_sessions: 0,
    active_connection_groups: 0,
    pending_enrollments: 0,
    upcoming_home_visits: 0,
    recent_sessions: [],
    overdue_assignments: [],
    upcoming_visits: [],
  }
}

function session(
  overrides: Partial<ParentOnboardingSessionSummary> & { id: number },
): ParentOnboardingSessionSummary {
  return {
    patron_id: 1,
    patron_name: 'Test Patron',
    staff_id: ME,
    status: 'scheduled',
    scheduled_date: '2026-05-25T10:00:00',
    ...overrides,
  }
}

function assignment(
  overrides: Partial<CareAssignmentSummary> & { id: number },
): CareAssignmentSummary {
  return {
    patron_id: 1,
    patron_name: 'Test Patron',
    coordinator_id: ME,
    risk_level: 'medium',
    ...overrides,
  }
}

function visit(
  overrides: Partial<ParentHomeVisitSummary> & { id: number },
): ParentHomeVisitSummary {
  return {
    patron_id: 1,
    patron_name: 'Test Patron',
    visitor_id: ME,
    purpose: 'check_in',
    status: 'scheduled',
    scheduled_date: '2026-05-25',
    ...overrides,
  }
}

describe('bucketUpNext', () => {
  it('places each entity type into the correct bucket based on date', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, scheduled_date: '2026-05-25T10:00:00' }), // today
        session({ id: 2, scheduled_date: '2026-05-22T10:00:00' }), // overdue
        session({ id: 3, scheduled_date: '2026-05-28T10:00:00' }), // this week
      ],
      overdue_assignments: [
        assignment({ id: 10, next_check_in_due: '2026-05-25' }), // today
        assignment({ id: 11, next_check_in_due: '2026-05-20' }), // overdue
      ],
      upcoming_visits: [
        visit({ id: 20, scheduled_date: '2026-05-26' }), // this week
        visit({ id: 21, scheduled_date: '2026-05-25' }), // today
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })

    expect(buckets.overdue.map((i) => i.key)).toEqual(['assignment:11', 'session:2'])
    expect(buckets.today.map((i) => i.key).sort()).toEqual([
      'assignment:10',
      'session:1',
      'visit:21',
    ])
    expect(buckets.thisWeek.map((i) => i.key)).toEqual(['visit:20', 'session:3'])
  })

  it('scopes sessions by staff_id, assignments by coordinator_id, visits by visitor_id', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, staff_id: ME, scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 2, staff_id: OTHER, scheduled_date: '2026-05-25T10:00:00' }),
        // Unassigned sessions (staff_id null) are visible on every
        // coordinator's rail, not just their own -- see file-level note.
        session({ id: 3, staff_id: null, scheduled_date: '2026-05-25T10:00:00' }),
      ],
      overdue_assignments: [
        assignment({ id: 10, coordinator_id: ME, next_check_in_due: '2026-05-20' }),
        assignment({ id: 11, coordinator_id: OTHER, next_check_in_due: '2026-05-20' }),
      ],
      upcoming_visits: [
        visit({ id: 20, visitor_id: ME, scheduled_date: '2026-05-26' }),
        visit({ id: 21, visitor_id: OTHER, scheduled_date: '2026-05-26' }),
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })

    expect(buckets.overdue.map((i) => i.key)).toEqual(['assignment:10'])
    expect(buckets.today.map((i) => i.key).sort()).toEqual(['session:1', 'session:3'])
    expect(buckets.thisWeek.map((i) => i.key)).toEqual(['visit:20'])
  })

  it('keeps unassigned sessions and visits visible to every coordinator, but stays strict for assignments', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, staff_id: null, scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 2, staff_id: OTHER, scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 3, staff_id: ME, scheduled_date: '2026-05-25T10:00:00' }),
      ],
      overdue_assignments: [
        // coordinator_id is required at creation; a null here isn't the
        // common "not yet assigned" case, so it stays excluded, not shown.
        assignment({ id: 10, coordinator_id: null, next_check_in_due: '2026-05-20' }),
      ],
      upcoming_visits: [
        visit({ id: 20, visitor_id: null, scheduled_date: '2026-05-25' }),
        visit({ id: 21, visitor_id: OTHER, scheduled_date: '2026-05-25' }),
        visit({ id: 22, visitor_id: ME, scheduled_date: '2026-05-25' }),
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })

    expect(buckets.today.map((i) => i.key).sort()).toEqual([
      'session:1',
      'session:3',
      'visit:20',
      'visit:22',
    ])
    expect(buckets.overdue).toEqual([])
  })

  it('populates the rail from a payload shaped exactly like the backend dashboard (regression: rail was always empty)', () => {
    // Mirrors ParentOnboardingDashboardService.get_dashboard()'s dict shape.
    // Before the staff_id/coordinator_id/visitor_id fields existed on the
    // summaries, every filter compared against undefined and dropped
    // EVERYTHING - the rail rendered empty for every coordinator, always.
    const dashboard: ParentOnboardingDashboard = {
      active_families: 3,
      upcoming_sessions: 1,
      overdue_check_ins: 1,
      active_childcare_sessions: 0,
      active_connection_groups: 2,
      pending_enrollments: 0,
      upcoming_home_visits: 1,
      recent_sessions: [
        {
          id: 42,
          patron_id: 7,
          patron_name: 'Jordan Reyes',
          staff_id: ME,
          scheduled_date: '2026-05-25T15:30:00',
          status: 'scheduled',
        },
      ],
      overdue_assignments: [
        {
          id: 9,
          patron_id: 8,
          patron_name: 'Sam Okafor',
          coordinator_id: ME,
          next_check_in_due: '2026-05-21',
          risk_level: 'high',
        },
      ],
      upcoming_visits: [
        {
          id: 5,
          patron_id: 9,
          patron_name: 'Ada Lin',
          visitor_id: ME,
          visitor_name: 'Me Myself',
          scheduled_date: '2026-05-27',
          scheduled_time: '11:00',
          purpose: 'check_in',
          status: 'confirmed',
        },
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.overdue.map((i) => i.key)).toEqual(['assignment:9'])
    expect(buckets.today.map((i) => i.key)).toEqual(['session:42'])
    expect(buckets.today[0]?.time).toBe('15:30')
    expect(buckets.thisWeek.map((i) => i.key)).toEqual(['visit:5'])
  })

  it('returns empty buckets when nothing matches', () => {
    const buckets = bucketUpNext(emptyDashboard(), { currentUserId: ME, now: NOW })
    expect(buckets.overdue).toEqual([])
    expect(buckets.today).toEqual([])
    expect(buckets.thisWeek).toEqual([])
  })

  it('sorts within Today by the datetime-derived time ascending; untimed assignments last', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, scheduled_date: '2026-05-25T14:00:00' }),
        session({ id: 2, scheduled_date: '2026-05-25T09:30:00' }),
      ],
      overdue_assignments: [
        // Assignments carry no time-of-day; they sort after timed items.
        assignment({ id: 3, next_check_in_due: '2026-05-25' }),
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.today.map((i) => i.key)).toEqual(['session:2', 'session:1', 'assignment:3'])
  })

  it('uses stable tiebreaker on identical sortKey so order is deterministic across re-renders', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 5, scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 3, scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 9, scheduled_date: '2026-05-25T10:00:00' }),
      ],
    }

    const first = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    const second = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    // localeCompare on 'session:3' < 'session:5' < 'session:9'
    expect(first.today.map((i) => i.key)).toEqual(['session:3', 'session:5', 'session:9'])
    expect(second.today.map((i) => i.key)).toEqual(first.today.map((i) => i.key))
  })

  it('drops completed / cancelled / no_show sessions and visits from the rail', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, status: 'completed', scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 2, status: 'cancelled', scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 3, status: 'no_show', scheduled_date: '2026-05-25T10:00:00' }),
        session({ id: 4, status: 'scheduled', scheduled_date: '2026-05-25T10:00:00' }),
      ],
      upcoming_visits: [
        visit({ id: 10, status: 'completed', scheduled_date: '2026-05-25' }),
        visit({ id: 11, status: 'scheduled', scheduled_date: '2026-05-25' }),
      ],
    }

    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.today.map((i) => i.key).sort()).toEqual(['session:4', 'visit:11'])
  })

  it('drops items more than 7 days out (not actionable from Up Next)', () => {
    // today = 2026-05-25; +7 days = 2026-06-01 (included), +8 = 2026-06-02 (excluded)
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({ id: 1, scheduled_date: '2026-06-15T10:00:00' }), // far future
        session({ id: 2, scheduled_date: '2026-06-02T10:00:00' }), // day 8
        session({ id: 3, scheduled_date: '2026-06-01T10:00:00' }), // day 7 - included
      ],
    }
    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.overdue).toEqual([])
    expect(buckets.today).toEqual([])
    expect(buckets.thisWeek.map((i) => i.key)).toEqual(['session:3'])
  })

  it('skips assignments without a next_check_in_due date', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      overdue_assignments: [
        assignment({ id: 1, next_check_in_due: undefined }),
        assignment({ id: 2, next_check_in_due: '2026-05-25' }),
      ],
    }
    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.today.map((i) => i.key)).toEqual(['assignment:2'])
  })

  it('falls back to "Patron #<id>" when patron_name is missing', () => {
    const dashboard: ParentOnboardingDashboard = {
      ...emptyDashboard(),
      recent_sessions: [
        session({
          id: 1,
          patron_id: 99,
          patron_name: undefined,
          scheduled_date: '2026-05-25T10:00:00',
        }),
      ],
    }
    const buckets = bucketUpNext(dashboard, { currentUserId: ME, now: NOW })
    expect(buckets.today[0]?.patronName).toBe('Patron #99')
  })
})
