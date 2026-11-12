/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Lost & Damaged Items Types ====================

export type LostItemStatus = 'reported' | 'confirmed' | 'charged' | 'found' | 'written_off'
export type LostItemType = 'lost_by_patron' | 'lost_in_transit' | 'missing_inventory' | 'claims_returned'
export type DamagedItemStatus = 'reported' | 'assessing' | 'in_mending' | 'repaired' | 'withdrawn'
export type DamageSeverity = 'minor' | 'moderate' | 'severe' | 'destroyed'
export type ClaimDisputeStatus = 'filed' | 'under_review' | 'searching' | 'resolved_approved' | 'resolved_denied' | 'resolved_found'

export interface ReplacementCostBreakdown {
  item_price: number
  processing_fee: number
  total: number
  source: string
}

export interface DamageAssessment {
  is_repairable: boolean
  severity: string
  estimated_repair_cost: number | null
  recommended_action: string
  patron_charge_amount: number | null
  charge_percentage: number | null
}

export interface LostItemRecord {
  id: number
  item_copy_id: number
  checkout_id: number | null
  catalog_item_id: number
  patron_id: number | null
  status: LostItemStatus
  lost_type: LostItemType
  item_price: number
  processing_fee: number
  replacement_cost: number
  credit_amount: number | null
  days_overdue_at_loss: number | null
  report_notes: string | null
  resolution_notes: string | null
  reported_at: string
  confirmed_at: string | null
  charged_at: string | null
  found_at: string | null
  written_off_at: string | null
  last_known_location: string | null
  patron_name: string | null
  item_title: string | null
  fine_amount: number | null
  fine_status: string | null
}

export interface DamagedItemRecord {
  id: number
  item_copy_id: number
  checkout_id: number | null
  catalog_item_id: number
  patron_id: number | null
  status: DamagedItemStatus
  severity: DamageSeverity
  damage_types: string[]
  damage_description: string
  photo_urls: string[] | null
  assessment_notes: string | null
  is_patron_responsible: boolean
  estimated_repair_cost: number | null
  actual_repair_cost: number | null
  replacement_cost: number | null
  charge_amount: number | null
  repair_priority: number | null
  repair_notes: string | null
  reported_at: string
  assessed_at: string | null
  resolved_at: string | null
  patron_name: string | null
  item_title: string | null
  fine_status: string | null
}

export interface MendingQueueEntry {
  id: number
  damaged_item_record_id: number
  item_copy_id: number
  priority: number
  queue_position: number
  repair_type: string | null
  repair_instructions: string | null
  materials_needed: string | null
  estimated_time_hours: number | null
  estimated_cost: number | null
  actual_cost: number | null
  is_in_progress: boolean
  is_completed: boolean
  added_at: string
  started_at: string | null
  completed_at: string | null
  notes: string | null
  completion_notes: string | null
  item_title: string | null
  assigned_to_name: string | null
}

export interface ClaimsReturnedDispute {
  id: number
  lost_item_record_id: number | null
  item_copy_id: number
  checkout_id: number
  patron_id: number
  status: ClaimDisputeStatus
  patron_statement: string
  claimed_return_date: string | null
  claimed_return_location: string | null
  investigation_notes: string | null
  search_locations: string[] | null
  resolution: string | null
  resolution_reason: string | null
  credit_amount: number | null
  patron_previous_claims_count: number
  filed_at: string
  reviewed_at: string | null
  resolved_at: string | null
  patron_name: string | null
  item_title: string | null
  reviewer_name: string | null
}

export interface PatronClaimsHistory {
  patron_id: number
  total_claims: number
  claims_this_year: number
  approved_claims: number
  denied_claims: number
  pending_claims: number
  items_later_found: number
  is_at_risk: boolean
  max_claims_allowed: number
}

// List response types
export interface LostItemListResponse {
  items: LostItemRecord[]
  total: number
  limit: number
  offset: number
}

export interface DamagedItemListResponse {
  items: DamagedItemRecord[]
  total: number
  limit: number
  offset: number
}

export interface MendingQueueListResponse {
  items: MendingQueueEntry[]
  total: number
  limit: number
  offset: number
}

export interface ClaimsListResponse {
  items: ClaimsReturnedDispute[]
  total: number
  limit: number
  offset: number
}

