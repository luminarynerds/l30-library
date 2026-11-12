/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable react-refresh/only-export-components */
import { Ban, Lock, AlertTriangle, Clock } from 'lucide-react'
import type { BanStats, BanStatsRaw } from './types'
import { parseDate } from '@/utils/format-utils'
import { getCurrentLocale } from '@/i18n'

export const US_STATES_MAP: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California',
  CO: 'Colorado', CT: 'Connecticut', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
  HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa',
  KS: 'Kansas', KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland',
  MA: 'Massachusetts', MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri',
  MT: 'Montana', NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey',
  NM: 'New Mexico', NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio',
  OK: 'Oklahoma', OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont',
  VA: 'Virginia', WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
  DC: 'District of Columbia',
}

export const US_STATES_LIST = [
  'AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA',
  'HI','ID','IL','IN','IA','KS','KY','LA','ME','MD',
  'MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ',
  'NM','NY','NC','ND','OH','OK','OR','PA','RI','SC',
  'SD','TN','TX','UT','VT','VA','WA','WV','WI','WY',
  'DC',
]

// Canonical reason_category values that prod data can already contain.
// Both producers (pen_america_sync_service._categorize_reason() and
// scripts/seed_ban_tracker.py) emit the same set after #994:
//   sexual_content, lgbtq, race, religion, drugs_alcohol,
//   violence_profanity, suicide_self_harm, other.
export const REASON_LABELS: Record<string, string> = {
  sexual_content: 'Sexual Content',
  lgbtq: 'LGBTQ+ Themes',
  race: 'Race & Racism',
  religion: 'Religion',
  drugs_alcohol: 'Drugs & Alcohol',
  violence_profanity: 'Violence & Profanity',
  suicide_self_harm: 'Suicide / Self-Harm',
  other: 'Other',
}

export const SOURCE_LABELS: Record<string, string> = {
  PEN_AMERICA: 'PEN America',
  ALA: 'American Library Association',
  STAFF_ENTRY: 'Staff Entry',
  NEWS: 'News Report',
}

export const BAN_TYPES = ['challenged', 'restricted', 'banned', 'pending'] as const

export const TARGET_LEVELS = [
  { value: 'any', label: 'Any' },
  { value: 'federal', label: 'Federal' },
  { value: 'state', label: 'State' },
  { value: 'local', label: 'Local' },
] as const

export function formatNumber(n: number): string {
  return n.toLocaleString()
}

export function formatReason(raw: string | null): string {
  if (!raw) return '--'
  return REASON_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function formatSource(raw: string | null): string {
  if (!raw) return '--'
  return SOURCE_LABELS[raw] ?? raw.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

export function formatDate(dateStr: string | null): string {
  if (!dateStr) return '--'
  try {
    return parseDate(dateStr)?.toLocaleDateString(getCurrentLocale(), {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }) ?? '--'
  } catch {
    return dateStr
  }
}

export function getBanTypeBadge(banType: string): { label: string; className: string } {
  switch (banType) {
    case 'banned':
      return {
        label: 'Banned',
        className: 'bg-status-danger-100 dark:bg-status-danger-900/30 text-status-danger-700 dark:text-status-danger-300',
      }
    case 'restricted':
      return {
        label: 'Restricted',
        className: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
      }
    case 'challenged':
      return {
        label: 'Challenged',
        className: 'bg-status-warning-100 dark:bg-status-warning-900/30 text-status-warning-700 dark:text-status-warning-300',
      }
    case 'pending':
      return {
        label: 'Pending',
        className: 'bg-earth-100 dark:bg-earth-800/30 text-lsc-rose dark:text-lsc-rose-light',
      }
    default:
      return {
        label: banType,
        className: 'bg-earth-100 dark:bg-earth-700 text-lsc-dark/70 dark:text-lsc-cream/70',
      }
  }
}

export function getBanTypeIcon(banType: string): React.ReactElement {
  switch (banType) {
    case 'banned':
      return <Ban className="w-4 h-4" aria-hidden="true" />
    case 'restricted':
      return <Lock className="w-4 h-4" aria-hidden="true" />
    case 'challenged':
      return <AlertTriangle className="w-4 h-4" aria-hidden="true" />
    case 'pending':
      return <Clock className="w-4 h-4" aria-hidden="true" />
    default:
      return <AlertTriangle className="w-4 h-4" aria-hidden="true" />
  }
}

export function banTypeBadgeClasses(type: string): string {
  switch (type) {
    case 'banned':
      return 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900/30 dark:text-status-danger-300'
    case 'restricted':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    case 'challenged':
      return 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900/30 dark:text-status-warning-300'
    case 'pending':
      return 'bg-lsc-cream text-lsc-dark dark:bg-earth-700/50 dark:text-lsc-cream/70'
    default:
      return 'bg-lsc-cream text-lsc-dark dark:bg-earth-700/50 dark:text-lsc-cream/70'
  }
}

export function targetLevelBadgeClasses(level: string): string {
  switch (level) {
    case 'federal':
      return 'bg-earth-100 text-earth-800 dark:bg-earth-800/30 dark:text-lsc-rose-light'
    case 'state':
      return 'bg-category-100 text-category-800 dark:bg-category-900/30 dark:text-category-300'
    case 'local':
      return 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900/30 dark:text-status-success-300'
    default:
      return 'bg-lsc-cream text-lsc-dark dark:bg-earth-700/50 dark:text-lsc-cream/70'
  }
}

export function normalizeStats(raw: BanStatsRaw): BanStats {
  return {
    total_reports: raw.total_reports ?? 0,
    total_states: raw.total_states ?? 0,
    total_has_in_cataloges: raw.total_catalog_matches ?? raw.total_has_in_cataloges ?? 0,
    by_state: Object.entries(raw.by_state ?? {}).map(([state, count]) => ({ state, count })),
    by_type: Object.entries(raw.by_type ?? {}).map(([ban_type, count]) => ({ ban_type, count })),
    by_reason: Object.entries(raw.by_reason ?? {}).map(([reason_category, count]) => ({ reason_category, count })),
  }
}
