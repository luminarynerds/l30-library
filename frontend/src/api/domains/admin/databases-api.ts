/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Database Subscriptions API Service
 *
 * Provides functions for:
 * - Public A-Z database list
 * - Database subscription management (staff/admin)
 * - Proxy configuration
 * - Vendor management
 * - Usage statistics
 */

import { fetchApi } from '@/lib/api-client'
import { getAccessToken } from '@/utils/tokenStore'
import { API_BASE } from '@/api/types'

// ============ TYPES ============

export type DatabaseCategory =
  | 'general_reference'
  | 'academic'
  | 'newspapers'
  | 'magazines'
  | 'ebooks'
  | 'audiobooks'
  | 'genealogy'
  | 'business'
  | 'legal'
  | 'health'
  | 'children'
  | 'teen'
  | 'language_learning'
  | 'test_prep'
  | 'streaming_video'
  | 'streaming_music'
  | 'diy_crafts'
  | 'automotive'
  | 'other'

export type SubscriptionStatus =
  | 'active'
  | 'expiring_soon'
  | 'expired'
  | 'cancelled'
  | 'pending'
  | 'trial'

export type ProxyType =
  | 'ezproxy'
  | 'openathens'
  | 'direct'
  | 'referrer'
  | 'shibboleth'

// Public database info (A-Z list)
export interface PublicDatabase {
  id: number
  name: string
  short_name: string | null
  description: string | null
  category: DatabaseCategory
  subjects: string[]
  proxy_url: string
  mobile_url: string | null
  help_url: string | null
  is_featured: boolean
  logo_url: string | null
  patron_types_allowed: string[]
  simultaneous_users: number | null
}

export interface DatabaseAZListResponse {
  databases: PublicDatabase[]
  total: number
  categories: string[]
}