// Workflow response types
export interface LostItemWorkflowResponse {
  success: boolean
  message: string
  lost_item_record: LostItemRecord | null
  replacement_cost: ReplacementCostBreakdown | null
  fine_id: number | null
  notification_sent: boolean
}

export interface FoundItemResponse {
  success: boolean
  message: string
  lost_item_record: LostItemRecord | null
  credit_amount: number | null
  item_restored: boolean
  notification_sent: boolean
}

export interface DamagedItemWorkflowResponse {
  success: boolean
  message: string
  damaged_item_record: DamagedItemRecord | null
  assessment: DamageAssessment | null
  fine_id: number | null
  mending_entry_id: number | null
  notification_sent: boolean
}

export interface RepairCompletionResponse {
  success: boolean
  message: string
  damaged_item_record: DamagedItemRecord | null
  item_restored: boolean
  actual_cost: number | null
}

export interface ClaimsReturnedWorkflowResponse {
  success: boolean
  message: string
  dispute: ClaimsReturnedDispute | null
  notification_sent: boolean
}

export interface ClaimResolutionResponse {
  success: boolean
  message: string
  dispute: ClaimsReturnedDispute | null
  credit_amount: number | null
  item_found: boolean
  notification_sent: boolean
}

// Bulk operation types
export interface BulkWriteOffRequest {
  lost_record_ids: number[]
  notes?: string
}

export interface BulkWriteOffResponse {
  success_count: number
  failure_count: number
  results: Array<{ record_id: number; success: boolean; message: string }>
}

export interface BulkMendingAssignRequest {
  mending_entry_ids: number[]
  assigned_to_id: number
  priority?: number
}

export interface BulkMendingAssignResponse {
  success_count: number
  failure_count: number
  results: Array<{ entry_id: number; success: boolean; message: string }>
}

export interface BulkMarkLostRequest {
  checkout_ids: number[]
  lost_type: string
  notes?: string
  send_notifications: boolean
}

export interface BulkMarkLostResponse {
  success_count: number
  failure_count: number
  total_charges: number
  notifications_sent: number
  results: Array<{ checkout_id: number; success: boolean; message: string; charge_amount?: string }>
}

// ==================== Lost Items API Functions ====================

export async function markItemLost(
  token: string,
  data: {
    checkout_id: number
    lost_type: string
    report_notes?: string
    custom_replacement_cost?: number
    send_notification?: boolean
  }
): Promise<LostItemWorkflowResponse> {
  try {
    return await fetchApi<LostItemWorkflowResponse>(`/staff/lost-damaged/lost/${data.checkout_id}/mark-lost`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark item as lost')
    }
    throw error
  }
}

export async function processFoundItem(
  token: string,
  data: {
    lost_record_id: number
    found_condition: string
    resolution_notes?: string
    send_notification?: boolean
  }
): Promise<FoundItemResponse> {
  try {
    return await fetchApi<FoundItemResponse>(`/staff/lost-damaged/lost/${data.lost_record_id}/mark-found`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process found item')
    }
    throw error
  }
}

