/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export type Tab = 'floor' | 'reservations' | 'guests' | 'stats'

export interface MaintenanceTarget {
  computerId: number
  computerName: string
}

export type StatusFilter = 'all' | 'available' | 'in_use' | 'attention' | 'maintenance' | 'offline'
export type TypeFilter = 'all' | 'adult' | 'teen' | 'kids' | 'accessible'
export type BulkAction = 'end_sessions' | 'mark_available' | 'mark_maintenance' | 'mark_offline'

export const STATUS_FILTERS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'attention', label: 'Needs Attention' },
  { value: 'available', label: 'Available' },
  { value: 'in_use', label: 'In Use' },
  { value: 'maintenance', label: 'Maintenance' },
  { value: 'offline', label: 'Offline' },
]

export const TYPE_FILTERS: { value: TypeFilter; label: string }[] = [
  { value: 'all', label: 'All Types' },
  { value: 'adult', label: 'Adult' },
  { value: 'teen', label: 'Teen' },
  { value: 'kids', label: "Children's" },
  { value: 'accessible', label: 'Accessible' },
]

export const BULK_ACTION_LABELS: Record<BulkAction, string> = {
  end_sessions: 'End Sessions',
  mark_available: 'Mark Available',
  mark_maintenance: 'Mark Maintenance',
  mark_offline: 'Mark Offline',
}

export const UNDO_WINDOW_MS = 10000

export interface ActiveSession {
  reservation_id: number
  patron_name: string | null
  started_at: string | null
  ends_at: string | null
  minutes_remaining: number
  is_overtime?: boolean
  minutes_overtime?: number
  extensions_used: number
  is_guest: boolean
  print_jobs_count: number
}

export type UrgencyTier = 'pending-ext' | 'overtime' | 'warning' | 'normal'

export interface PendingExtension {
  id: number
  extension_minutes: number
  requested_at: string | null
}

export interface FloorComputer {
  id: number
  name: string
  computer_number: string
  location: string | null
  computer_type: string
  status: string
  has_internet: boolean
  has_print_release: boolean
  max_session_minutes: number
  active_session: ActiveSession | null
  pending_extension: PendingExtension | null
}

export interface FloorSummary {
  total: number
  available: number
  in_use: number
  maintenance: number
  pending_extensions: number
}

export interface StaffReservation {
  id: number
  computer_id: number
  computer_name: string
  patron_id: number | null
  patron_name: string | null
  reserved_start_time: string
  reserved_end_time: string
  status: string
  session_duration_minutes: number
  is_guest_pass: boolean
  guest_name: string | null
  checked_in_at: string | null
  extensions_used: number
  print_jobs_count: number
}

export interface SystemStats {
  period_days: number
  total_reservations: number
  total_completed_sessions: number
  total_minutes_used: number
  guest_sessions: number
  cardholders_sessions: number
  cancelled_reservations: number
  no_show_count: number
  auto_no_shows?: number
  auto_logouts?: number
  average_session_minutes: number
}

export const TYPE_LABELS: Record<string, string> = {
  adult: 'Adult', teen: 'Teen', kids: "Children's", accessible: 'Accessible',
}

export const STATUS_COLORS: Record<string, string> = {
  available: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  in_use: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
  maintenance: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  offline: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  reserved: 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-400',
}

export const RESERVATION_STATUS_COLORS: Record<string, string> = {
  pending: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-400',
  confirmed: 'bg-status-info-100 text-status-info-800 dark:bg-status-info-900/30 dark:text-status-info-400',
  in_session: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-400',
  completed: 'bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-300',
  cancelled: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
  no_show: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-400',
}

export function formatTime(iso: string | null): string {
  if (!iso) return '--'
  return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}

export function formatMinutes(mins: number): string {
  if (mins < 60) return `${mins}m`
  const h = Math.floor(mins / 60)
  const m = mins % 60
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

export function urgencyTier(comp: FloorComputer): UrgencyTier {
  if (comp.pending_extension) return 'pending-ext'
  if (comp.active_session?.is_overtime) return 'overtime'
  if (comp.active_session && comp.active_session.minutes_remaining <= 5) return 'warning'
  return 'normal'
}

export const TIER_RANK: Record<UrgencyTier, number> = {
  'pending-ext': 0,
  'overtime': 1,
  'warning': 2,
  'normal': 3,
}

export function sortByAttention(a: FloorComputer, b: FloorComputer): number {
  const tierDiff = TIER_RANK[urgencyTier(a)] - TIER_RANK[urgencyTier(b)]
  if (tierDiff !== 0) return tierDiff
  return a.name.localeCompare(b.name)
}

export const TIER_BORDER: Record<UrgencyTier, string> = {
  'pending-ext': 'border-status-warning-400 dark:border-status-warning-600 ring-2 ring-status-warning-300/50 dark:ring-status-warning-700/40 motion-safe:animate-pulse',
  'overtime': 'border-status-danger-500 dark:border-status-danger-500 ring-2 ring-status-danger-300/50 dark:ring-status-danger-700/40 motion-safe:animate-pulse',
  'warning': 'border-status-danger-300 dark:border-status-danger-700',
  'normal': 'border-lsc-border dark:border-earth-700',
}
