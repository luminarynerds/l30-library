/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi, isApiError } from '@/lib/api-client'

// ==================== Enums ====================

export type PartnerType = 'school' | 'daycare' | 'senior_center' | 'community_center' | 'nonprofit' | 'correctional' | 'healthcare' | 'business' | 'government' | 'social_services';
export type PartnerStatus = 'prospect' | 'active' | 'inactive' | 'suspended' | 'terminated';
export type SchoolLevel = 'preschool' | 'elementary' | 'middle' | 'high' | 'college' | 'vocational' | 'other';
export type DepositType = 'classroom_checkout' | 'bulk_checkout' | 'institutional_card' | 'equipment' | 'special_collection';
export type DepositStatus = 'held' | 'partially_applied' | 'fully_applied' | 'refunded' | 'forfeited';
export type VisitType = 'storytime' | 'library_tour' | 'book_delivery' | 'card_signup' | 'classroom_visit' | 'presentation' | 'workshop' | 'collection_delivery' | 'collection_pickup' | 'assessment' | 'home_visit' | 'other';
export type VisitStatus = 'scheduled' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show' | 'rescheduled';
export type InstitutionalCardStatus = 'active' | 'suspended' | 'expired' | 'cancelled';
export type BulkCheckoutStatus = 'active' | 'returned' | 'partially_returned' | 'overdue' | 'lost';
// ==================== Partner Types ====================

export interface OutreachPartnerContact {
  id: number
  partner_id: number
  name: string
  title: string | null
  email: string | null
  phone: string | null
  role: string | null
  is_primary: boolean
  receives_notifications: boolean
  preferred_contact_method: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

export interface OutreachPartnerContactCreate {
  name: string
  title?: string | null
  email?: string | null
  phone?: string | null
  role?: string | null
  is_primary?: boolean
  receives_notifications?: boolean
  preferred_contact_method?: string | null
  notes?: string | null
}

export interface OutreachPartner {
  id: number
  name: string
  partner_type: string
  status: string

  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  zip_code: string | null

  primary_contact_name: string | null
  primary_contact_title: string | null
  primary_contact_email: string | null
  primary_contact_phone: string | null
  secondary_contact_name: string | null
  secondary_contact_email: string | null
  secondary_contact_phone: string | null

  school_level: string | null
  school_district: string | null
  student_count: number | null
  teacher_count: number | null

  partnership_start_date: string | null
  partnership_end_date: string | null
  agreement_document_url: string | null
  service_area: string | null

  allows_bulk_checkout: boolean
  allows_institutional_card: boolean
  requires_deposit: boolean
  default_deposit_amount: number
  checkout_limit: number
  loan_period_days: number

  notes: string | null
  tags: string[]
  custom_fields: Record<string, unknown>

  created_by_id: number | null
  created_at: string
  updated_at: string | null

  active_bulk_checkouts: number
  active_institutional_cards: number
  total_visits: number
  pending_deposits: number
}

export interface OutreachPartnerCreate {
  name: string
  partner_type?: PartnerType
  status?: PartnerStatus

  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null

  primary_contact_name?: string | null
  primary_contact_title?: string | null
  primary_contact_email?: string | null
  primary_contact_phone?: string | null
  secondary_contact_name?: string | null
  secondary_contact_email?: string | null
  secondary_contact_phone?: string | null

  school_level?: SchoolLevel | null
  school_district?: string | null
  student_count?: number | null
  teacher_count?: number | null

  partnership_start_date?: string | null
  partnership_end_date?: string | null
  agreement_document_url?: string | null
  service_area?: string | null

  allows_bulk_checkout?: boolean
  allows_institutional_card?: boolean
  requires_deposit?: boolean
  default_deposit_amount?: number
  checkout_limit?: number
  loan_period_days?: number

  notes?: string | null
  tags?: string[]
  custom_fields?: Record<string, unknown>
}

export interface OutreachPartnerUpdate {
  name?: string
  partner_type?: PartnerType
  status?: PartnerStatus

  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null

  primary_contact_name?: string | null
  primary_contact_title?: string | null
  primary_contact_email?: string | null
  primary_contact_phone?: string | null
  secondary_contact_name?: string | null
  secondary_contact_email?: string | null
  secondary_contact_phone?: string | null

  school_level?: SchoolLevel | null
  school_district?: string | null
  student_count?: number | null
  teacher_count?: number | null

  partnership_start_date?: string | null
  partnership_end_date?: string | null
  agreement_document_url?: string | null
  service_area?: string | null

