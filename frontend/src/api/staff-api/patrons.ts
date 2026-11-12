/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import { API_BASE } from '@/api/types'
import type { Checkout, Hold } from '../circulation-api'
import type { components } from '@/api/generated/schema';

// ==================== Patron Types ====================

// Patron lifecycle status type
export type PatronStatus = 'active' | 'suspended' | 'blocked' | 'deceased'

export interface Patron {
  id: number
  email: string | null
  /** Masked email (e.g. j***@example.com) populated by the PII filter when the caller is below SENSITIVE clearance. */
  email_masked?: string | null
  first_name: string
  last_name: string
  role: string
  is_active: boolean
  library_card: string | null
  library_card_number?: string | null
  phone: string | null
  address: string | null
  created_at: string
  fines_balance?: number
  total_checkouts: number
  current_checkouts: number
  current_holds: number
  photo_url?: string
  card_expires_at?: string
  blocked?: boolean
  // Lifecycle status fields
  patron_status?: PatronStatus
  suspension_reason?: string | null
  suspended_until?: string | null
  suspended_at?: string | null
  block_reason?: string | null
  blocked_at?: string | null
  date_of_death?: string | null
  estate_contact_name?: string | null
  estate_followup_required?: boolean
  last_login?: string | null
  card_type?: string | null
  date_of_birth?: string | null
  preferred_contact_method?: "email" | "phone" | "mail" | null
  language_preference?: string | null
  accessibility_needs?: string | null
  emergency_contact_name?: string | null
  emergency_contact_phone?: string | null
  // Onboarding fields
  onboarding_completed_at?: string | null
  onboarding_skipped?: boolean
  // Teacher card linkage (set via PATCH /staff/patrons/{id}/teacher-card)
  school_id?: number | null
}

export interface PatronSearchResult {
  patrons: Patron[]
  total: number
  page: number
  per_page: number
}

// Advanced filter types
export type PatronSortField = components['schemas']['PatronSortField'];
export type SortDirection = components['schemas']['SortDirection'];
export type OverdueFilter = components['schemas']['OverdueFilter'];
export type CardStatusFilter = 'any' | 'active' | 'expiring_30d' | 'expiring_90d' | 'expired'
export interface PatronAdvancedFilters {
  memberSinceFrom?: string  // ISO date string
  memberSinceTo?: string    // ISO date string
  finesMin?: number
  finesMax?: number
  checkoutCountMin?: number
  hasOverdue?: OverdueFilter
  cardStatus?: CardStatusFilter
  sortBy?: PatronSortField
  sortDirection?: SortDirection
}

export interface FilterPreset {
  id: string
  name: string
  filters: PatronAdvancedFilters & { statusFilter?: 'all' | 'active' | 'blocked' }
  createdAt: string
}

export interface PatronCheckout extends Checkout {
  patron_name?: string
  patron_email?: string
  barcode?: string
}

// ==================== Patron Statistics Types ====================

export interface AtRiskCounts {
  patrons_with_many_overdue: number
  patrons_with_high_fines: number
  inactive_patrons: number
}

export interface ExpiringCardsCounts {
  expiring_within_30d: number
  expiring_within_90d: number
  expired: number
}

export interface AtRiskPatron {
  id: number
  first_name: string
  last_name: string
  email: string
  library_card: string | null
  overdue_count: number
  fines_balance: number
  last_activity_date: string | null
}

export interface PatronStatistics {
  total_patrons: number
  active_patrons: number
  blocked_patrons: number
  new_this_week: number
  new_this_month: number
  total_fines_outstanding: number
  total_overdue_items: number
  at_risk_counts: AtRiskCounts
  expiring_cards_counts?: ExpiringCardsCounts
  patrons_with_many_overdue: AtRiskPatron[]
  patrons_with_high_fines: AtRiskPatron[]
  inactive_patrons: AtRiskPatron[]
}

// ==================== Family / Linked Accounts Types ====================

export interface LinkedAccountInfo {
  id: number
  first_name: string
  last_name: string
  email: string
  library_card: string | null
  is_active: boolean
}

export interface PatronFamilyResponse {
  patron_id: number
  parent_guardian: LinkedAccountInfo | null
  children: LinkedAccountInfo[]
}

// ==================== Block / Status Types ====================

export interface BlockPatronRequest {
  reason?: string
}

