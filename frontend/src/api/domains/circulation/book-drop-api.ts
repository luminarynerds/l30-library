/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Book Drop and Batch Check-in API Service
 *
 * Provides functions for:
 * - Book drop configuration management
 * - Batch check-in sessions
 * - Check-in statistics and analytics
 * - SIP2 device management
 * - Exception handling
 *
 * All endpoints require STAFF or ADMIN role.
 */

import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Types ====================

export type BookDropStatus = 'active' | 'inactive' | 'maintenance'
export type CheckInSessionStatus = 'active' | 'completed' | 'cancelled'
export type CheckInResultStatus = 'success' | 'hold_triggered' | 'transit' | 'exception' | 'not_found'
export type ExceptionType =
  | 'item_not_found'
  | 'item_not_checked_out'
  | 'hold_conflict'
  | 'damaged'
  | 'claims_returned'
  | 'missing'
  | 'other'
export type BackdateMode = 'none' | 'fixed_time' | 'hours_back' | 'days_back'

export interface BookDrop {
  id: number
  name: string
  code: string
  branch_location: string
  description: string | null
  physical_location: string | null
  status: BookDropStatus
  backdate_mode: BackdateMode
  backdate_fixed_time: string | null
  backdate_hours: number | null
  backdate_days: number | null
  processing_start_time: string | null
  processing_end_time: string | null
  exempt_overnight_fines: boolean
  max_backdate_hours: number | null
  sip2_device_id: number | null
  created_at: string
  updated_at: string | null
}

export interface BookDropCreate {
  name: string
  code: string
  branch_location: string
  description?: string
  physical_location?: string
  backdate_mode?: BackdateMode
  backdate_fixed_time?: string
  backdate_hours?: number
  backdate_days?: number
  processing_start_time?: string
  processing_end_time?: string
  exempt_overnight_fines?: boolean
  max_backdate_hours?: number
  sip2_device_id?: number
}

export interface BookDropUpdate {
  name?: string
  code?: string
  branch_location?: string
  description?: string
  physical_location?: string
  status?: BookDropStatus
  backdate_mode?: BackdateMode
  backdate_fixed_time?: string
  backdate_hours?: number
  backdate_days?: number
  processing_start_time?: string
  processing_end_time?: string
  exempt_overnight_fines?: boolean
  max_backdate_hours?: number
  sip2_device_id?: number
}

export interface SIP2Device {
  id: number
  device_id: string
  name: string
  description: string | null
  ip_address: string | null
  port: number | null
  status: 'online' | 'offline' | 'error'
  last_communication: string | null
  error_message: string | null
  created_at: string
  updated_at: string | null
}


export interface CheckInSession {
  id: number
  session_code: string
  book_drop_id: number | null
  branch_location: string
  workstation_id: string | null
  staff_id: number
  status: CheckInSessionStatus
  started_at: string
  ended_at: string | null
  use_backdating: boolean
  backdate_to: string | null
  total_items: number
  successful_checkins: number
  holds_trapped: number
  transits_created: number
  exceptions_count: number
  success_rate: number | null
}

export interface CheckInSessionCreate {
  branch_location: string
  book_drop_id?: number
  workstation_id?: string
  backdate_to?: string
}

export interface CheckInSessionSummary {
  id: number
  session_code: string
  branch_location: string
  status: CheckInSessionStatus
  started_at: string
  ended_at: string | null
  total_items: number
  staff_name: string | null
}

export interface CheckInResult {
  id: number
  barcode: string
  status: CheckInResultStatus
  item_copy_id: number | null
  checkout_id: number | null
  item_title: string | null
  item_author: string | null
  sort_destination: string | null
  sort_bin: string | null
  hold_id: number | null
  hold_patron_name: string | null
  destination_branch: string | null
  checked_in_at: string
  effective_checkin_time: string | null
  was_overdue: boolean
  overdue_days: number | null
  fine_amount: string
  fine_waived_by_backdate: boolean
  condition_checked: boolean
  condition_status: string | null
  exception_type: ExceptionType | null
  exception_message: string | null
}

