/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { components } from '@/api/generated/schema';

// ==================== Streaming Types ====================

export type StreamingService = components['schemas']['StreamingService'];
export type StreamingContentType =
  | 'movie'
  | 'tv_series'
  | 'tv_episode'
  | 'audiobook'
  | 'ebook'
  | 'music_album'
  | 'comic'
  | 'documentary'

export type StreamingCheckoutStatus = components['schemas']['StreamingCheckoutStatus'];
export interface StreamingServiceConfig {
  id: number
  service: StreamingService
  is_active: boolean
  api_base_url: string
  library_id: string | null
  cost_per_checkout: string
  app_deep_link_template: string | null
  web_deep_link_template: string | null
  created_at: string
  updated_at: string
}

export interface StreamingBudget {
  id: number
  service_config_id: number
  service_name: string | null
  fiscal_year: number
  fiscal_month: number | null
  allocated_amount: string
  spent_amount: string
  remaining_amount: string
  max_checkouts: number | null
  current_checkouts: number
  remaining_checkouts: number | null
  utilization_percentage: number
  created_at: string
  updated_at: string
}

export interface PatronStreamingLimit {
  id: number
  user_id: number
  service_config_id: number
  service_name: string | null
  monthly_limit: number
  current_month_checkouts: number
  remaining_checkouts: number
  limit_reset_date: string
}

export interface DefaultPatronStreamingLimit {
  id: number
  service_config_id: number
  user_role: string
  monthly_limit: number
  created_at: string
}

export interface StreamingCatalogItem {
  id: number
  service_config_id: number
  service_name: string | null
  external_id: string
  title: string
  author: string | null
  description: string | null
  content_type: StreamingContentType
  isbn: string | null
  duration_minutes: number | null
  release_year: number | null
  genres: string | null
  cover_url: string | null
  rating: string | null
  is_available: boolean
  available_until: string | null
  catalog_item_id: number | null
  last_synced_at: string
  created_at: string
  app_deep_link: string | null
  web_deep_link: string | null
}

export interface StreamingCheckout {
  id: number
  user_id: number | null
  service_config_id: number
  service_name: string | null
  streaming_item_id: number | null
  external_checkout_id: string | null
  status: StreamingCheckoutStatus
  checked_out_at: string
  expires_at: string | null
  returned_at: string | null
  cost: string
  item_title: string | null
  item_content_type: StreamingContentType | null
  cover_url: string | null
  app_deep_link: string | null
  web_deep_link: string | null
}

export interface PatronStreamingOverview {
  service: StreamingService
  service_name: string
  monthly_limit: number
  current_month_checkouts: number
  remaining_checkouts: number
  limit_reset_date: string
  active_checkouts: StreamingCheckout[]
  is_available: boolean
}

export interface PatronStreamingDashboard {
  services: PatronStreamingOverview[]
  total_active_checkouts: number
  recent_checkouts: StreamingCheckout[]
}

export interface UnifiedSearchResponse {
  items: StreamingCatalogItem[]
  total_count: number
  page: number
  page_size: number
  total_pages: number
  services_searched: string[]
  query: string
}

export interface CatalogStreamingAvailability {
  catalog_item_id: number
  catalog_item_title: string
  streaming_options: StreamingCatalogItem[]
  has_streaming: boolean
}

export interface BulkStreamingAvailability {
  items: CatalogStreamingAvailability[]
}

export interface DeepLinkResponse {
  streaming_item_id: number
  service: StreamingService
  title: string
  app_deep_link: string | null
  web_deep_link: string | null
  requires_checkout: boolean
  is_checked_out: boolean
}

export interface StreamingDashboardStats {
  total_checkouts_this_month: number
  total_cost_this_month: string
  unique_patrons_this_month: number
  average_cost_per_checkout: string
  service_stats: Array<{
    service: string
    checkouts: number
    cost: number
    unique_patrons: number
  }>
  total_budget_allocated: string
  total_budget_spent: string
  budget_utilization_percentage: number
  top_titles: Array<{
    title: string
    checkouts: number
    content_type: StreamingContentType | null
  }>
  checkouts_by_content_type: Record<string, number>
  checkouts_trend: Array<{
    date: string
    checkouts: number
  }>
}

