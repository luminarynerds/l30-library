/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { useQuery } from '@tanstack/react-query'
import * as Sentry from "@/lib/sentry-lazy"
import {
  Loader2,
  UsersRound,
  Calendar,
  Check,
  MapPin,
  Users,
  AlertTriangle,
  UserPlus,
  Download,
  Lock,
  Plus,
  MoreVertical,
} from 'lucide-react'
import { Link } from 'react-router-dom'
import {
  listConnectionGroups,
  type ParentConnectionGroup,
  type ConnectionGroupType,
} from '@/api/parent-onboarding-api'
import { useTranslation, getCurrentLocale } from '@/i18n'
import { useMemo, useState, useRef, useEffect } from 'react'
import { AdminShell } from '../components/shells/AdminShell'
import { parseDate } from '@/utils/format-utils'
import { useAuth } from '@/contexts/AuthContext'
import { EnrollPatronModal } from '@/components/staff/parent-onboarding/EnrollPatronModal'
import { GroupMembersDrawer } from '@/components/staff/parent-onboarding/GroupMembersDrawer'
import {
  ArchiveGroupDialog,
  CreateGroupModal,
  EditGroupModal,
  MeetingsDrawer,
} from '@/components/staff/parent-onboarding/ConnectionGroupLifecycleModals'

// Stable, namespaced i18n keys for group type labels.
// Keys live under `parentOnboarding.connectionGroups.types.*` in the locale files.
// (Previously this was an English-string-to-English-string map keyed off the
// same English label, which only worked because en.json happened to contain
// the literal "First-Time Parents" key. That silently breaks any other locale.)
const GROUP_TYPE_KEYS: Record<ConnectionGroupType, string> = {
  first_time_parents: 'parentOnboarding.connectionGroups.types.first_time_parents',
  teen_parents: 'parentOnboarding.connectionGroups.types.teen_parents',
  single_parents: 'parentOnboarding.connectionGroups.types.single_parents',
  postpartum_support: 'parentOnboarding.connectionGroups.types.postpartum_support',
  general: 'parentOnboarding.connectionGroups.types.general',
}

// Category palette — distinct from status-info/status-warning which carry
// genuine "informational" / "warning" semantics. Using brand/sage/earth/pink
// here keeps real alerts visually unambiguous. Tokens verified in
// tailwind.config.js (brand-* maps to accent-rose CSS vars; sage/earth/pink
// are present).
const GROUP_TYPE_COLORS: Record<ConnectionGroupType, string> = {
  first_time_parents: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
  teen_parents: 'bg-sage-100 text-sage-800 dark:bg-sage-900/30 dark:text-sage-300',
  single_parents: 'bg-earth-100 text-earth-700 dark:bg-earth-800 dark:text-earth-200',
  postpartum_support: 'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
  general: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-earth-300',
}

// Shared focus ring class — every interactive control on the page uses this.
// WCAG 2.4.7 (focus visible) + 2.4.11 (focus not obscured).
const FOCUS_RING =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-lsc-rose focus-visible:ring-offset-2 dark:focus-visible:ring-offset-earth-900'

// Redacted Sentry CaptureContext — strips identifying group fields before they
// reach Sentry. Kept as a module-level constant so it's referentially stable
// and tests can match on the exact object shape.
const REDACTED_CTX = {
  tags: { group_type: '[redacted]' },
  extra: { group_id: '[redacted]' },
} as const

function formatDate(d: string): string {
  const parsed = parseDate(d)
  if (!parsed) return '-'
  return parsed.toLocaleDateString(getCurrentLocale(), { weekday: 'short', month: 'short', day: 'numeric' })
}

function isPastDate(d: string | null | undefined): boolean {
  if (!d) return false
  const parsed = parseDate(d)
  if (!parsed) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return parsed.getTime() < today.getTime()
}