export interface BlockPatronResponse {
  patron: Patron
  message: string
}

export interface UpdatePatronStatusRequest {
  status: PatronStatus
  reason?: string
  suspended_until?: string
  date_of_death?: string
  estate_contact_name?: string
  estate_followup_required?: boolean
}

export interface UpdatePatronStatusResponse {
  patron: Patron
  message: string
  previous_status: PatronStatus
}

// ==================== Bulk Operations Types ====================

export interface BulkBlockRequest {
  patron_ids: number[]
  blocked: boolean
  reason?: string
}

export interface BulkBlockResponse {
  success: boolean
  processed_count: number
  failed_ids: number[]
  message: string
}

export interface BulkWaiveFinesRequest {
  patron_ids: number[]
  reason: string
}

export interface BulkWaiveFinesResponse {
  success: boolean
  patrons_processed: number
  fines_waived: number
  total_amount_waived: number
  failed_ids: number[]
  message: string
}

export interface BulkNotificationRequest {
  patron_ids: number[]
  subject: string
  message: string
  notification_type?: 'general' | 'reminder' | 'alert'
}

export interface BulkNotificationResponse {
  success: boolean
  sent_count: number
  failed_ids: number[]
  message: string
}

export interface PatronExportData {
  id: number
  first_name: string
  last_name: string
  email: string
  library_card: string | null
  phone: string | null
  address: string | null
  is_active: boolean
  created_at: string
  fines_balance: number
  current_checkouts: number
  current_holds: number
  total_checkouts: number
}

export interface PatronExportResponse {
  patrons: PatronExportData[]
  total_count: number
  exported_at: string
}

// ==================== Patron Account Management Types ====================

export interface PasswordResetRequest {
  send_email?: boolean
  generate_temp_code?: boolean
}

export interface PasswordResetResponse {
  message: string
  email_sent: boolean
  temp_code?: string
  last_password_change?: string
}

export interface PasswordInfo {
  patron_id: number
  last_password_change: string
  password_change_count: number
  has_pending_reset: boolean
}

export interface DuplicatePatron {
  id: number
  email: string
  first_name: string
  last_name: string
  phone?: string
  library_card?: string
  created_at: string
  is_active: boolean
  match_type: string
  match_score: number
  total_checkouts: number
  total_holds: number
  fines_balance: number
}

export interface DuplicateSearchResponse {
  patron_id: number
  duplicates: DuplicatePatron[]
  search_criteria: {
    email: string
    name: string
    phone?: string
  }
}

export interface MergeRequest {
  primary_patron_id: number
  secondary_patron_id: number
  merge_checkouts?: boolean
  merge_holds?: boolean
  merge_fines?: boolean
  merge_history?: boolean
}

export interface MergePreview {
  primary_patron: {
    id: number
    email: string
    name: string
    library_card?: string
    created_at: string
  }
  secondary_patron: {
    id: number
    email: string
    name: string
    library_card?: string
    created_at: string
  }
  checkouts_to_transfer: number
  holds_to_transfer: number
  fines_to_transfer: number
  history_records_to_transfer: number
}

export interface MergeResponse {
  message: string
  merged_patron_id: number
  deleted_patron_id: number
  checkouts_transferred: number
  holds_transferred: number
  fines_transferred: number
  history_transferred: number
}

export interface LibraryCardData {
  patron_id: number
  patron_name: string
  library_card_number: string
  barcode_value: string
  library_name: string
  library_logo_url?: string
  expiration_date?: string
  card_type: 'standard' | 'youth' | 'senior'
  issue_date: string
  patron_photo_url?: string
}

export interface CardPrintedRequest {
  card_type?: string
  is_replacement?: boolean
  reason?: string
}

export interface CardPrintHistory {
  id: number
  printed_at: string
  card_type: string
  is_replacement: boolean
  reason?: string
  printed_by_id: number
  printed_by_name: string
}

export interface CardPrintedResponse {
  message: string
  print_count: number
  print_history: CardPrintHistory[]
}

export interface AccountSettings {
  patron_id: number
  notification_email: boolean
  notification_sms: boolean
  notification_hold_ready: boolean
  notification_due_reminder: boolean
  notification_overdue: boolean
  checkout_limit: number
  hold_limit: number
  saved_searches_count: number
  reading_lists_count: number
  communication_preferences?: Record<string, unknown>
  display_preferences?: Record<string, unknown>
}

