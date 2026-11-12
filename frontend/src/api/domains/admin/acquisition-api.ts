/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { getAccessToken } from '../../../utils/tokenStore'

// Types
export interface Fund {
  id: number
  name: string
  code: string
  description: string | null
  fiscal_year: number
  allocated_amount: number
  available_amount: number
  encumbered_amount: number
  spent_amount: number
  current_balance?: number
  status: 'active' | 'inactive' | 'closed'
  created_at: string
}

export interface Vendor {
  id: number
  name: string
  code: string
  contact_name: string | null
  email: string | null
  phone: string | null
  address: string | null
  website: string | null
  notes: string | null
  status: 'active' | 'inactive'
  discount_percentage: number
  average_delivery_days: number | null
  created_at: string
  updated_at: string
}

export interface SelectionListItem {
  id: number
  title: string
  author: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  price: number | null
  format: string | null
  notes: string | null
  priority: 'low' | 'normal' | 'high' | 'urgent'
  status: 'pending' | 'approved' | 'ordered' | 'rejected'
  requested_by: number
  requested_by_name?: string
  requested_at: string
  source: string | null
}

export interface ExternalSearchResult {
  title: string
  author: string | null
  isbn: string | null
  publisher: string | null
  publication_year: number | null
  price: number | null
  format: string | null
  source: string
  source_url: string | null
  cover_image: string | null
  description: string | null
}

export interface FundCreateData {
  name: string
  code: string
  description?: string
  fiscal_year: number
  allocated_amount: number
}

export interface FundUpdateData {
  name?: string
  description?: string
  status?: string
}

export interface VendorCreateData {
  name: string
  code: string
  contact_name?: string
  email?: string
  phone?: string
  address?: string
  website?: string
  notes?: string
  discount_percentage?: number
}

export interface VendorUpdateData {
  name?: string
  contact_name?: string
  email?: string
  phone?: string
  address?: string
  website?: string
  notes?: string
  status?: string
  discount_percentage?: number
}

export interface SelectionListCreateData {
  title: string
  author?: string
  isbn?: string
  publisher?: string
  publication_year?: number
  price?: number
  format?: string
  notes?: string
  priority?: string
  source?: string
}

export interface PurchaseOrder {
  id: number
  po_number: string
  vendor_id: number
  vendor_name?: string
  fund_id: number
  fund_name?: string
  status: 'draft' | 'submitted' | 'approved' | 'ordered' | 'partially_received' | 'received' | 'cancelled'
  total_amount: number
  notes: string | null
  order_date: string | null
  expected_delivery_date: string | null
  created_by: number
  created_at: string
  updated_at: string
  items?: PurchaseOrderItem[]
}

export interface PurchaseOrderItem {
  id: number
  purchase_order_id: number
  title: string
  author: string | null
  isbn: string | null
  publisher: string | null
  quantity: number
  unit_price: number
  total_price: number
  status: 'pending' | 'ordered' | 'received' | 'cancelled'
  received_quantity: number
  notes: string | null
  selection_list_item_id: number | null
}


export interface EmailVendorData {
  subject?: string
  message?: string
  include_po_details?: boolean
}

