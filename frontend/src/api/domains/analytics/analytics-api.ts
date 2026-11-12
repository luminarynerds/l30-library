/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/* eslint-disable @typescript-eslint/no-empty-object-type */
 
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'

// Types - Aligned with backend schemas

export interface TrendData {
  direction: 'up' | 'down' | 'stable'
  change_percentage: number
  previous_value: number
  current_value: number
}

export interface StatsMetadata {
  generated_at: string
  cached: boolean
  cache_ttl: number
  time_window: string
}

export interface CirculationAnalytics {
  total_checkouts: number
  active_checkouts: number
  checkouts_today: number
  returns_today: number
  overdue_count: number
  checkout_trend: TrendData | null
  overdue_trend: TrendData | null
  unique_patrons: number
  avg_daily_checkouts: number
  turnover_rate: number
  metadata: StatsMetadata
}

export interface DormancyBreakdown {
  active_count: number
  active_percentage: number
  drifting_count: number
  drifting_percentage: number
  dormant_count: number
  dormant_percentage: number
}

export interface CollectionHealth {
  total_items: number
  total_available: number
  dormancy: DormancyBreakdown
  utilization_rate: number
  avg_checkouts_per_item: number
  never_checked_out: number
  damaged_items: number
  missing_items: number
  metadata: StatsMetadata
}

export interface DriftingItem {
  catalog_item_id: number
  title: string
  author: string | null
  days_since_checkout: number
  copy_count: number
}

export interface PatronEngagement {
  total_patrons: number
  active_patrons: number
  new_patrons: number
  dormant_patrons: number
  engagement_rate: number
  avg_checkouts_per_patron: number
  retention_rate: number
  engagement_trend: TrendData | null
  new_patrons_trend: TrendData | null
  metadata: StatsMetadata
}

export interface TopReader {
  user_id: number
  user_name: string
  total_minutes: number
  total_books: number
  reading_streak: number | null
}

export interface ReadingAnalytics {
  total_minutes_read: number
  total_books_completed: number
  total_pages_read: number
  total_participants: number
  avg_minutes_per_session: number
  avg_pages_per_session: number
  avg_rating: number | null
  minutes_trend: TrendData | null
  books_trend: TrendData | null
  metadata: StatsMetadata
}

export interface FineAnalytics {
  outstanding_total: number
  patrons_with_fines: number
  paid_this_month: number
  waived_this_month: number
  collection_rate: number
  outstanding_trend: TrendData | null
  metadata: StatsMetadata
}

export interface PopularItem {
  catalog_item_id: number
  title: string
  author: string | null
  checkout_count: number
  item_type: string | null
}

export interface CirculationTrend {
  date: string
  checkouts: number
  returns: number | null
}

export interface AnalyticsDashboard {
  circulation: CirculationAnalytics
  reading: ReadingAnalytics
  patron_engagement: PatronEngagement
  collection_health: CollectionHealth
  fines: FineAnalytics
  metadata: StatsMetadata
}

