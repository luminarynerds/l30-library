/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'

// ==================== Enums ====================

export type ConsortiumMemberType = 'FULL' | 'ASSOCIATE' | 'AFFILIATE' | 'FOUNDING'
export type ConsortiumMemberStatus = 'pending' | 'active' | 'suspended' | 'withdrawn' | 'expelled'
export type BillingStatus = 'pending' | 'invoiced' | 'paid' | 'overdue' | 'disputed' | 'cancelled'
export type BillingItemType = 'ILL_LOAN' | 'TRANSIT' | 'MEMBERSHIP_FEE' | 'LOST_ITEM' | 'other'
export type BillingCycleType = 'MONTHLY' | 'QUARTERLY' | 'ANNUALLY'

// ==================== Consortium Types ====================

export interface Consortium {
  id: number
  code: string
  name: string
  legal_name: string | null
  website: string | null
  email: string | null
  phone: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  country: string
  established_date: string | null
  governing_document_url: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface ConsortiumCreate {
  code: string
  name: string
  legal_name?: string | null
  website?: string | null
  email?: string | null
  phone?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string
  established_date?: string | null
  governing_document_url?: string | null
}

export interface ConsortiumUpdate {
  name?: string
  legal_name?: string | null
  website?: string | null
  email?: string | null
  phone?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string | null
  established_date?: string | null
  governing_document_url?: string | null
  is_active?: boolean
}

export interface ConsortiumSettings {
  id: number
  consortium_id: number
  enable_shared_catalog: boolean
  catalog_search_all_members: boolean
  enable_reciprocal_borrowing: boolean
  reciprocal_checkout_limit: number
  reciprocal_hold_limit: number
  enable_ill: boolean
  ill_request_limit: number
  ill_loan_period_days: number
  enable_consortium_transit: boolean
  default_transit_time_days: number
  enable_single_sign_on: boolean
  sso_provider: string | null
  sso_config: Record<string, unknown> | null
  cost_sharing_model: string | null
  ill_fee_per_item: string
  transit_fee_per_item: string
  billing_cycle: BillingCycleType
  enable_consortium_float: boolean
  updated_at: string | null
}

export interface ConsortiumDetail extends Consortium {
  members: ConsortiumMember[]
  settings: ConsortiumSettings | null
}

// ==================== Member Types ====================

export interface LibrarySystem {
  id: number
  code: string
  name: string
  legal_name: string | null
  website: string | null
  email: string | null
  phone: string | null
  city: string | null
  state: string | null
  is_active: boolean
}

export interface ConsortiumMember {
  id: number
  consortium_id: number
  library_system_id: number
  member_type: ConsortiumMemberType
  status: ConsortiumMemberStatus
  voting_member: boolean
  vote_weight: number
  annual_fee: string | null
  joined_date: string
  expiry_date: string | null
  fee_paid_through: string | null
  liaison_user_id: number | null
  created_at: string
  updated_at: string | null
}

export interface ConsortiumMemberDetail extends ConsortiumMember {
  library_system: LibrarySystem | null
  reciprocal_settings: ReciprocalBorrowingSettings | null
  white_label: ConsortiumWhiteLabel | null
}

export interface ConsortiumMemberCreate {
  consortium_id: number
  library_system_id: number
  member_type?: ConsortiumMemberType
  voting_member?: boolean
  vote_weight?: number
  annual_fee?: string | null
  joined_date?: string | null
  liaison_user_id?: number | null
}

export interface ConsortiumMemberUpdate {
  member_type?: ConsortiumMemberType
  status?: ConsortiumMemberStatus
  voting_member?: boolean
  vote_weight?: number
  annual_fee?: string | null
  fee_paid_through?: string | null
  liaison_user_id?: number | null
  expiry_date?: string | null
}

// ==================== Reciprocal Borrowing Types ====================

export interface ReciprocalBorrowingSettings {
  id: number
  member_id: number
  allow_incoming_borrowers: boolean
  incoming_checkout_limit: number
  incoming_hold_limit: number
  allow_outgoing_borrowers: boolean
  require_registration: boolean
  registration_valid_days: number
  blocked_item_types: string[] | null
  restricted_collections: string[] | null
  updated_at: string | null
}

export interface ReciprocalBorrowingSettingsUpdate {
  allow_incoming_borrowers?: boolean
  incoming_checkout_limit?: number
  incoming_hold_limit?: number
  allow_outgoing_borrowers?: boolean
  require_registration?: boolean
  registration_valid_days?: number
  blocked_item_types?: string[] | null
  restricted_collections?: string[] | null
}

export interface CanBorrowResponse {
  patron_id: number
  member_id: number
  can_borrow: boolean
  reason: string | null
  checkout_limit: number
  hold_limit: number
}

// ==================== Patron Link Types ====================

export interface ConsortiumPatronLink {
  id: number
  home_user_id: number
  home_member_id: number
  linked_member_id: number
  linked_card_number: string | null
  registered_at: string
  expires_at: string | null
  is_active: boolean
  blocked: boolean
  blocked_reason: string | null
  last_used_at: string | null
  total_checkouts: number
  created_at: string
  updated_at: string | null
}

export interface ConsortiumPatronLinkCreate {
  home_user_id: number
  home_member_id: number
  linked_member_id: number
  linked_card_number?: string | null
  expires_at?: string | null
}

// ==================== Billing Types ====================

export interface ConsortiumBilling {
  id: number
  consortium_id: number
  billing_member_id: number
  billed_member_id: number
  item_type: BillingItemType
  quantity: number
  unit_amount: string
  total_amount: string
  description: string | null
  billing_period_start: string
  billing_period_end: string
  status: BillingStatus
  invoice_number: string | null
  invoiced_at: string | null
  due_date: string | null
  paid_at: string | null
  payment_reference: string | null
  disputed_at: string | null
  dispute_reason: string | null
  dispute_resolved_at: string | null
  created_at: string
  updated_at: string | null
}

export interface MemberBalance {
  owed_to_member: string
  member_owes: string
  net_balance: string
}

export interface FinancialSummary {
  total_billed: string
  total_paid: string
  total_outstanding: string
  total_disputed: string
  by_status: Record<BillingStatus, number>
  by_item_type: Record<BillingItemType, number>
}

// ==================== White Label Types ====================

export interface ConsortiumWhiteLabel {
  id: number
  member_id: number
  logo_url: string | null
  logo_small_url: string | null
  banner_url: string | null
  primary_color: string | null
  secondary_color: string | null
  accent_color: string | null
  text_color: string | null
  background_color: string | null
  heading_font: string | null
  body_font: string | null
  custom_css: string | null
  custom_domain: string | null
  subdomain: string | null
  welcome_message: string | null
  footer_text: string | null
  contact_info: Record<string, unknown> | null
  facebook_url: string | null
  twitter_url: string | null
  instagram_url: string | null
  youtube_url: string | null
  show_consortium_branding: boolean
  show_member_list: boolean
  show_consortium_events: boolean
  updated_at: string | null
}

export interface ConsortiumWhiteLabelUpdate {
  logo_url?: string | null
  logo_small_url?: string | null
  banner_url?: string | null
  primary_color?: string | null
  secondary_color?: string | null
  accent_color?: string | null
  text_color?: string | null
  background_color?: string | null
  heading_font?: string | null
  body_font?: string | null
  custom_css?: string | null
  custom_domain?: string | null
  subdomain?: string | null
  welcome_message?: string | null
  footer_text?: string | null
  contact_info?: Record<string, unknown> | null
  facebook_url?: string | null
  twitter_url?: string | null
  instagram_url?: string | null
  youtube_url?: string | null
  show_consortium_branding?: boolean
  show_member_list?: boolean
  show_consortium_events?: boolean
}

// ==================== Consortium API Functions ====================

export async function createConsortium(
  token: string,
  data: ConsortiumCreate
): Promise<Consortium> {
  return fetchApi<Consortium>('/consortiums', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function listConsortiums(
  activeOnly = true
): Promise<Consortium[]> {
  const params = new URLSearchParams()
  params.set('active_only', String(activeOnly))
  return fetchApi<Consortium[]>(`/consortiums?${params.toString()}`)
}

export async function getConsortium(consortiumId: number): Promise<ConsortiumDetail> {
  return fetchApi<ConsortiumDetail>(`/consortiums/${consortiumId}`)
}

export async function updateConsortium(
  token: string,
  consortiumId: number,
  data: ConsortiumUpdate
): Promise<Consortium> {
  return fetchApi<Consortium>(`/consortiums/${consortiumId}`, {
    method: 'PATCH',
    token,
    body: data,
  })
}

export async function getConsortiumSettings(
  consortiumId: number
): Promise<ConsortiumSettings> {
  return fetchApi<ConsortiumSettings>(`/consortiums/${consortiumId}/settings`)
}

export async function updateConsortiumSettings(
  token: string,
  consortiumId: number,
  data: Partial<Omit<ConsortiumSettings, 'id' | 'consortium_id' | 'updated_at'>>
): Promise<ConsortiumSettings> {
  return fetchApi<ConsortiumSettings>(`/consortiums/${consortiumId}/settings`, {
    method: 'PATCH',
    token,
    body: data,
  })
}

// ==================== Member API Functions ====================

export async function addMember(
  token: string,
  consortiumId: number,
  data: Omit<ConsortiumMemberCreate, 'consortium_id'>
): Promise<ConsortiumMember> {
  return fetchApi<ConsortiumMember>(`/consortiums/${consortiumId}/members`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function listMembers(
  consortiumId: number,
  params?: {
    status?: ConsortiumMemberStatus
    active_only?: boolean
  }
): Promise<ConsortiumMember[]> {
  const searchParams = new URLSearchParams()
  if (params?.status) searchParams.set('status', params.status)
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only))
  const query = searchParams.toString()
  return fetchApi<ConsortiumMember[]>(
    `/consortiums/${consortiumId}/members${query ? `?${query}` : ''}`
  )
}

export async function getMember(memberId: number): Promise<ConsortiumMemberDetail> {
  return fetchApi<ConsortiumMemberDetail>(`/consortiums/members/${memberId}`)
}

export async function updateMember(
  token: string,
  memberId: number,
  data: ConsortiumMemberUpdate
): Promise<ConsortiumMember> {
  return fetchApi<ConsortiumMember>(`/consortiums/members/${memberId}`, {
    method: 'PATCH',
    token,
    body: data,
  })
}

export async function suspendMember(
  token: string,
  memberId: number
): Promise<ConsortiumMember> {
  return fetchApi<ConsortiumMember>(`/consortiums/members/${memberId}/suspend`, {
    method: 'POST',
    token,
  })
}

export async function activateMember(
  token: string,
  memberId: number
): Promise<ConsortiumMember> {
  return fetchApi<ConsortiumMember>(`/consortiums/members/${memberId}/activate`, {
    method: 'POST',
    token,
  })
}

// ==================== Reciprocal Borrowing API Functions ====================

export async function getReciprocalSettings(
  memberId: number
): Promise<ReciprocalBorrowingSettings> {
  return fetchApi<ReciprocalBorrowingSettings>(
    `/consortiums/members/${memberId}/reciprocal-settings`
  )
}

export async function updateReciprocalSettings(
  token: string,
  memberId: number,
  data: ReciprocalBorrowingSettingsUpdate
): Promise<ReciprocalBorrowingSettings> {
  return fetchApi<ReciprocalBorrowingSettings>(
    `/consortiums/members/${memberId}/reciprocal-settings`,
    {
      method: 'PATCH',
      token,
      body: data,
    }
  )
}

export async function checkCanBorrow(
  memberId: number,
  patronId: number
): Promise<CanBorrowResponse> {
  return fetchApi<CanBorrowResponse>(
    `/consortiums/members/${memberId}/can-borrow?patron_id=${patronId}`
  )
}

// ==================== Patron Link API Functions ====================

export async function createPatronLink(
  token: string,
  data: ConsortiumPatronLinkCreate
): Promise<ConsortiumPatronLink> {
  return fetchApi<ConsortiumPatronLink>('/consortiums/patron-links', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function listPatronLinks(
  patronId: number,
  activeOnly = true
): Promise<ConsortiumPatronLink[]> {
  const params = new URLSearchParams()
  params.set('patron_id', String(patronId))
  params.set('active_only', String(activeOnly))
  return fetchApi<ConsortiumPatronLink[]>(
    `/consortiums/patron-links?${params.toString()}`
  )
}

export async function blockPatronAtMember(
  token: string,
  userId: number,
  memberId: number,
  reason: string
): Promise<{ status: string; reason: string }> {
  return fetchApi<{ status: string; reason: string }>(
    `/consortiums/patron-links/${userId}/${memberId}/block?reason=${encodeURIComponent(reason)}`,
    {
      method: 'POST',
      token,
    }
  )
}

// ==================== Billing API Functions ====================

export async function generateBilling(
  token: string,
  consortiumId: number,
  periodStart: string,
  periodEnd: string
): Promise<{ records_created: number; period: { start: string; end: string } }> {
  const params = new URLSearchParams()
  params.set('period_start', periodStart)
  params.set('period_end', periodEnd)
  return fetchApi<{ records_created: number; period: { start: string; end: string } }>(
    `/consortiums/${consortiumId}/billing/generate?${params.toString()}`,
    {
      method: 'POST',
      token,
    }
  )
}

export async function listBillingRecords(
  consortiumId: number,
  params?: {
    member_id?: number
    status?: BillingStatus
    from_date?: string
    to_date?: string
    limit?: number
    offset?: number
  }
): Promise<ConsortiumBilling[]> {
  const searchParams = new URLSearchParams()
  if (params?.member_id) searchParams.set('member_id', String(params.member_id))
  if (params?.status) searchParams.set('status', params.status)
  if (params?.from_date) searchParams.set('from_date', params.from_date)
  if (params?.to_date) searchParams.set('to_date', params.to_date)
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.offset) searchParams.set('offset', String(params.offset))
  const query = searchParams.toString()
  return fetchApi<ConsortiumBilling[]>(
    `/consortiums/${consortiumId}/billing${query ? `?${query}` : ''}`
  )
}

export async function getBillingRecord(billingId: number): Promise<ConsortiumBilling> {
  return fetchApi<ConsortiumBilling>(`/consortiums/billing/${billingId}`)
}

export async function createInvoice(
  token: string,
  billingIds: number[],
  dueDays = 30
): Promise<{ invoice_number: string; records_count: number; due_date: string }> {
  return fetchApi<{ invoice_number: string; records_count: number; due_date: string }>(
    `/consortiums/billing/create-invoice?due_days=${dueDays}`,
    {
      method: 'POST',
      token,
      body: billingIds,
    }
  )
}

export async function recordPayment(
  token: string,
  billingId: number,
  paymentReference?: string
): Promise<ConsortiumBilling> {
  const params = paymentReference
    ? `?payment_reference=${encodeURIComponent(paymentReference)}`
    : ''
  return fetchApi<ConsortiumBilling>(
    `/consortiums/billing/${billingId}/pay${params}`,
    {
      method: 'POST',
      token,
    }
  )
}

export async function disputeBilling(
  token: string,
  billingId: number,
  reason: string
): Promise<ConsortiumBilling> {
  return fetchApi<ConsortiumBilling>(
    `/consortiums/billing/${billingId}/dispute?reason=${encodeURIComponent(reason)}`,
    {
      method: 'POST',
      token,
    }
  )
}

export async function getMemberBalance(
  consortiumId: number,
  memberId: number
): Promise<MemberBalance> {
  return fetchApi<MemberBalance>(
    `/consortiums/${consortiumId}/members/${memberId}/balance`
  )
}

export async function getFinancialSummary(
  consortiumId: number,
  params?: {
    from_date?: string
    to_date?: string
  }
): Promise<FinancialSummary> {
  const searchParams = new URLSearchParams()
  if (params?.from_date) searchParams.set('from_date', params.from_date)
  if (params?.to_date) searchParams.set('to_date', params.to_date)
  const query = searchParams.toString()
  return fetchApi<FinancialSummary>(
    `/consortiums/${consortiumId}/financial-summary${query ? `?${query}` : ''}`
  )
}

// ==================== White Label API Functions ====================

export async function getWhiteLabel(
  memberId: number
): Promise<ConsortiumWhiteLabel | null> {
  return fetchApi<ConsortiumWhiteLabel | null>(
    `/consortiums/members/${memberId}/white-label`
  )
}

export async function updateWhiteLabel(
  token: string,
  memberId: number,
  data: ConsortiumWhiteLabelUpdate
): Promise<ConsortiumWhiteLabel> {
  return fetchApi<ConsortiumWhiteLabel>(
    `/consortiums/members/${memberId}/white-label`,
    {
      method: 'PUT',
      token,
      body: data,
    }
  )
}

export async function getWhiteLabelByDomain(
  domain: string
): Promise<ConsortiumWhiteLabel> {
  return fetchApi<ConsortiumWhiteLabel>(
    `/consortiums/white-label/by-domain?domain=${encodeURIComponent(domain)}`
  )
}

// ==================== Search API Functions ====================

export async function getSearchableSystems(
  consortiumId: number,
  requestingSystemId?: number
): Promise<{ library_system_ids: number[] }> {
  const params = requestingSystemId
    ? `?requesting_system_id=${requestingSystemId}`
    : ''
  return fetchApi<{ library_system_ids: number[] }>(
    `/consortiums/${consortiumId}/searchable-systems${params}`
  )
}