/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 *
 * Up Next rail bucketing helper.
 *
 * Takes the existing parent-onboarding dashboard payload, filters it to the
 * signed-in coordinator, normalises the three entity types onto a single
 * shape, and buckets them into Overdue / Today / This Week.
 *
 * Pure function: `now` is injectable so tests don't need fake timers and so
 * we can document the timezone choice in one place (browser-local day,
 * resolved via the page's existing `parseDate` helper plus en-CA locale to
 * get an ISO YYYY-MM-DD key).
 *
 * Coordinator scoping (open question 4 in the spec), by the OWNER column each
 * summary actually carries (see the Summary schemas in
 * backend/app/schemas/parent_onboarding.py):
 *   - sessions: included when `staff_id == currentUserId` OR `staff_id` is
 *     null/unassigned. `ParentOnboardingSessionCreate.staff_id` is optional
 *     and never auto-assigned to the creating staffer, so unassigned is the
 *     common case, not an edge case -- treating it as excluded would empty
 *     the rail for everyone all over again, just one field later.
 *   - assignments: included when `coordinator_id == currentUserId`, strict.
 *     `CareCoordinatorAssignmentCreate.coordinator_id` is required, so every
 *     assignment has an owner from creation; it only ever goes null via the
 *     FK's `ON DELETE SET NULL` when that staff account is deleted, which
 *     isn't a case where "show it to everyone" is the right fallback.
 *   - visits: included when `visitor_id == currentUserId` OR `visitor_id` is
 *     null/unassigned, same reasoning as sessions --
 *     `ParentHomeVisitCreate.visitor_id` is optional and never auto-assigned.
 *
 * Visits where `visitor_id != coordinator_id` cannot be cross-listed onto the
 * coordinator's rail without a backend lookup (ParentHomeVisit has no
 * `coordinator_id`). Deferred to v2.
 */
import type {
  ParentOnboardingDashboard,
  ParentOnboardingSessionSummary,
  CareAssignmentSummary,
  ParentHomeVisitSummary,
  RiskLevel,
} from '@/api/parent-onboarding-api'
import { parseDate } from '@/utils/format-utils'

export type RailEntity = 'session' | 'assignment' | 'visit'

export interface RailItem {
  /** Globally-unique key combining entity + numeric id so React keys never collide. */
  key: string
  entity: RailEntity
  patronId: number
  patronName: string
  /** YYYY-MM-DD in browser-local time, used for bucketing. */
  date: string
  /** Optional HH:MM time string. Sessions/visits carry it; assignments do not. */
  time?: string
  /** Detail-route path. */
  link: string
  /** Lowercase status, e.g. 'scheduled', 'completed'. Undefined for assignments. */
  status?: string
  /** Risk level for assignments only. */
  riskLevel?: RiskLevel
  /** Visit purpose for visits only (e.g. 'intake'). */
  visitPurpose?: string
  /** Lower numbers sort earlier within a bucket. Untimed items go last. */
  sortKey: number
}

export interface UpNextBuckets {
  overdue: RailItem[]
  today: RailItem[]
  thisWeek: RailItem[]
}

const COMPLETED_STATUSES = new Set(['completed', 'cancelled', 'no_show'])

function localISODate(d: Date): string {
  return d.toLocaleDateString('en-CA') // "2026-05-25"
}

function daysDiff(target: string, today: string): number {
  const t = new Date(`${target}T00:00:00`).getTime()
  const n = new Date(`${today}T00:00:00`).getTime()
  return Math.round((t - n) / (1000 * 60 * 60 * 24))
}

function timeToMinutes(time: string | undefined): number {
  if (!time) return Number.MAX_SAFE_INTEGER
  const match = /^(\d{1,2}):(\d{2})/.exec(time)
  if (!match) return Number.MAX_SAFE_INTEGER
  const hh = Number(match[1])
  const mm = Number(match[2])
  if (Number.isNaN(hh) || Number.isNaN(mm)) return Number.MAX_SAFE_INTEGER
  return hh * 60 + mm
}

function sessionToItem(s: ParentOnboardingSessionSummary): RailItem | null {
  const parsed = parseDate(s.scheduled_date)
  if (!parsed) return null
  // The summary's scheduled_date is a full ISO datetime; derive the local
  // HH:MM from it (there is no separate scheduled_time field).
  const hh = String(parsed.getHours()).padStart(2, '0')
  const mm = String(parsed.getMinutes()).padStart(2, '0')
  const time = `${hh}:${mm}`
  return {
    key: `session:${s.id}`,
    entity: 'session',
    patronId: s.patron_id,
    patronName: s.patron_name ?? `Patron #${s.patron_id}`,
    date: localISODate(parsed),
    time,
    link: `/staff/parent-onboarding/sessions/${s.id}`,
    status: s.status,
    sortKey: timeToMinutes(time),
  }
}