  allows_bulk_checkout?: boolean
  allows_institutional_card?: boolean
  requires_deposit?: boolean
  default_deposit_amount?: number
  checkout_limit?: number
  loan_period_days?: number

  notes?: string | null
  tags?: string[]
  custom_fields?: Record<string, unknown>
}

export interface OutreachPartnerListResponse {
  partners: OutreachPartner[]
  total: number
  limit: number
  offset: number
}

// ==================== Deposit Types ====================

export interface OutreachDeposit {
  id: number
  partner_id: number
  partner_name: string | null
  deposit_type: string
  status: string
  amount: number
  amount_applied: number
  amount_refunded: number
  amount_remaining: number

  payment_method: string | null
  payment_reference: string | null
  receipt_number: string | null

  institutional_card_id: number | null
  bulk_checkout_id: number | null

  collected_date: string
  refund_date: string | null
  expiry_date: string | null

  notes: string | null
  refund_reason: string | null

  collected_by_id: number | null
  collected_by_name: string | null
  refunded_by_id: number | null
  refunded_by_name: string | null

  created_at: string
  updated_at: string | null
}

export interface OutreachDepositCreate {
  partner_id: number
  deposit_type?: DepositType
  amount: number
  payment_method?: string | null
  payment_reference?: string | null
  collected_date: string
  expiry_date?: string | null
  institutional_card_id?: number | null
  bulk_checkout_id?: number | null
  notes?: string | null
}

export interface OutreachDepositRefund {
  refund_amount: number
  refund_reason: string
}

export interface DepositApplicationCreate {
  amount: number
  reason: string
  fine_id?: number | null
  bulk_checkout_id?: number | null
  notes?: string | null
}

export interface DepositApplication {
  id: number
  deposit_id: number
  amount: number
  reason: string
  fine_id: number | null
  bulk_checkout_id: number | null
  applied_by_id: number | null
  applied_by_name: string | null
  applied_at: string
  notes: string | null
}

export interface OutreachDepositListResponse {
  deposits: OutreachDeposit[]
  total: number
  limit: number
  offset: number
}

// ==================== Visit Types ====================

export interface OutreachVisit {
  id: number
  partner_id: number
  partner_name: string | null

  visit_type: string
  status: string
  title: string
  description: string | null

  scheduled_date: string
  scheduled_start_time: string | null
  scheduled_end_time: string | null
  actual_start_time: string | null
  actual_end_time: string | null

  location_name: string | null
  location_room: string | null
  location_address: string | null

  expected_attendees: number | null
  actual_attendees: number | null
  age_group: string | null
  grade_levels: string[]

  lead_staff_id: number | null
  lead_staff_name: string | null
  additional_staff_ids: number[]

  materials_needed: string[]
  items_to_deliver: number
  items_delivered: number
  items_to_pickup: number
  items_picked_up: number

  outcome_notes: string | null
  new_cards_issued: number
  books_checked_out: number
  follow_up_needed: boolean
  follow_up_notes: string | null
  next_visit_date: string | null

  partner_feedback: string | null
  partner_rating: number | null
  staff_notes: string | null

  cancellation_reason: string | null
  cancelled_by_id: number | null
  cancelled_at: string | null

  is_recurring: boolean
  recurrence_pattern: string | null
  parent_visit_id: number | null

  created_by_id: number | null
  created_at: string
  updated_at: string | null
}

export interface OutreachVisitCreate {
  partner_id: number
  visit_type?: VisitType
  title: string
  description?: string | null

  scheduled_date: string
  scheduled_start_time?: string | null
  scheduled_end_time?: string | null

  location_name?: string | null
  location_room?: string | null
  location_address?: string | null

  expected_attendees?: number | null
  age_group?: string | null
  grade_levels?: string[]

  lead_staff_id?: number | null
  additional_staff_ids?: number[]

  materials_needed?: string[]
  items_to_deliver?: number
  items_to_pickup?: number

  is_recurring?: boolean
  recurrence_pattern?: string | null
}

export interface OutreachVisitUpdate {
  visit_type?: VisitType
  status?: VisitStatus
  title?: string
  description?: string | null

  scheduled_date?: string
  scheduled_start_time?: string | null
  scheduled_end_time?: string | null

  location_name?: string | null
  location_room?: string | null
  location_address?: string | null

  expected_attendees?: number | null
  age_group?: string | null
  grade_levels?: string[]

  lead_staff_id?: number | null
  additional_staff_ids?: number[]

