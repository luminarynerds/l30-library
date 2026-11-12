/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * Equipment Lending API Service
 * Handles equipment CRUD, checkouts, reservations, agreements, maintenance, and alerts
 */
import { fetchApi, isApiError } from '@/lib/api-client'
import type { components } from '@/api/generated/schema';

// ==================== Types ====================

export type EquipmentType =
  | 'laptop'
  | 'hotspot'
  | 'projector'
  | 'tablet'
  | 'e_reader'
  | 'camera'
  | 'audio_recorder'
  | 'calculator'
  | 'charger'
  | 'headphones'
  | 'keyboard'
  | 'mouse'
  | 'webcam'
  | 'microphone'
  | 'tripod'
  | 'light_kit'
  | 'gaming_console'
  | 'vr_headset'
  | 'telescope'
  | 'microscope'
  | 'tools'
  | 'other'

export type EquipmentStatus =
  | 'available'
  | 'checked_out'
  | 'reserved'
  | 'in_maintenance'
  | 'damaged'
  | 'lost'
  | 'retired'

export type EquipmentCondition =
  | 'excellent'
  | 'good'
  | 'fair'
  | 'poor'
  | 'needs_repair'
  | 'non_functional'

export type MaintenanceType =
  | 'routine_check'
  | 'cleaning'
  | 'software_update'
  | 'hardware_repair'
  | 'battery_replacement'
  | 'screen_repair'
  | 'accessory_replacement'
  | 'calibration'
  | 'deep_clean'
  | 'diagnostic'
  | 'other'

export type MaintenanceStatus =
  | 'scheduled'
  | 'in_progress'
  | 'completed'
  | 'cancelled'

export type CheckoutStatus = components['schemas']['CheckoutStatus'];
export type ReservationStatus =
  | 'pending'
  | 'confirmed'
  | 'ready_for_pickup'
  | 'checked_out'
  | 'cancelled'
  | 'expired'

export type AgreementStatus = components['schemas']['AgreementStatus'];
// ==================== Core Interfaces ====================

export interface Equipment {
  id: number
  name: string
  description: string | null
  equipment_type: EquipmentType
  barcode: string
  serial_number: string | null
  manufacturer: string | null
  model: string | null
  status: EquipmentStatus
  condition: EquipmentCondition
  location: string | null
  purchase_date: string | null
  purchase_price: string | null
  replacement_cost: string | null
  loan_period_days: number
  max_renewals: number
  deposit_required: string | null
  included_accessories: string | null
  return_instructions: string | null
  notes: string | null
  last_maintenance_date: string | null
  next_maintenance_date: string | null
  is_available: boolean
  created_at: string
  updated_at: string
}

export interface EquipmentBrief {
  id: number
  name: string
  equipment_type: EquipmentType
  barcode: string
  status: EquipmentStatus
  condition: EquipmentCondition
  is_available: boolean
}

