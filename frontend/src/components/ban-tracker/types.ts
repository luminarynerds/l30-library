/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
export interface BanReport {
  id: number
  title: string
  author: string
  state: string
  ban_type: 'challenged' | 'restricted' | 'banned' | 'pending'
  reason_category: string
  source?: string
  source_url?: string
  district?: string
  date_reported?: string
  has_in_catalog?: boolean
  catalog_item_id?: number
  cover_url?: string
}

export interface BanReportsResponse {
  items: BanReport[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface StateCount {
  state: string
  count: number
}

export interface TypeCount {
  ban_type: string
  count: number
}

export interface ReasonCount {
  reason_category: string
  count: number
}

export interface BanStats {
  total_reports: number
  total_states: number
  total_has_in_cataloges: number
  by_state: StateCount[]
  by_type: TypeCount[]
  by_reason: ReasonCount[]
}

export interface MostBannedBook {
  title: string
  author: string
  report_count: number
  state_count: number
  states: string[]
}

export interface BanStatsRaw {
  total_reports: number
  total_states: number
  total_catalog_matches?: number
  total_has_in_cataloges?: number
  by_state: Record<string, number>
  by_type: Record<string, number>
  by_reason: Record<string, number>
}

export interface AdminBanReport {
  id: number
  title: string
  author: string
  isbn: string | null
  state: string
  district: string | null
  institution: string | null
  ban_type: 'challenged' | 'restricted' | 'banned' | 'pending'
  reason: string | null
  reason_category: string | null
  source: string | null
  source_url: string | null
  date_reported: string
  notes: string | null
  catalog_match_id: number | null
  created_at: string
  // Acquisition-rationale enrichment (Task 11): backend fills these on
  // staff-only ban-tracker endpoints. Optional for forward-compat with
  // older responses or any cached payload that predates the rollout.
  rationale_present?: boolean
  rationale_anticipated?: boolean
  rationale_primary_use_case?: string | null
}

export interface BanReportMatch extends AdminBanReport {
  catalog_title: string
  catalog_author: string
}

export interface AdminBanStats {
  total_reports: number
  total_states: number
  total_catalog_matches: number
  by_state: Record<string, number>
  by_type: Record<string, number>
  by_reason: Record<string, number>
}

export interface AlertCount {
  unseen_count: number
}

export interface SyncStatus {
  last_sync_at: string | null
  status: 'idle' | 'running' | 'failed' | 'completed'
  records_synced: number
  error_message: string | null
}

export interface LetterTemplate {
  id: number
  title: string
  subject_line: string
  body_template: string
  target_level: 'any' | 'federal' | 'state' | 'local'
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface BanReportFormData {
  title: string
  author: string
  isbn: string
  state: string
  district: string
  institution: string
  ban_type: 'challenged' | 'restricted' | 'banned' | 'pending'
  reason: string
  reason_category: string
  source: string
  source_url: string
  date_reported: string
  notes: string
}

export interface LetterTemplateFormData {
  title: string
  subject_line: string
  body_template: string
  target_level: 'any' | 'federal' | 'state' | 'local'
  is_active: boolean
}

export type TabType = 'matches' | 'all' | 'templates'