  materials_needed?: string[]
  items_to_deliver?: number
  items_to_pickup?: number
}

export interface OutreachVisitComplete {
  actual_start_time?: string | null
  actual_end_time?: string | null
  actual_attendees?: number | null

  items_delivered?: number
  items_picked_up?: number

  outcome_notes?: string | null
  new_cards_issued?: number
  books_checked_out?: number

  follow_up_needed?: boolean
  follow_up_notes?: string | null
  next_visit_date?: string | null

  partner_feedback?: string | null
  partner_rating?: number | null
  staff_notes?: string | null
}

export interface OutreachVisitCancel {
  cancellation_reason: string
  reschedule_date?: string | null
}

export interface OutreachVisitListResponse {
  visits: OutreachVisit[]
  total: number
  limit: number
  offset: number
}

// ==================== Institutional Card Types ====================

export interface InstitutionalCard {
  id: number
  partner_id: number
  partner_name: string | null

  card_number: string
  card_name: string
  status: string

  authorized_users: string[]
  requires_pin: boolean

  checkout_limit: number
  hold_limit: number
  loan_period_days: number
  renewal_limit: number

  exempt_from_fines: boolean
  fine_cap: number | null

  deposit_required: boolean
  deposit_amount: number
  current_deposit_id: number | null

  issued_date: string
  expiry_date: string | null
  last_renewal_date: string | null

  total_checkouts: number
  current_checkouts: number
  current_holds: number
  current_fines: number

  notes: string | null

  issued_by_id: number | null
  issued_by_name: string | null
  created_at: string
  updated_at: string | null
}

export interface InstitutionalCardCreate {
  partner_id: number
  card_name: string

  authorized_users?: string[]
  requires_pin?: boolean
  pin?: string | null

  checkout_limit?: number
  hold_limit?: number
  loan_period_days?: number
  renewal_limit?: number

  exempt_from_fines?: boolean
  fine_cap?: number | null

  deposit_required?: boolean
  deposit_amount?: number

  expiry_date?: string | null
  notes?: string | null
}

export interface InstitutionalCardUpdate {
  card_name?: string
  status?: InstitutionalCardStatus

  authorized_users?: string[]
  requires_pin?: boolean
  new_pin?: string | null

  checkout_limit?: number
  hold_limit?: number
  loan_period_days?: number
  renewal_limit?: number

  exempt_from_fines?: boolean
  fine_cap?: number | null

  expiry_date?: string | null
  notes?: string | null
}

export interface InstitutionalCardListResponse {
  cards: InstitutionalCard[]
  total: number
  limit: number
  offset: number
}

export interface InstitutionalCheckoutCreate {
  barcode: string
  checked_out_by_name?: string | null
  pin?: string | null
}

export interface InstitutionalCheckout {
  id: number
  card_id: number
  card_number: string | null
  checkout_id: number | null

  item_copy_id: number | null
  barcode: string
  title: string | null

  checked_out_by_name: string | null
  checked_out_by_id: number | null

  checked_out_at: string
  due_date: string
  returned_at: string | null

  status: string
}

// ==================== Bulk Checkout Types ====================

export interface BulkCheckoutItem {
  id: number
  bulk_checkout_id: number
  item_copy_id: number | null
  checkout_id: number | null

  barcode: string
  title: string | null
  call_number: string | null

  status: string
  returned_at: string | null

  condition_out: string | null
  condition_in: string | null
  damage_notes: string | null

  replacement_cost: number | null
  fine_amount: number

  created_at: string
  updated_at: string | null
}

export interface BulkCheckout {
  id: number
  partner_id: number
  partner_name: string | null

  checkout_name: string
  status: string

  requestor_name: string
  requestor_email: string | null
  requestor_phone: string | null
  classroom_name: string | null
  grade_level: string | null

  checkout_date: string
  due_date: string
  returned_date: string | null

  total_items: number
  items_returned: number
  items_lost: number
  items_damaged: number
  items_outstanding: number

  deposit_required: boolean
  deposit_amount: number
  deposit_collected: boolean

  topic_requests: string[]
  reading_level_min: string | null
  reading_level_max: string | null
  format_preferences: string[]

  delivery_method: string | null
  delivery_address: string | null
  pickup_location: string | null
  outreach_visit_id: number | null

  notes: string | null
  return_notes: string | null

  processed_by_id: number | null
  processed_by_name: string | null
  created_at: string
  updated_at: string | null

  items: BulkCheckoutItem[]
}

export interface BulkCheckoutCreate {
  partner_id: number
  checkout_name: string

