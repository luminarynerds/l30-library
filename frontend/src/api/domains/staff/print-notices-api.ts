/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Print Notices API Service
 *
 * Provides functions for managing print notices including:
 * - Notice queue management
 * - Batch creation and processing
 * - PDF generation
 * - Cost tracking and reporting
 * - Returned mail handling
 * - Notice history
 */

import { fetchApi, isApiError } from '@/lib/api-client'
import { buildQueryString } from '@/lib/api-helpers'
import { getAccessToken } from '../../../utils/tokenStore'
import { API_BASE } from '@/api/types'

// ============================================================================
// Types
// ============================================================================

export type PrintNoticeType = 'overdue' | 'fine' | 'hold_ready' | 'account_expiring' | 'general'
export type PrintNoticeStatus = 'pending' | 'queued' | 'generated' | 'printed' | 'mailed' | 'delivered' | 'returned' | 'cancelled'
export type PrintNoticeBatchStatus = 'open' | 'closed' | 'generating' | 'generated' | 'printed' | 'mailed' | 'completed'
export type AddressStatus = 'unverified' | 'valid' | 'returned_mail' | 'invalid'
export type NoticePreference = 'email' | 'print' | 'both' | 'none'

export interface PrintNotice {
  id: number
  patron_id: number
  notice_type: PrintNoticeType
  status: PrintNoticeStatus
  batch_id: number | null
  merge_key: string | null
  recipient_name: string
  address_line1: string
  address_line2: string | null
  city: string
  state: string
  zip_code: string
  country: string
  subject: string
  context_data: Record<string, unknown> | null
  checkout_id: number | null
  hold_id: number | null
  fine_id: number | null
  pdf_file_path: string | null
  pdf_generated_at: string | null
  print_cost: number
  postage_cost: number
  total_cost: number
  pages: number
  scheduled_for: string | null
  printed_at: string | null
  mailed_at: string | null
  delivered_at: string | null
  returned_at: string | null
  return_reason: string | null
  created_at: string
  updated_at: string | null
}

export interface PrintNoticeBatch {
  id: number
  batch_number: string
  name: string | null
  status: PrintNoticeBatchStatus
  notice_types: string[] | null
  auto_close_at: string | null
  notice_count: number
  page_count: number
  total_print_cost: number
  total_postage_cost: number
  total_cost: number
  merged_pdf_path: string | null
  manifest_pdf_path: string | null
  opened_at: string
  closed_at: string | null
  printed_at: string | null
  mailed_at: string | null
  completed_at: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface PrintNoticeBatchDetail extends PrintNoticeBatch {
  notices: PrintNotice[]
}

export interface PrintNoticeHistory {
  id: number
  notice_id: number | null
  batch_id: number | null
  patron_id: number | null
  patron_name: string
  patron_library_card: string | null
  notice_type: PrintNoticeType
  subject: string
  mailing_address: string
  final_status: string
  mailed_at: string | null
  returned: boolean
  return_reason: string | null
  total_cost: number
  context_summary: string | null
  created_at: string
}

export interface CostConfig {
  id: number
  cost_per_page: number
  first_class_letter: number
  first_class_large_envelope: number
  presort_standard: number
  large_envelope_page_threshold: number
  is_active: boolean
  effective_from: string
  effective_to: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface CostSummary {
  total_notices: number
  total_cost: number
  returned_count: number
  return_rate: number
  period_start: string | null
  period_end: string | null
}

export interface AddressValidation {
  is_valid: boolean
  errors: string[]
  warnings: string[]
  normalized_address: {
    address_line1: string
    address_line2: string | null
    city: string
    state: string
    zip_code: string
    country: string
  } | null
}

export interface BatchMergeResult {
  merged_count: number
  total_savings: number
}

export interface BatchPDFGenerationResult {
  generated_count: number
  total_pages: number
  manifest_path: string
}

export interface DashboardStats {
  pending_notices: number
  open_batches: number
  ready_to_mail: number
  returned_this_month: number
  total_cost_this_month: number
  patrons_requiring_print: number
}

export interface PatronRequiringPrint {
  id: number
  name: string
  library_card: string
  notice_preference: string
  address_status: string
  has_valid_address: boolean
}

// ============================================================================
// Address Validation
// ============================================================================

export async function validateAddress(address: {
  address_line1: string
  address_line2?: string | null
  city: string
  state: string
  zip_code: string
  country?: string
}): Promise<AddressValidation> {
  const token = getAccessToken()
  try {
    return await fetchApi<AddressValidation>('/staff/print-notices/validate-address', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: address,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Address validation failed')
    }
    throw error
  }
}

// ============================================================================
// Patron Notice Preferences
// ============================================================================

export async function updatePatronNoticePreference(
  patronId: number,
  data: {
    notice_preference: NoticePreference
    address_line1?: string
    address_line2?: string
    city?: string
    state?: string
    zip_code?: string
  }
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/staff/print-notices/patrons/${patronId}/notice-preference`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update notice preference')
    }
    throw error
  }
}

export async function updatePatronAddressStatus(
  patronId: number,
  data: { address_status: AddressStatus; notes?: string }
): Promise<{ message: string }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ message: string }>(`/staff/print-notices/patrons/${patronId}/address-status`, {
      method: 'PUT',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update address status')
    }
    throw error
  }
}

// ============================================================================
// Print Notice Queue
// ============================================================================

export async function createOverdueNotice(
  patronId: number,
  checkoutIds: number[]
): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>('/staff/print-notices/notices/overdue', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { patron_id: patronId, checkout_ids: checkoutIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create overdue notice')
    }
    throw error
  }
}

export async function createFineNotice(
  patronId: number,
  fineIds: number[]
): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>('/staff/print-notices/notices/fine', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { patron_id: patronId, fine_ids: fineIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create fine notice')
    }
    throw error
  }
}

export async function createHoldReadyNotice(
  patronId: number,
  holdId: number
): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>('/staff/print-notices/notices/hold-ready', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { patron_id: patronId, hold_id: holdId },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create hold ready notice')
    }
    throw error
  }
}

export async function createAccountExpiringNotice(
  patronId: number,
  expirationDate: string
): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>('/staff/print-notices/notices/account-expiring', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { patron_id: patronId, expiration_date: expirationDate },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create account expiring notice')
    }
    throw error
  }
}

export async function listNotices(params?: {
  patron_id?: number
  status?: PrintNoticeStatus
  notice_type?: PrintNoticeType
  batch_id?: number
  limit?: number
  offset?: number
}): Promise<{ items: PrintNotice[]; total: number; limit: number; offset: number }> {
  const token = getAccessToken()
  const queryParams = {
    patron_id: params?.patron_id,
    status: params?.status,
    notice_type: params?.notice_type,
    batch_id: params?.batch_id,
    limit: params?.limit,
    offset: params?.offset,
  }
  const queryString = buildQueryString(queryParams)
  try {
    return await fetchApi<{ items: PrintNotice[]; total: number; limit: number; offset: number }>(
      `/staff/print-notices/notices${queryString}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to list notices')
    }
    throw error
  }
}

