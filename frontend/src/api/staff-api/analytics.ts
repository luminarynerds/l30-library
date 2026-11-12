/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Staff Dashboard Types ====================

export interface StaffDashboardStats {
  checkouts_today: number
  returns_today: number
  overdue_items: number
  active_holds: number
  new_patrons_this_week: number
  total_patrons: number
  // Additional metrics from backend
  active_checkouts?: number
  overdue_count?: number
  pending_holds?: number
  ready_holds?: number
  active_patrons_30d?: number
  outstanding_fines_total?: number
  patrons_with_fines?: number
  // Lost and damaged
  lost_items_total?: number
  lost_items_this_month?: number
  damaged_items_pending?: number
  items_in_mending?: number
  claims_returned_pending?: number
  lost_item_charges_outstanding?: number
  // Outreach
  active_outreach_partners?: number
  upcoming_visits?: number
  overdue_bulk_checkouts?: number
  deposits_held_total?: number
}

export interface ActivityItem {
  id: number
  type: 'checkout' | 'return' | 'hold_placed' | 'hold_ready' | 'patron_created' | 'item_added'
  description: string
  item_title?: string
  timestamp: string
}


interface BackendActivityItem {
  activity_type: ActivityItem['type']
  description: string
  item_title?: string
  timestamp: string
}

function normalizeActivityItem(item: ActivityItem | BackendActivityItem, index: number): ActivityItem {
  if ('type' in item) {
    return {
      ...item,
      id: item.id ?? index,
    }
  }

  return {
    id: index,
    type: item.activity_type,
    description: item.description,
    ...(item.item_title !== undefined ? { item_title: item.item_title } : {}),
    timestamp: item.timestamp,
  }
}

// ==================== Reports Types ====================

export interface FinancialSummaryReport {
  total_charges: number
  total_collected: number
  total_outstanding: number
  total_waived: number
  total_credits: number
  collection_rate: number
  period_start: string | null
  period_end: string | null
}

export interface ChargesByTypeReport {
  lost_item_charges: number
  damaged_item_charges: number
  processing_fees: number
  total: number
}

export interface InventorySummaryReport {
  total_lost: number
  lost_by_patron: number
  lost_in_transit: number
  claims_returned: number
  total_damaged: number
  damaged_repairable: number
  damaged_withdrawn: number
  in_mending: number
  items_found: number
  period_start: string | null
  period_end: string | null
}

export interface LostByCategoryReport {
  item_type: string
  count: number
  total_value: number
  percentage_of_total: number
}

export interface LostByLocationReport {
  location: string
  count: number
  total_value: number
  percentage_of_total: number
}

export interface TrendDataReport {
  period: string
  lost_count: number
  damaged_count: number
  charges: number
  credits: number
  net: number
}

export interface PatronRiskReport {
  patron_id: number
  patron_name: string
  patron_email: string
  lost_item_count: number
  damaged_item_count: number
  claims_returned_count: number
  total_charges: number
  outstanding_balance: number
  risk_score: number
}

// ==================== Dashboard Functions ====================

export async function getStaffDashboardStats(token: string): Promise<StaffDashboardStats> {
  return await fetchApi<StaffDashboardStats>('/staff/dashboard/stats', { token })
}

export async function getStaffActivityFeed(token: string, limit = 10): Promise<ActivityItem[]> {
  const response = await fetchApi<ActivityItem[] | { data?: ActivityItem[]; activities?: BackendActivityItem[] }>(`/staff/dashboard/activity?limit=${limit}`, { token })
  const activities: (ActivityItem | BackendActivityItem)[] = Array.isArray(response)
    ? response
    : (response.data ?? response.activities ?? [])

  return activities.map((item: ActivityItem | BackendActivityItem, index: number) => normalizeActivityItem(item, index))
}

// ==================== Reports API Functions ====================

export async function getFinancialSummary(
  token: string,
  filters?: {
    start_date?: string
    end_date?: string
    location?: string
  }
): Promise<FinancialSummaryReport> {
  try {
    const params = new URLSearchParams()
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    if (filters?.location) params.set('location', filters.location)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<FinancialSummaryReport>(`/staff/lost-damaged/reports/financial-summary${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch financial summary')
    }
    throw error
  }
}

export async function getChargesByType(
  token: string,
  filters?: {
    start_date?: string
    end_date?: string
  }
): Promise<ChargesByTypeReport> {
  try {
    const params = new URLSearchParams()
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<ChargesByTypeReport>(`/staff/lost-damaged/reports/charges-by-type${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch charges by type')
    }
    throw error
  }
}

export async function getInventorySummary(
  token: string,
  filters?: {
    start_date?: string
    end_date?: string
    location?: string
  }
): Promise<InventorySummaryReport> {
  try {
    const params = new URLSearchParams()
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    if (filters?.location) params.set('location', filters.location)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<InventorySummaryReport>(`/staff/lost-damaged/reports/inventory-summary${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch inventory summary')
    }
    throw error
  }
}

export async function getLostByCategory(
  token: string,
  filters?: {
    start_date?: string
    end_date?: string
  }
): Promise<LostByCategoryReport[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LostByCategoryReport[]>(`/staff/lost-damaged/reports/lost-by-category${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch lost by category')
    }
    throw error
  }
}

export async function getLostByLocation(
  token: string,
  filters?: {
    start_date?: string
    end_date?: string
  }
): Promise<LostByLocationReport[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.start_date) params.set('start_date', filters.start_date)
    if (filters?.end_date) params.set('end_date', filters.end_date)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LostByLocationReport[]>(`/staff/lost-damaged/reports/lost-by-location${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch lost by location')
    }
    throw error
  }
}

export async function getMonthlyTrend(token: string, months: number = 12): Promise<TrendDataReport[]> {
  try {
    return await fetchApi<TrendDataReport[]>(`/staff/lost-damaged/reports/monthly-trend?months=${months}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch monthly trend')
    }
    throw error
  }
}

export async function getPatronRiskReportLostDamaged(
  token: string,
  filters?: {
    min_incidents?: number
    days_back?: number
    limit?: number
  }
): Promise<PatronRiskReport[]> {
  try {
    const params = new URLSearchParams()
    if (filters?.min_incidents) params.set('min_incidents', filters.min_incidents.toString())
    if (filters?.days_back) params.set('days_back', filters.days_back.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronRiskReport[]>(`/staff/lost-damaged/reports/patron-risk${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron risk report')
    }
    throw error
  }
}
