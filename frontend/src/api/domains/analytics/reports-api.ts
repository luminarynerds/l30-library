/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import * as Sentry from "@/lib/sentry-lazy"
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Enhanced Dashboard Stats types (migrated from services/staff/)
export interface HourlyStats {
  hour: number
  checkouts: number
  returns: number
  total_activity: number
}

export interface ItemTrend {
  item_id: number
  title: string
  author?: string
  checkouts_today: number
  holds_current: number
  trend_score: number
}

export interface ComparisonStats {
  checkouts_today: number
  checkouts_last_week_same_day: number
  checkouts_last_year_same_day: number
  returns_today: number
  returns_last_week_same_day: number
  returns_last_year_same_day: number
  percent_change_from_last_week: number
  percent_change_from_last_year: number
}

export interface EnhancedDashboardStats {
  checkouts_today: number
  returns_today: number
  total_transactions_today: number
  pending_holds: number
  ready_holds: number
  items_on_hold_shelf: number
  total_items_on_hold: number
  active_checkouts: number
  overdue_count: number
  busiest_hour: number
  busiest_hour_activity: number
  hourly_breakdown: HourlyStats[]
  comparison: ComparisonStats
  trending_items: ItemTrend[]
  total_patrons: number
  active_patrons_30d: number
}

export async function getEnhancedDashboardStats(token: string): Promise<EnhancedDashboardStats | null> {
  try {
    return await fetchApi<EnhancedDashboardStats>('/staff/dashboard/stats/enhanced', { token })
  } catch (error: unknown) {
    Sentry.captureException(error instanceof Error ? error : new Error(String(error)))
    return null
  }
}

// Types for circulation reports
export interface DailyStats {
  date: string
  checkouts_today: number
  returns_today: number
  active_checkouts: number
  overdue_count: number
}

export interface HoldStats {
  pending_holds: number
  ready_for_pickup: number
  avg_wait_days: number | null
}

export interface FineStats {
  outstanding_total: number
  paid_this_month: number
  waived_this_month: number
  patrons_with_fines: number
}

export interface PopularItem {
  catalog_item_id: number
  title: string
  author: string
  checkout_count: number
  item_type?: string // Optional for backward compatibility with basic endpoint
}

export interface OverdueItem {
  checkout_id: number
  patron_name: string
  patron_email: string
  item_title: string
  due_date: string
  days_overdue: number
}

export interface TrendDataPoint {
  date: string
  checkouts: number
}

export interface InventorySummary {
  total_copies: number
  total_titles: number
  by_condition: Record<string, number>
}

export interface PopularItemsResponse {
  items: PopularItem[]
}

export interface OverdueItemsResponse {
  items: OverdueItem[]
}

export interface CirculationTrendsResponse {
  data: TrendDataPoint[]
}

// Day-specific drill-down types
export interface CheckoutDetail {
  checkout_id: number
  item_title: string
  item_author: string
  patron_name: string
  checked_out_at: string
}

export interface ReturnDetail {
  checkout_id: number
  item_title: string
  item_author: string
  patron_name: string
  returned_at: string
}

export interface DailyDrillDownData {
  date: string
  checkouts: CheckoutDetail[]
  returns: ReturnDetail[]
  patron_count: number
}

// Comparison types
export interface ComparisonTrendDataPoint extends TrendDataPoint {
  checkouts_previous?: number
  checkouts_previous_year?: number
}

// Common date range parameters
export interface DateRangeParams {
  start_date?: string
  end_date?: string
}

// Request parameter types
export interface PopularItemsParams extends DateRangeParams {
  days?: number
  limit?: number
}

export interface OverdueItemsParams {
  per_page?: number
  page?: number
}

export type Granularity = "hourly" | "daily" | "weekly" | "monthly"

export interface CirculationTrendsParams extends DateRangeParams {
  days?: number
  granularity?: Granularity
  compare_previous_period?: boolean
  compare_previous_year?: boolean
}

export interface DailyDetailsParams {
  date: string
}

// Build query string from params object
function buildQueryString(params?: Record<string, unknown> | object): string {
  if (!params || Object.keys(params).length === 0) {
    return ''
  }
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.set(key, String(value))
    }
  })
  return searchParams.toString() ? `?${searchParams}` : ''
}

// Circulation Reports API Functions

