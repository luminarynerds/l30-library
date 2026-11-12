/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
import { fetchApi } from '@/lib/api-client'
import type { components } from '@/api/generated/schema'

// ==================== Branch Types ====================

export type BranchType = components['schemas']['BranchType'];
// Source of truth: backend/app/models/multi_branch.py :: BranchStatus
// Re-exported from auto-generated OpenAPI schema — do NOT edit manually.
// To update: run `npm run api:generate` and this picks up changes automatically.
export type BranchStatus = components['schemas']['BranchStatus']

export interface Branch {
  id: number
  library_system_id: number
  region_id: number | null
  code: string
  name: string
  short_name: string | null
  branch_type: BranchType
  status: BranchStatus
  phone: string | null
  fax: string | null
  email: string | null
  website: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  country: string
  latitude: number | null
  longitude: number | null
  square_footage: number | null
  parking_spaces: number | null
  is_ada_accessible: boolean
  has_meeting_rooms: boolean
  has_computer_lab: boolean
  has_makerspace: boolean
  has_drive_through: boolean
  has_book_drop: boolean
  has_self_checkout: boolean
  ils_location_code: string | null
  display_order: number
  branch_manager_id: number | null
  opened_date: string | null
  closed_date: string | null
  created_at: string
  updated_at: string | null
}

export interface BranchHours {
  id: number
  branch_id: number
  day_of_week: string
  open_time: string | null
  close_time: string | null
  is_closed: boolean
  notes: string | null
}

export interface BranchWithDistance extends Branch {
  distance_miles: number | null
}

// ==================== Branch Functions ====================

export async function listBranches(params?: {
  library_system_id?: number
  region_id?: number
  branch_type?: BranchType
  status?: BranchStatus
  active_only?: boolean
}): Promise<Branch[]> {
  const searchParams = new URLSearchParams()
  if (params?.library_system_id) searchParams.set('library_system_id', String(params.library_system_id))
  if (params?.region_id) searchParams.set('region_id', String(params.region_id))
  if (params?.branch_type) searchParams.set('branch_type', params.branch_type)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.active_only !== undefined) searchParams.set('active_only', String(params.active_only))

  const query = searchParams.toString()
  return fetchApi<Branch[]>(`/branches${query ? `?${query}` : ''}`)
}

export async function getBranch(branchId: number): Promise<Branch> {
  return fetchApi<Branch>(`/branches/${branchId}`)
}

export async function getBranchHours(branchId: number): Promise<BranchHours[]> {
  return fetchApi<BranchHours[]>(`/branches/${branchId}/hours`)
}

// ==================== Geolocation Utilities ====================

export function calculateDistance(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 3958.8 // Earth's radius in miles

  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) * Math.sin(dLon / 2)

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))

  return R * c
}

function toRad(deg: number): number {
  return deg * (Math.PI / 180)
}

export function getCurrentPosition(): Promise<GeolocationPosition> {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error('Geolocation is not supported by this browser'))
      return
    }

    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 10000,
      maximumAge: 300000, // Cache for 5 minutes
    })
  })
}

export function sortBranchesByDistance(
  branches: Branch[],
  userLat: number,
  userLon: number
): BranchWithDistance[] {
  return branches
    .map((branch) => ({
      ...branch,
      distance_miles:
        branch.latitude && branch.longitude
          ? calculateDistance(userLat, userLon, branch.latitude, branch.longitude)
          : null,
    }))
    .sort((a, b) => {
      // Branches without coordinates go to the end
      if (a.distance_miles === null && b.distance_miles === null) return 0
      if (a.distance_miles === null) return 1
      if (b.distance_miles === null) return -1
      return a.distance_miles - b.distance_miles
    })
}

export function formatBranchAddress(branch: Branch): string {
  const parts = [
    branch.address_line1,
    branch.address_line2,
    branch.city && branch.state ? `${branch.city}, ${branch.state}` : branch.city || branch.state,
    branch.zip_code,
  ].filter(Boolean)

  return parts.join(', ')
}