// Vendor info
export interface DatabaseVendor {
  id: number
  name: string
  short_name: string | null
  website: string | null
  support_url: string | null
  support_email: string | null
  support_phone: string | null
  account_number: string | null
  account_rep_name: string | null
  account_rep_email: string | null
  account_rep_phone: string | null
  admin_portal_url: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface VendorBrief {
  id: number
  name: string
  short_name: string | null
  support_email: string | null
}

// Proxy configuration
export interface ProxyConfiguration {
  id: number
  name: string
  proxy_type: ProxyType
  ezproxy_base_url: string | null
  ezproxy_login_path: string
  ezproxy_url_param: string
  openathens_org_id: string | null
  openathens_entity_id: string | null
  openathens_wayfless_url: string | null
  shibboleth_entity_id: string | null
  shibboleth_discovery_url: string | null
  onsite_ip_ranges: string[]
  requires_library_card: boolean
  allows_guest_access: boolean
  is_active: boolean
  is_default: boolean
  notes: string | null
  created_at: string
  updated_at: string | null
}

// Full subscription (staff view)
export interface DatabaseSubscription {
  id: number
  name: string
  short_name: string | null
  description: string | null
  category: DatabaseCategory
  subjects: string[]
  keywords: string[]
  vendor_id: number | null
  vendor: VendorBrief | null
  access_url: string
  mobile_url: string | null
  admin_url: string | null
  help_url: string | null
  proxy_config_id: number | null
  proxy_type: ProxyType
  custom_proxy_url: string | null
  requires_proxy: boolean
  auth_method: string | null
  auth_notes: string | null
  subscription_start: string
  subscription_end: string
  trial_end: string | null
  status: SubscriptionStatus
  auto_renew: boolean
  renewal_reminder_days: number
  last_renewal_reminder: string | null
  renewal_contact_email: string | null
  renewal_notes: string | null
  annual_cost: string | null
  cost_per_use: string | null
  payment_frequency: string
  contract_number: string | null
  purchase_order: string | null
  invoice_number: string | null
  simultaneous_users: number | null
  patron_types_allowed: string[]
  branch_restrictions: string[]
  is_active: boolean
  is_featured: boolean
  display_order: number
  logo_url: string | null
  usage_stats_url: string | null
  last_usage_sync: string | null
  notes: string | null
  internal_notes: string | null
  created_at: string
  updated_at: string | null
  is_expired: boolean
  is_expiring_soon: boolean
  days_until_expiry: number
}

// Usage statistics
export interface DatabaseUsageStats {
  id: number
  subscription_id: number
  stat_year: number
  stat_month: number
  total_item_requests: number
  unique_item_requests: number
  total_item_investigations: number
  unique_item_investigations: number
  searches_regular: number
  searches_federated: number
  searches_automated: number
  total_sessions: number
  unique_users: number
  no_license: number
  onsite_sessions: number
  offsite_sessions: number
  data_source: string | null
  imported_at: string
  cost_per_use: string | null
}

// Dashboard
export interface ExpirationAlert {
  id: number
  name: string
  vendor_name: string | null
  subscription_end: string
  days_until_expiry: number
  status: SubscriptionStatus
  annual_cost: string | null
  renewal_contact_email: string | null
}

export interface SubscriptionDashboard {
  total_active: number
  total_expired: number
  total_expiring_soon: number
  total_annual_cost: string
  expiring_alerts: ExpirationAlert[]
  recently_renewed: DatabaseSubscription[]
  top_used: unknown[]
}

// Request/Create types
export interface CreateVendorRequest {
  name: string
  short_name?: string
  website?: string
  support_url?: string
  support_email?: string
  support_phone?: string
  account_number?: string
  account_rep_name?: string
  account_rep_email?: string
  account_rep_phone?: string
  admin_portal_url?: string
  notes?: string
}

export interface CreateSubscriptionRequest {
  name: string
  short_name?: string
  description?: string
  category?: DatabaseCategory
  subjects?: string[]
  keywords?: string[]
  vendor_id?: number
  access_url: string
  mobile_url?: string
  admin_url?: string
  help_url?: string
  proxy_config_id?: number
  proxy_type?: ProxyType
  custom_proxy_url?: string
  requires_proxy?: boolean
  auth_method?: string
  auth_notes?: string
  subscription_start: string
  subscription_end: string
  trial_end?: string
  auto_renew?: boolean
  renewal_reminder_days?: number
  renewal_contact_email?: string
  renewal_notes?: string
  annual_cost?: string
  cost_per_use?: string
  payment_frequency?: string
  contract_number?: string
  purchase_order?: string
  invoice_number?: string
  simultaneous_users?: number
  patron_types_allowed?: string[]
  branch_restrictions?: string[]
  is_active?: boolean
  is_featured?: boolean
  display_order?: number
  logo_url?: string
  usage_stats_url?: string
  notes?: string
  internal_notes?: string
}

export interface CreateProxyConfigRequest {
  name: string
  proxy_type?: ProxyType
  ezproxy_base_url?: string
  ezproxy_login_path?: string
  ezproxy_url_param?: string
  openathens_org_id?: string
  openathens_entity_id?: string
  openathens_wayfless_url?: string
  shibboleth_entity_id?: string
  shibboleth_discovery_url?: string
  onsite_ip_ranges?: string[]
  requires_library_card?: boolean
  allows_guest_access?: boolean
  is_active?: boolean
  is_default?: boolean
  notes?: string
}

export interface CreateUsageStatsRequest {
  stat_year: number
  stat_month: number
  total_item_requests?: number
  unique_item_requests?: number
  total_item_investigations?: number
  unique_item_investigations?: number
  searches_regular?: number
  searches_federated?: number
  searches_automated?: number
  total_sessions?: number
  unique_users?: number
  no_license?: number
  onsite_sessions?: number
  offsite_sessions?: number
  data_source?: string
}

// ============ PUBLIC FUNCTIONS ============

export async function getPublicDatabaseList(params?: {
  category?: string
  search?: string
  featured_only?: boolean
}): Promise<DatabaseAZListResponse> {
  const urlParams = new URLSearchParams()
  if (params?.category) urlParams.set('category', params.category)
  if (params?.search) urlParams.set('search', params.search)
  if (params?.featured_only) urlParams.set('featured_only', 'true')

  const query = urlParams.toString()
  return fetchApi<DatabaseAZListResponse>(
    `/databases/public/list${query ? `?${query}` : ''}`
  )
}

export async function getPublicDatabase(id: number): Promise<PublicDatabase> {
  return fetchApi<PublicDatabase>(`/databases/public/${id}`)
}

export async function logDatabaseAccess(
  id: number
): Promise<{ url: string; proxied: boolean }> {
  return fetchApi<{ url: string; proxied: boolean }>(
    `/databases/access/${id}`,
    { method: 'POST' }
  )
}

// ============ STAFF/ADMIN FUNCTIONS ============

// Proxy Configurations
export async function getProxyConfigs(): Promise<ProxyConfiguration[]> {
  return fetchApi<ProxyConfiguration[]>('/databases/proxy-configs')
}

export async function createProxyConfig(
  data: CreateProxyConfigRequest
): Promise<ProxyConfiguration> {
  return fetchApi<ProxyConfiguration>('/databases/proxy-configs', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateProxyConfig(
  id: number,
  data: Partial<CreateProxyConfigRequest>
): Promise<ProxyConfiguration> {
  return fetchApi<ProxyConfiguration>(`/databases/proxy-configs/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteProxyConfig(id: number): Promise<void> {
  await fetchApi<void>(`/databases/proxy-configs/${id}`, { method: 'DELETE' })
}

// Vendors
export async function getDatabaseVendors(): Promise<DatabaseVendor[]> {
  return fetchApi<DatabaseVendor[]>('/databases/vendors')
}

export async function createVendor(
  data: CreateVendorRequest
): Promise<DatabaseVendor> {
  return fetchApi<DatabaseVendor>('/databases/vendors', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateVendor(
  id: number,
  data: Partial<CreateVendorRequest>
): Promise<DatabaseVendor> {
  return fetchApi<DatabaseVendor>(`/databases/vendors/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteVendor(id: number): Promise<void> {
  await fetchApi<void>(`/databases/vendors/${id}`, { method: 'DELETE' })
}

// Subscriptions
export async function getSubscriptions(params?: {
  status_filter?: SubscriptionStatus
  category?: DatabaseCategory
  vendor_id?: number
  include_inactive?: boolean
}): Promise<DatabaseSubscription[]> {
  const urlParams = new URLSearchParams()
  if (params?.status_filter) urlParams.set('status_filter', params.status_filter)
  if (params?.category) urlParams.set('category', params.category)
  if (params?.vendor_id) urlParams.set('vendor_id', String(params.vendor_id))
  if (params?.include_inactive) urlParams.set('include_inactive', 'true')

  const query = urlParams.toString()
  return fetchApi<DatabaseSubscription[]>(
    `/databases/subscriptions${query ? `?${query}` : ''}`
  )
}

export async function getSubscription(id: number): Promise<DatabaseSubscription> {
  return fetchApi<DatabaseSubscription>(`/databases/subscriptions/${id}`)
}

export async function createSubscription(
  data: CreateSubscriptionRequest
): Promise<DatabaseSubscription> {
  return fetchApi<DatabaseSubscription>('/databases/subscriptions', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateSubscription(
  id: number,
  data: Partial<CreateSubscriptionRequest>
): Promise<DatabaseSubscription> {
  return fetchApi<DatabaseSubscription>(`/databases/subscriptions/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteSubscription(id: number): Promise<void> {
  await fetchApi<void>(`/databases/subscriptions/${id}`, { method: 'DELETE' })
}

// Usage Statistics
export async function getUsageStats(
  subscriptionId: number,
  year?: number
): Promise<DatabaseUsageStats[]> {
  const query = year ? `?year=${year}` : ''
  return fetchApi<DatabaseUsageStats[]>(
    `/databases/subscriptions/${subscriptionId}/usage${query}`
  )
}

// Upsert: re-posting the same period overwrites; no duplicate rows are created.
export async function addUsageStats(
  subscriptionId: number,
  data: CreateUsageStatsRequest
): Promise<DatabaseUsageStats> {
  return fetchApi<DatabaseUsageStats>(
    `/databases/subscriptions/${subscriptionId}/usage`,
    {
      method: 'POST',
      body: JSON.stringify(data),
    }
  )
}

export type UpdateUsageStatsRequest = Partial<Omit<CreateUsageStatsRequest, 'stat_year' | 'stat_month'>>

export async function updateUsageStats(
  subscriptionId: number,
  statsId: number,
  data: UpdateUsageStatsRequest
): Promise<DatabaseUsageStats> {
  return fetchApi<DatabaseUsageStats>(
    `/databases/subscriptions/${subscriptionId}/usage/${statsId}`,
    {
      method: 'PUT',
      body: JSON.stringify(data),
    }
  )
}

export async function deleteUsageStats(
  subscriptionId: number,
  statsId: number
): Promise<void> {
  await fetchApi<void>(
    `/databases/subscriptions/${subscriptionId}/usage/${statsId}`,
    { method: 'DELETE' }
  )
}

// COUNTER R5 DR_D1 report (annual rollup)
export interface UsageReportRow {
  subscription_id: number
  database: string
  publisher: string | null
  platform: string | null
  searches_regular: number
  searches_federated: number
  searches_automated: number
  total_item_requests: number
  unique_item_requests: number
  total_item_investigations: number
  unique_item_investigations: number
  no_license: number
  annual_cost: string | null
  cost_per_use: string | null
}

export interface UsageReportPreview {
  year: number
  institution_name: string
  rows: UsageReportRow[]
  totals: Record<string, number>
}

export async function getUsageReportPreview(year: number): Promise<UsageReportPreview> {
  return fetchApi<UsageReportPreview>(`/databases/reports/usage?year=${year}`)
}

export async function downloadUsageReport(year: number, format: 'csv' | 'tsv' = 'tsv'): Promise<void> {
  const token = getAccessToken()
  const res = await fetch(`${API_BASE}/databases/reports/usage?year=${year}&format=${format}`, {
    credentials: 'include',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok) throw new Error(`Usage report download failed (${res.status})`)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `dr_d1_${year}.${format}`
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// Dashboard
export async function getDashboard(): Promise<SubscriptionDashboard> {
  return fetchApi<SubscriptionDashboard>('/databases/dashboard')
}

// ============ UTILITY FUNCTIONS ============

export function getCategoryDisplayName(category: DatabaseCategory): string {
  const names: Record<DatabaseCategory, string> = {
    general_reference: 'General Reference',
    academic: 'Academic',
    newspapers: 'Newspapers',
    magazines: 'Magazines',
    ebooks: 'E-Books',
    audiobooks: 'Audiobooks',
    genealogy: 'Genealogy',
    business: 'Business',
    legal: 'Legal',
    health: 'Health & Wellness',
    children: 'Children',
    teen: 'Teen',
    language_learning: 'Language Learning',
    test_prep: 'Test Preparation',
    streaming_video: 'Streaming Video',
    streaming_music: 'Streaming Music',
    diy_crafts: 'DIY & Crafts',
    automotive: 'Automotive',
    other: 'Other',
  }
  return names[category] || category
}

export function getStatusColor(status: SubscriptionStatus): string {
  const colors: Record<SubscriptionStatus, string> = {
    active: 'bg-status-success-100 text-status-success-800 dark:bg-status-success-900 dark:text-status-success-200',
    expiring_soon: 'bg-status-warning-100 text-status-warning-800 dark:bg-status-warning-900 dark:text-status-warning-200',
    expired: 'bg-status-danger-100 text-status-danger-800 dark:bg-status-danger-900 dark:text-status-danger-200',
    cancelled: 'bg-earth-100 text-earth-800 dark:bg-earth-700 dark:text-earth-200',
    pending: 'bg-earth-100 text-earth-800 dark:bg-earth-800 dark:text-lsc-rose-light/80',
    trial: 'bg-category-100 text-category-800 dark:bg-category-900 dark:text-category-200',
  }
  return colors[status] || colors.active
}