export interface BatchCheckInItem {
  barcode: string
  condition_status?: string
  condition_notes?: string
}

export interface BatchCheckInRequest {
  items: BatchCheckInItem[]
  skip_condition_check?: boolean
  override_backdate?: string
}

export interface SingleCheckInRequest {
  barcode: string
  condition_status?: string
  condition_notes?: string
  override_backdate?: string
}

export interface BatchCheckInResponse {
  session_id: number
  processed_count: number
  successful_count: number
  holds_trapped: number
  transits_created: number
  exceptions_count: number
  results: CheckInResult[]
  items_with_holds: CheckInResult[]
  items_for_transit: CheckInResult[]
  items_with_exceptions: CheckInResult[]
}

export interface BookDropCheckInRequest {
  book_drop_id: number
  items: BatchCheckInItem[]
  apply_backdating?: boolean
  calculate_backdate_from?: string
}

export interface BookDropCheckInResponse {
  book_drop_id: number
  book_drop_name: string
  session_id: number
  backdated_to: string | null
  fines_waived_count: number
  fines_waived_amount: string
  processed_count: number
  successful_count: number
  holds_trapped: number
  transits_created: number
  exceptions_count: number
  results: CheckInResult[]
}

export interface CheckInException {
  id: number
  session_id: number
  result_id: number
  exception_type: ExceptionType
  barcode: string
  message: string
  resolved: boolean
  resolved_at: string | null
  resolved_by_id: number | null
  resolved_by_name: string | null
  action_taken: string | null
  created_at: string
}

export interface ResolveExceptionRequest {
  action_taken: string
}

export interface CheckInStatistic {
  id: number
  date: string
  branch_location: string
  book_drop_id: number | null
  total_checkins: number
  successful_checkins: number
  holds_trapped: number
  transits_created: number
  exceptions_count: number
  total_fines: string
  fines_waived: string
  staff_checkins: number
  book_drop_checkins: number
  self_service_checkins: number
  peak_hour: number
}

export interface StatisticsSummary {
  period_start: string
  period_end: string
  branch_location: string | null
  total_checkins: number
  avg_daily_checkins: number
  peak_hour: number
  peak_day_of_week: number
  holds_trapped_total: number
  transits_total: number
  exceptions_total: number
  total_fines: string
  total_fines_waived: string
  staff_checkins_pct: number
  book_drop_checkins_pct: number
  self_service_checkins_pct: number
}

export interface SessionDetailSummary {
  session: CheckInSession
  results_by_status: Record<CheckInResultStatus, number>
  items_by_sort_destination: Record<string, number>
  overdue_stats: {
    total_overdue: number
    total_fines: string
    fines_waived: string
  }
  hourly_breakdown: { hour: number; count: number }[]
}

export interface FastScanResponse {
  result: CheckInResult
  destination_summary?: DestinationSummaryResponse
  requires_damage_check?: boolean
}

export interface DestinationSummaryResponse {
  destinations: Record<string, number>
  total_items: number
  holds_count: number
  transit_count: number
}

export interface ResolveClaimsReturnedResponse {
  result_id: number
  barcode: string
  resolved: boolean
  resolution_notes: string
  checkout_cleared: boolean
  fine_waived: boolean
}

export interface DamageCheckRequirement {
  required: boolean
  check_in_result_id: number
  barcode: string
  item_title?: string | null
  last_condition_status?: string | null
  days_since_last_checkout?: number | null
}

// ==================== Book Drop Management ====================

export async function createBookDrop(
  token: string,
  data: BookDropCreate
): Promise<BookDrop> {
  try {
    return await fetchApi<BookDrop>('/book-drop/locations', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create book drop')
    }
    throw error
  }
}