export interface AccountSettingsUpdate {
  notification_email?: boolean | undefined
  notification_sms?: boolean | undefined
  notification_hold_ready?: boolean | undefined
  notification_due_reminder?: boolean | undefined
  notification_overdue?: boolean | undefined
  checkout_limit?: number | undefined
  hold_limit?: number | undefined
  communication_preferences?: Record<string, unknown> | undefined
  display_preferences?: Record<string, unknown> | undefined
}

// ==================== Merge History Types ====================

export interface MergeAuditLog {
  id: number
  merged_at: string
  merged_by_id?: number
  merged_by_name?: string
  primary_patron_id?: number
  secondary_patron_id: number
  deleted_patron_email?: string
  deleted_patron_name?: string
  checkouts_transferred: number
  holds_transferred: number
  fines_transferred: number
  reading_lists_transferred: number
  favorites_transferred: number
  total_items_transferred: number
  has_archived_data: boolean
}

export interface MergeHistoryResponse {
  patron_id: number
  as_primary: MergeAuditLog[]
  as_secondary: MergeAuditLog[]
  total_merges: number
}

export interface MergeAuditDetails {
  id: number
  merged_at: string
  merged_by?: {
    id: number
    name: string
    email: string
  }
  primary_patron?: {
    id: number
    name: string
    email: string
    library_card?: string
  }
  primary_patron_id?: number
  secondary_patron_id: number
  data_transferred: {
    checkouts: Array<{ id: number; item_id: number; status?: string }>
    holds: Array<{ id: number; item_id: number; status?: string }>
    fines: Array<{ id: number; amount: string; status?: string }>
    reading_lists: Array<{ id: number; name: string }>
    favorites: Array<{ id: number; catalog_item_id: number }>
  }
  data_archived: {
    user: {
      id: number
      email: string
      first_name: string
      last_name: string
      phone?: string
      address?: string
      library_card?: string
    }
    checkouts: Array<{ id: number; item_id: number; status?: string }>
    holds: Array<{ id: number; item_id: number; status?: string }>
    fines: Array<{ id: number; amount: string; status?: string }>
    reading_lists: Array<{ id: number; name: string }>
    favorites: Array<{ id: number; catalog_item_id: number }>
  }
  checkouts_transferred: number
  holds_transferred: number
  fines_transferred: number
  reading_lists_transferred: number
  favorites_transferred: number
  total_items_transferred: number
  notes?: string
  ip_address?: string
  created_at: string
}

// ==================== Deceased/Estate Management Types ====================

export interface MarkDeceasedRequest {
  date_of_death?: string
  estate_contact_name?: string
  estate_contact_email?: string
  estate_contact_phone?: string
  notes?: string
}

export interface DeceasedPatronResponse {
  message: string
  patron_id: number
  patron_name: string
  date_of_death?: string
  outstanding_checkouts: number
  outstanding_holds: number
  outstanding_fines_amount: number
  estate_followup_required: boolean
  estate_contact_name?: string
  estate_contact_email?: string
  notification_sent: boolean
}

export interface EstateOutstandingItem {
  checkout_id: number
  item_id: number
  title: string
  author?: string
  barcode?: string
  checked_out_at?: string
  due_date?: string
  status: string
}

export interface EstateFine {
  fine_id: number
  type: string
  amount: number
  amount_paid: number
  amount_due: number
  description?: string
  created_at?: string
}

export interface EstateOutstandingResponse {
  patron_id: number
  patron_name: string
  date_of_death?: string
  estate_contact_name?: string
  estate_contact_email?: string
  estate_contact_phone?: string
  checkouts: EstateOutstandingItem[]
  fines: EstateFine[]
  total_fines_amount: number
  notes?: string
}

export interface EstateContactUpdate {
  estate_contact_name?: string
  estate_contact_email?: string
  estate_contact_phone?: string
  notes?: string
}

export interface EstateResolvedResponse {
  message: string
  patron_id: number
  estate_followup_required: boolean
}

// ==================== Patron Activity Timeline Types ====================

export type PatronActivityType =
  | 'checkout'
  | 'return'
  | 'renewal'
  | 'fine_created'
  | 'fine_paid'
  | 'fine_waived'
  | 'hold_placed'
  | 'hold_fulfilled'
  | 'hold_cancelled'
  | 'hold_expired'
  | 'account_blocked'
  | 'account_unblocked'
  | 'account_created'
  | 'profile_updated'

