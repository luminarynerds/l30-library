/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ============ Types ============

export type PurchaseRequestStatus =
  | 'pending'
  | 'under_review'
  | 'approved'
  | 'ordered'
  | 'received'
  | 'declined'
  | 'cancelled'

export type RequestMaterialType =
  | 'book'
  | 'audiobook'
  | 'ebook'
  | 'dvd'
  | 'cd'
  | 'magazine'
  | 'other'

export interface PurchaseRequest {
  id: number
  title: string
  author: string | null
  isbn: string | null
  material_type: RequestMaterialType
  publisher: string | null
  publication_year: number | null
  patron_notes: string | null
  status: PurchaseRequestStatus
  decline_reason: string | null
  created_at: string
  updated_at: string | null
}

export interface PurchaseRequestStaff extends PurchaseRequest {
  patron_id: number
  patron_name: string | null
  reviewed_by_id: number | null
  reviewer_name: string | null
  reviewed_at: string | null
  staff_notes: string | null
  duplicate_of_catalog_id: number | null
  duplicate_check_done: boolean
  duplicate_title: string | null
  review_source_rating: number | null
  review_source_data: string | null
  review_source_checked: boolean
  purchase_order_id: number | null
}

export interface PurchaseRequestListResponse {
  items: PurchaseRequest[]
  total: number
  page: number
  per_page: number
}

export interface PurchaseRequestStaffListResponse {
  items: PurchaseRequestStaff[]
  total: number
  page: number
  per_page: number
}

export interface PurchaseRequestCreate {
  title: string
  author?: string
  isbn?: string
  material_type?: RequestMaterialType
  publisher?: string
  publication_year?: number
  patron_notes?: string
}

export interface DuplicateCheckResult {
  has_duplicate: boolean
  catalog_item_id: number | null
  catalog_title: string | null
  catalog_author: string | null
  match_type: string | null
}

export interface BulkActionResult {
  request_id: number
  success: boolean
  error: string | null
}

export interface BulkActionResponse {
  total_requested: number
  succeeded: number
  failed: number
  results: BulkActionResult[]
}

export interface FulfillmentStats {
  total_requests: number
  pending_count: number
  under_review_count: number
  approved_count: number
  ordered_count: number
  received_count: number
  declined_count: number
  cancelled_count: number
  fulfillment_rate: number
  avg_days_to_review: number | null
  avg_days_to_fulfill: number | null
}

export interface DeclineReasonTemplate {
  id: number
  label: string
  message: string
  is_active: boolean
  usage_count: number
  created_by_id: number
  created_at: string
}

// ============ Patron API ============

// fetchApi already prepends API_BASE (/api/v1); BASE must be a bare path
// or the prefix doubles (/api/v1/api/v1/...) and every call 404s.
const BASE = '/purchase-requests'

export async function submitPurchaseRequest(
  data: PurchaseRequestCreate,
  token: string,
): Promise<PurchaseRequest> {
  return fetchApi(BASE, { method: 'POST', body: data, token })
}

export async function getMyRequests(
  token: string,
  page = 1,
  status?: PurchaseRequestStatus,
): Promise<PurchaseRequestListResponse> {
  const params = new URLSearchParams({ page: String(page) })
  if (status) params.set('status', status)
  return fetchApi(`${BASE}/mine?${params}`, { token })
}

export async function getMyRequest(
  id: number,
  token: string,
): Promise<PurchaseRequest> {
  return fetchApi(`${BASE}/mine/${id}`, { token })
}

export async function cancelMyRequest(
  id: number,
  token: string,
): Promise<PurchaseRequest> {
  return fetchApi(`${BASE}/mine/${id}/cancel`, { method: 'POST', token })
}

export async function checkDuplicate(
  title: string,
  token: string,
  author?: string,
  isbn?: string,
): Promise<DuplicateCheckResult> {
  const params = new URLSearchParams({ title })
  if (author) params.set('author', author)
  if (isbn) params.set('isbn', isbn)
  return fetchApi(`${BASE}/check-duplicate?${params}`, { token })
}

// ============ Staff API ============

export async function getReviewQueue(
  token: string,
  page = 1,
  status?: PurchaseRequestStatus,
  hasDuplicate?: boolean,
): Promise<PurchaseRequestStaffListResponse> {
  const params = new URLSearchParams({ page: String(page) })
  if (status) params.set('status', status)
  if (hasDuplicate !== undefined) params.set('has_duplicate', String(hasDuplicate))
  return fetchApi(`${BASE}/queue?${params}`, { token })
}

export async function getStaffRequest(
  id: number,
  token: string,
): Promise<PurchaseRequestStaff> {
  return fetchApi(`${BASE}/queue/${id}`, { token })
}

export async function approveRequest(
  id: number,
  token: string,
  staffNotes?: string,
): Promise<PurchaseRequestStaff> {
  return fetchApi(`${BASE}/queue/${id}/approve`, {
    method: 'POST',
    body: { staff_notes: staffNotes || null },
    token,
  })
}

export async function declineRequest(
  id: number,
  token: string,
  declineReason: string,
  staffNotes?: string,
): Promise<PurchaseRequestStaff> {
  return fetchApi(`${BASE}/queue/${id}/decline`, {
    method: 'POST',
    body: { decline_reason: declineReason, staff_notes: staffNotes || null },
    token,
  })
}

export async function bulkApprove(
  requestIds: number[],
  token: string,
  staffNotes?: string,
): Promise<BulkActionResponse> {
  return fetchApi(`${BASE}/queue/bulk-approve`, {
    method: 'POST',
    body: { request_ids: requestIds, staff_notes: staffNotes || null },
    token,
  })
}

export async function bulkDecline(
  requestIds: number[],
  token: string,
  declineReason: string,
  staffNotes?: string,
): Promise<BulkActionResponse> {
  return fetchApi(`${BASE}/queue/bulk-decline`, {
    method: 'POST',
    body: { request_ids: requestIds, decline_reason: declineReason, staff_notes: staffNotes || null },
    token,
  })
}

export async function linkToOrder(
  requestId: number,
  purchaseOrderId: number,
  token: string,
): Promise<PurchaseRequestStaff> {
  return fetchApi(`${BASE}/queue/${requestId}/link-order`, {
    method: 'POST',
    body: { purchase_order_id: purchaseOrderId },
    token,
  })
}

export async function markReceived(
  requestId: number,
  token: string,
): Promise<PurchaseRequestStaff> {
  return fetchApi(`${BASE}/queue/${requestId}/mark-received`, {
    method: 'POST',
    token,
  })
}

export async function getFulfillmentStats(
  token: string,
): Promise<FulfillmentStats> {
  return fetchApi(`${BASE}/stats`, { token })
}

// ============ Decline Templates ============

export async function getDeclineTemplates(
  token: string,
): Promise<DeclineReasonTemplate[]> {
  return fetchApi(`${BASE}/decline-templates`, { token })
}

export async function createDeclineTemplate(
  label: string,
  message: string,
  token: string,
): Promise<DeclineReasonTemplate> {
  return fetchApi(`${BASE}/decline-templates`, {
    method: 'POST',
    body: { label, message },
    token,
  })
}

export async function deleteDeclineTemplate(
  id: number,
  token: string,
): Promise<void> {
  return fetchApi(`${BASE}/decline-templates/${id}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

export async function addPurchaseRequestToSelection(
  requestId: number,
  token: string,
): Promise<{ id: number; message: string }> {
  return fetchApi(`${BASE}/queue/${requestId}/add-to-selection`, {
    method: 'POST',
    token,
  })
}