export async function listBookDrops(
  token: string,
  options?: {
    branch_location?: string
    status?: BookDropStatus
    limit?: number
    offset?: number
  }
): Promise<BookDrop[]> {
  try {
    const params = new URLSearchParams()
    if (options?.branch_location) params.set('branch_location', options.branch_location)
    if (options?.status) params.set('status', options.status)
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<BookDrop[]>(`/book-drop/locations${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch book drops')
    }
    throw error
  }
}

export async function getBookDrop(
  token: string,
  bookDropId: number
): Promise<BookDrop> {
  try {
    return await fetchApi<BookDrop>(`/book-drop/locations/${bookDropId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch book drop')
    }
    throw error
  }
}

export async function updateBookDrop(
  token: string,
  bookDropId: number,
  data: BookDropUpdate
): Promise<BookDrop> {
  try {
    return await fetchApi<BookDrop>(`/book-drop/locations/${bookDropId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update book drop')
    }
    throw error
  }
}

export async function deleteBookDrop(
  token: string,
  bookDropId: number
): Promise<void> {
  try {
    await fetchApi<void>(`/book-drop/locations/${bookDropId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete book drop')
    }
    throw error
  }
}

// ==================== Check-in Sessions ====================

export async function startCheckInSession(
  token: string,
  data: CheckInSessionCreate
): Promise<CheckInSession> {
  try {
    return await fetchApi<CheckInSession>('/book-drop/sessions', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to start session')
    }
    throw error
  }
}

export async function listSessions(
  token: string,
  options?: {
    branch_location?: string
    status?: CheckInSessionStatus
    limit?: number
  }
): Promise<CheckInSessionSummary[]> {
  try {
    const params = new URLSearchParams()
    if (options?.branch_location) params.set('branch_location', options.branch_location)
    if (options?.status) params.set('status', options.status)
    if (options?.limit) params.set('limit', options.limit.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<CheckInSessionSummary[]>(`/book-drop/sessions${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch sessions')
    }
    throw error
  }
}

export async function listActiveSessions(
  token: string,
  branch_location?: string
): Promise<CheckInSession[]> {
  try {
    const params = branch_location ? `?branch_location=${encodeURIComponent(branch_location)}` : ''
    return await fetchApi<CheckInSession[]>(`/book-drop/sessions/active${params}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch active sessions')
    }
    throw error
  }
}

export async function getSession(
  token: string,
  sessionId: number
): Promise<CheckInSession> {
  try {
    return await fetchApi<CheckInSession>(`/book-drop/sessions/${sessionId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch session')
    }
    throw error
  }
}

export async function getSessionSummary(
  token: string,
  sessionId: number
): Promise<SessionDetailSummary> {
  try {
    return await fetchApi<SessionDetailSummary>(`/book-drop/sessions/${sessionId}/summary`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch session summary')
    }
    throw error
  }
}

export async function endSession(
  token: string,
  sessionId: number
): Promise<CheckInSession> {
  try {
    return await fetchApi<CheckInSession>(`/book-drop/sessions/${sessionId}/end`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to end session')
    }
    throw error
  }
}

// ==================== Check-in Operations ====================

export async function checkInItem(
  token: string,
  sessionId: number,
  data: SingleCheckInRequest
): Promise<CheckInResult> {
  try {
    return await fetchApi<CheckInResult>(`/book-drop/sessions/${sessionId}/checkin`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Check-in failed')
    }
    throw error
  }
}

export async function checkInBatch(
  token: string,
  sessionId: number,
  data: BatchCheckInRequest
): Promise<BatchCheckInResponse> {
  try {
    return await fetchApi<BatchCheckInResponse>(`/book-drop/sessions/${sessionId}/batch`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Batch check-in failed')
    }
    throw error
  }
}

export async function processBookDrop(
  token: string,
  data: BookDropCheckInRequest
): Promise<BookDropCheckInResponse> {
  try {
    return await fetchApi<BookDropCheckInResponse>('/book-drop/process-book-drop', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Book drop processing failed')
    }
    throw error
  }
}

export async function getSessionResults(
  token: string,
  sessionId: number,
  options?: {
    status?: CheckInResultStatus
    limit?: number
    offset?: number
  }
): Promise<CheckInResult[]> {
  try {
    const params = new URLSearchParams()
    if (options?.status) params.set('status', options.status)
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<CheckInResult[]>(`/book-drop/sessions/${sessionId}/results${queryString}`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch session results')
    }
    throw error
  }
}

// ==================== Fast Processing ====================

export async function fastProcessingScan(
  token: string,
  sessionId: number,
  barcode: string,
  checkDamage?: boolean,
  damageStatus?: string
): Promise<FastScanResponse> {
  try {
    return await fetchApi<FastScanResponse>(`/book-drop/sessions/${sessionId}/fast-scan`, {
      method: 'POST',
      token,
      body: {
        session_id: sessionId,
        barcode,
        check_damage: checkDamage || false,
        damage_status: damageStatus,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to process barcode')
    }
    throw error
  }
}

export async function getDestinationSummary(token: string, sessionId: number): Promise<DestinationSummaryResponse> {
  try {
    return await fetchApi<DestinationSummaryResponse>(`/book-drop/sessions/${sessionId}/destination-summary`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get destination summary')
    }
    throw error
  }
}

export async function resolveClaimsReturned(
  token: string,
  resultId: number,
  resolutionNotes: string
): Promise<ResolveClaimsReturnedResponse> {
  try {
    return await fetchApi<ResolveClaimsReturnedResponse>(`/book-drop/check-in-results/${resultId}/resolve-claims-returned`, {
      method: 'POST',
      token,
      body: {
        check_in_result_id: resultId,
        resolution_notes: resolutionNotes,
      },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve claims returned')
    }
    throw error
  }
}

export async function getDamageCheckRequirement(token: string, resultId: number): Promise<DamageCheckRequirement> {
  try {
    return await fetchApi<DamageCheckRequirement>(`/book-drop/check-in-results/${resultId}/damage-check-required`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get damage check requirement')
    }
    throw error
  }
}

// ==================== Exceptions ====================

export async function listExceptions(
  token: string,
  options?: {
    branch_location?: string
    exception_type?: ExceptionType
    resolved?: boolean
    limit?: number
    offset?: number
  }
): Promise<CheckInException[]> {
  try {
    const params = new URLSearchParams()
    if (options?.branch_location) params.set('branch_location', options.branch_location)
    if (options?.exception_type) params.set('exception_type', options.exception_type)
    if (options?.resolved !== undefined) params.set('resolved', options.resolved.toString())
    if (options?.limit) params.set('limit', options.limit.toString())
    if (options?.offset) params.set('offset', options.offset.toString())

    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<CheckInException[]>(`/book-drop/exceptions${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch exceptions')
    }
    throw error
  }
}

export async function resolveException(
  token: string,
  exceptionId: number,
  data: ResolveExceptionRequest
): Promise<CheckInException> {
  try {
    return await fetchApi<CheckInException>(`/book-drop/exceptions/${exceptionId}/resolve`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to resolve exception')
    }
    throw error
  }
}

// ==================== Statistics ====================

export async function getStatistics(
  token: string,
  startDate: string,
  endDate: string,
  options?: {
    branch_location?: string
    book_drop_id?: number
  }
): Promise<CheckInStatistic[]> {
  try {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)
    if (options?.branch_location) params.set('branch_location', options.branch_location)
    if (options?.book_drop_id) params.set('book_drop_id', options.book_drop_id.toString())

    return await fetchApi<CheckInStatistic[]>(`/book-drop/statistics?${params.toString()}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch statistics')
    }
    throw error
  }
}

export async function getStatisticsSummary(
  token: string,
  startDate: string,
  endDate: string,
  branch_location?: string
): Promise<StatisticsSummary> {
  try {
    const params = new URLSearchParams()
    params.set('start_date', startDate)
    params.set('end_date', endDate)
    if (branch_location) params.set('branch_location', branch_location)

    return await fetchApi<StatisticsSummary>(`/book-drop/statistics/summary?${params.toString()}`, {
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch statistics summary')
    }
    throw error
  }
}

// ==================== SIP2 Devices ====================


export async function listSIP2Devices(token: string): Promise<SIP2Device[]> {
  try {
    return await fetchApi<SIP2Device[]>('/book-drop/sip2-devices', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch SIP2 devices')
    }
    throw error
  }
}

export async function getSIP2Device(
  token: string,
  deviceId: number
): Promise<SIP2Device> {
  try {
    return await fetchApi<SIP2Device>(`/book-drop/sip2-devices/${deviceId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch SIP2 device')
    }
    throw error
  }
}



export async function testSIP2Device(
  token: string,
  deviceId: number
): Promise<{
  device_id: string
  online: boolean
  status?: string
  last_communication?: string
  error_message?: string
  error?: string
}> {
  try {
    return await fetchApi(`/book-drop/sip2-devices/${deviceId}/test`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to test SIP2 device')
    }
    throw error
  }
}

// ==================== Utility Functions ====================

export function getResultStatusLabel(status: CheckInResultStatus): string {
  const labels: Record<CheckInResultStatus, string> = {
    success: 'Success',
    hold_triggered: 'Hold Triggered',
    transit: 'In Transit',
    exception: 'Exception',
    not_found: 'Not Found',
  }
  return labels[status] || status
}

export function getResultStatusColor(status: CheckInResultStatus): string {
  const colors: Record<CheckInResultStatus, string> = {
    success: 'green',
    hold_triggered: 'blue',
    transit: 'purple',
    exception: 'red',
    not_found: 'gray',
  }
  return colors[status] || 'gray'
}

export function getExceptionTypeLabel(type: ExceptionType): string {
  const labels: Record<ExceptionType, string> = {
    item_not_found: 'Item Not Found',
    item_not_checked_out: 'Not Checked Out',
    hold_conflict: 'Hold Conflict',
    damaged: 'Damaged',
    claims_returned: 'Claims Returned',
    missing: 'Missing',
    other: 'Other',
  }
  return labels[type] || type
}

export function getBookDropStatusLabel(status: BookDropStatus): string {
  const labels: Record<BookDropStatus, string> = {
    active: 'Active',
    inactive: 'Inactive',
    maintenance: 'Maintenance',
  }
  return labels[status] || status
}

export function getBackdateModeLabel(mode: BackdateMode): string {
  const labels: Record<BackdateMode, string> = {
    none: 'No Backdating',
    fixed_time: 'Fixed Time',
    hours_back: 'Hours Back',
    days_back: 'Days Back',
  }
  return labels[mode] || mode
}

export function formatCurrency(amount: string | number): string {
  const num = typeof amount === 'string' ? parseFloat(amount) : amount
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(num)
}

/**
 * Available exception types for filtering
 */
export const EXCEPTION_TYPES: { value: ExceptionType; label: string }[] = [
  { value: 'item_not_found', label: 'Item Not Found' },
  { value: 'item_not_checked_out', label: 'Not Checked Out' },
  { value: 'hold_conflict', label: 'Hold Conflict' },
  { value: 'damaged', label: 'Damaged' },
  { value: 'claims_returned', label: 'Claims Returned' },
  { value: 'missing', label: 'Missing' },
  { value: 'other', label: 'Other' },
]

/**
 * Available book drop statuses
 */
export const BOOK_DROP_STATUSES: { value: BookDropStatus; label: string }[] = [
  { value: 'active', label: 'Active' },
  { value: 'inactive', label: 'Inactive' },
  { value: 'maintenance', label: 'Maintenance' },
]

/**
 * Available backdate modes
 */
export const BACKDATE_MODES: { value: BackdateMode; label: string }[] = [
  { value: 'none', label: 'No Backdating' },
  { value: 'fixed_time', label: 'Fixed Time Daily' },
  { value: 'hours_back', label: 'Hours Back from Processing' },
  { value: 'days_back', label: 'Days Back' },
]