  requestor_name: string
  requestor_email?: string | null
  requestor_phone?: string | null
  classroom_name?: string | null
  grade_level?: string | null

  checkout_date: string
  due_date: string

  deposit_required?: boolean
  deposit_amount?: number

  topic_requests?: string[]
  reading_level_min?: string | null
  reading_level_max?: string | null
  format_preferences?: string[]

  delivery_method?: string | null
  delivery_address?: string | null
  pickup_location?: string | null
  outreach_visit_id?: number | null

  notes?: string | null
}

export interface BulkCheckoutItemAdd {
  barcodes: string[]
}

export interface BulkCheckoutItemReturn {
  barcode: string
  condition?: string | null
  damage_notes?: string | null
}

export interface BulkCheckoutListResponse {
  checkouts: BulkCheckout[]
  total: number
  limit: number
  offset: number
}

// ==================== Report Types ====================

export interface OutreachReportRequest {
  start_date: string
  end_date: string
  partner_ids?: number[] | null
  partner_types?: PartnerType[] | null
  visit_types?: VisitType[] | null
  include_details?: boolean
  branch_id?: number | null
}

export interface OutreachStatistics {
  id: number
  period_start: string
  period_end: string
  branch_id: number | null

  total_partners: number
  active_partners: number
  new_partners: number
  partners_by_type: Record<string, number>

  total_visits: number
  visits_completed: number
  visits_cancelled: number
  total_attendees: number
  visits_by_type: Record<string, number>

  bulk_checkouts_created: number
  bulk_checkouts_returned: number
  bulk_items_checked_out: number
  bulk_items_returned: number
  bulk_items_lost: number

  institutional_cards_active: number
  institutional_cards_issued: number
  institutional_checkouts: number

  deposits_collected: number
  deposits_refunded: number
  deposits_applied_to_fines: number

  new_cards_from_outreach: number
  reading_program_signups: number

  generated_at: string
}

export interface OutreachReport {
  report_period: string
  generated_at: string
  statistics: OutreachStatistics
  partner_details: OutreachPartner[] | null
  visit_details: OutreachVisit[] | null
  bulk_checkout_details: BulkCheckout[] | null
}

// ==================== Partner Functions ====================

export async function createPartner(
  token: string,
  data: OutreachPartnerCreate
): Promise<OutreachPartner> {
  try {
    return await fetchApi<OutreachPartner>('/outreach/partners', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create partner')
    }
    throw error
  }
}

export async function updatePartner(
  token: string,
  partnerId: number,
  data: OutreachPartnerUpdate
): Promise<OutreachPartner> {
  try {
    return await fetchApi<OutreachPartner>(`/outreach/partners/${partnerId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update partner')
    }
    throw error
  }
}

export async function deletePartner(token: string, partnerId: number): Promise<void> {
  try {
    await fetchApi<void>(`/outreach/partners/${partnerId}`, {
      method: 'DELETE',
      token,
      skipJsonParse: true,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to delete partner')
    }
    throw error
  }
}

export async function addPartnerContact(
  token: string,
  partnerId: number,
  data: OutreachPartnerContactCreate
): Promise<OutreachPartnerContact> {
  try {
    return await fetchApi<OutreachPartnerContact>(`/outreach/partners/${partnerId}/contacts`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to add partner contact')
    }
    throw error
  }
}

// ==================== Deposit Functions ====================

export async function createDeposit(
  token: string,
  data: OutreachDepositCreate
): Promise<OutreachDeposit> {
  try {
    return await fetchApi<OutreachDeposit>('/outreach/deposits', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create deposit')
    }
    throw error
  }
}

export async function refundDeposit(
  token: string,
  depositId: number,
  data: OutreachDepositRefund
): Promise<OutreachDeposit> {
  try {
    return await fetchApi<OutreachDeposit>(`/outreach/deposits/${depositId}/refund`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Refund amount exceeds available balance')
      }
      throw new Error(error.detail || 'Failed to refund deposit')
    }
    throw error
  }
}

export async function applyDeposit(
  token: string,
  depositId: number,
  data: DepositApplicationCreate
): Promise<DepositApplication> {
  try {
    return await fetchApi<DepositApplication>(`/outreach/deposits/${depositId}/apply`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Application amount exceeds available balance')
      }
      throw new Error(error.detail || 'Failed to apply deposit')
    }
    throw error
  }
}

// ==================== Visit Functions ====================

export async function createVisit(
  token: string,
  data: OutreachVisitCreate
): Promise<OutreachVisit> {
  try {
    return await fetchApi<OutreachVisit>('/outreach/visits', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create visit')
    }
    throw error
  }
}

export async function updateVisit(
  token: string,
  visitId: number,
  data: OutreachVisitUpdate
): Promise<OutreachVisit> {
  try {
    return await fetchApi<OutreachVisit>(`/outreach/visits/${visitId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update visit')
    }
    throw error
  }
}

export async function completeVisit(
  token: string,
  visitId: number,
  data: OutreachVisitComplete
): Promise<OutreachVisit> {
  try {
    return await fetchApi<OutreachVisit>(`/outreach/visits/${visitId}/complete`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Visit is already completed')
      }
      throw new Error(error.detail || 'Failed to complete visit')
    }
    throw error
  }
}

export async function cancelVisit(
  token: string,
  visitId: number,
  data: OutreachVisitCancel
): Promise<OutreachVisit> {
  try {
    return await fetchApi<OutreachVisit>(`/outreach/visits/${visitId}/cancel`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Visit cannot be cancelled')
      }
      throw new Error(error.detail || 'Failed to cancel visit')
    }
    throw error
  }
}