export async function getDailyStats(params?: DateRangeParams): Promise<DailyStats> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    return await fetchApi<DailyStats>(`/reports/circulation/daily${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getHoldsStats(_params?: DateRangeParams): Promise<HoldStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<HoldStats>('/reports/circulation/holds', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getFineStats(params?: DateRangeParams): Promise<FineStats> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    return await fetchApi<FineStats>(`/reports/circulation/fines${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getPopularItemsFromReports(params?: PopularItemsParams): Promise<PopularItem[]> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    const response = await fetchApi<PopularItemsResponse>(`/reports/circulation/popular${query}`, { ...(token ? { token } : {}) })
    return response.items || []
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getOverdueItems(params?: OverdueItemsParams): Promise<OverdueItem[]> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    const response = await fetchApi<OverdueItemsResponse>(`/reports/circulation/overdue${query}`, { ...(token ? { token } : {}) })
    return response.items || []
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getCirculationTrendsFromReports(params?: CirculationTrendsParams): Promise<TrendDataPoint[]> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    const response = await fetchApi<CirculationTrendsResponse>(`/reports/circulation/trends${query}`, { ...(token ? { token } : {}) })
    return response.data || []
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getDailyDetails(params: DailyDetailsParams): Promise<DailyDrillDownData> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    return await fetchApi<DailyDrillDownData>(`/reports/circulation/daily-details${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getCirculationTrendsWithComparison(
  params?: CirculationTrendsParams
): Promise<ComparisonTrendDataPoint[]> {
  const token = getAccessToken()
  const query = buildQueryString(params)
  try {
    const response = await fetchApi<{ data: ComparisonTrendDataPoint[] }>(`/reports/circulation/trends${query}`, { ...(token ? { token } : {}) })
    return response.data || []
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function getInventorySummary(): Promise<InventorySummary> {
  const token = getAccessToken()
  try {
    return await fetchApi<InventorySummary>('/reports/inventory/summary', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

export async function fetchAllCirculationReports(
  trendDays: number = 30,
  dateRange?: DateRangeParams,
  granularity?: Granularity,
): Promise<{
  daily: DailyStats
  holds: HoldStats
  fines: FineStats
  popular: PopularItem[]
  overdue: OverdueItem[]
  trends: TrendDataPoint[]
  inventory: InventorySummary
}> {
  const results = await Promise.allSettled([
    getDailyStats(dateRange),
    getHoldsStats(dateRange),
    getFineStats(dateRange),
    getPopularItemsFromReports({ days: trendDays, limit: 10, ...dateRange }),
    getOverdueItems({ per_page: 10 }),
    getCirculationTrendsFromReports({ days: trendDays, granularity, ...dateRange }),
    getInventorySummary(),
  ])

  const defaultDaily: DailyStats = { date: new Date().toISOString().slice(0, 10), checkouts_today: 0, returns_today: 0, active_checkouts: 0, overdue_count: 0 }
  const defaultHolds: HoldStats = { pending_holds: 0, ready_for_pickup: 0, avg_wait_days: null }
  const defaultFines: FineStats = { outstanding_total: 0, paid_this_month: 0, waived_this_month: 0, patrons_with_fines: 0 }
  const defaultInventory: InventorySummary = { total_copies: 0, total_titles: 0, by_condition: {} }

  return {
    daily: results[0].status === 'fulfilled' ? results[0].value : defaultDaily,
    holds: results[1].status === 'fulfilled' ? results[1].value : defaultHolds,
    fines: results[2].status === 'fulfilled' ? results[2].value : defaultFines,
    popular: results[3].status === 'fulfilled' ? results[3].value : [],
    overdue: results[4].status === 'fulfilled' ? results[4].value : [],
    trends: results[5].status === 'fulfilled' ? results[5].value : [],
    inventory: results[6].status === 'fulfilled' ? results[6].value : defaultInventory,
  }
}

// Financial Reports API Functions

export interface ClearCacheResponse {
  status: string
  message: string
}

export async function clearFinancialCache(): Promise<ClearCacheResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ClearCacheResponse>('/financial/cache/clear', {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || `Request failed with status ${error.status}`)
    }
    throw error
  }
}

// Lost & Damaged Reports Types and Functions

export interface FinancialSummary {
  total_charges: number
  total_collected: number
  total_outstanding: number
  total_waived: number
  total_credits: number
  collection_rate: number
}

export interface ChargesByType {
  lost_item_charges: number
  damaged_item_charges: number
  processing_fees: number
}

export interface LostDamagedInventorySummary {
  total_lost: number
  total_damaged: number
  lost_by_patron: number
  lost_in_transit: number
  in_mending: number
  items_found: number
}

export interface LostByCategory {
  item_type: string
  count: number
  total_value: number
}

export interface LostByLocation {
  location: string
  count: number
  total_value: number
}

export interface MonthlyTrend {
  period: string
  lost_count: number
  damaged_count: number
  charges: number
  net: number
}

export interface PatronRisk {
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

export async function fetchAllLostDamagedReports(
  startDate?: string,
  endDate?: string,
  location?: string
): Promise<{
  financialSummary: FinancialSummary
  chargesByType: ChargesByType
  inventorySummary: LostDamagedInventorySummary
  lostByCategory: LostByCategory[]
  lostByLocation: LostByLocation[]
  monthlyTrend: MonthlyTrend[]
  patronRisk: PatronRisk[]
}> {
  const token = getAccessToken()
  const dateParams = new URLSearchParams()
  if (startDate) dateParams.append('start_date', startDate)
  if (endDate) dateParams.append('end_date', endDate)
  const dateQuery = dateParams.toString() ? `?${dateParams.toString()}` : ''

  const locationParams = new URLSearchParams(dateParams)
  if (location) locationParams.append('location', location)
  const locationQuery = locationParams.toString() ? `?${locationParams.toString()}` : ''

  const opts = { ...(token ? { token } : {}) }

  const results = await Promise.allSettled([
    fetchApi<FinancialSummary>(`/staff/lost-damaged/reports/financial-summary${locationQuery}`, opts),
    fetchApi<ChargesByType>(`/staff/lost-damaged/reports/charges-by-type${dateQuery}`, opts),
    fetchApi<LostDamagedInventorySummary>(`/staff/lost-damaged/reports/inventory-summary${locationQuery}`, opts),
    fetchApi<LostByCategory[]>(`/staff/lost-damaged/reports/lost-by-category${dateQuery}`, opts),
    fetchApi<LostByLocation[]>(`/staff/lost-damaged/reports/lost-by-location${dateQuery}`, opts),
    fetchApi<MonthlyTrend[]>(`/staff/lost-damaged/reports/monthly-trend`, opts),
    fetchApi<PatronRisk[]>(`/staff/lost-damaged/reports/patron-risk`, opts),
  ])

  const defaultFinancial: FinancialSummary = { total_charges: 0, total_collected: 0, total_outstanding: 0, total_waived: 0, total_credits: 0, collection_rate: 0 }
  const defaultCharges: ChargesByType = { lost_item_charges: 0, damaged_item_charges: 0, processing_fees: 0 }
  const defaultInventory: LostDamagedInventorySummary = { total_lost: 0, total_damaged: 0, lost_by_patron: 0, lost_in_transit: 0, in_mending: 0, items_found: 0 }

  return {
    financialSummary: results[0].status === 'fulfilled' ? results[0].value : defaultFinancial,
    chargesByType: results[1].status === 'fulfilled' ? results[1].value : defaultCharges,
    inventorySummary: results[2].status === 'fulfilled' ? results[2].value : defaultInventory,
    lostByCategory: results[3].status === 'fulfilled' ? results[3].value : [],
    lostByLocation: results[4].status === 'fulfilled' ? results[4].value : [],
    monthlyTrend: results[5].status === 'fulfilled' ? results[5].value : [],
    patronRisk: results[6].status === 'fulfilled' ? results[6].value : [],
  }
}

// Makerspace Reports Types and Functions

export interface ResourceUtilizationItem {
  resource_id: number
  resource_name: string
  total_checkouts: number
  total_hours: number
  unique_users: number
  utilization_rate: number
}

export interface RevenueReport {
  total_revenue: number
  revenue_by_category: Record<string, number>
  monthly_trend: Array<{
    month: string
    revenue: number
  }>
}

export interface PopularEquipmentItem {
  equipment_id: number
  equipment_name: string
  checkout_count: number
  total_hours: number
  popularity_score: number
}

export interface IncidentSummaryReport {
  total_incidents: number
  incidents_by_severity: Record<string, number>
  recent_incidents: Array<{
    incident_id: number
    description: string
    severity: string
    date: string
  }>
}

export async function fetchAllMakerspaceReports(
  startDate?: string,
  endDate?: string,
  resourceType?: string
): Promise<{
  utilization: ResourceUtilizationItem[]
  revenue: RevenueReport
  popular: PopularEquipmentItem[]
  incidents: IncidentSummaryReport
}> {
  const token = getAccessToken()
  const dateParams = new URLSearchParams()
  if (startDate) dateParams.append('start_date', startDate)
  if (endDate) dateParams.append('end_date', endDate)
  const dateQuery = dateParams.toString() ? `?${dateParams.toString()}` : ''

  const utilParams = new URLSearchParams(dateParams)
  if (resourceType) utilParams.append('resource_id', resourceType)
  const utilQuery = utilParams.toString() ? `?${utilParams.toString()}` : ''

  const opts = { ...(token ? { token } : {}) }

  const defaultRevenue: RevenueReport = { total_revenue: 0, revenue_by_category: {}, monthly_trend: [] }
  const defaultIncidents: IncidentSummaryReport = { total_incidents: 0, incidents_by_severity: {}, recent_incidents: [] }

  const results = await Promise.allSettled([
    fetchApi<ResourceUtilizationItem[]>(`/staff/makerspace/reports/utilization${utilQuery}`, opts),
    fetchApi<RevenueReport>(`/staff/makerspace/reports/revenue${dateQuery}`, opts),
    fetchApi<PopularEquipmentItem[]>(`/staff/makerspace/reports/popular-equipment${dateQuery}`, opts),
    fetchApi<IncidentSummaryReport>(`/staff/makerspace/reports/incidents${dateQuery}`, opts),
  ])

  return {
    utilization: results[0].status === 'fulfilled' ? results[0].value : [],
    revenue: results[1].status === 'fulfilled' ? results[1].value : defaultRevenue,
    popular: results[2].status === 'fulfilled' ? results[2].value : [],
    incidents: results[3].status === 'fulfilled' ? results[3].value : defaultIncidents,
  }
}