export function getBranchTypeLabel(type: BranchType, t?: (key: string, fallback?: string) => string): string {
  const labels: Record<BranchType, string> = {
    main: 'Main Library',
    branch: 'Branch',
    bookmobile: 'Bookmobile',
    kiosk: 'Kiosk',
    digital_only: 'Digital Only',
    outreach: 'Outreach',
  }
  const keys: Record<BranchType, string> = {
    main: 'branches.type.main',
    branch: 'branches.type.branch',
    bookmobile: 'branches.type.bookmobile',
    kiosk: 'branches.type.kiosk',
    digital_only: 'branches.type.digitalOnly',
    outreach: 'branches.type.outreach',
  }
  const label = labels[type] || type
  if (!t || !keys[type]) return label
  return t(keys[type], label)
}

export function isBranchOpen(hours: BranchHours[]): boolean {
  const now = new Date()
  const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
  const todayName = dayNames[now.getDay()]

  const todayHours = hours.find((h) => h.day_of_week === todayName)
  if (!todayHours || todayHours.is_closed || !todayHours.open_time || !todayHours.close_time) {
    return false
  }

  const currentTime = now.toTimeString().slice(0, 5)
  return currentTime >= todayHours.open_time && currentTime <= todayHours.close_time
}

// ==================== Library System Types ====================