export interface PatronActivity {
  id: number
  patron_id: number
  staff_id: number | null
  staff_name: string | null
  activity_type: PatronActivityType
  type?: PatronActivityType
  description: string
  item_id: number | null
  item_title: string | null
  item_author: string | null
  fine_id: number | null
  fine_amount: string | null
  checkout_id: number | null
  hold_id: number | null
  metadata: string | null
  created_at: string
}

export interface PatronActivityListResponse {
  activities: PatronActivity[]
  total: number
  page: number
  per_page: number
  has_more: boolean
}

// ==================== Patron Photo Types ====================

export interface PatronPhotoUpload {
  photo_data: string
  content_type: string
}

export interface PatronPhotoResponse {
  photo_url: string
  message: string
}

// ==================== Enhanced Patron Profile Types ====================

export interface EnhancedPatronProfile extends Patron {
  emergency_contact_name?: string
  emergency_contact_phone?: string
  preferred_contact_method?: 'email' | 'phone' | 'mail'
  language_preference?: string
  accessibility_needs?: string
  patron_type?: 'adult' | 'teen' | 'child'
  custom_fields?: string
  photo_url?: string
  date_of_birth?: string
}

export interface PatronProfileUpdate {
  first_name?: string
  last_name?: string
  phone?: string
  address?: string
  emergency_contact_name?: string
  emergency_contact_phone?: string
  preferred_contact_method?: 'email' | 'phone' | 'mail'
  language_preference?: string
  accessibility_needs?: string
  patron_type?: 'adult' | 'teen' | 'child'
  custom_fields?: string
  date_of_birth?: string
}

// ==================== Patron Functions ====================