// CSV escape per RFC 4180: wrap in quotes when needed, double internal quotes.
function csvCell(v: string | number | null | undefined): string {
  const s = v == null ? '' : String(v)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

// Exported for unit-testing. Lives next to the page rather than in a sibling
// module because the CSV column ordering is part of the page contract; keep
// them together. (react-refresh false-positive — disabled inline.)
// eslint-disable-next-line react-refresh/only-export-components
export function buildGroupsCsv(groups: ParentConnectionGroup[]): string {
  const header = [
    'name',
    'type',
    'schedule',
    'next_meeting',
    'location',
    'current_members',
    'max_members',
    'topics',
  ]
  const rows = groups.map((g) =>
    [
      csvCell(g.name),
      // raw enum string — locale-stable, admin-readable
      csvCell(g.group_type),
      csvCell(g.meeting_schedule ?? ''),
      csvCell(g.next_meeting_date ?? ''),
      csvCell(g.meeting_location ?? ''),
      csvCell(typeof g.current_members === 'number' ? g.current_members : ''),
      csvCell(g.max_members),
      csvCell((g.topics ?? []).join('|')),
    ].join(','),
  )
  return [header.join(','), ...rows].join('\n') + '\n'
}

function downloadCsv(filename: string, contents: string): void {
  const blob = new Blob([contents], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export default function ParentConnectionGroupsPage() {
  const { t } = useTranslation()
  const { user } = useAuth()
  // library_admin gate: matches the server-side require_library_admin dep so
  // we hide buttons that would 403 anyway. Backend re-enforces — this is UX.
  const isLibraryAdmin = user?.role === 'library_admin'
  const [filterType, setFilterType] = useState<ConnectionGroupType | ''>('')
  // Controlled live-region message — derived state from mutations does NOT
  // re-announce reliably, so we drive announcements off explicit setLiveMsg
  // calls inside onSuccess/onError.
  const [liveMsg] = useState('')
  const [enrollFor, setEnrollFor] = useState<ParentConnectionGroup | null>(null)
  const [membersFor, setMembersFor] = useState<ParentConnectionGroup | null>(null)
  // Admin lifecycle state. Each holds the group that the modal/drawer is
  // currently targeting. `createOpen` is the only one without a group ref
  // because creation builds a new one.
  const [createOpen, setCreateOpen] = useState(false)
  const [editFor, setEditFor] = useState<ParentConnectionGroup | null>(null)
  const [archiveFor, setArchiveFor] = useState<ParentConnectionGroup | null>(null)
  const [meetingsFor, setMeetingsFor] = useState<ParentConnectionGroup | null>(null)

  const {
    data,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['connection-groups', filterType],
    queryFn: () =>
      listConnectionGroups({
        is_active: true,
        ...(filterType && { group_type: filterType }),
        limit: 50,
      }),
  })


  if (error) {
    Sentry.captureException(error, REDACTED_CTX)
  }

  const groups: ParentConnectionGroup[] = useMemo(
    () => data?.groups ?? [],
    [data],
  )

  // Sort by soonest meeting; null next_meeting_date sorts to bottom.
  const sortedGroups = useMemo(() => {
    const withDate = groups.filter((g) => g.next_meeting_date)
    const withoutDate = groups.filter((g) => !g.next_meeting_date)
    withDate.sort((a, b) => {
      const da = parseDate(a.next_meeting_date as string)?.getTime() ?? 0
      const db = parseDate(b.next_meeting_date as string)?.getTime() ?? 0
      return da - db
    })
    return [...withDate, ...withoutDate]
  }, [groups])

  // KPI aggregates.
  const kpi = useMemo(() => {
    const totalGroups = groups.length
    const totalMembers = groups.reduce((s, g) => s + (g.current_members ?? 0), 0)
    const totalCapacity = groups.reduce((s, g) => s + (g.max_members ?? 0), 0)
    const fullGroups = groups.filter((g) => (g.current_members ?? 0) >= (g.max_members ?? 0)).length
    const utilization = totalCapacity > 0 ? Math.round((totalMembers / totalCapacity) * 100) : 0
    return { totalGroups, totalMembers, utilization, fullGroups }
  }, [groups])

  const onExportCsv = () => {
    const csv = buildGroupsCsv(sortedGroups)
    const today = new Date().toISOString().slice(0, 10)
    downloadCsv(`connection-groups-${today}.csv`, csv)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <Loader2
          className="w-8 h-8 motion-safe:animate-spin text-lsc-rose"
          role="status"
          aria-label={t('parentOnboarding.connectionGroups.pageStrings.loadingLabel', 'Loading')}
        />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="bg-status-danger-50 dark:bg-status-danger-900/20 border border-status-danger-200 dark:border-status-danger-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-status-danger-500 mx-auto mb-2" aria-hidden="true" />
          <p className="text-status-danger-700 dark:text-status-danger-300">{t('parentOnboarding.connectionGroups.failedToLoad', 'Failed to load connection groups')}</p>
        </div>
      </div>
    )
  }

  return (
    <AdminShell title="Parent Connection Groups">
    <div className="max-w-5xl mx-auto p-6 space-y-6">
      {/* Visually-hidden live region for join/leave outcomes. role=status +
          aria-live=polite is more reliably announced than toast libraries. */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
        data-testid="conngroups-live-region"
      >
        {liveMsg}
      </div>

      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="text-2xl font-serif font-bold text-lsc-dark dark:text-lsc-cream">
            {t('parentOnboarding.connectionGroups.title', 'Parent Connection Groups')}
          </h1>
          <p className="text-sm text-lsc-dark/85 dark:text-lsc-cream/85 mt-1">
            {t('parentOnboarding.connectionGroups.subtitleStaff', 'Manage parent connection group enrollment.')}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          {isLibraryAdmin && (
            <button
              type="button"
              onClick={() => setCreateOpen(true)}
              data-testid="conngroups-new-group"
              className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg bg-lsc-rose text-white hover:bg-lsc-rose/90 transition-colors ${FOCUS_RING}`}
            >
              <Plus className="w-4 h-4" aria-hidden="true" />
              {t('parentOnboarding.connectionGroups.admin.newGroup')}
            </button>
          )}
          <button
            type="button"
            onClick={onExportCsv}
            disabled={groups.length === 0}
            data-testid="conngroups-export-csv"
            className={`inline-flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border border-lsc-border dark:border-earth-700 bg-lsc-white dark:bg-earth-800 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors disabled:opacity-50 ${FOCUS_RING}`}
          >
            <Download className="w-4 h-4" aria-hidden="true" />
            {t('parentOnboarding.connectionGroups.pageStrings.exportCsv', 'Export CSV')}
          </button>
        </div>
      </div>

      {/* KPI strip — client-side aggregates over the active groups list.
          Warm civic palette: cream/earth tiles, serif numerals, sm label. */}
      <div
        className="grid grid-cols-2 md:grid-cols-4 gap-3"
        data-testid="conngroups-kpi-strip"
      >
        <div className="bg-lsc-cream/40 dark:bg-earth-800/60 rounded-xl p-4">
          <div className="text-sm font-medium text-lsc-dark/85 dark:text-lsc-cream/85">
            {t('parentOnboarding.connectionGroups.pageStrings.kpiActiveGroups', 'Active groups')}
          </div>
          <div
            className="text-2xl font-serif text-lsc-dark dark:text-lsc-cream mt-1"
            data-testid="conngroups-kpi-active-groups"
          >
            {kpi.totalGroups}
          </div>
        </div>
        <div className="bg-lsc-cream/40 dark:bg-earth-800/60 rounded-xl p-4">
          <div className="text-sm font-medium text-lsc-dark/85 dark:text-lsc-cream/85">
            {t('parentOnboarding.connectionGroups.pageStrings.kpiActiveMembers', 'Active members')}
          </div>
          <div
            className="text-2xl font-serif text-lsc-dark dark:text-lsc-cream mt-1"
            data-testid="conngroups-kpi-active-members"
          >
            {kpi.totalMembers}
          </div>
        </div>
        <div className="bg-lsc-cream/40 dark:bg-earth-800/60 rounded-xl p-4">
          <div className="text-sm font-medium text-lsc-dark/85 dark:text-lsc-cream/85">
            {t('parentOnboarding.connectionGroups.pageStrings.kpiCapacityUtilization', 'Capacity used')}
          </div>
          <div
            className="text-2xl font-serif text-lsc-dark dark:text-lsc-cream mt-1"
            data-testid="conngroups-kpi-utilization"
          >
            {kpi.utilization}%
          </div>
        </div>
        <div className="bg-lsc-cream/40 dark:bg-earth-800/60 rounded-xl p-4">
          <div className="text-sm font-medium text-lsc-dark/85 dark:text-lsc-cream/85">
            {t('parentOnboarding.connectionGroups.pageStrings.kpiFullGroups', 'Groups full')}
          </div>
          <div
            className="text-2xl font-serif text-lsc-dark dark:text-lsc-cream mt-1"
            data-testid="conngroups-kpi-full-groups"
          >
            {kpi.fullGroups}
          </div>
        </div>
      </div>

      {/* Filter */}
      <div
        className="flex items-center gap-2 flex-wrap"
        role="group"
        aria-label={t('parentOnboarding.connectionGroups.pageStrings.filterAriaLabel', 'Filter groups by type')}
      >
        <span className="text-sm text-lsc-dark/85 dark:text-lsc-cream/85">{t('parentOnboarding.connectionGroups.filterByType')}:</span>
        <button
          type="button"
          aria-pressed={filterType === ''}
          onClick={() => setFilterType('')}
          className={`px-3 py-1.5 text-xs rounded-full transition-colors ${FOCUS_RING} ${
            filterType === ''
              ? 'bg-lsc-rose text-white ring-2 ring-lsc-rose ring-offset-1 dark:ring-offset-earth-900'
              : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-600'
          }`}
        >
          {filterType === '' && <Check className="w-3.5 h-3.5" aria-hidden="true" />}
          {t('parentOnboarding.connectionGroups.pageStrings.allFilter', 'All')}
        </button>
        {(Object.entries(GROUP_TYPE_KEYS) as [ConnectionGroupType, string][]).map(([type, key]) => (
          <button
            type="button"
            key={type}
            aria-pressed={filterType === type}
            onClick={() => setFilterType(type)}
            className={`px-3 py-1.5 text-xs rounded-full transition-colors ${FOCUS_RING} ${
              filterType === type
                ? 'bg-lsc-rose text-white ring-2 ring-lsc-rose ring-offset-1 dark:ring-offset-earth-900'
                : 'bg-lsc-cream dark:bg-earth-700 text-lsc-dark dark:text-lsc-cream hover:bg-lsc-border dark:hover:bg-earth-600'
            }`}
          >
            {filterType === type && <Check className="w-3.5 h-3.5" aria-hidden="true" />}
            {t(key)}
          </button>
        ))}
      </div>

      {/* Groups Grid */}
      {sortedGroups.length === 0 ? (
        <div className="text-center py-12">
          <UsersRound className="w-12 h-12 text-lsc-dark/20 dark:text-lsc-cream/85 mx-auto mb-3" aria-hidden="true" />
          <p className="text-lsc-dark/85 dark:text-lsc-cream/85">{t('parentOnboarding.connectionGroups.noGroupsAvailable', 'No groups available at this time')}</p>
        </div>
      ) : (
        <ul
          role="list"
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 list-none p-0"
          data-testid="conngroups-grid"
        >
          {sortedGroups.map((group: ParentConnectionGroup) => {
            const stale = isPastDate(group.next_meeting_date)
            const isConfidential = group.confidential === true
            return (
              <li
                key={group.id}
                data-testid={isConfidential ? 'conngroups-card-confidential' : 'conngroups-card'}
                className="bg-lsc-white dark:bg-earth-800 rounded-xl border border-lsc-border dark:border-earth-700 p-5 flex flex-col"
              >
                <div className="flex items-start justify-between gap-2 mb-2">
                  <h3 className="text-sm font-semibold text-lsc-dark dark:text-lsc-cream flex-1">
                    {group.name}
                  </h3>
                  <div className="flex items-center gap-2">
                    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${GROUP_TYPE_COLORS[group.group_type]}`}>
                      {t(GROUP_TYPE_KEYS[group.group_type])}
                    </span>
                    {isLibraryAdmin && (
                      <AdminKebabMenu
                        group={group}
                        onEdit={() => setEditFor(group)}
                        onArchive={() => setArchiveFor(group)}
                        onManageMeetings={() => setMeetingsFor(group)}
                      />
                    )}
                  </div>
                </div>

                {isConfidential && (
                  <div
                    className="flex items-center gap-1.5 mb-2 text-xs text-lsc-dark/85 dark:text-lsc-cream/85"
                    data-testid="conngroups-confidential-label"
                  >
                    <Lock
                      className="w-3.5 h-3.5"
                      aria-label={t('connectionGroups.confidential.cardLabel')}
                    />
                    <span>{t('connectionGroups.confidential.cardSubtext')}</span>
                  </div>
                )}

                {group.description && (
                  <p className="text-xs text-lsc-dark/85 dark:text-lsc-cream/85 mb-3">
                    {group.description}
                  </p>
                )}

                <div className="space-y-2 text-sm text-lsc-dark/85 dark:text-lsc-cream/85 flex-1">
                  {group.meeting_schedule && (
                    <div className="flex items-center gap-2">
                      <Calendar className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                      {group.meeting_schedule}
                    </div>
                  )}
                  {group.next_meeting_date && (
                    <div
                      className={`flex items-center gap-2 ${stale ? 'text-status-warning-600 dark:text-status-warning-400' : ''}`}
                      data-testid={stale ? 'next-meeting-stale' : 'next-meeting'}
                    >
                      {stale ? (
                        <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
                      ) : (
                        <Calendar className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                      )}
                      <span>
                        {t('common.next', 'Next')}: {formatDate(group.next_meeting_date)}
                      </span>
                      {stale && (
                        <span className="sr-only">
                          {' '}
                          — {t('parentOnboarding.connectionGroups.pageStrings.pastMeetingSr', 'Past meeting date — needs scheduling')}
                        </span>
                      )}
                    </div>
                  )}
                  {group.meeting_location && (
                    <div className="flex items-center gap-2">
                      <MapPin className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                      {group.meeting_location}
                    </div>
                  )}
                  {isConfidential ? (
                    <div className="flex items-center gap-2" data-testid="conngroups-limited-capacity">
                      <Users className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                      {t('connectionGroups.confidential.limitedCapacity')}
                    </div>
                  ) : (
                    typeof group.current_members === 'number' && (
                      <div className="flex items-center gap-2" data-testid="member-count">
                        <Users className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                        {group.current_members}/{group.max_members} {t('parentOnboarding.connectionGroups.membersCountSuffix', 'members')}
                      </div>
                    )
                  )}
                  {/* Facilitator is intentionally omitted at the DOM level for
                      confidential groups (spec property #3 — not CSS-hidden). */}
                  {!isConfidential && group.facilitator_name && (
                    <div className="flex items-center gap-2">
                      <UsersRound className="w-3.5 h-3.5 text-lsc-dark/85 dark:text-lsc-cream/85" aria-hidden="true" />
                      {t('common.facilitator', 'Facilitator')}: {group.facilitator_name}
                    </div>
                  )}
                </div>

                {group.topics && group.topics.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-3">
                    {group.topics.slice(0, 4).map((topic, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-lsc-cream dark:bg-earth-700 text-lsc-dark/85 dark:text-lsc-cream/85"
                      >
                        {topic}
                      </span>
                    ))}
                    {group.topics.length > 4 && (
                      <span className="text-xs text-lsc-dark/85 dark:text-lsc-cream/85">
                        +{group.topics.length - 4} {t('common.moreCount', 'more')}
                      </span>
                    )}
                  </div>
                )}

                <div className="mt-4 pt-3 border-t border-lsc-border dark:border-earth-700 flex gap-2 flex-wrap">
                  <button
                    type="button"
                    onClick={() => setEnrollFor(group)}
                    data-testid="conngroups-enroll"
                    className={`flex-1 flex items-center justify-center gap-1.5 px-3 py-2 text-sm bg-lsc-rose text-white rounded-lg hover:bg-lsc-rose/90 transition-colors ${FOCUS_RING}`}
                  >
                    <UserPlus className="w-4 h-4" aria-hidden="true" />
                    {isConfidential
                      ? t('connectionGroups.confidential.requestButton')
                      : t('parentOnboarding.connectionGroups.enroll.enrollAction', 'Enroll patron')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setMembersFor(group)}
                    data-testid="conngroups-view-members"
                    className={`flex items-center justify-center gap-1.5 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors ${FOCUS_RING}`}
                  >
                    <Users className="w-4 h-4" aria-hidden="true" />
                    {t('parentOnboarding.connectionGroups.enroll.viewMembersAction', 'View members')}
                  </button>
                  {isConfidential && (
                    <Link
                      to="/staff/parent-onboarding/connection-groups/approvals"
                      data-testid="conngroups-view-approval-queue"
                      className={`flex items-center justify-center gap-1.5 px-3 py-2 text-sm border border-lsc-border dark:border-earth-700 text-lsc-dark dark:text-lsc-cream rounded-lg hover:bg-lsc-cream dark:hover:bg-earth-700 transition-colors ${FOCUS_RING}`}
                    >
                      {t('connectionGroups.approvalQueue.viewLink')}
                    </Link>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </div>
    {enrollFor && (
      <EnrollPatronModal
        group={enrollFor}
        isOpen={enrollFor !== null}
        onClose={() => setEnrollFor(null)}
      />
    )}
    {membersFor && (
      <GroupMembersDrawer
        group={membersFor}
        isOpen={membersFor !== null}
        onClose={() => setMembersFor(null)}
      />
    )}
    {isLibraryAdmin && (
      <>
        <CreateGroupModal isOpen={createOpen} onClose={() => setCreateOpen(false)} />
        {editFor && (
          <EditGroupModal
            group={editFor}
            activeMemberCount={editFor.current_members ?? editFor.member_count}
            isOpen={editFor !== null}
            onClose={() => setEditFor(null)}
          />
        )}
        {archiveFor && (
          <ArchiveGroupDialog
            group={archiveFor}
            isOpen={archiveFor !== null}
            onClose={() => setArchiveFor(null)}
          />
        )}
        {meetingsFor && (
          <MeetingsDrawer
            group={meetingsFor}
            isOpen={meetingsFor !== null}
            onClose={() => setMeetingsFor(null)}
          />
        )}
      </>
    )}
    </AdminShell>
  )
}

// Small kebab menu component. Lives in this file because it's only used by
// the page and doesn't merit its own module. ARIA semantics: button with
// aria-haspopup="menu" + a <ul role="menu"> popover that closes on outside
// click and ESC. Each menu item is a <button role="menuitem">.
function AdminKebabMenu({
  group, onEdit, onArchive, onManageMeetings,
}: {
  group: ParentConnectionGroup
  onEdit: () => void
  onArchive: () => void
  onManageMeetings: () => void
}) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function onClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onClickOutside)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onClickOutside)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-haspopup="menu"
        aria-expanded={open}
        aria-label={t('parentOnboarding.connectionGroups.admin.groupActions')}
        data-testid="conngroups-card-kebab"
        className={`p-1 rounded text-lsc-dark/70 dark:text-lsc-cream/70 hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
      >
        <MoreVertical className="w-4 h-4" aria-hidden="true" />
      </button>
      {open && (
        <ul
          role="menu"
          aria-label={t('parentOnboarding.connectionGroups.admin.groupActions')}
          className="absolute right-0 mt-1 z-10 w-48 bg-lsc-white dark:bg-earth-800 border border-lsc-border dark:border-earth-700 rounded-lg shadow-lg py-1 text-sm"
          data-testid={`conngroups-card-menu-${group.id}`}
        >
          <li role="none">
            <button
              role="menuitem"
              type="button"
              onClick={() => { setOpen(false); onEdit() }}
              className={`w-full text-left px-3 py-2 hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
              data-testid="conngroups-card-edit"
            >
              {t('parentOnboarding.connectionGroups.admin.editGroup')}
            </button>
          </li>
          <li role="none">
            <button
              role="menuitem"
              type="button"
              onClick={() => { setOpen(false); onManageMeetings() }}
              className={`w-full text-left px-3 py-2 hover:bg-lsc-cream dark:hover:bg-earth-700 ${FOCUS_RING}`}
              data-testid="conngroups-card-manage-meetings"
            >
              {t('parentOnboarding.connectionGroups.admin.manageMeetings')}
            </button>
          </li>
          <li role="none">
            <button
              role="menuitem"
              type="button"
              onClick={() => { setOpen(false); onArchive() }}
              className={`w-full text-left px-3 py-2 hover:bg-lsc-cream dark:hover:bg-earth-700 text-status-danger-700 dark:text-status-danger-300 ${FOCUS_RING}`}
              data-testid="conngroups-card-archive"
            >
              {t('parentOnboarding.connectionGroups.admin.archiveGroup')}
            </button>
          </li>
        </ul>
      )}
    </div>
  )
}