export interface LibrarySystem {
  id: number
  code: string
  name: string
  legal_name: string | null
  website: string | null
  email: string | null
  phone: string | null
  fax: string | null
  address_line1: string | null
  address_line2: string | null
  city: string | null
  state: string | null
  zip_code: string | null
  country: string | null
  tax_id: string | null
  state_library_id: string | null
  governance_type: string | null
  fiscal_year_start_month: number | null
  timezone: string | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface LibrarySystemCreate {
  code: string
  name: string
  legal_name?: string | null
  website?: string | null
  email?: string | null
  phone?: string | null
  fax?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string | null
  tax_id?: string | null
  state_library_id?: string | null
  governance_type?: string | null
  fiscal_year_start_month?: number | null
  timezone?: string | null
}

export interface LibrarySystemUpdate {
  name?: string | null
  legal_name?: string | null
  website?: string | null
  email?: string | null
  phone?: string | null
  fax?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string | null
  tax_id?: string | null
  state_library_id?: string | null
  governance_type?: string | null
  fiscal_year_start_month?: number | null
  timezone?: string | null
  is_active?: boolean | null
}

export interface SystemSettings {
  id: number
  library_system_id: number
  default_loan_period_days: number | null
  default_renewal_limit: number | null
  default_hold_limit: number | null
  default_checkout_limit: number | null
  default_overdue_fine_per_day: number | null
  default_max_fine: number | null
  grace_period_days: number | null
  fine_free_juvenile: boolean | null
  lost_item_threshold_days: number | null
  default_replacement_cost: number | null
  processing_fee: number | null
  hold_pickup_days: number | null
  allow_hold_on_available: boolean | null
  transit_time_estimate_days: number | null
  auto_approve_transit: boolean | null
  require_address_verification: boolean | null
  allow_self_registration: boolean | null
  card_expiry_years: number | null
  age_transition_threshold: number | null
  auto_transition_enabled: boolean | null
  forgive_reading_minutes_on_transition: boolean | null
  overdue_notice_days: number[] | null
  courtesy_notice_days: number | null
  enable_floating_collections: boolean | null
  enable_reciprocal_borrowing: boolean | null
  enable_self_checkout: boolean | null
  updated_at: string | null
}

export interface SystemSettingsUpdate {
  default_loan_period_days?: number | null
  default_renewal_limit?: number | null
  default_hold_limit?: number | null
  default_checkout_limit?: number | null
  default_overdue_fine_per_day?: number | null
  default_max_fine?: number | null
  grace_period_days?: number | null
  fine_free_juvenile?: boolean | null
  lost_item_threshold_days?: number | null
  default_replacement_cost?: number | null
  processing_fee?: number | null
  hold_pickup_days?: number | null
  allow_hold_on_available?: boolean | null
  transit_time_estimate_days?: number | null
  auto_approve_transit?: boolean | null
  require_address_verification?: boolean | null
  allow_self_registration?: boolean | null
  card_expiry_years?: number | null
  age_transition_threshold?: number | null
  auto_transition_enabled?: boolean | null
  forgive_reading_minutes_on_transition?: boolean | null
  overdue_notice_days?: number[] | null
  courtesy_notice_days?: number | null
  enable_floating_collections?: boolean | null
  enable_reciprocal_borrowing?: boolean | null
  enable_self_checkout?: boolean | null
}

// ==================== Region Types ====================

export interface Region {
  id: number
  library_system_id: number
  code: string
  name: string
  description: string | null
  manager_user_id: number | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

export interface RegionCreate {
  library_system_id: number
  code: string
  name: string
  description?: string | null
  manager_user_id?: number | null
}

export interface RegionUpdate {
  name?: string | null
  description?: string | null
  manager_user_id?: number | null
  is_active?: boolean | null
}

// ==================== Branch Update Types ====================

export interface BranchUpdate {
  name?: string | null
  short_name?: string | null
  branch_type?: BranchType | null
  status?: BranchStatus | null
  region_id?: number | null
  phone?: string | null
  fax?: string | null
  email?: string | null
  website?: string | null
  address_line1?: string | null
  address_line2?: string | null
  city?: string | null
  state?: string | null
  zip_code?: string | null
  country?: string | null
  latitude?: number | null
  longitude?: number | null
  square_footage?: number | null
  parking_spaces?: number | null
  is_ada_accessible?: boolean | null
  has_meeting_rooms?: boolean | null
  has_computer_lab?: boolean | null
  has_makerspace?: boolean | null
  has_drive_through?: boolean | null
  has_book_drop?: boolean | null
  has_self_checkout?: boolean | null
  branch_manager_id?: number | null
  ils_location_code?: string | null
  display_order?: number | null
  opened_date?: string | null
  closed_date?: string | null
}

// ==================== Branch Hours Types ====================

export type DayOfWeek = components['schemas']['DayOfWeek'];
export interface BranchHoursUpdate {
  is_closed?: boolean | null
  open_time?: string | null
  close_time?: string | null
  open_time_2?: string | null
  close_time_2?: string | null
  effective_from?: string | null
  effective_until?: string | null
  notes?: string | null
}

export interface BranchHoursResponse {
  id: number
  branch_id: number
  day_of_week: DayOfWeek
  is_closed: boolean
  open_time: string | null
  close_time: string | null
  open_time_2: string | null
  close_time_2: string | null
  effective_from: string | null
  effective_until: string | null
  notes: string | null
  created_at: string
  updated_at: string | null
}

// ==================== Branch Closure Types ====================

export interface BranchClosure {
  id: number
  branch_id: number
  start_date: string
  end_date: string
  start_time: string | null
  end_time: string | null
  reason: string
  description: string | null
  is_system_wide: boolean
  is_annual: boolean
  created_by_id: number | null
  created_at: string
  // Closure management status (backend/app/schemas/multi_branch.py ::
  // BranchClosureResponse) -- mirrors the coerce-none-to-false validator, so
  // these are always present booleans, never null.
  patrons_with_holds_notified: boolean
  staff_notified: boolean
  partner_organizations_notified: boolean
  website_updated: boolean
  phone_message_updated: boolean
  social_media_updated: boolean
  google_maps_updated: boolean
  apple_maps_updated: boolean
  events_canceled: boolean
  programs_rescheduled: boolean
  closure_documentation: string | null
  reopening_announcement: string | null
}

export interface BranchClosureCreate {
  branch_id: number
  start_date: string
  end_date: string
  start_time?: string | null
  end_time?: string | null
  reason: string
  description?: string | null
  is_system_wide?: boolean
  is_annual?: boolean
}

// ==================== Branch Settings Types ====================

export type FloatingCollectionType = components['schemas']['FloatingCollectionType'];
export interface BranchSettings {
  id: number
  branch_id: number
  loan_period_days: number | null
  renewal_limit: number | null
  hold_limit: number | null
  checkout_limit: number | null
  overdue_fine_per_day: number | null
  max_fine: number | null
  fine_free: boolean | null
  allow_ill_pickup: boolean | null
  allow_hold_pickup: boolean | null
  allow_returns: boolean | null
  floating_type: FloatingCollectionType | null
  default_pickup_branch: boolean | null
  checkout_message: string | null
  hold_pickup_message: string | null
  print_receipt_header: string | null
  print_receipt_footer: string | null
  updated_at: string | null
}

export interface BranchSettingsUpdate {
  loan_period_days?: number | null
  renewal_limit?: number | null
  hold_limit?: number | null
  checkout_limit?: number | null
  overdue_fine_per_day?: number | null
  max_fine?: number | null
  fine_free?: boolean | null
  allow_ill_pickup?: boolean | null
  allow_hold_pickup?: boolean | null
  allow_returns?: boolean | null
  floating_type?: FloatingCollectionType | null
  default_pickup_branch?: boolean | null
  checkout_message?: string | null
  hold_pickup_message?: string | null
  print_receipt_header?: string | null
  print_receipt_footer?: string | null
}

// ==================== Transit Types ====================

export type TransitStatus = components['schemas']['TransitStatus'];
export type TransitPriority = components['schemas']['TransitPriority'];
export type TransitReason = components['schemas']['TransitReason'];
export interface TransitRequest {
  id: number
  item_copy_id: number
  from_branch_id: number
  to_branch_id: number
  status: TransitStatus
  reason: TransitReason
  priority: TransitPriority
  hold_id: number | null
  notes: string | null
  requested_at: string
  requested_by_id: number
  approved_at: string | null
  approved_by_id: number | null
  picked_up_at: string | null
  picked_up_by_id: number | null
  shipped_at: string | null
  received_at: string | null
  received_by_id: number | null
  cancelled_at: string | null
  cancelled_by_id: number | null
  cancellation_reason: string | null
  expected_arrival_date: string | null
}

export interface TransitRequestCreate {
  item_copy_id: number
  from_branch_id: number
  to_branch_id: number
  reason: TransitReason
  priority?: TransitPriority
  hold_id?: number | null
  notes?: string | null
}

export interface TransitShipment {
  id: number
  shipment_number: string
  from_branch_id: number
  to_branch_id: number
  container_count: number
  carrier: string | null
  tracking_number: string | null
  notes: string | null
  item_count: number
  created_at: string
  created_by_id: number
  shipped_at: string | null
  shipped_by_id: number | null
  received_at: string | null
  received_by_id: number | null
}

export interface TransitShipmentCreate {
  from_branch_id: number
  to_branch_id: number
  container_count?: number
  carrier?: string | null
  tracking_number?: string | null
  notes?: string | null
}

export interface TransitShipmentItem {
  id: number
  shipment_id: number
  transit_request_id: number
  scanned_in_at: string
  scanned_in_by_id: number | null
  received_at: string | null
  received_by_id: number | null
  notes: string | null
}

// ==================== Branch Item Types ====================

export interface BranchItemCopy {
  id: number
  item_copy_id: number
  home_branch_id: number | null
  current_branch_id: number
  is_floating: boolean
  float_scope: FloatingCollectionType
  shelving_location: string | null
  last_seen_at: string | null
  last_circulated_branch_id: number | null
  assigned_at: string
  updated_at: string | null
}

export interface BranchItemCopyCreate {
  item_copy_id: number
  is_floating?: boolean
  float_scope?: FloatingCollectionType
  shelving_location?: string | null
}

// ==================== Library System Functions ====================

export async function createLibrarySystem(data: LibrarySystemCreate): Promise<LibrarySystem> {
  return fetchApi<LibrarySystem>(`/branches/systems`, {
    method: 'POST',
    body: data,
  })
}

export async function updateLibrarySystem(systemId: number, data: LibrarySystemUpdate): Promise<LibrarySystem> {
  return fetchApi<LibrarySystem>(`/branches/systems/${systemId}`, {
    method: 'PATCH',
    body: data,
  })
}

export async function updateSystemSettings(systemId: number, data: SystemSettingsUpdate): Promise<SystemSettings> {
  return fetchApi<SystemSettings>(`/branches/systems/${systemId}/settings`, {
    method: 'PATCH',
    body: data,
  })
}

// ==================== Region Functions ====================

export async function createRegion(data: RegionCreate): Promise<Region> {
  return fetchApi<Region>(`/branches/regions`, {
    method: 'POST',
    body: data,
  })
}

export async function updateRegion(regionId: number, data: RegionUpdate): Promise<Region> {
  return fetchApi<Region>(`/branches/regions/${regionId}`, {
    method: 'PATCH',
    body: data,
  })
}

// ==================== Branch Update Functions ====================

export async function updateBranch(branchId: number, data: BranchUpdate): Promise<Branch> {
  return fetchApi<Branch>(`/branches/${branchId}`, {
    method: 'PATCH',
    body: data,
  })
}

export async function setBranchHours(
  branchId: number,
  dayOfWeek: DayOfWeek,
  data: BranchHoursUpdate
): Promise<BranchHoursResponse> {
  return fetchApi<BranchHoursResponse>(`/branches/${branchId}/hours/${dayOfWeek}`, {
    method: 'PUT',
    body: data,
  })
}

export async function createBranchClosure(branchId: number, data: Omit<BranchClosureCreate, 'branch_id'>): Promise<BranchClosure> {
  return fetchApi<BranchClosure>(`/branches/${branchId}/closures`, {
    method: 'POST',
    body: { ...data, branch_id: branchId },
  })
}

// Upcoming closures for a branch (includes closures already in progress).
// GET /branches/{branch_id}/closures -- unauthenticated, unlike the
// close-today/external-services/notify-partners/schedule-reopening actions.
export async function listBranchClosures(branchId: number, daysAhead?: number): Promise<BranchClosure[]> {
  const searchParams = new URLSearchParams()
  if (daysAhead !== undefined) searchParams.set('days_ahead', String(daysAhead))
  const query = searchParams.toString()
  return fetchApi<BranchClosure[]>(`/branches/${branchId}/closures${query ? `?${query}` : ''}`)
}

export async function updateBranchSettings(branchId: number, data: BranchSettingsUpdate): Promise<BranchSettings> {
  return fetchApi<BranchSettings>(`/branches/${branchId}/settings`, {
    method: 'PATCH',
    body: data,
  })
}

// ==================== Transit Request Functions ====================

export async function createTransitRequest(data: TransitRequestCreate): Promise<TransitRequest> {
  return fetchApi<TransitRequest>(`/branches/transit/requests`, {
    method: 'POST',
    body: data,
  })
}

export async function approveTransitRequest(requestId: number): Promise<TransitRequest> {
  return fetchApi<TransitRequest>(`/branches/transit/requests/${requestId}/approve`, {
    method: 'POST',
  })
}

export async function pickupTransitRequest(requestId: number): Promise<TransitRequest> {
  return fetchApi<TransitRequest>(`/branches/transit/requests/${requestId}/pickup`, {
    method: 'POST',
  })
}

export async function receiveTransitRequest(requestId: number): Promise<TransitRequest> {
  return fetchApi<TransitRequest>(`/branches/transit/requests/${requestId}/receive`, {
    method: 'POST',
  })
}

export async function cancelTransitRequest(requestId: number, reason?: string): Promise<TransitRequest> {
  const searchParams = new URLSearchParams()
  if (reason) searchParams.set('reason', reason)
  const query = searchParams.toString()
  return fetchApi<TransitRequest>(`/branches/transit/requests/${requestId}/cancel${query ? `?${query}` : ''}`, {
    method: 'POST',
  })
}

// ==================== Transit Shipment Functions ====================

export async function createTransitShipment(data: TransitShipmentCreate): Promise<TransitShipment> {
  return fetchApi<TransitShipment>(`/branches/transit/shipments`, {
    method: 'POST',
    body: data,
  })
}

export async function addItemToShipment(shipmentId: number, transitRequestId: number): Promise<TransitShipmentItem> {
  const searchParams = new URLSearchParams()
  searchParams.set('transit_request_id', String(transitRequestId))
  return fetchApi<TransitShipmentItem>(`/branches/transit/shipments/${shipmentId}/items?${searchParams.toString()}`, {
    method: 'POST',
  })
}

export async function shipShipment(shipmentId: number, trackingNumber?: string): Promise<TransitShipment> {
  const searchParams = new URLSearchParams()
  if (trackingNumber) searchParams.set('tracking_number', trackingNumber)
  const query = searchParams.toString()
  return fetchApi<TransitShipment>(`/branches/transit/shipments/${shipmentId}/ship${query ? `?${query}` : ''}`, {
    method: 'POST',
  })
}

export async function receiveShipment(shipmentId: number): Promise<TransitShipment> {
  return fetchApi<TransitShipment>(`/branches/transit/shipments/${shipmentId}/receive`, {
    method: 'POST',
  })
}

// ==================== Branch Item Functions ====================

export async function addItemToBranch(branchId: number, data: BranchItemCopyCreate): Promise<BranchItemCopy> {
  return fetchApi<BranchItemCopy>(`/branches/${branchId}/items`, {
    method: 'POST',
    body: data,
  })
}