export async function getNotice(noticeId: number): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>(`/staff/print-notices/notices/${noticeId}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get notice')
    }
    throw error
  }
}

export function getNoticePdfUrl(noticeId: number): string {
  return `${API_BASE}/staff/print-notices/notices/${noticeId}/pdf`
}

// ============================================================================
// Batch Management
// ============================================================================

export async function createBatch(data: {
  name?: string
  notice_types?: PrintNoticeType[]
  auto_close_hours?: number
}): Promise<PrintNoticeBatch> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatch>('/staff/print-notices/batches', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create batch')
    }
    throw error
  }
}

export async function listBatches(params?: {
  status?: PrintNoticeBatchStatus
  limit?: number
  offset?: number
}): Promise<{ items: PrintNoticeBatch[]; total: number; limit: number; offset: number }> {
  const token = getAccessToken()
  const queryParams = {
    status: params?.status,
    limit: params?.limit,
    offset: params?.offset,
  }
  const queryString = buildQueryString(queryParams)
  try {
    return await fetchApi<{ items: PrintNoticeBatch[]; total: number; limit: number; offset: number }>(
      `/staff/print-notices/batches${queryString}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to list batches')
    }
    throw error
  }
}

export async function getBatch(batchId: number): Promise<PrintNoticeBatchDetail> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatchDetail>(`/staff/print-notices/batches/${batchId}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get batch')
    }
    throw error
  }
}

export async function addNoticesToBatch(
  batchId: number,
  noticeIds: number[]
): Promise<PrintNoticeBatch> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatch>(`/staff/print-notices/batches/${batchId}/add-notices`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { notice_ids: noticeIds },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add notices to batch')
    }
    throw error
  }
}

export async function addAllPendingToBatch(
  batchId: number,
  noticeTypes?: PrintNoticeType[]
): Promise<{ message: string; added_count: number; batch?: PrintNoticeBatch }> {
  const token = getAccessToken()
  const queryString = buildQueryString({ notice_types: noticeTypes })
  try {
    return await fetchApi<{ message: string; added_count: number; batch?: PrintNoticeBatch }>(
      `/staff/print-notices/batches/${batchId}/add-pending${queryString}`,
      {
        method: 'POST',
        ...(token ? { token } : {}),
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add pending notices')
    }
    throw error
  }
}

export async function mergeBatchNotices(batchId: number): Promise<BatchMergeResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<BatchMergeResult>(`/staff/print-notices/batches/${batchId}/merge`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to merge batch notices')
    }
    throw error
  }
}

export async function closeBatch(batchId: number): Promise<PrintNoticeBatch> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatch>(`/staff/print-notices/batches/${batchId}/close`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to close batch')
    }
    throw error
  }
}

export async function generateBatchPdfs(batchId: number): Promise<BatchPDFGenerationResult> {
  const token = getAccessToken()
  try {
    return await fetchApi<BatchPDFGenerationResult>(`/staff/print-notices/batches/${batchId}/generate-pdfs`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate PDFs')
    }
    throw error
  }
}

export function getBatchManifestUrl(batchId: number): string {
  return `${API_BASE}/staff/print-notices/batches/${batchId}/manifest`
}

export async function markBatchPrinted(batchId: number): Promise<PrintNoticeBatch> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatch>(`/staff/print-notices/batches/${batchId}/mark-printed`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark batch as printed')
    }
    throw error
  }
}

export async function markBatchMailed(batchId: number): Promise<PrintNoticeBatch> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNoticeBatch>(`/staff/print-notices/batches/${batchId}/mark-mailed`, {
      method: 'POST',
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark batch as mailed')
    }
    throw error
  }
}

// ============================================================================
// Returned Mail Handling
// ============================================================================

export async function markNoticeReturned(
  noticeId: number,
  returnReason: string,
  updatePatronAddress: boolean = true
): Promise<PrintNotice> {
  const token = getAccessToken()
  try {
    return await fetchApi<PrintNotice>(`/staff/print-notices/notices/${noticeId}/returned`, {
      method: 'POST',
      ...(token ? { token } : {}),
      body: { return_reason: returnReason, update_patron_address: updatePatronAddress },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark notice as returned')
    }
    throw error
  }
}

export async function markNoticesBulkReturned(
  noticeIds: number[],
  returnReason: string,
  updatePatronAddresses: boolean = true
): Promise<{ processed_count: number; failed_count: number; failed: Array<{ notice_id: number; error: string }> }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ processed_count: number; failed_count: number; failed: Array<{ notice_id: number; error: string }> }>(
      '/staff/print-notices/notices/bulk-returned',
      {
        method: 'POST',
        ...(token ? { token } : {}),
        body: { notice_ids: noticeIds, return_reason: returnReason, update_patron_addresses: updatePatronAddresses },
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark notices as returned')
    }
    throw error
  }
}

// ============================================================================
// Cost Configuration and Tracking
// ============================================================================

export async function getCostConfig(): Promise<CostConfig> {
  const token = getAccessToken()
  try {
    return await fetchApi<CostConfig>('/staff/print-notices/cost-config', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get cost configuration')
    }
    throw error
  }
}

export async function updateCostConfig(data: {
  cost_per_page?: number
  first_class_letter?: number
  first_class_large_envelope?: number
  presort_standard?: number
  large_envelope_page_threshold?: number
  notes?: string
}): Promise<CostConfig> {
  const token = getAccessToken()
  try {
    return await fetchApi<CostConfig>('/staff/print-notices/cost-config', {
      method: 'POST',
      ...(token ? { token } : {}),
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update cost configuration')
    }
    throw error
  }
}

export async function getCostSummary(params?: {
  start_date?: string
  end_date?: string
}): Promise<CostSummary> {
  const token = getAccessToken()
  const queryString = buildQueryString({
    start_date: params?.start_date,
    end_date: params?.end_date,
  })
  try {
    return await fetchApi<CostSummary>(`/staff/print-notices/cost-summary${queryString}`, {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get cost summary')
    }
    throw error
  }
}

// ============================================================================
// Notice History
// ============================================================================

export async function getNoticeHistory(params?: {
  patron_id?: number
  limit?: number
  offset?: number
}): Promise<{ items: PrintNoticeHistory[]; total: number; limit: number; offset: number }> {
  const token = getAccessToken()
  const queryParams = {
    patron_id: params?.patron_id,
    limit: params?.limit,
    offset: params?.offset,
  }
  const queryString = buildQueryString(queryParams)
  try {
    return await fetchApi<{ items: PrintNoticeHistory[]; total: number; limit: number; offset: number }>(
      `/staff/print-notices/history${queryString}`,
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get notice history')
    }
    throw error
  }
}

// ============================================================================
// Patrons Requiring Print Notices
// ============================================================================

export async function getPatronsRequiringPrint(): Promise<{ patrons: PatronRequiringPrint[]; total: number }> {
  const token = getAccessToken()
  try {
    return await fetchApi<{ patrons: PatronRequiringPrint[]; total: number }>(
      '/staff/print-notices/patrons-requiring-print',
      { ...(token ? { token } : {}) }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get patrons requiring print')
    }
    throw error
  }
}

// ============================================================================
// Dashboard Statistics
// ============================================================================

export async function getDashboardStats(): Promise<DashboardStats> {
  const token = getAccessToken()
  try {
    return await fetchApi<DashboardStats>('/staff/print-notices/dashboard-stats', {
      ...(token ? { token } : {}),
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get dashboard stats')
    }
    throw error
  }
}