export async function writeOffLostItem(
  token: string,
  recordId: number,
  notes?: string
): Promise<LostItemWorkflowResponse> {
  try {
    const params = notes ? `?notes=${encodeURIComponent(notes)}` : ''
    return await fetchApi<LostItemWorkflowResponse>(`/staff/lost-damaged/lost/${recordId}/write-off${params}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to write off lost item')
    }
    throw error
  }
}

export async function listLostItems(
  token: string,
  filters?: {
    status?: string
    lost_type?: string
    patron_id?: number
    days_ago?: number
    limit?: number
    offset?: number
  }
): Promise<LostItemListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.lost_type) params.set('lost_type', filters.lost_type)
    if (filters?.patron_id) params.set('patron_id', filters.patron_id.toString())
    if (filters?.days_ago) params.set('days_ago', filters.days_ago.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    if (filters?.offset) params.set('offset', filters.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<LostItemListResponse>(`/staff/lost-damaged/lost-items${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch lost items')
    }
    throw error
  }
}

export async function autoConvertOverdueToLost(
  token: string,
  data: {
    threshold_days: number
    dry_run?: boolean
  }
): Promise<{ processed_count: number; dry_run: boolean; results: LostItemWorkflowResponse[] }> {
  try {
    return await fetchApi<{ processed_count: number; dry_run: boolean; results: LostItemWorkflowResponse[] }>(
      '/staff/lost-damaged/lost/auto-convert',
      {
        method: 'POST',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to auto-convert overdue items')
    }
    throw error
  }
}

// ==================== Damaged Items API Functions ====================

export async function reportDamage(
  token: string,
  data: {
    item_copy_id: number
    damage_types: string[]
    damage_description: string
    severity: string
    checkout_id?: number
    patron_id?: number
    is_patron_responsible?: boolean
    photo_urls?: string[]
    send_notification?: boolean
  }
): Promise<DamagedItemWorkflowResponse> {
  try {
    return await fetchApi<DamagedItemWorkflowResponse>('/staff/lost-damaged/damaged/report', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to report damage')
    }
    throw error
  }
}

export async function completeAssessment(
  token: string,
  data: {
    damage_record_id: number
    is_repairable: boolean
    charge_patron?: boolean
    charge_amount?: number
    assessment_notes?: string
    patron_responsibility_reason?: string
    send_notification?: boolean
  }
): Promise<DamagedItemWorkflowResponse> {
  try {
    return await fetchApi<DamagedItemWorkflowResponse>('/staff/lost-damaged/damaged/assess', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to complete assessment')
    }
    throw error
  }
}

export async function sendToMending(
  token: string,
  data: {
    damage_record_id: number
    priority?: number
    repair_type?: string
    repair_instructions?: string
    materials_needed?: string
    estimated_time_hours?: number
    estimated_cost?: number
    assigned_to_id?: number
  }
): Promise<DamagedItemWorkflowResponse> {
  try {
    return await fetchApi<DamagedItemWorkflowResponse>(`/staff/lost-damaged/damaged/${data.damage_record_id}/send-to-mending`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to send to mending')
    }
    throw error
  }
}

export async function completeRepair(
  token: string,
  data: {
    mending_entry_id: number
    actual_cost?: number
    completion_notes?: string
    new_condition: string
  }
): Promise<RepairCompletionResponse> {
  try {
    return await fetchApi<RepairCompletionResponse>(`/staff/lost-damaged/damaged/${data.mending_entry_id}/repair-complete`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to complete repair')
    }
    throw error
  }
}

export async function withdrawDamagedItem(
  token: string,
  data: {
    damage_record_id: number
    withdrawal_reason: string
    charge_patron?: boolean
    charge_amount?: number
    send_notification?: boolean
  }
): Promise<DamagedItemWorkflowResponse> {
  try {
    return await fetchApi<DamagedItemWorkflowResponse>(`/staff/lost-damaged/damaged/${data.damage_record_id}/withdraw`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to withdraw damaged item')
    }
    throw error
  }
}

export async function listDamagedItems(
  token: string,
  filters?: {
    status?: string
    severity?: string
    patron_id?: number
    is_patron_responsible?: boolean
    days_ago?: number
    limit?: number
    offset?: number
  }
): Promise<DamagedItemListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.severity) params.set('severity', filters.severity)
    if (filters?.patron_id) params.set('patron_id', filters.patron_id.toString())
    if (filters?.is_patron_responsible !== undefined) params.set('is_patron_responsible', filters.is_patron_responsible.toString())
    if (filters?.days_ago) params.set('days_ago', filters.days_ago.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    if (filters?.offset) params.set('offset', filters.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<DamagedItemListResponse>(`/staff/lost-damaged/damaged-items${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch damaged items')
    }
    throw error
  }
}

export async function listMendingQueue(
  token: string,
  filters?: {
    include_completed?: boolean
    assigned_to_id?: number
    priority?: number
    limit?: number
    offset?: number
  }
): Promise<MendingQueueListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.include_completed !== undefined) params.set('include_completed', filters.include_completed.toString())
    if (filters?.assigned_to_id) params.set('assigned_to_id', filters.assigned_to_id.toString())
    if (filters?.priority) params.set('priority', filters.priority.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    if (filters?.offset) params.set('offset', filters.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<MendingQueueListResponse>(`/staff/lost-damaged/mending-queue${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch mending queue')
    }
    throw error
  }
}

// ==================== Claims Returned API Functions ====================

export async function fileClaim(
  token: string,
  data: {
    checkout_id: number
    patron_statement: string
    claimed_return_date?: string
    claimed_return_location?: string
    send_notification?: boolean
  }
): Promise<ClaimsReturnedWorkflowResponse> {
  try {
    return await fetchApi<ClaimsReturnedWorkflowResponse>('/staff/lost-damaged/claims-returned/file', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to file claim')
    }
    throw error
  }
}

export async function startClaimReview(
  token: string,
  data: {
    dispute_id: number
    initial_notes?: string
  }
): Promise<ClaimsReturnedWorkflowResponse> {
  try {
    return await fetchApi<ClaimsReturnedWorkflowResponse>(`/staff/lost-damaged/claims-returned/${data.dispute_id}/start-review`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start review')
    }
    throw error
  }
}

export async function startClaimSearch(
  token: string,
  data: {
    dispute_id: number
    search_locations: string[]
    search_notes?: string
  }
): Promise<ClaimsReturnedWorkflowResponse> {
  try {
    return await fetchApi<ClaimsReturnedWorkflowResponse>(`/staff/lost-damaged/claims-returned/${data.dispute_id}/start-search`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start search')
    }
    throw error
  }
}

export async function resolveClaim(
  token: string,
  data: {
    dispute_id: number
    approved: boolean
    resolution_reason: string
    item_found?: boolean
    credit_amount?: number
    send_notification?: boolean
  }
): Promise<ClaimResolutionResponse> {
  try {
    return await fetchApi<ClaimResolutionResponse>(`/staff/lost-damaged/claims-returned/${data.dispute_id}/resolve`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve claim')
    }
    throw error
  }
}

export async function listClaims(
  token: string,
  filters?: {
    status?: string
    patron_id?: number
    days_ago?: number
    unresolved_only?: boolean
    limit?: number
    offset?: number
  }
): Promise<ClaimsListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.status) params.set('status', filters.status)
    if (filters?.patron_id) params.set('patron_id', filters.patron_id.toString())
    if (filters?.days_ago) params.set('days_ago', filters.days_ago.toString())
    if (filters?.unresolved_only !== undefined) params.set('unresolved_only', filters.unresolved_only.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    if (filters?.offset) params.set('offset', filters.offset.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<ClaimsListResponse>(`/staff/lost-damaged/claims-returned${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch claims')
    }
    throw error
  }
}

export async function getPatronClaimsHistory(token: string, patronId: number): Promise<PatronClaimsHistory> {
  try {
    return await fetchApi<PatronClaimsHistory>(`/staff/lost-damaged/claims-returned/patron/${patronId}/history`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron claims history')
    }
    throw error
  }
}

export async function getOverdueDisputes(token: string): Promise<{ count: number; items: ClaimsReturnedDispute[] }> {
  try {
    return await fetchApi<{ count: number; items: ClaimsReturnedDispute[] }>('/staff/lost-damaged/claims-returned/overdue', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch overdue disputes')
    }
    throw error
  }
}

// ==================== Bulk Operations API Functions ====================

export async function bulkWriteOffLostItems(token: string, data: BulkWriteOffRequest): Promise<BulkWriteOffResponse> {
  try {
    return await fetchApi<BulkWriteOffResponse>('/staff/lost-damaged/bulk/write-off', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk write-off failed')
    }
    throw error
  }
}

export async function bulkAssignMending(token: string, data: BulkMendingAssignRequest): Promise<BulkMendingAssignResponse> {
  try {
    return await fetchApi<BulkMendingAssignResponse>('/staff/lost-damaged/bulk/mending-assign', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk mending assignment failed')
    }
    throw error
  }
}

export async function bulkMarkLost(token: string, data: BulkMarkLostRequest): Promise<BulkMarkLostResponse> {
  try {
    return await fetchApi<BulkMarkLostResponse>('/staff/lost-damaged/bulk/mark-lost', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk mark lost failed')
    }
    throw error
  }
}

export async function bulkUpdateMendingPriority(
  token: string,
  entryIds: number[],
  priority: number
): Promise<{ updated_count: number; requested_count: number; priority: number }> {
  try {
    const params = new URLSearchParams()
    params.set('entry_ids', entryIds.join(','))
    params.set('priority', priority.toString())
    return await fetchApi<{ updated_count: number; requested_count: number; priority: number }>(
      `/staff/lost-damaged/bulk/mending-priority?${params.toString()}`,
      {
        method: 'POST',
        token,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk priority update failed')
    }
    throw error
  }
}

// ==================== Unified Item Issues API ====================

export type UnifiedIssueType = 'lost' | 'damaged' | 'claims'
export type UnifiedIssueStatus = 'reported' | 'claimed' | 'resolved'

export interface UnifiedItemIssue {
  id: number
  issue_type: UnifiedIssueType
  status: string
  patron_id: number | null
  patron_name: string | null
  patron_email: string | null
  item_title: string | null
  item_copy_id: number | null
  reported_at: string
  reported_by_id: number | null
  reported_by_name: string | null
  lost_type?: string
  replacement_cost?: number
  severity?: string
  is_patron_responsible?: boolean
  claimed_return_date?: string
  days_since_reported: number
  resolved_at: string | null
}

export interface UnifiedItemIssuesListResponse {
  items: UnifiedItemIssue[]
  total: number
  limit: number
  offset: number
}

export interface UnifiedIssuesSummary {
  total: number
  by_type: {
    lost: number
    damaged: number
    claims: number
  }
  by_status: {
    reported: number
    claimed: number
    resolved: number
  }
}

export async function listUnifiedItemIssues(
  token: string,
  filters?: {
    issue_types?: string[]
    statuses?: string[]
    patron_id?: number
    days_ago?: number
    limit?: number
    offset?: number
    sort_by?: string
    sort_order?: string
  }
): Promise<UnifiedItemIssuesListResponse> {
  try {
    const params = new URLSearchParams()
    if (filters?.issue_types?.length) params.set('issue_types', filters.issue_types.join(','))
    if (filters?.statuses?.length) params.set('statuses', filters.statuses.join(','))
    if (filters?.patron_id) params.set('patron_id', filters.patron_id.toString())
    if (filters?.days_ago) params.set('days_ago', filters.days_ago.toString())
    if (filters?.limit) params.set('limit', filters.limit.toString())
    if (filters?.offset) params.set('offset', filters.offset.toString())
    if (filters?.sort_by) params.set('sort_by', filters.sort_by)
    if (filters?.sort_order) params.set('sort_order', filters.sort_order)
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<UnifiedItemIssuesListResponse>(`/staff/lost-damaged/item-issues${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch item issues')
    }
    throw error
  }
}

export async function updateItemIssueStatus(
  token: string,
  issueId: number,
  issueType: UnifiedIssueType,
  data: {
    status: string
    notes?: string
  }
): Promise<{ success: boolean; message: string; issue_id: number; issue_type: string }> {
  try {
    const params = new URLSearchParams()
    params.set('issue_type', issueType)
    return await fetchApi<{ success: boolean; message: string; issue_id: number; issue_type: string }>(
      `/staff/lost-damaged/item-issues/${issueId}/status?${params.toString()}`,
      {
        method: 'PATCH',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update status')
    }
    throw error
  }
}

export async function bulkUpdateItemIssueStatuses(
  token: string,
  updates: Array<{ id: number; issue_type: UnifiedIssueType; status: string; notes?: string }>
): Promise<{ success: number; failed: number; errors: string[] }> {
  try {
    return await fetchApi<{ success: number; failed: number; errors: string[] }>(
      '/staff/lost-damaged/item-issues/bulk-update-status',
      {
        method: 'POST',
        token,
        body: { updates },
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk update failed')
    }
    throw error
  }
}

export async function contactPatronAboutIssue(
  token: string,
  issueId: number,
  issueType: UnifiedIssueType,
  data: {
    message: string
    send_email?: boolean
    send_sms?: boolean
  }
): Promise<{ success: boolean; patron_id: number; patron_name: string; messaging_url: string }> {
  try {
    const params = new URLSearchParams()
    params.set('issue_type', issueType)
    return await fetchApi<{ success: boolean; patron_id: number; patron_name: string; messaging_url: string }>(
      `/staff/lost-damaged/item-issues/${issueId}/contact-patron?${params.toString()}`,
      {
        method: 'POST',
        token,
        body: data,
      }
    )
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to contact patron')
    }
    throw error
  }
}

export async function getUnifiedIssuesSummary(token: string): Promise<UnifiedIssuesSummary> {
  try {
    return await fetchApi<UnifiedIssuesSummary>('/staff/lost-damaged/item-issues/stats/summary', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch summary')
    }
    throw error
  }
}
