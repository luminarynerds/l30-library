/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import api from '@/lib/api-client'
import { API_BASE } from '@/api/types'

const BASE = `${API_BASE}/community-outcomes`

export interface CategoryMetrics {
  [key: string]: number | string | Record<string, number>
}

export interface TransactionalMetrics {
  checkouts: number
  returns: number
  renewals: number
  holds_placed: number
  holds_filled: number
}

export interface DashboardResponse {
  period_start: string
  period_end: string
  branch_id: number | null
  transactional?: TransactionalMetrics
  categories: Record<string, CategoryMetrics>
}

export interface TrendPoint {
  period: string
  period_start: string
  period_end: string
  metrics: CategoryMetrics
}

export interface SummaryResponse {
  total_participants: number
  unique_patrons: number
  active_partnerships: number
  period: string
}

export async function getCommunityDashboard(params?: {
  start_date?: string
  end_date?: string
  branch_id?: number
}): Promise<DashboardResponse> {
  const query = new URLSearchParams()
  if (params?.start_date) query.set('start_date', params.start_date)
  if (params?.end_date) query.set('end_date', params.end_date)
  if (params?.branch_id) query.set('branch_id', String(params.branch_id))
  const qs = query.toString()
  return api.get<DashboardResponse>(`${BASE}/dashboard${qs ? `?${qs}` : ''}`)
}

export async function getCommunityTrends(
  category: string,
  periods = 12,
  branch_id?: number,
): Promise<TrendPoint[]> {
  const query = new URLSearchParams({ category, periods: String(periods) })
  if (branch_id) query.set('branch_id', String(branch_id))
  return api.get<TrendPoint[]>(`${BASE}/trends?${query}`)
}

export async function getCommunitySummary(
  branch_id?: number,
): Promise<SummaryResponse> {
  const query = new URLSearchParams()
  if (branch_id) query.set('branch_id', String(branch_id))
  const qs = query.toString()
  return api.get<SummaryResponse>(`${BASE}/summary${qs ? `?${qs}` : ''}`)
}