export interface CollectionDevelopmentReport {
  report_period_start: string
  report_period_end: string
  most_watched_titles: Array<{
    title: string
    checkouts: number
    service: string | null
    content_type: string | null
  }>
  most_watched_genres: Array<{
    genre: string
    checkouts: number
  }>
  most_active_content_types: Array<{
    content_type: string
    checkouts: number
  }>
  total_cost: string
  cost_by_service: Record<string, number>
  cost_by_content_type: Record<string, number>
  cost_per_checkout_by_service: Record<string, number>
  total_unique_patrons: number
  patron_engagement_by_service: Record<string, number>
  repeat_user_rate: number
  titles_frequently_unavailable: Array<unknown>
  recommended_additions: Array<unknown>
}

// ==================== Service Configuration ====================

export async function getServiceConfigs(token: string): Promise<StreamingServiceConfig[]> {
  try {
    return await fetchApi<StreamingServiceConfig[]>('/streaming/config', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch streaming configurations')
    }
    throw error
  }
}

export async function createServiceConfig(
  token: string,
  config: {
    service: StreamingService
    api_base_url: string
    api_key?: string
    api_secret?: string
    library_id?: string
    cost_per_checkout?: string
    app_deep_link_template?: string
    web_deep_link_template?: string
  }
): Promise<StreamingServiceConfig> {
  try {
    return await fetchApi<StreamingServiceConfig>('/streaming/config', {
      method: 'POST',
      token,
      body: config,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create streaming configuration')
    }
    throw error
  }
}

export async function updateServiceConfig(
  token: string,
  configId: number,
  updates: Partial<{
    is_active: boolean
    api_base_url: string
    api_key: string
    api_secret: string
    library_id: string
    cost_per_checkout: string
    app_deep_link_template: string
    web_deep_link_template: string
  }>
): Promise<StreamingServiceConfig> {
  try {
    return await fetchApi<StreamingServiceConfig>(`/streaming/config/${configId}`, {
      method: 'PATCH',
      token,
      body: updates,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update streaming configuration')
    }
    throw error
  }
}

// ==================== Budget Management ====================

export async function getBudgets(
  token: string,
  options?: {
    service_config_id?: number
    fiscal_year?: number
  }
): Promise<StreamingBudget[]> {
  const params = new URLSearchParams()
  if (options?.service_config_id) params.append('service_config_id', String(options.service_config_id))
  if (options?.fiscal_year) params.append('fiscal_year', String(options.fiscal_year))

  const queryString = params.toString()
  const url = `/streaming/budgets${queryString ? `?${queryString}` : ''}`

  try {
    return await fetchApi<StreamingBudget[]>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch streaming budgets')
    }
    throw error
  }
}

export async function createBudget(
  token: string,
  budget: {
    service_config_id: number
    fiscal_year: number
    allocated_amount: string
    fiscal_month?: number
    max_checkouts?: number
  }
): Promise<StreamingBudget> {
  try {
    return await fetchApi<StreamingBudget>('/streaming/budgets', {
      method: 'POST',
      token,
      body: budget,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create streaming budget')
    }
    throw error
  }
}

// ==================== Patron Limits ====================

export async function getDefaultLimits(
  token: string,
  serviceConfigId?: number
): Promise<DefaultPatronStreamingLimit[]> {
  const url = serviceConfigId
    ? `/streaming/limits/defaults?service_config_id=${serviceConfigId}`
    : '/streaming/limits/defaults'

  try {
    return await fetchApi<DefaultPatronStreamingLimit[]>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch default limits')
    }
    throw error
  }
}

export async function setDefaultLimit(
  token: string,
  data: {
    service_config_id: number
    user_role: string
    monthly_limit: number
  }
): Promise<DefaultPatronStreamingLimit> {
  try {
    return await fetchApi<DefaultPatronStreamingLimit>('/streaming/limits/defaults', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to set default limit')
    }
    throw error
  }
}

export async function getPatronLimits(
  token: string,
  userId: number
): Promise<PatronStreamingLimit[]> {
  try {
    return await fetchApi<PatronStreamingLimit[]>(`/streaming/limits/patron/${userId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron limits')
    }
    throw error
  }
}

export async function updatePatronLimit(
  token: string,
  userId: number,
  serviceConfigId: number,
  monthlyLimit: number
): Promise<PatronStreamingLimit> {
  try {
    return await fetchApi<PatronStreamingLimit>(
      `/streaming/limits/patron/${userId}/${serviceConfigId}`,
      {
        method: 'PATCH',
        token,
        body: { monthly_limit: monthlyLimit },
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update patron limit')
    }
    throw error
  }
}

// ==================== Search ====================

export async function searchStreaming(
  token: string,
  options: {
    query: string
    content_type?: StreamingContentType
    service?: StreamingService
    page?: number
    page_size?: number
  }
): Promise<UnifiedSearchResponse> {
  const params = new URLSearchParams()
  params.append('q', options.query)
  if (options.content_type) params.append('content_type', options.content_type)
  if (options.service) params.append('service', options.service)
  if (options.page) params.append('page', String(options.page))
  if (options.page_size) params.append('per_page', String(options.page_size))

  try {
    return await fetchApi<UnifiedSearchResponse>(`/streaming/search?${params.toString()}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Search failed')
    }
    throw error
  }
}

export async function searchStreamingAdvanced(
  token: string,
  searchQuery: {
    query: string
    content_types?: StreamingContentType[]
    services?: StreamingService[]
    include_unavailable?: boolean
    page?: number
    page_size?: number
  }
): Promise<UnifiedSearchResponse> {
  try {
    return await fetchApi<UnifiedSearchResponse>('/streaming/search', {
      method: 'POST',
      token,
      body: searchQuery,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Search failed')
    }
    throw error
  }
}

// ==================== Checkouts ====================

export async function checkoutStreamingContent(
  token: string,
  streamingItemId: number
): Promise<StreamingCheckout> {
  try {
    return await fetchApi<StreamingCheckout>('/streaming/checkouts', {
      method: 'POST',
      token,
      body: { streaming_item_id: streamingItemId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Checkout failed')
    }
    throw error
  }
}

export async function returnStreamingContent(
  token: string,
  checkoutId: number
): Promise<{ ok: boolean; message: string }> {
  try {
    return await fetchApi<{ ok: boolean; message: string }>(`/streaming/return/${checkoutId}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Return failed')
    }
    throw error
  }
}

export async function getMyStreamingCheckouts(
  token: string,
  status?: StreamingCheckoutStatus
): Promise<StreamingCheckout[]> {
  const url = status ? `/streaming/checkouts?status=${status}` : '/streaming/checkouts'

  try {
    return await fetchApi<StreamingCheckout[]>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch checkouts')
    }
    throw error
  }
}

export async function getUserStreamingCheckouts(
  token: string,
  userId: number,
  status?: StreamingCheckoutStatus
): Promise<StreamingCheckout[]> {
  const url = status
    ? `/streaming/checkouts/patron/${userId}?status=${status}`
    : `/streaming/checkouts/patron/${userId}`

  try {
    return await fetchApi<StreamingCheckout[]>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch user checkouts')
    }
    throw error
  }
}

// ==================== Patron Dashboard ====================

export async function getPatronStreamingDashboard(token: string): Promise<PatronStreamingDashboard> {
  try {
    return await fetchApi<PatronStreamingDashboard>('/streaming/dashboard', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch streaming dashboard')
    }
    throw error
  }
}

// ==================== Catalog Integration ====================

export async function getStreamingAvailability(
  token: string,
  catalogItemId: number
): Promise<CatalogStreamingAvailability> {
  try {
    return await fetchApi<CatalogStreamingAvailability>(`/streaming/availability/${catalogItemId}`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check streaming availability')
    }
    throw error
  }
}

export async function getBulkStreamingAvailability(
  token: string,
  catalogItemIds: number[]
): Promise<BulkStreamingAvailability> {
  try {
    return await fetchApi<BulkStreamingAvailability>('/streaming/availability/bulk', {
      method: 'POST',
      token,
      body: catalogItemIds,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to check streaming availability')
    }
    throw error
  }
}

export async function linkStreamingToCatalog(
  token: string,
  streamingItemId: number,
  catalogItemId: number
): Promise<{ ok: boolean; message: string }> {
  try {
    return await fetchApi<{ ok: boolean; message: string }>(
      `/streaming/link/${streamingItemId}/catalog/${catalogItemId}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to link streaming item')
    }
    throw error
  }
}

// ==================== Deep Links ====================

export async function getDeepLink(token: string, streamingItemId: number): Promise<DeepLinkResponse> {
  try {
    return await fetchApi<DeepLinkResponse>(`/streaming/deeplink/${streamingItemId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get deep link')
    }
    throw error
  }
}

// ==================== Analytics & Reports (Staff) ====================

export async function getStreamingDashboardStats(
  token: string,
  options?: {
    start_date?: string
    end_date?: string
  }
): Promise<StreamingDashboardStats> {
  const params = new URLSearchParams()
  if (options?.start_date) params.append('start_date', options.start_date)
  if (options?.end_date) params.append('end_date', options.end_date)

  const queryString = params.toString()
  const url = `/streaming/dashboard/stats${queryString ? `?${queryString}` : ''}`

  try {
    return await fetchApi<StreamingDashboardStats>(url, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch dashboard stats')
    }
    throw error
  }
}

export async function getCollectionDevelopmentReport(
  token: string,
  startDate: string,
  endDate: string
): Promise<CollectionDevelopmentReport> {
  const params = new URLSearchParams()
  params.append('start_date', startDate)
  params.append('end_date', endDate)

  try {
    return await fetchApi<CollectionDevelopmentReport>(
      `/streaming/reports/collection-development?${params.toString()}`,
      { token }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch collection development report')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function formatContentType(contentType: StreamingContentType): string {
  const labels: Record<StreamingContentType, string> = {
    movie: 'Movie',
    tv_series: 'TV Series',
    tv_episode: 'TV Episode',
    audiobook: 'Audiobook',
    ebook: 'eBook',
    music_album: 'Music Album',
    comic: 'Comic',
    documentary: 'Documentary',
  }
  return labels[contentType] || contentType
}

export function formatServiceName(service: StreamingService): string {
  const labels: Partial<Record<StreamingService, string>> = {
    palace: 'Palace Project',
  }
  return labels[service] || service
}

export function getServiceIcon(service: StreamingService): string {
  // Return icon identifiers for use with icon libraries
  const icons: Partial<Record<StreamingService, string>> = {
    palace: 'book-open',
  }
  return icons[service] || 'video'
}

export function formatDuration(minutes: number | null): string {
  if (!minutes) return 'N/A'
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  const mins = minutes % 60
  return mins > 0 ? `${hours}h ${mins}m` : `${hours}h`
}

export function isCheckoutExpiringSoon(checkout: StreamingCheckout): boolean {
  if (!checkout.expires_at) return false
  const expiresAt = new Date(checkout.expires_at)
  const now = new Date()
  const hoursUntilExpiry = (expiresAt.getTime() - now.getTime()) / (1000 * 60 * 60)
  return hoursUntilExpiry <= 24 && hoursUntilExpiry > 0
}

export function getCheckoutTimeRemaining(checkout: StreamingCheckout): string {
  if (!checkout.expires_at) return 'No expiration'
  const expiresAt = new Date(checkout.expires_at)
  const now = new Date()
  const diff = expiresAt.getTime() - now.getTime()

  if (diff <= 0) return 'Expired'

  const hours = Math.floor(diff / (1000 * 60 * 60))
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))

  if (hours >= 24) {
    const days = Math.floor(hours / 24)
    return `${days} day${days > 1 ? 's' : ''} remaining`
  }

  if (hours > 0) {
    return `${hours}h ${minutes}m remaining`
  }

  return `${minutes} minutes remaining`
}