export async function getPatronStatistics(token: string): Promise<PatronStatistics> {
  try {
    return await fetchApi<PatronStatistics>('/staff/patrons/statistics', { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron statistics')
    }
    throw error
  }
}

export async function searchPatrons(
  token: string,
  query: string,
  page = 1,
  advancedFilters?: PatronAdvancedFilters,
  statusFilter?: 'all' | 'active' | 'blocked',
  perPage = 20
): Promise<PatronSearchResult> {
  const params = new URLSearchParams()
  if (query) params.set('search', query)

  // Pagination - backend uses limit/offset, convert from page
  params.set('limit', perPage.toString())
  params.set('offset', ((page - 1) * perPage).toString())

  // Status filter
  if (statusFilter && statusFilter !== 'all') {
    params.set('is_active', statusFilter === 'active' ? 'true' : 'false')
  }

  // Advanced filters
  if (advancedFilters) {
    if (advancedFilters.memberSinceFrom) {
      params.set('member_since_from', advancedFilters.memberSinceFrom)
    }
    if (advancedFilters.memberSinceTo) {
      params.set('member_since_to', advancedFilters.memberSinceTo)
    }
    if (advancedFilters.finesMin !== undefined) {
      params.set('fines_min', advancedFilters.finesMin.toString())
    }
    if (advancedFilters.finesMax !== undefined) {
      params.set('fines_max', advancedFilters.finesMax.toString())
    }
    if (advancedFilters.checkoutCountMin !== undefined) {
      params.set('checkout_count_min', advancedFilters.checkoutCountMin.toString())
    }
    if (advancedFilters.hasOverdue && advancedFilters.hasOverdue !== 'all') {
      params.set('has_overdue', advancedFilters.hasOverdue)
    }
    if (advancedFilters.cardStatus && advancedFilters.cardStatus !== 'any') {
      params.set('cardStatus', advancedFilters.cardStatus)
    }
    if (advancedFilters.sortBy) {
      params.set('sort_by', advancedFilters.sortBy)
    }
    if (advancedFilters.sortDirection) {
      params.set('sort_direction', advancedFilters.sortDirection)
    }
  }

  const response = await fetchApi<{ patrons: Patron[]; total_count: number }>(`/staff/patrons?${params}`, { token })

  return {
    patrons: response.patrons,
    total: response.total_count,
    page,
    per_page: perPage,
  }
}

// Quick search for autocomplete suggestions (limited results)
export async function searchPatronsSuggestions(
  token: string,
  query: string
): Promise<Patron[]> {
  try {
    if (!query || query.length < 2) return []

    const params = new URLSearchParams()
    params.set('search', query)
    params.set('limit', '5')
    params.set('offset', '0')

    const response = await fetchApi<{ patrons: Patron[]; total_count: number }>(`/staff/patrons?${params}`, { token })
    return response.patrons
  } catch {
    return []
  }
}

export async function getPatron(token: string, patronId: number): Promise<Patron> {
  try {
    return await fetchApi<Patron>(`/staff/patrons/${patronId}`, { token })
  } catch {
    throw new Error('Failed to fetch patron')
  }
}


export async function togglePatronBlock(token: string, patronId: number, blocked: boolean): Promise<Patron> {
  try {
    return await fetchApi<Patron>(`/staff/patrons/${patronId}/block`, {
      method: 'POST',
      token,
      body: { blocked },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Action failed')
    }
    throw error
  }
}

export async function blockPatron(
  token: string,
  patronId: number,
  reason?: string
): Promise<BlockPatronResponse> {
  try {
    return await fetchApi<BlockPatronResponse>(`/staff/patrons/${patronId}/block`, {
      method: 'POST',
      token,
      body: { blocked: true, reason },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to block patron')
    }
    throw error
  }
}

export async function updatePatronStatus(
  token: string,
  patronId: number,
  data: UpdatePatronStatusRequest
): Promise<UpdatePatronStatusResponse> {
  try {
    return await fetchApi<UpdatePatronStatusResponse>(`/staff/patrons/${patronId}/status`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update patron status')
    }
    throw error
  }
}

export async function getPatronCheckouts(token: string, patronId: number): Promise<PatronCheckout[]> {
  try {
    return await fetchApi<PatronCheckout[]>(`/staff/patrons/${patronId}/checkouts`, { token })
  } catch {
    throw new Error('Failed to fetch patron checkouts')
  }
}

export async function getPatronHolds(token: string, patronId: number): Promise<Hold[]> {
  try {
    return await fetchApi<Hold[]>(`/staff/patrons/${patronId}/holds`, { token })
  } catch {
    throw new Error('Failed to fetch patron holds')
  }
}

export async function getPatronFamily(token: string, patronId: number): Promise<PatronFamilyResponse> {
  try {
    return await fetchApi<PatronFamilyResponse>(`/staff/patrons/${patronId}/family`, { token })
  } catch {
    // Return empty family data if endpoint fails
    return {
      patron_id: patronId,
      parent_guardian: null,
      children: [],
    }
  }
}

// ==================== Bulk Operations Functions ====================

export async function bulkBlockPatrons(token: string, data: BulkBlockRequest): Promise<BulkBlockResponse> {
  try {
    return await fetchApi<BulkBlockResponse>('/staff/patrons/bulk-block', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk block operation failed')
    }
    throw error
  }
}

export async function bulkWaiveFines(token: string, data: BulkWaiveFinesRequest): Promise<BulkWaiveFinesResponse> {
  try {
    return await fetchApi<BulkWaiveFinesResponse>('/staff/patrons/bulk-waive-fines', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk waive fines operation failed')
    }
    throw error
  }
}

export async function bulkSendNotification(token: string, data: BulkNotificationRequest): Promise<BulkNotificationResponse> {
  try {
    return await fetchApi<BulkNotificationResponse>('/staff/patrons/bulk-notify', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk notification operation failed')
    }
    throw error
  }
}

// ===== Bulk patron messaging (5th bulk action on StaffPatronsPage) =====

export type BulkMessageChannel = 'email' | 'in_app' | 'sms'

export interface BulkMessageRequest {
  patron_ids: number[]
  template_id?: number | null
  subject?: string | null
  body: string
  channels: BulkMessageChannel[]
}

export interface BulkMessageRecipientResult {
  patron_id: number
  status: 'sent' | 'capped' | 'failed' | 'skipped'
  channels_sent: string[]
  reason?: string | null
}

export interface BulkMessageResponse {
  sent: number
  failed: number
  capped: number
  skipped: number
  per_recipient: BulkMessageRecipientResult[]
}

export async function bulkMessagePatrons(
  token: string,
  data: BulkMessageRequest
): Promise<BulkMessageResponse> {
  try {
    return await fetchApi<BulkMessageResponse>('/staff/patrons/messages/bulk', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Bulk message send failed')
    }
    throw error
  }
}

export async function exportPatrons(
  token: string,
  options?: {
    patronIds?: number[]
    statusFilter?: 'active' | 'blocked' | 'all'
    format?: 'json' | 'csv'
  }
): Promise<PatronExportResponse | Blob> {
  const params = new URLSearchParams()
  if (options?.patronIds && options.patronIds.length > 0) {
    params.set('patron_ids', options.patronIds.join(','))
  }
  if (options?.statusFilter) {
    params.set('status_filter', options.statusFilter)
  }
  if (options?.format) {
    params.set('format', options.format)
  }

  const queryString = params.toString() ? `?${params.toString()}` : ''

  // For CSV format, handle as blob
  if (options?.format === 'csv') {
    const response = await fetch(`${API_BASE}/staff/patrons/export${queryString}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
    if (!response.ok) {
      throw new Error('Export failed')
    }
    return response.blob()
  }

  try {
    return await fetchApi<PatronExportResponse>(`/staff/patrons/export${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Export failed')
    }
    throw error
  }
}

// ==================== Patron Account Management Functions ====================

// Password Reset
export async function resetPatronPassword(token: string, patronId: number, options: PasswordResetRequest = {}): Promise<PasswordResetResponse> {
  try {
    return await fetchApi<PasswordResetResponse>(`/staff/patrons/${patronId}/reset-password`, {
      method: 'POST',
      token,
      body: options,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to reset password')
    }
    throw error
  }
}

export async function getPatronPasswordInfo(token: string, patronId: number): Promise<PasswordInfo> {
  try {
    return await fetchApi<PasswordInfo>(`/staff/patrons/${patronId}/password-info`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get password info')
    }
    throw error
  }
}

// Duplicate Detection
export async function findDuplicatePatrons(token: string, patronId: number): Promise<DuplicateSearchResponse> {
  try {
    return await fetchApi<DuplicateSearchResponse>(`/staff/patrons/${patronId}/duplicates`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to find duplicates')
    }
    throw error
  }
}

export async function previewPatronMerge(token: string, request: MergeRequest): Promise<MergePreview> {
  try {
    return await fetchApi<MergePreview>('/staff/patrons/merge/preview', {
      method: 'POST',
      token,
      body: request,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to preview merge')
    }
    throw error
  }
}

export async function mergePatronRecords(token: string, request: MergeRequest): Promise<MergeResponse> {
  try {
    return await fetchApi<MergeResponse>('/staff/patrons/merge', {
      method: 'POST',
      token,
      body: request,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to merge patrons')
    }
    throw error
  }
}

// Library Card
export async function getLibraryCardData(token: string, patronId: number, cardType: string = 'standard'): Promise<LibraryCardData> {
  try {
    return await fetchApi<LibraryCardData>(`/staff/patrons/${patronId}/card?card_type=${cardType}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get card data')
    }
    throw error
  }
}

export async function logCardPrinted(token: string, patronId: number, request: CardPrintedRequest = {}): Promise<CardPrintedResponse> {
  try {
    return await fetchApi<CardPrintedResponse>(`/staff/patrons/${patronId}/card-printed`, {
      method: 'POST',
      token,
      body: request,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to log card print')
    }
    throw error
  }
}

// Account Settings
export async function getPatronAccountSettings(token: string, patronId: number): Promise<AccountSettings> {
  try {
    return await fetchApi<AccountSettings>(`/staff/patrons/${patronId}/settings`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to get account settings')
    }
    throw error
  }
}

export async function updatePatronAccountSettings(token: string, patronId: number, settings: AccountSettingsUpdate): Promise<AccountSettings> {
  try {
    return await fetchApi<AccountSettings>(`/staff/patrons/${patronId}/settings`, {
      method: 'PUT',
      token,
      body: settings,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update account settings')
    }
    throw error
  }
}

// ==================== Merge History Functions ====================

export async function getPatronMergeHistory(token: string, patronId: number): Promise<MergeHistoryResponse> {
  try {
    return await fetchApi<MergeHistoryResponse>(`/staff/patrons/${patronId}/merge-history`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch merge history')
    }
    throw error
  }
}

export async function getMergeAuditDetails(token: string, auditId: number): Promise<MergeAuditDetails> {
  try {
    return await fetchApi<MergeAuditDetails>(`/staff/patrons/merge-audit/${auditId}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch merge audit details')
    }
    throw error
  }
}

// ==================== Deceased/Estate Management Functions ====================

export async function markPatronDeceased(
  token: string,
  patronId: number,
  request: MarkDeceasedRequest
): Promise<DeceasedPatronResponse> {
  try {
    return await fetchApi<DeceasedPatronResponse>(`/staff/patrons/${patronId}/mark-deceased`, {
      method: 'POST',
      token,
      body: request,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark patron as deceased')
    }
    throw error
  }
}

export async function getEstateOutstanding(token: string, patronId: number): Promise<EstateOutstandingResponse> {
  try {
    return await fetchApi<EstateOutstandingResponse>(`/staff/patrons/${patronId}/estate-outstanding`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch estate outstanding items')
    }
    throw error
  }
}

export async function updateEstateContact(
  token: string,
  patronId: number,
  contact: EstateContactUpdate
): Promise<{ message: string; patron_id: number; estate_contact_name?: string; estate_contact_email?: string; estate_contact_phone?: string }> {
  try {
    const params = new URLSearchParams()
    if (contact.estate_contact_name) params.set('estate_contact_name', contact.estate_contact_name)
    if (contact.estate_contact_email) params.set('estate_contact_email', contact.estate_contact_email)
    if (contact.estate_contact_phone) params.set('estate_contact_phone', contact.estate_contact_phone)
    if (contact.notes) params.set('notes', contact.notes)

    return await fetchApi(`/staff/patrons/${patronId}/estate-contact?${params.toString()}`, {
      method: 'PUT',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update estate contact')
    }
    throw error
  }
}

export async function markEstateResolved(
  token: string,
  patronId: number,
  resolutionNotes?: string
): Promise<EstateResolvedResponse> {
  try {
    const params = resolutionNotes ? `?resolution_notes=${encodeURIComponent(resolutionNotes)}` : ''
    return await fetchApi<EstateResolvedResponse>(`/staff/patrons/${patronId}/estate-resolved${params}`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to mark estate as resolved')
    }
    throw error
  }
}

// ==================== Patron Activity Timeline Functions ====================

export async function getPatronActivity(
  token: string,
  patronId: number,
  options?: {
    activityType?: PatronActivityType
    page?: number
    perPage?: number
  }
): Promise<PatronActivityListResponse> {
  try {
    const params = new URLSearchParams()
    if (options?.activityType) params.set('activity_type', options.activityType)
    if (options?.page) params.set('page', options.page.toString())
    if (options?.perPage) params.set('per_page', options.perPage.toString())
    const queryString = params.toString() ? `?${params.toString()}` : ''
    return await fetchApi<PatronActivityListResponse>(`/staff/patrons/${patronId}/activity${queryString}`, { token })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to fetch patron activity')
    }
    throw error
  }
}

// ==================== Patron Photo Functions ====================

export async function uploadPatronPhoto(
  token: string,
  patronId: number,
  photoData: string,
  contentType: string = 'image/jpeg'
): Promise<PatronPhotoResponse> {
  try {
    return await fetchApi<PatronPhotoResponse>(`/staff/patrons/${patronId}/photo`, {
      method: 'POST',
      token,
      body: { photo_data: photoData, content_type: contentType },
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to upload photo')
    }
    throw error
  }
}

export async function deletePatronPhoto(token: string, patronId: number): Promise<void> {
  try {
    await fetchApi<void>(`/staff/patrons/${patronId}/photo`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete photo')
    }
    throw error
  }
}

// ==================== Enhanced Patron Profile Functions ====================

export async function updatePatronProfile(
  token: string,
  patronId: number,
  data: PatronProfileUpdate
): Promise<EnhancedPatronProfile> {
  try {
    return await fetchApi<EnhancedPatronProfile>(`/staff/patrons/${patronId}`, {
      method: 'PUT',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update profile')
    }
    throw error
  }
}

// ==================== Staff: Register New Patron ====================

export interface StaffCreatePatronData {
  first_name: string
  last_name: string
  email?: string
  phone?: string
  address?: string
}

export interface StaffCreatePatronResponse {
  id: number
  first_name: string
  last_name: string
  email: string
  library_card: string
  temporary_password: string
}

export async function staffCreatePatron(
  token: string,
  data: StaffCreatePatronData,
): Promise<StaffCreatePatronResponse> {
  try {
    return await fetchApi<StaffCreatePatronResponse>('/staff/patrons', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create patron')
    }
    throw error
  }
}