// Funds API
export async function getFunds(params?: {
  fiscal_year?: number
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: Fund[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.fiscal_year) searchParams.set('fiscal_year', params.fiscal_year.toString())
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: Fund[]; total: number }>(`/acquisition/funds${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getFund(id: number): Promise<Fund> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fund>(`/acquisition/funds/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function createFund(data: FundCreateData): Promise<Fund> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fund>('/acquisition/funds', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function updateFund(id: number, data: FundUpdateData): Promise<Fund> {
  const token = getAccessToken()
  try {
    return await fetchApi<Fund>(`/acquisition/funds/${id}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function rolloverFunds(data: { source_fiscal_year: number; target_fiscal_year: number }): Promise<{ message: string; funds_created: number }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string; funds_created: number }>('/acquisition/funds/rollover', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Vendors API
export async function getVendors(params?: {
  status?: string
  q?: string
  page?: number
  per_page?: number
}): Promise<{ items: Vendor[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.q) searchParams.set('q', params.q)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: Vendor[]; total: number }>(`/acquisition/vendors${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getVendor(id: number): Promise<Vendor> {
  const token = getAccessToken()
  try {
    return await fetchApi<Vendor>(`/acquisition/vendors/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function createVendor(data: VendorCreateData): Promise<Vendor> {
  const token = getAccessToken()
  try {
    return await fetchApi<Vendor>('/acquisition/vendors', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function updateVendor(id: number, data: VendorUpdateData): Promise<Vendor> {
  const token = getAccessToken()
  try {
    return await fetchApi<Vendor>(`/acquisition/vendors/${id}`, {
      method: 'PATCH',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// Purchase Orders API
export async function getPurchaseOrders(params?: {
  vendor_id?: number
  fund_id?: number
  status?: string
  page?: number
  per_page?: number
}): Promise<{ items: PurchaseOrder[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.vendor_id) searchParams.set('vendor_id', params.vendor_id.toString())
  if (params?.fund_id) searchParams.set('fund_id', params.fund_id.toString())
  if (params?.status) searchParams.set('status', params.status)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: PurchaseOrder[]; total: number }>(`/acquisition/purchase-orders${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function getPurchaseOrder(id: number): Promise<PurchaseOrder> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrder>(`/acquisition/purchase-orders/${id}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}


export async function emailVendor(poId: number, data?: EmailVendorData): Promise<{ message: string; email_sent_to: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string; email_sent_to: string }>(`/acquisition/purchase-orders/${poId}/email-vendor`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data || {},
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}



export interface CollectionInsightItem {
  key: string
  title: string
  author?: string | null
  isbn?: string | null
  reason: string
  score: number
  source: string
  metadata: Record<string, string | number>
}

export interface CollectionIntelligenceReport {
  patrons_searched_missing: CollectionInsightItem[]
  popular_titles_not_owned: CollectionInsightItem[]
  series_missing_volumes: CollectionInsightItem[]
  high_hold_ratio_items: CollectionInsightItem[]
  outdated_subjects: CollectionInsightItem[]
  peer_library_gaps: CollectionInsightItem[]
  missing_award_winners: CollectionInsightItem[]
  trending_topics_without_coverage: CollectionInsightItem[]
}

// Selection List API
export async function getSelectionList(params?: {
  status?: string
  priority?: string
  page?: number
  per_page?: number
}): Promise<{ items: SelectionListItem[]; total: number }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.priority) searchParams.set('priority', params.priority)
  if (params?.page) searchParams.set('page', params.page.toString())
  if (params?.per_page) searchParams.set('per_page', params.per_page.toString())
  const query = searchParams.toString() ? `?${searchParams}` : ''
  try {
    return await fetchApi<{ items: SelectionListItem[]; total: number }>(`/acquisition/selection-list${query}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function addToSelectionList(data: SelectionListCreateData): Promise<SelectionListItem> {
  const token = getAccessToken()
  try {
    return await fetchApi<SelectionListItem>('/acquisition/selection-list', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function removeFromSelectionList(id: number): Promise<void> {
  const token = getAccessToken()
  try {
    await fetchApi<void>(`/acquisition/selection-list/${id}`, {
      method: 'DELETE',
      ...(token ? { token } : {}),
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

export async function convertSelectionToPO(data: { selection_item_ids: number[]; vendor_id: number; fund_id: number }): Promise<PurchaseOrder> {
  const token = getAccessToken()
  try {
    return await fetchApi<PurchaseOrder>('/acquisition/selection-list/convert-to-po', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}



export async function getCollectionIntelligenceReport(): Promise<CollectionIntelligenceReport> {
  const token = getAccessToken()
  return await fetchApi<CollectionIntelligenceReport>('/acquisition/collection-intelligence/report', { ...(token ? { token } : {}) })
}

export async function addInsightToPurchaseConsideration(data: {
  title: string
  author?: string
  isbn?: string
  notes: string
  source?: string
  source_id?: string
}): Promise<{ message: string; selection_item_id: number }> {
  const token = getAccessToken()
  return await fetchApi<{ message: string; selection_item_id: number }>('/acquisition/collection-intelligence/add-to-selection', {
    method: 'POST',
    ...(token ? { token } : {}),
    body: data,
  })
}

// External Search API
export async function searchExternalCatalogs(params: {
  q: string
  source?: string
  isbn?: string
}): Promise<{ results: ExternalSearchResult[]; sources_searched: string[] }> {
  const token = getAccessToken()
  const searchParams = new URLSearchParams()
  searchParams.set('q', params.q)
  if (params?.source) searchParams.set('source', params.source)
  if (params?.isbn) searchParams.set('isbn', params.isbn)
  try {
    return await fetchApi<{ results: ExternalSearchResult[]; sources_searched: string[] }>(`/acquisition/external-search?${searchParams}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Request failed')
    }
    throw error
  }
}

// ============ ISBN Lookup Types ============

export interface ISBNLookupResult {
  isbn: string
  isbn_10: string | null
  isbn_13: string | null
  title: string
  author: string | null
  cover_url: string | null
  publisher: string | null
  publication_year: number | null
  description: string | null
  page_count: number | null
  subjects: string[]
  estimated_price: number | null
  source: string
  source_id: string
  in_catalog: boolean
  catalog_item_id: number | null
  previously_ordered: boolean
  previous_po_numbers: string[]
}

export interface ISBNLookupResponse {
  success: boolean
  result: ISBNLookupResult | null
  error: string | null
}

export interface BulkISBNResult {
  isbn: string
  success: boolean
  result: ISBNLookupResult | null
  error: string | null
}

export interface BulkISBNResponse {
  total: number
  successful: number
  failed: number
  results: BulkISBNResult[]
}

export interface ISBNValidationResult {
  input: string
  normalized: string
  valid: boolean
  format: string | null
  isbn_10: string | null
  isbn_13: string | null
}

export interface CatalogCheckResult {
  isbn: string
  in_catalog: boolean
  catalog_item_id: number | null
  previously_ordered: boolean
  previous_po_numbers: string[]
}

// ============ ISBN Lookup API Functions ============

export async function lookupISBN(isbn: string): Promise<ISBNLookupResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<ISBNLookupResponse>(`/acquisition/isbn-lookup/${encodeURIComponent(isbn)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'ISBN lookup failed')
    }
    throw error
  }
}

export async function bulkLookupISBNs(isbns: string[]): Promise<BulkISBNResponse> {
  const token = getAccessToken()
  try {
    return await fetchApi<BulkISBNResponse>('/acquisition/isbn-lookup/bulk', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { isbns },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk ISBN lookup failed')
    }
    throw error
  }
}

export async function validateISBN(isbn: string): Promise<ISBNValidationResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<ISBNValidationResult>(`/acquisition/isbn-validate/${encodeURIComponent(isbn)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'ISBN validation failed')
    }
    throw error
  }
}

export async function checkISBNInCatalog(isbn: string): Promise<CatalogCheckResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<CatalogCheckResult>(`/acquisition/check-catalog/${encodeURIComponent(isbn)}`, { ...(token ? { token } : {}) })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Catalog check failed')
    }
    throw error
  }
}