// Analytics API Functions
export async function getAnalyticsDashboard(): Promise<AnalyticsDashboard> {
  const token = getAccessToken()
  try {
    return await fetchApi<AnalyticsDashboard>('/reports/analytics/dashboard', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCirculationAnalytics(params?: { days?: number }): Promise<CirculationAnalytics> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<CirculationAnalytics>(`/reports/analytics/circulation${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCollectionHealth(): Promise<CollectionHealth> {
  const token = getAccessToken()
  try {
    return await fetchApi<CollectionHealth>('/reports/analytics/collection-health', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getDriftingItems(params?: { limit?: number }): Promise<{ items: DriftingItem[]; total_drifting: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: DriftingItem[]; total_drifting: number }>(`/reports/analytics/drifting-items${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getPatronEngagement(params?: { days?: number }): Promise<PatronEngagement> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PatronEngagement>(`/reports/analytics/patron-engagement${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getTopReaders(params?: { limit?: number; days?: number }): Promise<{ readers: TopReader[]; period_days: number; total_readers: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ readers: TopReader[]; period_days: number; total_readers: number }>(`/reports/analytics/top-readers${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingAnalytics(params?: { days?: number }): Promise<ReadingAnalytics> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<ReadingAnalytics>(`/reports/analytics/reading${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getFineAnalytics(params?: { days?: number }): Promise<FineAnalytics> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<FineAnalytics>(`/reports/analytics/fines${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getPopularItems(params?: { limit?: number; days?: number }): Promise<{ items: PopularItem[]; period_days: number; total_unique_items: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: PopularItem[]; period_days: number; total_unique_items: number }>(`/reports/analytics/popular-items${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCirculationTrends(params?: { days?: number }): Promise<{ data: CirculationTrend[]; period_days: number; avg_checkouts: number; peak_day: string | null; peak_count: number | null }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ data: CirculationTrend[]; period_days: number; avg_checkouts: number; peak_day: string | null; peak_count: number | null }>(`/reports/analytics/circulation-trends${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Extended Analytics Types for Dashboard Enhancement
// Note: TrendData, StatsMetadata, and DormancyBreakdown are already defined above

export interface CirculationStatsEnhanced extends CirculationAnalytics {}

export interface CollectionHealthEnhanced extends CollectionHealth {}
export interface PatronEngagementEnhanced extends PatronEngagement {}
export interface ReadingStatsEnhanced extends ReadingAnalytics {}
export interface FineStatsEnhanced extends FineAnalytics {}

export interface OverdueItem {
  checkout_id: number
  patron_name: string | null
  patron_email: string | null
  item_title: string | null
  due_date: string | null
  days_overdue: number
}

export interface OverdueItemsResponse {
  items: OverdueItem[]
  total: number
  page: number
}

export interface HoldStats {
  pending_holds: number
  ready_for_pickup: number
  avg_wait_days: number | null
}

export interface InventorySummary {
  total_copies: number
  total_titles: number
  by_condition: Record<string, number>
}

export interface CirculationTrendsEnhanced {
  data: {
    date: string
    checkouts: number
    returns: number | null
  }[]
  period_days: number
  avg_checkouts: number
  peak_day: string | null
  peak_count: number | null
}

export interface DriftingItemEnhanced extends DriftingItem {}
export interface DriftingItemsResponseEnhanced {
  items: DriftingItemEnhanced[]
  total_drifting: number
}

// Enhanced API Functions

export async function getCirculationStatsEnhanced(params?: { days?: number }): Promise<CirculationStatsEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<CirculationStatsEnhanced>(`/reports/analytics/circulation${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCollectionHealthEnhanced(): Promise<CollectionHealthEnhanced> {
  const token = getAccessToken()
  try {
    return await fetchApi<CollectionHealthEnhanced>('/reports/analytics/collection-health', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getPatronEngagementEnhanced(params?: { days?: number }): Promise<PatronEngagementEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<PatronEngagementEnhanced>(`/reports/analytics/patron-engagement${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getReadingStatsEnhanced(params?: { days?: number }): Promise<ReadingStatsEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<ReadingStatsEnhanced>(`/reports/analytics/reading${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getFineStatsEnhanced(params?: { days?: number }): Promise<FineStatsEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<FineStatsEnhanced>(`/reports/analytics/fines${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getOverdueItems(params?: { page?: number; per_page?: number }): Promise<OverdueItemsResponse> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<OverdueItemsResponse>(`/reports/circulation/overdue${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getHoldStats(): Promise<HoldStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<HoldStats>('/reports/circulation/holds', { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
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
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getCirculationTrendsEnhanced(params?: { days?: number }): Promise<CirculationTrendsEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.days) searchParams.set('days', params.days.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<CirculationTrendsEnhanced>(`/reports/analytics/circulation-trends${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getDriftingItemsEnhanced(params?: { limit?: number }): Promise<DriftingItemsResponseEnhanced> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', params.limit.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<DriftingItemsResponseEnhanced>(`/reports/analytics/drifting-items${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// ==================== Staff Analytics Dashboard Types ====================

export interface CirculationTrendPoint {
  date: string
  checkouts: number
  returns: number
}

export interface DayOfWeekData {
  day: string
  checkouts: number
  returns: number
}

export interface CirculationTrendData {
  totalCheckouts: number
  totalReturns: number
  dailyAverage: number
  overdueCount: number
  checkoutChange: number
  returnChange: number
  overdueChange: number
  trends: CirculationTrendPoint[]
  byDayOfWeek: DayOfWeekData[]
}

export interface PopularItemEntry {
  itemId: number
  title: string
  author: string
  count: number
  category: string
}

export interface TrendingItem extends PopularItemEntry {
  growthPercent: number
}

export interface CategoryCount {
  category: string
  count: number
}

export interface PopularItemData {
  topCheckouts: PopularItemEntry[]
  topHolds: PopularItemEntry[]
  trending: TrendingItem[]
  byCategory: CategoryCount[]
}

export interface FineTrendPoint {
  date: string
  collected: number
  assessed: number
}

export interface FinesSummaryData {
  totalOutstanding: number
  totalCollected: number
  totalWaived: number
  patronsWithFines: number
  collectionChange: number
  trends: FineTrendPoint[]
}

export interface FineAgingBracket {
  bracket: string
  amount: number
  count: number
}

export interface FineAgingData {
  brackets: FineAgingBracket[]
  totalOutstanding: number
}

export interface PaymentMethodEntry {
  method: string
  amount: number
  count: number
  percentage: number
}

export interface PaymentMethodData {
  methods: PaymentMethodEntry[]
  totalAmount: number
}

export interface WaiverReason {
  reason: string
  count: number
  amount: number
}

export interface WaivedFineData {
  totalWaived: number
  count: number
  averageAmount: number
  topReasons: WaiverReason[]
}

export interface RegistrationTrendPoint {
  date: string
  registrations: number
}

export interface ActivityDistribution {
  range: string
  count: number
}

export interface TopActivePatron {
  patronId: number
  name: string
  checkoutCount: number
}

export interface PatronStatsData {
  totalPatrons: number
  newRegistrations: number
  activePatrons: number
  blockedPatrons: number
  registrationChange: number
  registrationTrends: RegistrationTrendPoint[]
  activityDistribution: ActivityDistribution[]
  topActivePatrons: TopActivePatron[]
}

export interface CategoryUsage {
  category: string
  titles: number
  copies: number
  checkouts: number
  turnoverRate: number
  percentOfCollection: number
}

export interface CollectionUsageData {
  totalTitles: number
  totalCopies: number
  turnoverRate: number
  neverCirculated: number
  byCategory: CategoryUsage[]
}

// ==================== Staff Analytics Dashboard API Functions ====================

export async function getAnalyticsCirculationTrends(
  token: string,
  startDate: string,
  endDate: string
): Promise<CirculationTrendData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<CirculationTrendData>(
    `/analytics/circulation/trends?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsPopularItems(
  token: string,
  startDate: string,
  endDate: string
): Promise<PopularItemData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<PopularItemData>(
    `/analytics/popular-items?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsFinesSummary(
  token: string,
  startDate: string,
  endDate: string
): Promise<FinesSummaryData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<FinesSummaryData>(
    `/analytics/fines/summary?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsFineAging(token: string): Promise<FineAgingData> {
  const response = await fetchApi<FineAgingData>('/analytics/fines/aging', { token })
  return response
}

export async function getAnalyticsPaymentMethods(
  token: string,
  startDate: string,
  endDate: string
): Promise<PaymentMethodData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<PaymentMethodData>(
    `/analytics/fines/payment-methods?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsWaivedFines(
  token: string,
  startDate: string,
  endDate: string
): Promise<WaivedFineData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<WaivedFineData>(
    `/analytics/fines/waived?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsPatronStats(
  token: string,
  startDate: string,
  endDate: string
): Promise<PatronStatsData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<PatronStatsData>(
    `/analytics/patrons/stats?${params}`,
    { token }
  )
  return response
}

export async function getAnalyticsCollectionUsage(
  token: string,
  startDate: string,
  endDate: string
): Promise<CollectionUsageData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<CollectionUsageData>(
    `/analytics/collection/usage?${params}`,
    { token }
  )
  return response
}

// --- Collection Details (extended analytics) ---

export interface CirculatedItem {
  catalogItemId: number
  title: string
  author: string | null
  checkoutCount: number
  lastCheckout: string | null
}

export interface CostEfficiency {
  totalReplacementCost: number
  copiesWithCost: number
  checkoutsOfCostedItems: number
  avgCostPerCirculation: number | null
}

export interface CollectionDetailsData {
  totalItems: number
  totalCheckouts: number
  avgCheckoutsPerItem: number
  avgAgeYears: number
  byCondition: Record<string, number>
  topCirculated: CirculatedItem[]
  leastCirculated: CirculatedItem[]
  costEfficiency: CostEfficiency
}

export async function getAnalyticsCollectionDetails(
  token: string,
  startDate: string,
  endDate: string,
): Promise<CollectionDetailsData> {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  })
  const response = await fetchApi<CollectionDetailsData>(
    `/analytics/collection/details?${params}`,
    { token },
  )
  return response
}