export interface EquipmentListResponse {
  items: Equipment[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface EquipmentCheckout {
  id: number
  equipment_id: number
  user_id: number | null
  status: CheckoutStatus
  checked_out_at: string
  due_date: string
  returned_at: string | null
  renewal_count: number
  condition_at_checkout: EquipmentCondition | null
  condition_at_return: EquipmentCondition | null
  checkout_notes: string | null
  return_notes: string | null
  fine_amount: string
  fine_paid: boolean
  deposit_amount: string
  deposit_collected: boolean
  deposit_refunded: boolean
  deposit_refund_amount: string | null
  deposit_deduction_reason: string | null
  equipment_name: string | null
  equipment_type: EquipmentType | null
  equipment_barcode: string | null
  return_instructions: string | null
  included_accessories: string | null
  patron_name?: string | null
  patron_email?: string | null
}

export interface EquipmentCheckoutListResponse {
  items: EquipmentCheckout[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface EquipmentReservation {
  id: number
  equipment_id: number
  user_id: number
  status: ReservationStatus
  start_date: string
  end_date: string
  position: number
  notified_at: string | null
  pickup_deadline: string | null
  purpose: string | null
  notes: string | null
  confirmed_at: string | null
  cancelled_at: string | null
  cancellation_reason: string | null
  created_at: string
  updated_at: string
  equipment_name: string | null
  equipment_type: EquipmentType | null
  equipment_barcode: string | null
  patron_name?: string | null
  patron_email?: string | null
}

export interface ReservationListResponse {
  items: EquipmentReservation[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface EquipmentAgreement {
  id: number
  user_id: number
  agreement_version: string
  status: AgreementStatus
  agreement_text: string
  signature: string | null
  signed_at: string | null
  valid_from: string | null
  valid_until: string | null
  equipment_types_covered: string | null
  is_valid: boolean
  created_at: string
  updated_at: string
  patron_name?: string | null
  patron_email?: string | null
}

export interface AgreementStatusResponse {
  has_valid_agreement: boolean
  agreement_id: number | null
  signed_at: string | null
  valid_until: string | null
  equipment_types_covered: string[] | null
}

export interface MaintenanceRecord {
  id: number
  equipment_id: number
  maintenance_type: MaintenanceType
  status: MaintenanceStatus
  description: string | null
  issues_found: string | null
  work_performed: string | null
  scheduled_date: string | null
  started_at: string | null
  completed_at: string | null
  condition_before: EquipmentCondition | null
  condition_after: EquipmentCondition | null
  parts_cost: string | null
  labor_cost: string | null
  total_cost: string | null
  external_vendor: string | null
  vendor_invoice: string | null
  performed_by_id: number | null
  requires_followup: boolean
  followup_notes: string | null
  followup_date: string | null
  created_at: string
  updated_at: string
  equipment_name: string | null
  equipment_barcode: string | null
}

export interface MaintenanceListResponse {
  items: MaintenanceRecord[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface EquipmentAlert {
  id: number
  alert_type: string
  priority: string
  status: string
  equipment_id: number | null
  checkout_id: number | null
  reservation_id: number | null
  user_id: number | null
  title: string
  message: string
  days_overdue: number | null
  escalation_level: number
  created_at: string
  acknowledged_at: string | null
  resolved_at: string | null
  equipment_name: string | null
  equipment_barcode: string | null
  patron_name: string | null
  patron_email: string | null
  patron_phone: string | null
}

export interface AlertListResponse {
  items: EquipmentAlert[]
  total: number
  page: number
  per_page: number
  pages: number
}

export interface EquipmentAvailability {
  equipment_id: number
  is_available: boolean
  current_status: EquipmentStatus
  next_available_date: string | null
  pending_reservations: number
  queue_position: number | null
}

// ==================== Report Types ====================

export interface EquipmentReportSummary {
  total_equipment: number
  available_count: number
  checked_out_count: number
  maintenance_count: number
  retired_count: number
  overdue_checkouts: number
  active_reservations: number
  pending_maintenance: number
  total_value: string
  types_breakdown: Record<string, number>
}

export interface EquipmentUtilizationReport {
  equipment_id: number
  equipment_name: string
  equipment_type: EquipmentType
  total_checkouts: number
  total_days_out: number
  utilization_rate: number
  average_loan_duration: number
}

export interface PopularEquipmentReport {
  equipment_id: number
  equipment_name: string
  equipment_type: EquipmentType
  checkout_count: number
  unique_patrons: number
}

export interface PatronEquipmentHistory {
  patron_id: number
  patron_name: string
  patron_email: string
  total_checkouts: number
  current_checkouts: number
  overdue_count: number
  total_fines: string
  equipment_types_used: string[]
}

// ==================== Create/Update Types ====================

export interface EquipmentCreate {
  name: string
  description?: string
  equipment_type: EquipmentType
  barcode?: string
  serial_number?: string
  manufacturer?: string
  model?: string
  condition?: EquipmentCondition
  location?: string
  purchase_date?: string
  purchase_price?: string
  replacement_cost?: string
  loan_period_days?: number
  max_renewals?: number
  deposit_required?: string
  included_accessories?: string
  return_instructions?: string
  notes?: string
}

export interface EquipmentUpdate {
  name?: string
  description?: string
  equipment_type?: EquipmentType
  barcode?: string
  serial_number?: string
  manufacturer?: string
  model?: string
  status?: EquipmentStatus
  condition?: EquipmentCondition
  location?: string
  purchase_date?: string
  purchase_price?: string
  replacement_cost?: string
  loan_period_days?: number
  max_renewals?: number
  deposit_required?: string
  included_accessories?: string
  return_instructions?: string
  notes?: string
  next_maintenance_date?: string
}

export interface CheckoutCreate {
  equipment_id: number
  patron_id?: number
  checkout_notes?: string
  deposit_collected?: boolean
}

export interface CheckoutReturn {
  condition_at_return: EquipmentCondition
  return_notes?: string
  refund_deposit?: boolean
  deposit_deduction_amount?: string
  deposit_deduction_reason?: string
}

export interface MaintenanceCreate {
  equipment_id: number
  maintenance_type: MaintenanceType
  scheduled_date?: string
  description?: string
}

export interface MaintenanceComplete {
  work_performed: string
  condition_after: EquipmentCondition
  issues_found?: string
  parts_cost?: string
  labor_cost?: string
  external_vendor?: string
  vendor_invoice?: string
  requires_followup?: boolean
  followup_notes?: string
  followup_date?: string
}

export interface ReservationCreate {
  equipment_id: number
  start_date: string
  end_date: string
  purpose?: string
  notes?: string
}

// ==================== Equipment CRUD Functions ====================

export async function listEquipment(
  token: string,
  params?: {
    page?: number
    per_page?: number
    equipment_type?: EquipmentType
    status?: EquipmentStatus
    condition?: EquipmentCondition
    location?: string
    search?: string
    available_only?: boolean
  }
): Promise<EquipmentListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  if (params?.equipment_type) searchParams.set('equipment_type', params.equipment_type)
  if (params?.status) searchParams.set('status', params.status)
  if (params?.condition) searchParams.set('condition', params.condition)
  if (params?.location) searchParams.set('location', params.location)
  if (params?.search) searchParams.set('search', params.search)
  if (params?.available_only) searchParams.set('available_only', 'true')

  const queryString = searchParams.toString()
  return fetchApi<EquipmentListResponse>(
    `/equipment${queryString ? '?' + queryString : ''}`,
    { token }
  )
}

export async function listAvailableEquipment(
  token: string,
  equipmentType?: EquipmentType
): Promise<EquipmentBrief[]> {
  const queryString = equipmentType ? `?equipment_type=${equipmentType}` : ''
  return fetchApi<EquipmentBrief[]>(`/equipment/available${queryString}`, { token })
}

export async function getEquipment(token: string, equipmentId: number): Promise<Equipment> {
  return fetchApi<Equipment>(`/equipment/${equipmentId}`, { token })
}

export async function getEquipmentByBarcode(token: string, barcode: string): Promise<Equipment> {
  return fetchApi<Equipment>(`/equipment/barcode/${encodeURIComponent(barcode)}`, { token })
}

export async function createEquipment(token: string, data: EquipmentCreate): Promise<Equipment> {
  return fetchApi<Equipment>('/equipment', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function updateEquipment(
  token: string,
  equipmentId: number,
  data: EquipmentUpdate
): Promise<Equipment> {
  return fetchApi<Equipment>(`/equipment/${equipmentId}`, {
    method: 'PATCH',
    token,
    body: data,
  })
}

export async function retireEquipment(
  token: string,
  equipmentId: number,
  notes?: string
): Promise<Equipment> {
  const queryString = notes ? `?notes=${encodeURIComponent(notes)}` : ''
  return fetchApi<Equipment>(`/equipment/${equipmentId}/retire${queryString}`, {
    method: 'POST',
    token,
  })
}

export async function checkEquipmentAvailability(
  token: string,
  equipmentId: number
): Promise<EquipmentAvailability> {
  return fetchApi<EquipmentAvailability>(`/equipment/${equipmentId}/availability`, { token })
}

// ==================== Checkout Functions ====================

export async function checkoutEquipment(
  token: string,
  data: CheckoutCreate
): Promise<EquipmentCheckout> {
  return fetchApi<EquipmentCheckout>('/equipment/checkout', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function returnEquipment(
  token: string,
  checkoutId: number,
  data: CheckoutReturn
): Promise<EquipmentCheckout> {
  return fetchApi<EquipmentCheckout>(`/equipment/return/${checkoutId}`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function returnEquipmentByBarcode(
  token: string,
  barcode: string,
  data: CheckoutReturn
): Promise<EquipmentCheckout> {
  return fetchApi<EquipmentCheckout>(`/equipment/return/barcode/${encodeURIComponent(barcode)}`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function renewEquipmentCheckout(
  token: string,
  checkoutId: number,
  notes?: string
): Promise<EquipmentCheckout> {
  const queryParams = notes ? `?notes=${encodeURIComponent(notes)}` : ''
  return fetchApi<EquipmentCheckout>(`/equipment/renew/${checkoutId}${queryParams}`, {
    method: 'POST',
    token,
  })
}

export async function getMyEquipmentCheckouts(
  token: string,
  includeHistory: boolean = false,
  page: number = 1,
  perPage: number = 20
): Promise<EquipmentCheckoutListResponse> {
  return fetchApi<EquipmentCheckoutListResponse>(
    `/equipment/checkouts/my?include_history=${includeHistory}&page=${page}&per_page=${perPage}`,
    { token }
  )
}

export async function getPatronEquipmentCheckouts(
  token: string,
  patronId: number,
  includeHistory: boolean = false,
  page: number = 1,
  perPage: number = 20
): Promise<EquipmentCheckoutListResponse> {
  return fetchApi<EquipmentCheckoutListResponse>(
    `/equipment/checkouts/patron/${patronId}?include_history=${includeHistory}&page=${page}&per_page=${perPage}`,
    { token }
  )
}

// ==================== Agreement Functions ====================

export async function getMyAgreementStatus(
  token: string,
  equipmentType?: EquipmentType
): Promise<AgreementStatusResponse> {
  const queryParams = equipmentType ? `?equipment_type=${equipmentType}` : ''
  return fetchApi<AgreementStatusResponse>(`/equipment/agreements/my${queryParams}`, { token })
}

export async function createAgreement(
  token: string,
  data: { patron_id?: number; equipment_types_covered?: EquipmentType[] }
): Promise<EquipmentAgreement> {
  return fetchApi<EquipmentAgreement>('/equipment/agreements', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function signAgreement(
  token: string,
  agreementId: number,
  signature: string
): Promise<EquipmentAgreement> {
  return fetchApi<EquipmentAgreement>(`/equipment/agreements/${agreementId}/sign`, {
    method: 'POST',
    token,
    body: { signature },
  })
}

export async function revokeAgreement(
  token: string,
  agreementId: number,
  reason: string
): Promise<EquipmentAgreement> {
  return fetchApi<EquipmentAgreement>(
    `/equipment/agreements/${agreementId}/revoke?reason=${encodeURIComponent(reason)}`,
    {
      method: 'POST',
      token,
    }
  )
}

export async function getPatronAgreementStatus(
  token: string,
  patronId: number,
  equipmentType?: EquipmentType
): Promise<AgreementStatusResponse> {
  const queryParams = equipmentType ? `?equipment_type=${equipmentType}` : ''
  return fetchApi<AgreementStatusResponse>(
    `/equipment/agreements/patron/${patronId}${queryParams}`,
    { token }
  )
}

// ==================== Reservation Functions ====================

export async function createReservation(
  token: string,
  data: ReservationCreate
): Promise<EquipmentReservation> {
  return fetchApi<EquipmentReservation>('/equipment/reservations', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function cancelReservation(
  token: string,
  reservationId: number,
  reason?: string
): Promise<void> {
  const queryParams = reason ? `?reason=${encodeURIComponent(reason)}` : ''
  await fetchApi(`/equipment/reservations/${reservationId}${queryParams}`, {
    method: 'DELETE',
    token,
    skipJsonParse: true,
  })
}

export async function getMyReservations(
  token: string,
  page: number = 1,
  perPage: number = 20
): Promise<ReservationListResponse> {
  return fetchApi<ReservationListResponse>(
    `/equipment/reservations/my?page=${page}&per_page=${perPage}`,
    { token }
  )
}

export async function getEquipmentReservations(
  token: string,
  equipmentId: number,
  includePast: boolean = false
): Promise<EquipmentReservation[]> {
  return fetchApi<EquipmentReservation[]>(
    `/equipment/${equipmentId}/reservations?include_past=${includePast}`,
    { token }
  )
}

// ==================== Maintenance Functions ====================

export async function scheduleMaintenance(
  token: string,
  data: MaintenanceCreate
): Promise<MaintenanceRecord> {
  return fetchApi<MaintenanceRecord>('/equipment/maintenance', {
    method: 'POST',
    token,
    body: data,
  })
}

export async function startMaintenance(
  token: string,
  maintenanceId: number
): Promise<MaintenanceRecord> {
  return fetchApi<MaintenanceRecord>(`/equipment/maintenance/${maintenanceId}/start`, {
    method: 'POST',
    token,
  })
}

export async function completeMaintenance(
  token: string,
  maintenanceId: number,
  data: MaintenanceComplete
): Promise<MaintenanceRecord> {
  return fetchApi<MaintenanceRecord>(`/equipment/maintenance/${maintenanceId}/complete`, {
    method: 'POST',
    token,
    body: data,
  })
}

export async function getMaintenanceHistory(
  token: string,
  equipmentId: number,
  page: number = 1,
  perPage: number = 20
): Promise<MaintenanceListResponse> {
  return fetchApi<MaintenanceListResponse>(
    `/equipment/${equipmentId}/maintenance?page=${page}&per_page=${perPage}`,
    { token }
  )
}

export async function getEquipmentDueForMaintenance(token: string): Promise<EquipmentBrief[]> {
  return fetchApi<EquipmentBrief[]>('/equipment/maintenance/due', { token })
}

// ==================== Alert Functions ====================

export async function getActiveAlerts(
  token: string,
  params?: {
    page?: number
    per_page?: number
    priority?: string
    alert_type?: string
  }
): Promise<AlertListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.per_page) searchParams.set('per_page', String(params.per_page))
  if (params?.priority) searchParams.set('priority', params.priority)
  if (params?.alert_type) searchParams.set('alert_type', params.alert_type)

  const queryString = searchParams.toString()
  return fetchApi<AlertListResponse>(
    `/equipment/alerts${queryString ? '?' + queryString : ''}`,
    { token }
  )
}

export async function acknowledgeAlert(
  token: string,
  alertId: number,
  notes?: string
): Promise<EquipmentAlert> {
  return fetchApi<EquipmentAlert>(`/equipment/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    token,
    body: { notes },
  })
}

export async function resolveAlert(
  token: string,
  alertId: number,
  resolutionNotes?: string
): Promise<EquipmentAlert> {
  return fetchApi<EquipmentAlert>(`/equipment/alerts/${alertId}/resolve`, {
    method: 'POST',
    token,
    body: { resolution_notes: resolutionNotes },
  })
}

export async function processOverdueAlerts(token: string): Promise<{ alerts_created: number }> {
  return fetchApi<{ alerts_created: number }>('/equipment/alerts/process-overdue', {
    method: 'POST',
    token,
  })
}

// ==================== Report Functions ====================

export async function getEquipmentSummary(token: string): Promise<EquipmentReportSummary> {
  return fetchApi<EquipmentReportSummary>('/equipment/reports/summary', { token })
}

export async function getUtilizationReport(
  token: string,
  params?: {
    start_date?: string
    end_date?: string
    equipment_type?: EquipmentType
  }
): Promise<EquipmentUtilizationReport[]> {
  const searchParams = new URLSearchParams()
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)
  if (params?.equipment_type) searchParams.set('equipment_type', params.equipment_type)

  const queryString = searchParams.toString()
  return fetchApi<EquipmentUtilizationReport[]>(
    `/equipment/reports/utilization${queryString ? '?' + queryString : ''}`,
    { token }
  )
}

export async function getPopularEquipmentReport(
  token: string,
  params?: {
    limit?: number
    start_date?: string
    end_date?: string
  }
): Promise<PopularEquipmentReport[]> {
  const searchParams = new URLSearchParams()
  if (params?.limit) searchParams.set('limit', String(params.limit))
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)

  const queryString = searchParams.toString()
  return fetchApi<PopularEquipmentReport[]>(
    `/equipment/reports/popular${queryString ? '?' + queryString : ''}`,
    { token }
  )
}

export async function getConditionTrendsReport(
  token: string,
  months: number = 6,
  equipmentId?: number
): Promise<unknown> {
  const searchParams = new URLSearchParams()
  searchParams.set('months', String(months))
  if (equipmentId) searchParams.set('equipment_id', String(equipmentId))

  return fetchApi(`/equipment/reports/condition-trends?${searchParams.toString()}`, { token })
}

export async function getEquipmentByTypeReport(token: string): Promise<unknown> {
  return fetchApi('/equipment/reports/by-type', { token })
}

export async function getOverdueEquipmentReport(token: string): Promise<unknown> {
  return fetchApi('/equipment/reports/overdue', { token })
}

export async function getMaintenanceReport(
  token: string,
  params?: {
    start_date?: string
    end_date?: string
  }
): Promise<unknown> {
  const searchParams = new URLSearchParams()
  if (params?.start_date) searchParams.set('start_date', params.start_date)
  if (params?.end_date) searchParams.set('end_date', params.end_date)

  const queryString = searchParams.toString()
  return fetchApi(`/equipment/reports/maintenance${queryString ? '?' + queryString : ''}`, {
    token,
  })
}

export async function getPatronEquipmentHistory(
  token: string,
  patronId: number
): Promise<PatronEquipmentHistory> {
  return fetchApi<PatronEquipmentHistory>(`/equipment/reports/patron/${patronId}`, { token })
}

export async function getEquipmentDashboard(token: string): Promise<unknown> {
  return fetchApi('/equipment/reports/dashboard', { token })
}

// ==================== Helper Functions ====================

export function formatEquipmentType(type: EquipmentType | null): string {
  if (!type) return 'Unknown'

  const typeLabels: Record<EquipmentType, string> = {
    laptop: 'Laptop',
    hotspot: 'Wi-Fi Hotspot',
    projector: 'Projector',
    tablet: 'Tablet',
    e_reader: 'E-Reader',
    camera: 'Camera',
    audio_recorder: 'Audio Recorder',
    calculator: 'Calculator',
    charger: 'Charger',
    headphones: 'Headphones',
    keyboard: 'Keyboard',
    mouse: 'Mouse',
    webcam: 'Webcam',
    microphone: 'Microphone',
    tripod: 'Tripod',
    light_kit: 'Light Kit',
    gaming_console: 'Gaming Console',
    vr_headset: 'VR Headset',
    telescope: 'Telescope',
    microscope: 'Microscope',
    tools: 'Tools',
    other: 'Other Equipment',
  }

  return typeLabels[type] || type
}

export function formatCondition(condition: EquipmentCondition | null): string {
  if (!condition) return 'Unknown'

  const conditionLabels: Record<EquipmentCondition, string> = {
    excellent: 'Excellent',
    good: 'Good',
    fair: 'Fair',
    poor: 'Poor',
    needs_repair: 'Needs Repair',
    non_functional: 'Non-Functional',
  }

  return conditionLabels[condition] || condition
}

export function formatStatus(status: EquipmentStatus | null): string {
  if (!status) return 'Unknown'

  const statusLabels: Record<EquipmentStatus, string> = {
    available: 'Available',
    checked_out: 'Checked Out',
    reserved: 'Reserved',
    in_maintenance: 'In Maintenance',
    damaged: 'Damaged',
    lost: 'Lost',
    retired: 'Retired',
  }

  return statusLabels[status] || status
}

export function getStatusColor(status: EquipmentStatus | CheckoutStatus | null): string {
  if (!status) return 'bg-earth-100 text-earth-700 dark:text-earth-200'

  const colors: Record<string, string> = {
    available: 'bg-status-success-100 text-status-success-700',
    checked_out: 'bg-earth-100 text-lsc-rose',
    reserved: 'bg-category-100 text-category-700',
    in_maintenance: 'bg-status-warning-100 text-status-warning-700',
    damaged: 'bg-status-warning-100 text-status-warning-700',
    retired: 'bg-earth-100 text-earth-700 dark:text-earth-200',
    lost: 'bg-status-danger-100 text-status-danger-700',
    active: 'bg-earth-100 text-lsc-rose',
    returned: 'bg-status-success-100 text-status-success-700',
    overdue: 'bg-status-danger-100 text-status-danger-700',
  }

  return colors[status] || 'bg-earth-100 text-earth-700 dark:text-earth-200'
}

export function getConditionColor(condition: EquipmentCondition | null): string {
  if (!condition) return 'bg-earth-100 text-earth-700 dark:text-earth-200'

  const colors: Record<EquipmentCondition, string> = {
    excellent: 'bg-status-success-100 text-status-success-700',
    good: 'bg-earth-100 text-lsc-rose',
    fair: 'bg-status-warning-100 text-status-warning-700',
    poor: 'bg-status-warning-100 text-status-warning-700',
    needs_repair: 'bg-status-danger-100 text-status-danger-700',
    non_functional: 'bg-earth-100 text-earth-700 dark:text-earth-200',
  }

  return colors[condition] || 'bg-earth-100 text-earth-700 dark:text-earth-200'
}

export function isCheckoutOverdue(checkout: EquipmentCheckout): boolean {
  if (checkout.status === 'returned') return false
  return new Date(checkout.due_date) < new Date()
}

export function parseAccessories(accessoriesJson: string | null): string[] {
  if (!accessoriesJson) return []
  try {
    const parsed = JSON.parse(accessoriesJson)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return accessoriesJson.split(',').map((s) => s.trim()).filter(Boolean)
  }
}

export { isApiError }