function assignmentToItem(a: CareAssignmentSummary): RailItem | null {
  if (!a.next_check_in_due) return null
  const parsed = parseDate(a.next_check_in_due)
  if (!parsed) return null
  return {
    key: `assignment:${a.id}`,
    entity: 'assignment',
    patronId: a.patron_id,
    patronName: a.patron_name ?? `Patron #${a.patron_id}`,
    date: localISODate(parsed),
    link: `/staff/parent-onboarding/care-assignments/${a.id}`,
    riskLevel: a.risk_level,
    sortKey: Number.MAX_SAFE_INTEGER, // assignments have no time-of-day; sort last within bucket
  }
}

function visitToItem(v: ParentHomeVisitSummary): RailItem | null {
  const parsed = parseDate(v.scheduled_date)
  if (!parsed) return null
  return {
    key: `visit:${v.id}`,
    entity: 'visit',
    patronId: v.patron_id,
    patronName: v.patron_name ?? `Patron #${v.patron_id}`,
    date: localISODate(parsed),
    time: v.scheduled_time ?? undefined,
    link: `/staff/parent-onboarding/home-visits/${v.id}`,
    status: v.status,
    visitPurpose: v.purpose,
    sortKey: timeToMinutes(v.scheduled_time ?? undefined),
  }
}

function compareItems(a: RailItem, b: RailItem): number {
  if (a.sortKey !== b.sortKey) return a.sortKey - b.sortKey
  return a.key.localeCompare(b.key)
}

export interface BucketUpNextOptions {
  /** Signed-in coordinator's user id. Items whose owner != this are filtered out. */
  currentUserId: number
  /** "Now" - injected so tests don't need fake timers. */
  now: Date
}

export function bucketUpNext(
  dashboard: ParentOnboardingDashboard,
  options: BucketUpNextOptions,
): UpNextBuckets {
  const { currentUserId, now } = options
  const today = localISODate(now)

  const items: RailItem[] = []

  // Sessions: scope by staff_id (the owner column the summary actually
  // carries), including unassigned (staff_id == null) sessions so they stay
  // visible to every coordinator rather than vanish for everyone -- see the
  // scoping note above. Also drop completed/cancelled/no_show that happen to
  // be in the recent_sessions list (the dashboard caps at "recent", which
  // can include yesterday's completed work - we don't want that on Up Next).
  for (const s of dashboard.recent_sessions) {
    if (s.staff_id != null && s.staff_id !== currentUserId) continue
    if (COMPLETED_STATUSES.has(s.status)) continue
    const item = sessionToItem(s)
    if (item) items.push(item)
  }

  // Assignments: scope by coordinator_id, strict -- creation requires a
  // coordinator, so there's no "unassigned is the common case" story here
  // (see the scoping note above). The dashboard hands these to us as
  // "overdue" but they can also include due-today rows; bucketing decides
  // which header they land under.
  for (const a of dashboard.overdue_assignments) {
    if (a.coordinator_id !== currentUserId) continue
    const item = assignmentToItem(a)
    if (item) items.push(item)
  }

  // Visits: scope by visitor_id, including unassigned (visitor_id == null)
  // visits, same reasoning as sessions -- see the scoping note above.
  for (const v of dashboard.upcoming_visits) {
    if (v.visitor_id != null && v.visitor_id !== currentUserId) continue
    if (COMPLETED_STATUSES.has(v.status)) continue
    const item = visitToItem(v)
    if (item) items.push(item)
  }

  const overdue: RailItem[] = []
  const todayBucket: RailItem[] = []
  const thisWeek: RailItem[] = []

  for (const item of items) {
    const diff = daysDiff(item.date, today)
    if (diff < 0) overdue.push(item)
    else if (diff === 0) todayBucket.push(item)
    else if (diff <= 7) thisWeek.push(item)
    // diff > 7 is silently dropped; they aren't actionable from this rail.
  }

  // Overdue sorts by date ascending (oldest first = most overdue), tiebreak by sortKey/key.
  overdue.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date)
    return compareItems(a, b)
  })
  todayBucket.sort(compareItems)
  // This Week sorts by date first (today+1 ... today+7), then by time-of-day.
  thisWeek.sort((a, b) => {
    if (a.date !== b.date) return a.date.localeCompare(b.date)
    return compareItems(a, b)
  })

  return { overdue, today: todayBucket, thisWeek }
}