// ==================== Institutional Card Functions ====================

export async function createInstitutionalCard(
  token: string,
  data: InstitutionalCardCreate
): Promise<InstitutionalCard> {
  try {
    return await fetchApi<InstitutionalCard>('/outreach/institutional-cards', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create institutional card')
    }
    throw error
  }
}

export async function updateInstitutionalCard(
  token: string,
  cardId: number,
  data: InstitutionalCardUpdate
): Promise<InstitutionalCard> {
  try {
    return await fetchApi<InstitutionalCard>(`/outreach/institutional-cards/${cardId}`, {
      method: 'PATCH',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to update institutional card')
    }
    throw error
  }
}

export async function institutionalCheckout(
  token: string,
  cardId: number,
  data: InstitutionalCheckoutCreate
): Promise<InstitutionalCheckout> {
  try {
    return await fetchApi<InstitutionalCheckout>(`/outreach/institutional-cards/${cardId}/checkout`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Checkout failed - check card status or PIN')
      }
      throw new Error(error.detail || 'Failed to checkout item')
    }
    throw error
  }
}

// ==================== Bulk Checkout Functions ====================

export async function createBulkCheckout(
  token: string,
  data: BulkCheckoutCreate
): Promise<BulkCheckout> {
  try {
    return await fetchApi<BulkCheckout>('/outreach/bulk-checkouts', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to create bulk checkout')
    }
    throw error
  }
}

export async function addBulkCheckoutItems(
  token: string,
  checkoutId: number,
  data: BulkCheckoutItemAdd
): Promise<BulkCheckoutItem[]> {
  try {
    return await fetchApi<BulkCheckoutItem[]>(`/outreach/bulk-checkouts/${checkoutId}/items`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 400) {
        throw new Error(error.detail || 'Cannot add items to a non-active checkout')
      }
      throw new Error(error.detail || 'Failed to add items to bulk checkout')
    }
    throw error
  }
}

export async function returnBulkCheckoutItem(
  token: string,
  checkoutId: number,
  data: BulkCheckoutItemReturn
): Promise<BulkCheckoutItem> {
  try {
    return await fetchApi<BulkCheckoutItem>(`/outreach/bulk-checkouts/${checkoutId}/return`, {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      if (error.status === 404) {
        throw new Error('Item not found in this bulk checkout')
      }
      if (error.status === 400) {
        throw new Error(error.detail || 'Item is not currently checked out')
      }
      throw new Error(error.detail || 'Failed to return item')
    }
    throw error
  }
}

export async function returnAllBulkCheckoutItems(
  token: string,
  checkoutId: number
): Promise<BulkCheckout> {
  try {
    return await fetchApi<BulkCheckout>(`/outreach/bulk-checkouts/${checkoutId}/return-all`, {
      method: 'POST',
      token,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to return all items')
    }
    throw error
  }
}

// ==================== Report Functions ====================

export async function generateOutreachReport(
  token: string,
  data: OutreachReportRequest
): Promise<OutreachReport> {
  try {
    return await fetchApi<OutreachReport>('/outreach/reports/generate', {
      method: 'POST',
      token,
      body: data,
    })
  } catch (error: unknown) {
    if (isApiError(error)) {
      throw new Error(error.detail || 'Failed to generate outreach report')
    }
    throw error
  }
}
